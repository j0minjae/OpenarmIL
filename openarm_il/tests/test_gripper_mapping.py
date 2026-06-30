import numpy as np

from openarm_il.gripper_mapping import GripperConfig, gripper_from_keypoints


def test_gripper_mapping_bounds_values_between_zero_and_one():
    keypoints = np.zeros((21, 3), dtype=np.float32)
    keypoints[4] = [0.0, 0.0, 0.0]
    keypoints[8] = [0.06, 0.0, 0.0]

    value = gripper_from_keypoints(keypoints, GripperConfig())

    assert 0.0 <= value <= 1.0
    assert abs(value - 0.5) < 1e-6


def test_gripper_mapping_uses_previous_value_for_missing_keypoints():
    keypoints = np.full((21, 3), np.nan, dtype=np.float32)

    value = gripper_from_keypoints(keypoints, GripperConfig(), previous=0.25)

    assert value == 0.25
