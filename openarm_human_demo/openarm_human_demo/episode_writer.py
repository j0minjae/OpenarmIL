"""Per-episode mp4 + frame-timestamp CSV writer, independent of ROS."""

from __future__ import annotations

import csv
import os
import re

import cv2

_EPISODE_RE = re.compile(r"^episode_(\d+)\.mp4$")


class EpisodeRecorder:
    """Writes one episode (mp4 + timestamps.csv) at a time to episode_dir."""

    def __init__(self, episode_dir: str, fps: float):
        self.episode_dir = episode_dir
        self.fps = fps
        self.episode_path = None
        self.csv_path = None
        self.frame_count = 0
        self._writer = None
        self._csv_file = None
        self._csv_writer = None

    @property
    def is_recording(self) -> bool:
        return self._writer is not None

    def next_episode_index(self) -> int:
        if not os.path.isdir(self.episode_dir):
            return 1
        max_idx = 0
        for name in os.listdir(self.episode_dir):
            match = _EPISODE_RE.match(name)
            if match:
                max_idx = max(max_idx, int(match.group(1)))
        return max_idx + 1

    def start(self, frame_shape) -> str:
        if self.is_recording:
            raise RuntimeError("EpisodeRecorder is already recording")
        os.makedirs(self.episode_dir, exist_ok=True)
        stem = f"episode_{self.next_episode_index():04d}"
        self.episode_path = os.path.join(self.episode_dir, f"{stem}.mp4")
        self.csv_path = os.path.join(self.episode_dir, f"{stem}_timestamps.csv")

        height, width = frame_shape[0], frame_shape[1]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(self.episode_path, fourcc, self.fps, (width, height))

        self._csv_file = open(self.csv_path, "w", newline="")
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(["frame_idx", "wall_time", "ros_stamp"])

        self.frame_count = 0
        return self.episode_path

    def write_frame(self, frame_bgr, wall_time: float, ros_stamp: float) -> None:
        if not self.is_recording:
            raise RuntimeError("EpisodeRecorder is not recording")
        self._writer.write(frame_bgr)
        self._csv_writer.writerow([self.frame_count, f"{wall_time:.6f}", f"{ros_stamp:.6f}"])
        self.frame_count += 1

    def stop(self):
        """Close the writer/CSV and return (episode_path, frame_count)."""
        episode_path = self.episode_path
        frame_count = self.frame_count
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        if self._csv_file is not None:
            self._csv_file.close()
            self._csv_file = None
        self.episode_path = None
        return episode_path, frame_count
