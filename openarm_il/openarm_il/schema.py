"""Dataset schema helpers for OpenArm ACT demonstrations."""

from __future__ import annotations

import logging
from collections.abc import Mapping

import numpy as np

from openarm_il.config import DatasetSchema

LOGGER = logging.getLogger(__name__)

STATE_DIM = 16
ACTION_DIM = 16
EE_POSE_DIM = 16


def _joint_value(positions: Mapping[str, float], name: str) -> float:
    try:
        return float(positions[name])
    except KeyError as exc:
        raise KeyError(f"missing required joint '{name}'") from exc


def build_state_vector(positions: Mapping[str, float], schema: DatasetSchema) -> np.ndarray:
    values = [_joint_value(positions, name) for name in schema.left_arm_joints]
    values.extend(_joint_value(positions, name) for name in schema.right_arm_joints)

    for gripper_name in [schema.left_gripper_joint, schema.right_gripper_joint]:
        if gripper_name and gripper_name in positions:
            values.append(float(positions[gripper_name]))
        else:
            LOGGER.warning("Gripper joint '%s' is unavailable; using 0.0", gripper_name)
            values.append(0.0)

    state = np.asarray(values, dtype=np.float32)
    if state.shape != (STATE_DIM,):
        raise ValueError(f"observation.state must be shape ({STATE_DIM},), got {state.shape}")
    return state


def build_action_from_next_state(_current_state: np.ndarray, next_state: np.ndarray) -> np.ndarray:
    action = np.asarray(next_state, dtype=np.float32)
    if action.shape != (ACTION_DIM,):
        raise ValueError(f"action must be shape ({ACTION_DIM},), got {action.shape}")
    return action.copy()


def zero_ee_pose() -> np.ndarray:
    return np.zeros(EE_POSE_DIM, dtype=np.float32)


def ensure_vector(name: str, values: np.ndarray, dim: int) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    if array.shape != (dim,):
        raise ValueError(f"{name} must be shape ({dim},), got {array.shape}")
    if np.isnan(array).any():
        raise ValueError(f"{name} contains NaN")
    return array
