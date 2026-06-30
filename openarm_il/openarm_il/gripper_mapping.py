"""Map human hand keypoints to scalar gripper commands."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GripperConfig:
    thumb_tip_index: int = 4
    index_tip_index: int = 8
    d_min: float = 0.02
    d_max: float = 0.10
    invert: bool = False
    default_open: float = 1.0


def gripper_from_keypoints(keypoints: np.ndarray, config: GripperConfig, previous: float | None = None) -> float:
    points = np.asarray(keypoints, dtype=np.float32)
    fallback = config.default_open if previous is None else float(previous)
    if points.ndim != 2 or points.shape[0] <= max(config.thumb_tip_index, config.index_tip_index):
        return fallback
    thumb = points[config.thumb_tip_index]
    index = points[config.index_tip_index]
    if np.isnan(thumb).any() or np.isnan(index).any():
        return fallback
    denom = max(config.d_max - config.d_min, 1e-6)
    value = float(np.clip((np.linalg.norm(thumb - index) - config.d_min) / denom, 0.0, 1.0))
    return 1.0 - value if config.invert else value


def gripper_sequence(keypoints: np.ndarray, config: GripperConfig) -> np.ndarray:
    values = []
    previous = config.default_open
    for frame in keypoints:
        previous = gripper_from_keypoints(frame, config, previous=previous)
        values.append(previous)
    return np.asarray(values, dtype=np.float32)
