"""Passive ROS2 recorder for OpenArm V10 real demonstrations."""

from __future__ import annotations

import argparse
import logging
import sys
import termios
import threading
import time
import tty
from pathlib import Path
from typing import Any

import numpy as np

from openarm_il.action_reader import command_vector
from openarm_il.camera_reader import CameraReader
from openarm_il.config import load_collection_config, load_dataset_schema, load_topic_config
from openarm_il.episode_writer import EpisodeWriter
from openarm_il.fk_solver import FKSolver
from openarm_il.robot_state_reader import joint_state_positions, message_timestamp
from openarm_il.schema import ACTION_DIM, build_action_from_next_state, build_state_vector
from openarm_il.sync_buffer import SyncBuffer, TimestampedItem

LOGGER = logging.getLogger(__name__)


class RealDemoRecorder:
    def __init__(self, args: argparse.Namespace) -> None:
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import Image, JointState
        from std_msgs.msg import Float64MultiArray
        from trajectory_msgs.msg import JointTrajectory

        self.rclpy = rclpy
        self.node = Node("openarm_il_real_demo_recorder")
        self.collection = load_collection_config(args.config)
        self.topics = load_topic_config(args.topics_config)
        self.schema = load_dataset_schema(args.schema_config)
        self.task = args.task or self.collection.task
        self.episode_id = args.episode_id or self.collection.episode_id
        self.output_dir = Path(args.output_dir or self.collection.output_dir).expanduser()
        self.duration = float(args.duration if args.duration is not None else self.collection.duration)
        self.keyboard = bool(args.keyboard)
        self.camera_names = list(self.topics.cameras.keys())
        self.camera_reader = CameraReader()
        self.fk_solver = FKSolver(self.collection.fk)
        self.sync = SyncBuffer(
            required_streams=self.collection.required_streams,
            optional_streams=[stream for stream in self.collection.optional_streams if stream != "actions"] + list(self.topics.actions),
            tolerance_sec=self.collection.sync_tolerance_sec,
        )
        self.writer: EpisodeWriter | None = None
        self.recording = False
        self.cancelled = False
        self._pending: tuple[float, dict[str, np.ndarray], np.ndarray, np.ndarray] | None = None
        self._last_command_action: np.ndarray | None = None

        self.node.create_subscription(JointState, self.topics.joint_states, self._joint_state_cb, 20)
        for camera_name, topic in self.topics.cameras.items():
            self.node.create_subscription(Image, topic, self._camera_cb(camera_name), 10)
        for action_name, topic in self.topics.actions.items():
            msg_type = JointTrajectory if "trajectory" in topic else Float64MultiArray
            self.node.create_subscription(msg_type, topic, self._action_cb(action_name), 10)

        period = 1.0 / float(self.collection.record_rate_hz)
        self.node.create_timer(period, self._timer_cb)

    def _now(self) -> float:
        return float(self.node.get_clock().now().nanoseconds) * 1e-9

    def _joint_state_cb(self, msg: Any) -> None:
        timestamp = message_timestamp(msg, self._now())
        self.sync.add("joint_states", TimestampedItem(timestamp, joint_state_positions(msg)))

    def _camera_cb(self, camera_name: str):
        def callback(msg: Any) -> None:
            timestamp = message_timestamp(msg, self._now())
            self.sync.add(camera_name, TimestampedItem(timestamp, self.camera_reader.to_rgb(msg)))

        return callback

    def _action_cb(self, action_name: str):
        def callback(msg: Any) -> None:
            timestamp = message_timestamp(msg, self._now())
            vector = command_vector(msg)
            self.sync.add(action_name, TimestampedItem(timestamp, vector))
            if vector.size:
                self._last_command_action = self._merge_command_action(action_name, vector)

        return callback

    def _merge_command_action(self, action_name: str, vector: np.ndarray) -> np.ndarray:
        action = np.zeros(ACTION_DIM, dtype=np.float32) if self._last_command_action is None else self._last_command_action.copy()
        if action_name == "left_arm":
            action[: min(7, vector.size)] = vector[:7]
        elif action_name == "right_arm":
            action[7 : 7 + min(7, vector.size)] = vector[:7]
        elif action_name == "left_gripper" and vector.size:
            action[14] = vector[0]
        elif action_name == "right_gripper" and vector.size:
            action[15] = vector[0]
        return action

    def start(self) -> None:
        self.writer = EpisodeWriter(
            output_dir=self.output_dir,
            task=self.task,
            episode_id=self.episode_id,
            episode_index=int(str(self.episode_id).lstrip("0") or "0"),
            camera_names=self.camera_names,
            image_size=(self.collection.image.width, self.collection.image.height),
        )
        self.recording = True
        self.node.get_logger().info(f"recording started: task={self.task} episode={self.episode_id}")

    def stop(self) -> Path | None:
        self.recording = False
        if self.writer is None:
            return None
        if self._pending is not None:
            timestamp, images, state, ee_pose = self._pending
            action = self._last_command_action if self.collection.action_source == "command" and self._last_command_action is not None else state
            self.writer.add_frame(timestamp, images, state, ee_pose, action)
            self._pending = None
        path = self.writer.close(metadata_extra={"action_source": self.collection.action_source, "sync_dropped_frames": self.sync.dropped_count})
        self.node.get_logger().info(f"recording saved: {path}")
        return path

    def cancel(self) -> None:
        self.cancelled = True
        self.recording = False
        if self.writer is not None:
            self.writer.cancel()
        self.node.get_logger().warning("recording cancelled")

    def _timer_cb(self) -> None:
        if not self.recording or self.writer is None:
            return
        now = self._now()
        sample = self.sync.get_synchronized_sample(now)
        if sample is None:
            return
        try:
            state = build_state_vector(sample.items["joint_states"].data, self.schema)
        except Exception as exc:
            self.node.get_logger().warning(f"dropping frame due to invalid joint state: {exc}")
            return
        images = {name: sample.items[name].data for name in self.camera_names if name in sample.items}
        ee_pose = self.fk_solver.compute(state)

        if self.collection.action_source == "command" and self._last_command_action is not None:
            action = self._last_command_action
            self.writer.add_frame(sample.timestamp, images, state, ee_pose, action)
            return

        if self._pending is not None:
            pending_timestamp, pending_images, pending_state, pending_ee_pose = self._pending
            action = build_action_from_next_state(pending_state, state)
            self.writer.add_frame(pending_timestamp, pending_images, pending_state, pending_ee_pose, action)
        self._pending = (sample.timestamp, images, state, ee_pose)

    def run(self) -> int:
        if self.keyboard:
            thread = threading.Thread(target=self._keyboard_loop, daemon=True)
            thread.start()
        else:
            self.start()

        start_time = time.monotonic()
        try:
            while self.rclpy.ok() and not self.cancelled:
                self.rclpy.spin_once(self.node, timeout_sec=0.1)
                if not self.keyboard and time.monotonic() - start_time >= self.duration:
                    break
                if self.keyboard and not self.recording and self.writer is not None:
                    break
        finally:
            if not self.cancelled and self.writer is not None:
                self.stop()
            self.node.destroy_node()
        return 1 if self.cancelled else 0

    def _keyboard_loop(self) -> None:
        print("Keyboard controls: s=start, q=stop/save, x=cancel")
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                char = sys.stdin.read(1)
                if char == "s" and not self.recording:
                    self.start()
                elif char == "q":
                    self.recording = False
                    break
                elif char == "x":
                    self.cancel()
                    break
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect passive OpenArm V10 bimanual real demonstrations.")
    parser.add_argument("--task")
    parser.add_argument("--episode-id")
    parser.add_argument("--duration", type=float)
    parser.add_argument("--output-dir")
    parser.add_argument("--keyboard", action="store_true")
    parser.add_argument("--config")
    parser.add_argument("--topics-config")
    parser.add_argument("--schema-config")
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        import rclpy
    except Exception as exc:
        raise SystemExit(f"rclpy is required for real demo collection: {exc}")

    args = build_arg_parser().parse_args()
    rclpy.init()
    recorder = RealDemoRecorder(args)
    try:
        return recorder.run()
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
