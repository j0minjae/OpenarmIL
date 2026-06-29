#!/usr/bin/env python3
"""ROS2 teleop node for OpenArm VR teleoperation.

Mirrors openarmx_teleop_vr_node.py but uses openarm_ prefix joints directly.
"""

import threading

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float32, Float64MultiArray

from .ik_solver import IKConfig, PositionIKSolver
from .teleop_core import TeleopCore


class OpenArmTeleopNode(Node):
    LEFT = 0
    RIGHT = 1
    ARM_DOF = 7
    GRIPPER_MAX_M = 0.04

    def __init__(self):
        super().__init__("openarm_teleop_node")
        self.cb_group = ReentrantCallbackGroup()

        # --- Parameters ---
        self.declare_parameter("urdf_path", "")
        self.declare_parameter("left_ee_frame", "openarm_left_joint7")
        self.declare_parameter("right_ee_frame", "openarm_right_joint7")
        self.declare_parameter("control_rate", 100.0)
        self.declare_parameter("grip_threshold", 0.5)

        # IK parameters
        self.declare_parameter("ik.damping", 0.05)
        self.declare_parameter("ik.position_weight", 50.0)
        self.declare_parameter("ik.rotation_weight", 1.0)

        # Null-space
        self.declare_parameter("null_space.joint_regularization_weight", 0.2)
        self.declare_parameter("null_space.joint3_regularization_weight", 0.05)
        self.declare_parameter("null_space.joint4_regularization_weight", 0.12)
        self.declare_parameter("null_space.q_home", [0.0] * 14)

        # Step limiting (per joint, degrees)
        for i in range(1, 8):
            self.declare_parameter(f"max_step_deg_joint{i}", 4.0)
            self.declare_parameter(f"fast_max_step_deg_joint{i}", 10.0)
            self.declare_parameter(f"step_threshold_deg_joint{i}", 10.0)

        # Filter
        self.declare_parameter("q_filter_weights", [0.4, 0.3, 0.2, 0.1])

        # Button motion
        self.declare_parameter("button_motion_step_deg", 0.5)
        self.declare_parameter("button_motion_done_tolerance_deg", 1.0)

        # --- Load parameters ---
        urdf_path = self.get_parameter("urdf_path").value
        if not urdf_path:
            self.get_logger().error("urdf_path not provided")
            raise ValueError("urdf_path is required")

        control_rate = float(self.get_parameter("control_rate").value)
        grip_threshold = float(self.get_parameter("grip_threshold").value)

        ik_config = IKConfig(
            damping=float(self.get_parameter("ik.damping").value),
            position_weight=float(self.get_parameter("ik.position_weight").value),
            rotation_weight=float(self.get_parameter("ik.rotation_weight").value),
            joint_regularization_weight=float(self.get_parameter("null_space.joint_regularization_weight").value),
            joint3_regularization_weight=float(self.get_parameter("null_space.joint3_regularization_weight").value),
            joint4_regularization_weight=float(self.get_parameter("null_space.joint4_regularization_weight").value),
            q_home=np.array(self.get_parameter("null_space.q_home").value, dtype=np.float64),
        )

        left_ee = self.get_parameter("left_ee_frame").value
        right_ee = self.get_parameter("right_ee_frame").value

        # --- IK Solver + Teleop Core ---
        ik_solver = PositionIKSolver(urdf_path, left_ee, right_ee, config=ik_config)
        self.get_logger().info(f"IK solver loaded: nq={ik_solver.nq} EE=[{left_ee}, {right_ee}]")

        q_filter_weights = self.get_parameter("q_filter_weights").value
        self.core = TeleopCore(ik_solver, grip_threshold, q_filter_weights, logger=self.get_logger())

        # Step limiting
        self.max_step_rad = np.zeros(14)
        self.fast_max_step_rad = np.zeros(14)
        self.step_threshold_rad = np.zeros(14)
        for i in range(7):
            self.max_step_rad[i] = np.deg2rad(float(self.get_parameter(f"max_step_deg_joint{i+1}").value))
            self.max_step_rad[i + 7] = self.max_step_rad[i]
            self.fast_max_step_rad[i] = np.deg2rad(float(self.get_parameter(f"fast_max_step_deg_joint{i+1}").value))
            self.fast_max_step_rad[i + 7] = self.fast_max_step_rad[i]
            self.step_threshold_rad[i] = np.deg2rad(float(self.get_parameter(f"step_threshold_deg_joint{i+1}").value))
            self.step_threshold_rad[i + 7] = self.step_threshold_rad[i]

        self.is_full_speed = False

        # Button motion
        self.button_motion_step_rad = np.deg2rad(float(self.get_parameter("button_motion_step_deg").value))
        self.button_motion_tolerance_rad = np.deg2rad(float(self.get_parameter("button_motion_done_tolerance_deg").value))
        self.button_motion_active = False
        self.button_motion_name = None
        self.button_motion_target_q = None
        self.button_motion_command_q = None
        self.button_target_reached_count = 0
        self.button_lock = threading.Lock()
        self.pending_go_home = False
        self.pending_hands_up = False
        self.prev_button_b = False
        self.prev_button_y = False

        # Joint state
        self.joint_positions = {}
        self.joint_names = [
            f"openarm_{side}_joint{i}" for side in ["left", "right"] for i in range(1, 8)
        ]

        # Finger positions for gripper hold
        self.finger_positions = {"left": 0.0, "right": 0.0}

        # Control lock
        self.control_lock = threading.Lock()

        # --- ROS interfaces ---
        self._setup_subscriptions()
        self._setup_publishers()

        self.timer = self.create_timer(1.0 / control_rate, self._control_loop, callback_group=self.cb_group)
        self.get_logger().info(f"OpenArm teleop node ready ({control_rate} Hz, grip_threshold={grip_threshold})")

    def _setup_subscriptions(self):
        p = lambda t: self.create_subscription(PoseStamped, t, lambda m, idx=None: None, 10, callback_group=self.cb_group)

        self.create_subscription(PoseStamped, "/pico_left_controller/pose",
            lambda m: self._pose_cb(self.LEFT, m), 10, callback_group=self.cb_group)
        self.create_subscription(PoseStamped, "/pico_right_controller/pose",
            lambda m: self._pose_cb(self.RIGHT, m), 10, callback_group=self.cb_group)
        self.create_subscription(Float32, "/pico_left_controller/grip",
            lambda m: self.core.update_grip(self.LEFT, m.data), 10, callback_group=self.cb_group)
        self.create_subscription(Float32, "/pico_right_controller/grip",
            lambda m: self.core.update_grip(self.RIGHT, m.data), 10, callback_group=self.cb_group)
        self.create_subscription(Float32, "/pico_left_controller/trigger",
            lambda m: self.core.update_trigger(self.LEFT, m.data), 10, callback_group=self.cb_group)
        self.create_subscription(Float32, "/pico_right_controller/trigger",
            lambda m: self.core.update_trigger(self.RIGHT, m.data), 10, callback_group=self.cb_group)
        self.create_subscription(Float32, "/pico_left_controller/rate",
            lambda m: self._rate_cb(m), 10, callback_group=self.cb_group)
        self.create_subscription(Bool, "/pico_right_controller/button_b",
            lambda m: self._button_cb("b", m), 10, callback_group=self.cb_group)
        self.create_subscription(Bool, "/pico_left_controller/button_y",
            lambda m: self._button_cb("y", m), 10, callback_group=self.cb_group)
        self.create_subscription(JointState, "/joint_states",
            self._joint_state_cb, 10, callback_group=self.cb_group)

    def _setup_publishers(self):
        self.left_cmd_pub = self.create_publisher(Float64MultiArray, "/left_forward_position_controller/commands", 10)
        self.right_cmd_pub = self.create_publisher(Float64MultiArray, "/right_forward_position_controller/commands", 10)

    # --- Callbacks ---

    def _pose_cb(self, arm_idx, msg: PoseStamped):
        pos = np.array([msg.pose.position.x, msg.pose.position.y, msg.pose.position.z])
        quat = (msg.pose.orientation.x, msg.pose.orientation.y, msg.pose.orientation.z, msg.pose.orientation.w)
        self.core.update_vr_pose(arm_idx, pos, quat)

    def _rate_cb(self, msg: Float32):
        self.is_full_speed = msg.data >= 0.999

    def _button_cb(self, name, msg: Bool):
        with self.button_lock:
            if name == "b":
                if msg.data and not self.prev_button_b:
                    self.pending_go_home = True
                self.prev_button_b = msg.data
            elif name == "y":
                if msg.data and not self.prev_button_y:
                    self.pending_hands_up = True
                self.prev_button_y = msg.data

    def _joint_state_cb(self, msg: JointState):
        if not msg.name or not msg.position:
            return

        q = np.zeros(14)
        for i, name in enumerate(self.joint_names):
            if name in msg.name:
                idx = msg.name.index(name)
                if idx < len(msg.position):
                    q[i] = msg.position[idx]
            else:
                return

        self.core.update_joint_states(q)

        for side in ["left", "right"]:
            fname = f"openarm_{side}_finger_joint1"
            if fname in msg.name:
                idx = msg.name.index(fname)
                if idx < len(msg.position):
                    self.finger_positions[side] = msg.position[idx]

    # --- Control loop ---

    def _control_loop(self):
        if not self.control_lock.acquire(blocking=False):
            return
        try:
            self._process_button_events()
            if self.button_motion_active:
                self._run_button_motion()
                return

            result = self.core.step()
            if result.target_q is None:
                return

            command_q = self._limit_joint_step(result.target_q, self.core.joint_q)

            left_gripper = self.core.arms[self.LEFT].trigger_value * self.GRIPPER_MAX_M if result.left_active else self.finger_positions["left"]
            right_gripper = self.core.arms[self.RIGHT].trigger_value * self.GRIPPER_MAX_M if result.right_active else self.finger_positions["right"]

            self._publish_commands(command_q, left_gripper, right_gripper)
        except Exception as e:
            self.get_logger().error(f"Control loop error: {e}")
        finally:
            self.control_lock.release()

    def _limit_joint_step(self, target_q, current_q):
        max_s = self.fast_max_step_rad if self.is_full_speed else self.max_step_rad
        command = np.copy(current_q)
        for i in range(14):
            delta = target_q[i] - current_q[i]
            if abs(delta) > self.step_threshold_rad[i]:
                delta = np.clip(delta, -max_s[i], max_s[i])
            command[i] = current_q[i] + delta
        return command

    def _publish_commands(self, command_q, left_gripper, right_gripper):
        left_msg = Float64MultiArray()
        left_msg.data = list(command_q[:7]) + [float(left_gripper)]
        self.left_cmd_pub.publish(left_msg)

        right_msg = Float64MultiArray()
        right_msg.data = list(command_q[7:14]) + [float(right_gripper)]
        self.right_cmd_pub.publish(right_msg)

    # --- Button motion ---

    def _process_button_events(self):
        with self.button_lock:
            go_home = self.pending_go_home
            hands_up = self.pending_hands_up
            self.pending_go_home = False
            self.pending_hands_up = False

        if go_home:
            self._start_button_motion("go_home", np.zeros(14))
        if hands_up:
            target = np.zeros(14)
            target[3] = min(2.0, float(self.core.ik.q_upper[3]))
            target[10] = min(2.0, float(self.core.ik.q_upper[10]))
            self._start_button_motion("hands_up", target)

    def _start_button_motion(self, name, target_q):
        self.button_motion_active = True
        self.button_motion_name = name
        self.button_motion_target_q = np.asarray(target_q, dtype=np.float64)
        self.button_motion_command_q = self.core.joint_q.copy()
        self.button_target_reached_count = 0
        self.get_logger().info(f"Starting button motion '{name}'")

    def _run_button_motion(self):
        if not self.core.joint_received:
            return

        # Cancel if grip override
        for arm in self.core.arms:
            if arm.grip_value > self.core.grip_threshold and arm.vr_pose_received:
                self.button_motion_active = False
                self.get_logger().info(f"Button motion '{self.button_motion_name}' cancelled: grip override")
                return

        target = self.button_motion_target_q
        cmd = self.button_motion_command_q
        step = self.button_motion_step_rad

        for i in range(14):
            delta = target[i] - cmd[i]
            cmd[i] += np.clip(delta, -step, step)

        max_err = float(np.max(np.abs(target - self.core.joint_q)))
        if max_err <= self.button_motion_tolerance_rad:
            self.button_target_reached_count += 1
        else:
            self.button_target_reached_count = 0

        self._publish_commands(cmd, self.finger_positions["left"], self.finger_positions["right"])
        self.button_motion_command_q = cmd

        if self.button_target_reached_count >= 5:
            self.button_motion_active = False
            self.get_logger().info(f"Button motion '{self.button_motion_name}' done")


def main(args=None):
    rclpy.init(args=args)
    node = OpenArmTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
