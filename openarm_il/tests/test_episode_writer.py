import json
from pathlib import Path

import numpy as np

from openarm_il.episode_writer import EpisodeWriter
from openarm_il.schema import STATE_DIM, EE_POSE_DIM


def _rgb(value: int) -> np.ndarray:
    return np.full((4, 6, 3), value, dtype=np.uint8)


def test_episode_writer_creates_required_raw_episode_layout(tmp_path: Path):
    writer = EpisodeWriter(
        output_dir=tmp_path,
        task="handover",
        episode_id="0001",
        episode_index=1,
        camera_names=["chest", "left_wrist", "right_wrist"],
        image_size=(6, 4),
    )

    writer.add_frame(
        timestamp=1.0,
        images={"chest": _rgb(32)},
        observation_state=np.arange(STATE_DIM, dtype=np.float32),
        observation_ee_pose=np.zeros(EE_POSE_DIM, dtype=np.float32),
        action=np.ones(STATE_DIM, dtype=np.float32),
    )
    episode_dir = writer.close(metadata_extra={"operator": "test"})

    assert (episode_dir / "metadata.json").exists()
    assert (episode_dir / "data.jsonl").exists()
    assert (episode_dir / "images" / "chest" / "000000.png").exists()
    assert (episode_dir / "images" / "left_wrist" / "000000.png").exists()
    assert (episode_dir / "arrays" / "observation_state.npy").exists()
    assert (episode_dir / "arrays" / "observation_ee_pose.npy").exists()
    assert (episode_dir / "arrays" / "action.npy").exists()
    assert (episode_dir / "arrays" / "timestamps.npy").exists()

    row = json.loads((episode_dir / "data.jsonl").read_text().splitlines()[0])
    assert row["sample_type"] == "real"
    assert row["confidence"] == 1.0
    assert row["task"] == "handover"
    assert row["images"]["left_wrist"] == "images/left_wrist/000000.png"

    state = np.load(episode_dir / "arrays" / "observation_state.npy")
    action = np.load(episode_dir / "arrays" / "action.npy")
    assert state.shape == (1, STATE_DIM)
    assert action.shape == (1, STATE_DIM)


def test_episode_writer_zero_pads_missing_optional_wrist_image(tmp_path: Path):
    writer = EpisodeWriter(
        output_dir=tmp_path,
        task="handover",
        episode_id="0002",
        episode_index=2,
        camera_names=["chest", "left_wrist"],
        image_size=(6, 4),
    )

    writer.add_frame(
        timestamp=1.0,
        images={"chest": _rgb(128)},
        observation_state=np.zeros(STATE_DIM, dtype=np.float32),
        observation_ee_pose=np.zeros(EE_POSE_DIM, dtype=np.float32),
        action=np.zeros(STATE_DIM, dtype=np.float32),
    )
    episode_dir = writer.close()

    from PIL import Image

    wrist = np.asarray(Image.open(episode_dir / "images" / "left_wrist" / "000000.png"))
    assert wrist.shape == (4, 6, 3)
    assert int(wrist.sum()) == 0
