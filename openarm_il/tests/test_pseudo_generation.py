import json
from pathlib import Path

import numpy as np

from openarm_il.hand_pose_schema import write_hand_pose_episode
from openarm_il.pseudo_generator import generate_pseudo_episode
from openarm_il.pseudo_validator import validate_pseudo_dataset


def _write_human_episode(root: Path) -> Path:
    from PIL import Image

    episode = root / "raw_human" / "handover" / "episode_0001"
    frames = episode / "frames"
    frames.mkdir(parents=True)
    for index in range(3):
        Image.fromarray(np.full((12, 16, 3), index * 40, dtype=np.uint8), mode="RGB").save(frames / f"{index:06d}.png")
    np.save(episode / "timestamps.npy", np.array([0.0, 0.1, 0.2], dtype=np.float64))
    metadata = {
        "task": "handover",
        "episode_id": "0001",
        "fps": 10,
        "width": 16,
        "height": 12,
        "num_frames": 3,
        "camera": "synthetic",
        "data_type": "human_rgb",
    }
    (episode / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return episode


def _write_hand_pose(root: Path) -> Path:
    keypoints = [[float(i) * 0.01, 0.0, 0.0] for i in range(21)]
    rows = []
    for index in range(3):
        rows.append(
            {
                "timestamp": float(index) * 0.1,
                "frame_index": index,
                "left": {
                    "wrist_pose": [0.01 * index, 0, 0, 0, 0, 0, 1],
                    "keypoints": keypoints,
                    "confidence": 0.9,
                },
                "right": {
                    "wrist_pose": [0, -0.01 * index, 0, 0, 0, 0, 1],
                    "keypoints": keypoints,
                    "confidence": 0.8,
                },
            }
        )
    precomputed = root / "precomputed.jsonl"
    precomputed.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return write_hand_pose_episode(precomputed, root / "hand_pose" / "handover" / "episode_0001")


def test_pseudo_generation_writes_valid_pseudo_episode(tmp_path: Path):
    human_episode = _write_human_episode(tmp_path)
    hand_pose = _write_hand_pose(tmp_path)

    episode_dir = generate_pseudo_episode(
        human_episode_dir=human_episode,
        hand_pose_dir=hand_pose,
        output_dir=tmp_path / "raw_pseudo",
        task="handover",
        episode_id="0001",
    )

    report = validate_pseudo_dataset(episode_dir)
    rows = [json.loads(line) for line in (episode_dir / "data.jsonl").read_text().splitlines()]
    state = np.load(episode_dir / "arrays" / "observation_state.npy")
    action = np.load(episode_dir / "arrays" / "action.npy")
    confidence = np.load(episode_dir / "arrays" / "confidence.npy")

    assert report.ok
    assert rows[0]["sample_type"] == "pseudo"
    assert state.shape == (3, 16)
    assert action.shape == (3, 16)
    assert np.all(state == 0.0)
    assert np.all((confidence >= 0.0) & (confidence <= 1.0))
    assert (episode_dir / "images" / "left_wrist" / "000000.png").exists()
