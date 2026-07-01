import csv
import json
import os

import numpy as np

from openarm_il.teleop_episode_writer import JOINT_COLUMNS, TeleopEpisode


def test_multi_camera_episode_and_joint_csv(tmp_path):
    base_dir = str(tmp_path / "task")
    cameras = ["chest_camera", "left_wrist_camera", "right_wrist_camera"]
    episode = TeleopEpisode(base_dir, cameras, fps=30.0)

    frame = np.zeros((240, 424, 3), dtype=np.uint8)
    shapes = {name: frame.shape for name in cameras}

    episode_dir = episode.start(shapes)
    assert episode_dir == os.path.join(base_dir, "episode_0001")

    for i in range(5):
        for name in cameras:
            episode.write_camera_frame(name, frame, wall_time=float(i), ros_stamp=float(i) + 0.1)
    for i in range(10):
        episode.write_joint_sample(float(i) * 0.5, float(i) * 0.5 + 0.01, list(range(16)))

    saved_dir, metadata = episode.stop()
    assert saved_dir == episode_dir
    assert metadata["camera_frame_counts"] == {name: 5 for name in cameras}
    assert metadata["joint_sample_count"] == 10
    assert metadata["joint_columns"] == JOINT_COLUMNS

    for name in cameras:
        assert os.path.exists(os.path.join(episode_dir, f"{name}.mp4"))
        with open(os.path.join(episode_dir, f"{name}_timestamps.csv")) as f:
            rows = list(csv.reader(f))
        assert rows[0] == ["frame_idx", "wall_time", "ros_stamp"]
        assert len(rows) - 1 == 5

    with open(os.path.join(episode_dir, "joint_angles.csv")) as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["sample_idx", "wall_time", "ros_stamp"] + JOINT_COLUMNS
    assert len(rows) - 1 == 10

    with open(os.path.join(episode_dir, "metadata.json")) as f:
        assert json.load(f)["episode_index"] == 1


def test_episode_numbering_increments(tmp_path):
    base_dir = str(tmp_path / "task")
    cameras = ["chest_camera"]
    frame = np.zeros((240, 424, 3), dtype=np.uint8)
    shapes = {"chest_camera": frame.shape}

    episode1 = TeleopEpisode(base_dir, cameras, fps=30.0)
    episode1.start(shapes)
    episode1.stop()

    episode2 = TeleopEpisode(base_dir, cameras, fps=30.0)
    path2 = episode2.start(shapes)
    assert path2 == os.path.join(base_dir, "episode_0002")
    episode2.stop()
