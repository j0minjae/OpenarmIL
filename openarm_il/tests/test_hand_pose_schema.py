import json
from pathlib import Path

import numpy as np

from openarm_il.hand_pose_loader import load_hand_pose_episode
from openarm_il.hand_pose_schema import HandPoseFrame, write_hand_pose_episode


def test_precomputed_hand_pose_loads_standard_arrays(tmp_path: Path):
    precomputed = tmp_path / "pose.jsonl"
    keypoints = [[float(i), 0.0, 0.0] for i in range(21)]
    rows = [
        {
            "timestamp": 0.0,
            "frame_index": 0,
            "left": {"wrist_pose": [0, 0, 0, 0, 0, 0, 1], "keypoints": keypoints, "confidence": 0.9},
            "right": {"wrist_pose": [1, 0, 0, 0, 0, 0, 1], "keypoints": keypoints, "confidence": 0.8},
        },
        {
            "timestamp": 0.1,
            "frame_index": 1,
            "left": None,
            "right": {"wrist_pose": [1, 1, 0, 0, 0, 0, 1], "keypoints": keypoints, "confidence": 0.7},
        },
    ]
    precomputed.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    episode_dir = write_hand_pose_episode(precomputed, tmp_path / "hand_pose" / "handover" / "episode_0001")
    episode = load_hand_pose_episode(episode_dir)

    assert episode.left_wrist_pose.shape == (2, 7)
    assert episode.right_wrist_pose.shape == (2, 7)
    assert episode.left_keypoints.shape == (2, 21, 3)
    np.testing.assert_allclose(episode.right_confidence, [0.8, 0.7], atol=1e-6)
    assert np.isnan(episode.left_wrist_pose[1]).all()
    assert episode.left_confidence[1] == 0.0
    assert (episode_dir / "hand_pose.jsonl").exists()


def test_hand_pose_frame_serializes_missing_hand_as_null():
    frame = HandPoseFrame(timestamp=0.0, frame_index=0, left=None, right=None)

    row = frame.to_json()

    assert row["left"] is None
    assert row["right"] is None
