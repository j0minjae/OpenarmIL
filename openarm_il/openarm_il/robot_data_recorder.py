"""ROS2 node for headless teleop demonstration recording.

Records the 3 OpenArm bimanual cameras (chest/left_wrist/right_wrist) plus raw
CAN-FD joint-angle feedback (/joint_states) into per-episode mp4 + CSV files.
Toggled with a global space-bar hotkey (via pynput, works regardless of window
focus) so an operator driving the robot with a Quest3 headset can start/stop
without looking at a terminal. Quits on 'q' or ESC.

EEF pose and any derived action/gripper-state values are intentionally not
computed here -- only raw joint angles are recorded, with per-stream
timestamps for post-hoc time alignment. See teleop_episode_writer.py.
"""

from __future__ import annotations

import os
import sys
import threading
import time

import cv2
import rclpy
from cv_bridge import CvBridge
from pynput import keyboard
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, JointState

from openarm_il.teleop_episode_writer import JOINT_COLUMNS, TeleopEpisode

_DEFAULT_CAMERA_TOPICS = {
    "chest_camera": "/chest_camera/color/image_raw",
    "left_wrist_camera": "/left_wrist_camera/color/image_raw",
    "right_wrist_camera": "/right_wrist_camera/color/image_raw",
}

# Maps JOINT_COLUMNS (teleop_episode_writer.py) to the real joint_states names
# published by openarm_bimanual_controllers.yaml.
_JOINT_NAME_MAP = {
    "left_joint1": "openarm_left_joint1",
    "left_joint2": "openarm_left_joint2",
    "left_joint3": "openarm_left_joint3",
    "left_joint4": "openarm_left_joint4",
    "left_joint5": "openarm_left_joint5",
    "left_joint6": "openarm_left_joint6",
    "left_joint7": "openarm_left_joint7",
    "left_gripper": "openarm_left_finger_joint1",
    "right_joint1": "openarm_right_joint1",
    "right_joint2": "openarm_right_joint2",
    "right_joint3": "openarm_right_joint3",
    "right_joint4": "openarm_right_joint4",
    "right_joint5": "openarm_right_joint5",
    "right_joint6": "openarm_right_joint6",
    "right_joint7": "openarm_right_joint7",
    "right_gripper": "openarm_right_finger_joint1",
}


def _beep(times: int = 1, gap: float = 0.15) -> None:
    for i in range(times):
        sys.stdout.write("\a")
        sys.stdout.flush()
        if i + 1 < times:
            time.sleep(gap)


def classify_key(key) -> str | None:
    """Map a pynput key event to an action, independent of ROS/X11 for testability."""
    if key == keyboard.Key.space:
        return "toggle"
    if key == keyboard.Key.esc:
        return "quit"
    if getattr(key, "char", None) == "q":
        return "quit"
    return None


class RobotDataRecorderNode(Node):
    def __init__(self):
        super().__init__("robot_data_recorder")

        self.declare_parameter("task_name", "default_task")
        self.declare_parameter("output_dir", "~/datasets/openarm_il/raw_teleop")
        self.declare_parameter("fps", 30.0)  # must match the cameras' real publish rate; verify with 'ros2 topic hz'
        self.declare_parameter("monitor", False)
        self.declare_parameter("joint_states_topic", "/joint_states")
        for camera_name, default_topic in _DEFAULT_CAMERA_TOPICS.items():
            self.declare_parameter(f"{camera_name}_topic", default_topic)

        task_name = self.get_parameter("task_name").value
        output_dir = os.path.expanduser(self.get_parameter("output_dir").value)
        fps = float(self.get_parameter("fps").value)
        self._monitor = bool(self.get_parameter("monitor").value)
        joint_states_topic = self.get_parameter("joint_states_topic").value

        self.camera_names = list(_DEFAULT_CAMERA_TOPICS.keys())
        camera_topics = {name: self.get_parameter(f"{name}_topic").value for name in self.camera_names}

        episode_base_dir = os.path.join(output_dir, task_name)
        self._episode = TeleopEpisode(episode_base_dir, self.camera_names, fps)

        self._bridge = CvBridge()
        self._latest_frames: dict[str, object] = {}
        self._latest_joint_values: list[float] | None = None
        self._latest_joint_stamp: float | None = None

        self._toggle_event = threading.Event()
        self._quit_event = threading.Event()
        self.should_exit = False

        for camera_name, topic in camera_topics.items():
            self.create_subscription(Image, topic, self._make_image_cb(camera_name), qos_profile_sensor_data)
        self.create_subscription(JointState, joint_states_topic, self._on_joint_state, 50)
        self._poll_timer = self.create_timer(0.02, self._poll_events)

        self._listener = keyboard.Listener(on_press=self._on_key_press)
        self._listener.start()

        self.get_logger().info(
            f"Subscribed to cameras {list(camera_topics.values())} and '{joint_states_topic}'. "
            f"Episodes will be saved under '{episode_base_dir}'. "
            "Press SPACE to start/stop recording, q/ESC to quit."
        )

    def _on_key_press(self, key) -> None:
        action = classify_key(key)
        if action == "toggle":
            self._toggle_event.set()
        elif action == "quit":
            self._quit_event.set()

    def _make_image_cb(self, camera_name: str):
        def callback(msg: Image) -> None:
            try:
                frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            except Exception as exc:  # noqa: BLE001 - log and drop malformed frames
                self.get_logger().error(f"Failed to convert image from {camera_name}: {exc}")
                return
            self._latest_frames[camera_name] = frame
            if self._episode.is_recording:
                ros_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
                self._episode.write_camera_frame(camera_name, frame, time.time(), ros_stamp)

        return callback

    def _on_joint_state(self, msg: JointState) -> None:
        name_to_position = dict(zip(msg.name, msg.position))
        try:
            values = [name_to_position[_JOINT_NAME_MAP[column]] for column in JOINT_COLUMNS]
        except KeyError as exc:
            self.get_logger().warning(f"joint_states message missing expected joint {exc}; dropping sample.")
            return
        self._latest_joint_values = values
        ros_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self._latest_joint_stamp = ros_stamp
        if self._episode.is_recording:
            self._episode.write_joint_sample(time.time(), ros_stamp, values)

    def _poll_events(self) -> None:
        if self._toggle_event.is_set():
            self._toggle_event.clear()
            self._toggle_recording()
        if self._quit_event.is_set():
            self._quit_event.clear()
            self._request_shutdown()

    def _toggle_recording(self) -> None:
        if not self._episode.is_recording:
            missing = [name for name in self.camera_names if name not in self._latest_frames]
            if missing or self._latest_joint_values is None:
                self.get_logger().warning(
                    f"Cannot start recording yet; missing frames from {missing or 'none'}"
                    f"{'' if self._latest_joint_values is not None else ' and no joint_states received'}."
                )
                return
            shapes = {name: frame.shape for name, frame in self._latest_frames.items()}
            path = self._episode.start(shapes)
            _beep(1)
            self.get_logger().info(f"Recording started: {path}")
        else:
            episode_path, metadata = self._episode.stop()
            _beep(2)
            self.get_logger().info(
                f"Episode saved: {episode_path} "
                f"(camera frames={metadata['camera_frame_counts']}, joint samples={metadata['joint_sample_count']})"
            )
            if self._monitor:
                self._show_preview()

    def _show_preview(self) -> None:
        frame = self._latest_frames.get("chest_camera")
        if frame is None:
            return
        window_name = "episode preview (chest_camera)"
        cv2.imshow(window_name, frame)
        cv2.waitKey(1500)
        cv2.destroyWindow(window_name)

    def _request_shutdown(self) -> None:
        if self._episode.is_recording:
            episode_path, metadata = self._episode.stop()
            self.get_logger().info(
                f"Episode saved: {episode_path} "
                f"(camera frames={metadata['camera_frame_counts']}, joint samples={metadata['joint_sample_count']})"
            )
        self.get_logger().info("Shutdown requested.")
        self.should_exit = True

    def destroy_node(self) -> bool:
        if self._episode.is_recording:
            self._episode.stop()
        self._listener.stop()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RobotDataRecorderNode()
    try:
        while rclpy.ok() and not node.should_exit:
            rclpy.spin_once(node, timeout_sec=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
