from pathlib import Path

import numpy as np

from openarm_il.episode_writer import EpisodeWriter
from openarm_il.schema import EE_POSE_DIM, STATE_DIM
from openarm_il.validator import validate_raw_dataset


def _write_episode(tmp_path: Path) -> Path:
    writer = EpisodeWriter(
        output_dir=tmp_path,
        task="handover",
        episode_id="0001",
        episode_index=1,
        camera_names=["chest", "left_wrist", "right_wrist"],
        image_size=(6, 4),
    )
    for index in range(3):
        writer.add_frame(
            timestamp=float(index),
            images={"chest": np.full((4, 6, 3), index, dtype=np.uint8)},
            observation_state=np.full(STATE_DIM, index, dtype=np.float32),
            observation_ee_pose=np.zeros(EE_POSE_DIM, dtype=np.float32),
            action=np.full(STATE_DIM, index + 1, dtype=np.float32),
        )
    return writer.close()


def test_validator_accepts_valid_raw_episode(tmp_path: Path):
    episode_dir = _write_episode(tmp_path)

    report = validate_raw_dataset(episode_dir)

    assert report.ok
    assert report.episode_count == 1
    assert report.frame_count == 3
    assert report.errors == []


def test_validator_detects_missing_required_image(tmp_path: Path):
    episode_dir = _write_episode(tmp_path)
    (episode_dir / "images" / "chest" / "000001.png").unlink()

    report = validate_raw_dataset(episode_dir)

    assert not report.ok
    assert any("missing image" in error for error in report.errors)


def test_validator_detects_wrong_action_dimension(tmp_path: Path):
    episode_dir = _write_episode(tmp_path)
    np.save(episode_dir / "arrays" / "action.npy", np.zeros((3, 15), dtype=np.float32))

    report = validate_raw_dataset(episode_dir)

    assert not report.ok
    assert any("action dimension" in error for error in report.errors)
