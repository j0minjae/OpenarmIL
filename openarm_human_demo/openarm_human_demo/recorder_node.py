"""ROS2 node for headless human-demonstration video recording.

Toggles recording with a global space-bar hotkey (via pynput, works regardless
of window focus) so an operator can start/stop without looking at a screen.
Quits on 'q' or ESC. Feedback is a terminal bell by default; --monitor shows a
short post-episode preview instead of a live camera feed.
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
from sensor_msgs.msg import Image

from openarm_human_demo.episode_writer import EpisodeRecorder


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


class HumanDemoRecorderNode(Node):
    def __init__(self):
        super().__init__("human_demo_recorder")

        self.declare_parameter("image_topic", "/human_camera/color/image_raw")
        self.declare_parameter("task_name", "default_task")
        self.declare_parameter("output_dir", "/home/home/Project/OpenarmIL/datasets/openarm_human_demo")
        self.declare_parameter("fps", 30.0)
        self.declare_parameter("monitor", False)

        image_topic = self.get_parameter("image_topic").value
        task_name = self.get_parameter("task_name").value
        output_dir = os.path.expanduser(self.get_parameter("output_dir").value)
        fps = float(self.get_parameter("fps").value)
        self._monitor = bool(self.get_parameter("monitor").value)

        episode_dir = os.path.join(output_dir, task_name)
        self._recorder = EpisodeRecorder(episode_dir, fps)

        self._bridge = CvBridge()
        self._latest_frame = None

        self._toggle_event = threading.Event()
        self._quit_event = threading.Event()
        self.should_exit = False

        self._sub = self.create_subscription(Image, image_topic, self._on_image, 10)
        self._poll_timer = self.create_timer(0.02, self._poll_events)

        self._listener = keyboard.Listener(on_press=self._on_key_press)
        self._listener.start()

        self.get_logger().info(
            f"Subscribed to '{image_topic}'. Episodes will be saved under '{episode_dir}'. "
            "Press SPACE to start/stop recording, q/ESC to quit."
        )

    def _on_key_press(self, key) -> None:
        action = classify_key(key)
        if action == "toggle":
            self._toggle_event.set()
        elif action == "quit":
            self._quit_event.set()

    def _on_image(self, msg: Image) -> None:
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:  # noqa: BLE001 - log and drop malformed frames
            self.get_logger().error(f"Failed to convert image: {exc}")
            return

        self._latest_frame = frame
        if self._recorder.is_recording:
            ros_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            self._recorder.write_frame(frame, time.time(), ros_stamp)

    def _poll_events(self) -> None:
        if self._toggle_event.is_set():
            self._toggle_event.clear()
            self._toggle_recording()
        if self._quit_event.is_set():
            self._quit_event.clear()
            self._request_shutdown()

    def _toggle_recording(self) -> None:
        if not self._recorder.is_recording:
            if self._latest_frame is None:
                self.get_logger().warning("No frames received yet; cannot start recording.")
                return
            path = self._recorder.start(self._latest_frame.shape)
            _beep(1)
            self.get_logger().info(f"Recording started: {path}")
        else:
            episode_path, frame_count = self._recorder.stop()
            _beep(2)
            self.get_logger().info(f"Episode saved: {episode_path} ({frame_count} frames)")
            if self._monitor and self._latest_frame is not None:
                self._show_preview(self._latest_frame)

    def _show_preview(self, frame) -> None:
        window_name = "episode preview"
        cv2.imshow(window_name, frame)
        cv2.waitKey(1500)
        cv2.destroyWindow(window_name)

    def _request_shutdown(self) -> None:
        if self._recorder.is_recording:
            episode_path, frame_count = self._recorder.stop()
            self.get_logger().info(f"Episode saved: {episode_path} ({frame_count} frames)")
        self.get_logger().info("Shutdown requested.")
        self.should_exit = True

    def destroy_node(self) -> bool:
        if self._recorder.is_recording:
            self._recorder.stop()
        self._listener.stop()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HumanDemoRecorderNode()
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
