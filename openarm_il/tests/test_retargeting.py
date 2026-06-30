import numpy as np

from openarm_il.retargeting import RetargetConfig, retarget_wrist_poses


def test_retargeting_returns_left_and_right_ee_pose_sequences():
    left = np.array([[0, 0, 0, 0, 0, 0, 1], [0.1, 0, 0, 0, 0, 0, 1]], dtype=np.float32)
    right = np.array([[0, 0, 0, 0, 0, 0, 1], [0, 0.1, 0, 0, 0, 0, 1]], dtype=np.float32)
    config = RetargetConfig.default()

    output = retarget_wrist_poses(left, right, config)

    assert output.left_ee_pose.shape == (2, 7)
    assert output.right_ee_pose.shape == (2, 7)
    np.testing.assert_allclose(output.left_ee_pose[0, :3], [0.3, 0.2, 0.25], atol=1e-6)
    np.testing.assert_allclose(output.left_ee_pose[1, :3], [0.4, 0.2, 0.25], atol=1e-6)
    assert output.workspace_violation.shape == (2,)


def test_retargeting_clips_workspace_and_tracks_violation():
    poses = np.array([[0, 0, 0, 0, 0, 0, 1], [10, 0, 0, 0, 0, 0, 1]], dtype=np.float32)
    config = RetargetConfig.default()

    output = retarget_wrist_poses(poses, poses, config)

    assert output.left_ee_pose[1, 0] <= config.left.workspace_max[0]
    assert output.workspace_violation[1] > 0.0
