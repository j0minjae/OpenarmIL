import json
from pathlib import Path

import numpy as np

from openarm_il.episode_writer import EpisodeWriter
from openarm_il.lerobot_exporter import export_lerobot_dataset
from openarm_il.schema import EE_POSE_DIM, STATE_DIM


def test_export_lerobot_dataset_writes_local_act_ready_format(tmp_path: Path):
    writer = EpisodeWriter(
        output_dir=tmp_path / "raw_real",
        task="handover",
        episode_id="0001",
        episode_index=1,
        camera_names=["chest", "left_wrist", "right_wrist"],
        image_size=(6, 4),
    )
    writer.add_frame(
        timestamp=0.0,
        images={"chest": np.zeros((4, 6, 3), dtype=np.uint8)},
        observation_state=np.zeros(STATE_DIM, dtype=np.float32),
        observation_ee_pose=np.zeros(EE_POSE_DIM, dtype=np.float32),
        action=np.ones(STATE_DIM, dtype=np.float32),
    )
    writer.close()

    output_dir = export_lerobot_dataset(tmp_path / "raw_real", tmp_path / "lerobot_real")

    meta = json.loads((output_dir / "meta" / "info.json").read_text())
    episodes = json.loads((output_dir / "meta" / "episodes.jsonl").read_text().splitlines()[0])
    frames = (output_dir / "data" / "frames.jsonl").read_text().splitlines()

    assert meta["codebase_version"] == "openarm_il_local_v1"
    assert meta["features"]["observation.state"] == "float32[16]"
    assert episodes["task"] == "handover"
    assert len(frames) == 1
    assert (output_dir / "data" / "handover" / "episode_0001" / "arrays" / "action.npy").exists()
