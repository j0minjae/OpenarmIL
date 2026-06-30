"""Load standardized hand-pose episodes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class HandPoseEpisode:
    episode_dir: Path
    left_wrist_pose: np.ndarray
    right_wrist_pose: np.ndarray
    left_keypoints: np.ndarray
    right_keypoints: np.ndarray
    left_confidence: np.ndarray
    right_confidence: np.ndarray
    timestamps: np.ndarray


def load_hand_pose_episode(episode_dir: str | Path) -> HandPoseEpisode:
    root = Path(episode_dir).expanduser()
    arrays = root / "arrays"
    return HandPoseEpisode(
        episode_dir=root,
        left_wrist_pose=np.load(arrays / "left_wrist_pose.npy"),
        right_wrist_pose=np.load(arrays / "right_wrist_pose.npy"),
        left_keypoints=np.load(arrays / "left_keypoints.npy"),
        right_keypoints=np.load(arrays / "right_keypoints.npy"),
        left_confidence=np.load(arrays / "left_confidence.npy"),
        right_confidence=np.load(arrays / "right_confidence.npy"),
        timestamps=np.load(arrays / "timestamps.npy"),
    )
