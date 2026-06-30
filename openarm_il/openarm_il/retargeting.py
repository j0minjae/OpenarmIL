"""Human wrist to OpenArm end-effector retargeting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml


@dataclass(frozen=True)
class ArmRetargetConfig:
    scale: float
    p_ee_init: np.ndarray
    R_align_rpy: np.ndarray
    R_offset_rpy: np.ndarray
    workspace_min: np.ndarray
    workspace_max: np.ndarray


@dataclass(frozen=True)
class RetargetConfig:
    left: ArmRetargetConfig
    right: ArmRetargetConfig
    smoothing_enable: bool = True
    smoothing_window_size: int = 5

    @classmethod
    def default(cls) -> "RetargetConfig":
        return cls(
            left=ArmRetargetConfig(
                scale=1.0,
                p_ee_init=np.array([0.3, 0.2, 0.25], dtype=np.float32),
                R_align_rpy=np.zeros(3, dtype=np.float32),
                R_offset_rpy=np.zeros(3, dtype=np.float32),
                workspace_min=np.array([0.1, -0.5, 0.05], dtype=np.float32),
                workspace_max=np.array([0.7, 0.5, 0.6], dtype=np.float32),
            ),
            right=ArmRetargetConfig(
                scale=1.0,
                p_ee_init=np.array([0.3, -0.2, 0.25], dtype=np.float32),
                R_align_rpy=np.zeros(3, dtype=np.float32),
                R_offset_rpy=np.zeros(3, dtype=np.float32),
                workspace_min=np.array([0.1, -0.5, 0.05], dtype=np.float32),
                workspace_max=np.array([0.7, 0.5, 0.6], dtype=np.float32),
            ),
        )


def _arm_from_dict(data: dict, default: ArmRetargetConfig) -> ArmRetargetConfig:
    return ArmRetargetConfig(
        scale=float(data.get("scale", default.scale)),
        p_ee_init=np.asarray(data.get("p_ee_init", default.p_ee_init), dtype=np.float32),
        R_align_rpy=np.asarray(data.get("R_align_rpy", default.R_align_rpy), dtype=np.float32),
        R_offset_rpy=np.asarray(data.get("R_offset_rpy", default.R_offset_rpy), dtype=np.float32),
        workspace_min=np.asarray(data.get("workspace_min", default.workspace_min), dtype=np.float32),
        workspace_max=np.asarray(data.get("workspace_max", default.workspace_max), dtype=np.float32),
    )


def load_retarget_config(path: str | Path | None) -> RetargetConfig:
    default = RetargetConfig.default()
    if path is None:
        return default
    data = yaml.safe_load(Path(path).expanduser().read_text(encoding="utf-8")) or {}
    smoothing = data.get("smoothing", {})
    return RetargetConfig(
        left=_arm_from_dict(data.get("left", {}), default.left),
        right=_arm_from_dict(data.get("right", {}), default.right),
        smoothing_enable=bool(smoothing.get("enable", default.smoothing_enable)),
        smoothing_window_size=int(smoothing.get("window_size", default.smoothing_window_size)),
    )


@dataclass(frozen=True)
class RetargetedTrajectory:
    left_ee_pose: np.ndarray
    right_ee_pose: np.ndarray
    workspace_violation: np.ndarray


def _retarget_one(wrist_pose: np.ndarray, config: ArmRetargetConfig) -> tuple[np.ndarray, np.ndarray]:
    output = np.zeros_like(wrist_pose, dtype=np.float32)
    violation = np.zeros(wrist_pose.shape[0], dtype=np.float32)
    valid = ~np.isnan(wrist_pose[:, :3]).any(axis=1)
    if not valid.any():
        output[:] = np.nan
        return output, violation
    anchor = wrist_pose[np.where(valid)[0][0], :3]
    previous = np.concatenate([config.p_ee_init, np.array([0, 0, 0, 1], dtype=np.float32)])
    for index, pose in enumerate(wrist_pose):
        if np.isnan(pose).any():
            output[index] = previous
            continue
        position = config.p_ee_init + config.scale * (pose[:3] - anchor)
        clipped = np.clip(position, config.workspace_min, config.workspace_max)
        violation[index] = float(np.linalg.norm(position - clipped))
        output[index, :3] = clipped
        output[index, 3:7] = pose[3:7]
        previous = output[index]
    return output, violation


def retarget_wrist_poses(left_wrist_pose: np.ndarray, right_wrist_pose: np.ndarray, config: RetargetConfig) -> RetargetedTrajectory:
    left, left_violation = _retarget_one(np.asarray(left_wrist_pose, dtype=np.float32), config.left)
    right, right_violation = _retarget_one(np.asarray(right_wrist_pose, dtype=np.float32), config.right)
    return RetargetedTrajectory(
        left_ee_pose=left,
        right_ee_pose=right,
        workspace_violation=np.maximum(left_violation, right_violation),
    )
