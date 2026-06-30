from pathlib import Path

import numpy as np

from openarm_il.config import load_collection_config, load_dataset_schema
from openarm_il.schema import (
    ACTION_DIM,
    EE_POSE_DIM,
    STATE_DIM,
    build_action_from_next_state,
    build_state_vector,
    zero_ee_pose,
)


def test_default_configs_load_from_package_root():
    root = Path(__file__).resolve().parents[1]

    collection = load_collection_config(root / "config" / "real_collection.yaml")
    schema = load_dataset_schema(root / "config" / "dataset_schema.yaml")

    assert collection.action_source == "next_state"
    assert collection.sync_tolerance_sec == 0.05
    assert schema.left_arm_joints[0] == "openarm_left_joint1"
    assert schema.right_arm_joints[-1] == "openarm_right_joint7"


def test_state_vector_uses_configured_joint_order_and_zero_grippers():
    schema = load_dataset_schema(Path(__file__).resolve().parents[1] / "config" / "dataset_schema.yaml")
    names = schema.left_arm_joints + schema.right_arm_joints
    positions = {name: float(index + 1) for index, name in enumerate(names)}

    state = build_state_vector(positions, schema)

    assert state.dtype == np.float32
    assert state.shape == (STATE_DIM,)
    np.testing.assert_array_equal(state[:7], np.arange(1, 8, dtype=np.float32))
    np.testing.assert_array_equal(state[7:14], np.arange(8, 15, dtype=np.float32))
    assert state[14] == 0.0
    assert state[15] == 0.0


def test_next_state_action_generation_is_16d_float32():
    current = np.zeros(STATE_DIM, dtype=np.float32)
    next_state = np.arange(STATE_DIM, dtype=np.float32)

    action = build_action_from_next_state(current, next_state)

    assert action.dtype == np.float32
    assert action.shape == (ACTION_DIM,)
    np.testing.assert_array_equal(action, next_state)


def test_zero_ee_pose_shape():
    ee_pose = zero_ee_pose()

    assert ee_pose.dtype == np.float32
    assert ee_pose.shape == (EE_POSE_DIM,)
    assert float(ee_pose.sum()) == 0.0
