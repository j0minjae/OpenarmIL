"""Per-episode raw teleop writer: per-camera mp4 + joint-angle CSV + metadata.

This is deliberately separate from ``episode_writer.EpisodeWriter``: that writer's
schema requires ``observation_ee_pose`` and ``action`` per frame, which this raw
teleop collection path does not compute (EEF pose and derived actions are left to
a later post-processing step). Streams here are timestamped independently and
are not resampled onto a shared clock -- alignment happens post-hoc using the
recorded wall_time/ros_stamp columns.
"""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone

import cv2

_EPISODE_RE = re.compile(r"^episode_(\d+)$")

# CSV column order for one joint_states sample; reshapes to (2, 8) as [left_arm, right_arm].
JOINT_COLUMNS = [
    "left_joint1", "left_joint2", "left_joint3", "left_joint4",
    "left_joint5", "left_joint6", "left_joint7", "left_gripper",
    "right_joint1", "right_joint2", "right_joint3", "right_joint4",
    "right_joint5", "right_joint6", "right_joint7", "right_gripper",
]


class _CameraStream:
    def __init__(self, episode_dir: str, camera_name: str, fps: float):
        self._path = os.path.join(episode_dir, f"{camera_name}.mp4")
        self._csv_path = os.path.join(episode_dir, f"{camera_name}_timestamps.csv")
        self._fps = fps
        self._writer = None
        self._csv_file = None
        self._csv_writer = None
        self.frame_count = 0

    def open(self, frame_shape) -> None:
        height, width = frame_shape[0], frame_shape[1]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(self._path, fourcc, self._fps, (width, height))
        self._csv_file = open(self._csv_path, "w", newline="")
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(["frame_idx", "wall_time", "ros_stamp"])

    @property
    def is_open(self) -> bool:
        return self._writer is not None

    def write_frame(self, frame_bgr, wall_time: float, ros_stamp: float) -> None:
        self._writer.write(frame_bgr)
        self._csv_writer.writerow([self.frame_count, f"{wall_time:.6f}", f"{ros_stamp:.6f}"])
        self.frame_count += 1

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        if self._csv_file is not None:
            self._csv_file.close()
            self._csv_file = None


class TeleopEpisode:
    """One episode directory holding N camera streams plus a joint-angle CSV."""

    def __init__(self, base_dir: str, camera_names: list[str], fps: float):
        self.base_dir = base_dir
        self.camera_names = list(camera_names)
        self.fps = fps
        self.episode_dir = None
        self.episode_index = None
        self._cameras: dict[str, _CameraStream] = {}
        self._joint_csv_file = None
        self._joint_csv_writer = None
        self.joint_sample_count = 0

    @property
    def is_recording(self) -> bool:
        return self.episode_dir is not None

    def _next_episode_index(self) -> int:
        if not os.path.isdir(self.base_dir):
            return 1
        max_idx = 0
        for name in os.listdir(self.base_dir):
            match = _EPISODE_RE.match(name)
            if match:
                max_idx = max(max_idx, int(match.group(1)))
        return max_idx + 1

    def start(self, frame_shapes: dict[str, tuple]) -> str:
        if self.is_recording:
            raise RuntimeError("TeleopEpisode is already recording")
        os.makedirs(self.base_dir, exist_ok=True)
        self.episode_index = self._next_episode_index()
        self.episode_dir = os.path.join(self.base_dir, f"episode_{self.episode_index:04d}")
        os.makedirs(self.episode_dir, exist_ok=True)

        self._cameras = {name: _CameraStream(self.episode_dir, name, self.fps) for name in self.camera_names}
        for name, stream in self._cameras.items():
            stream.open(frame_shapes[name])

        self._joint_csv_file = open(os.path.join(self.episode_dir, "joint_angles.csv"), "w", newline="")
        self._joint_csv_writer = csv.writer(self._joint_csv_file)
        self._joint_csv_writer.writerow(["sample_idx", "wall_time", "ros_stamp"] + JOINT_COLUMNS)
        self.joint_sample_count = 0

        return self.episode_dir

    def write_camera_frame(self, camera_name: str, frame_bgr, wall_time: float, ros_stamp: float) -> None:
        self._cameras[camera_name].write_frame(frame_bgr, wall_time, ros_stamp)

    def write_joint_sample(self, wall_time: float, ros_stamp: float, values: list[float]) -> None:
        self._joint_csv_writer.writerow([self.joint_sample_count, f"{wall_time:.6f}", f"{ros_stamp:.6f}"] + list(values))
        self.joint_sample_count += 1

    def stop(self, extra_metadata: dict | None = None) -> tuple[str, dict]:
        episode_dir = self.episode_dir
        frame_counts = {name: stream.frame_count for name, stream in self._cameras.items()}
        for stream in self._cameras.values():
            stream.close()
        if self._joint_csv_file is not None:
            self._joint_csv_file.close()
            self._joint_csv_file = None

        metadata = {
            "episode_index": self.episode_index,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "camera_names": self.camera_names,
            "camera_frame_counts": frame_counts,
            "joint_sample_count": self.joint_sample_count,
            "joint_columns": JOINT_COLUMNS,
            "fps": self.fps,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        with open(os.path.join(episode_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)

        self._cameras = {}
        self.episode_dir = None
        self.episode_index = None
        return episode_dir, metadata
