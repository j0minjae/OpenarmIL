"""Phase 2 IK interface for pseudo demonstration generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from openarm_il.schema import ACTION_DIM


@dataclass(frozen=True)
class IKConfig:
    enable: bool = False
    allow_ik_disabled: bool = True
    invalid_action_fill: str = "zeros"


@dataclass(frozen=True)
class IKResult:
    action: np.ndarray
    valid: np.ndarray
    residual: np.ndarray


def load_ik_config(path: str | Path | None) -> IKConfig:
    if path is None:
        return IKConfig()
    data = yaml.safe_load(Path(path).expanduser().read_text(encoding="utf-8")) or {}
    ik = data.get("ik", data)
    return IKConfig(
        enable=bool(ik.get("enable", False)),
        allow_ik_disabled=bool(data.get("allow_ik_disabled", True)),
        invalid_action_fill=str(data.get("invalid_action_fill", "zeros")),
    )


def solve_pseudo_actions(
    left_ee_pose: np.ndarray,
    right_ee_pose: np.ndarray,
    left_gripper: np.ndarray,
    right_gripper: np.ndarray,
    config: IKConfig | None = None,
) -> IKResult:
    cfg = config or IKConfig()
    count = int(left_ee_pose.shape[0])
    if not cfg.enable:
        if not cfg.allow_ik_disabled:
            raise RuntimeError("IK is disabled and allow_ik_disabled is false")
        action = np.zeros((count, ACTION_DIM), dtype=np.float32)
        action[:, 14] = np.asarray(left_gripper, dtype=np.float32)
        action[:, 15] = np.asarray(right_gripper, dtype=np.float32)
        return IKResult(action=action, valid=np.zeros(count, dtype=bool), residual=np.zeros(count, dtype=np.float32))
    raise NotImplementedError("Numerical OpenArm IK is not implemented in Phase 2; set ik.enable=false to use invalid zero joint actions.")
