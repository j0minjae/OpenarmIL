import csv
import os

import numpy as np

from openarm_human_demo.episode_writer import EpisodeRecorder


def test_episode_numbering_and_frame_count(tmp_path):
    episode_dir = str(tmp_path / "task")
    recorder = EpisodeRecorder(episode_dir, fps=30.0)

    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    path1 = recorder.start(frame.shape)
    assert path1 == os.path.join(episode_dir, "episode_0001.mp4")
    for i in range(5):
        recorder.write_frame(frame, wall_time=float(i), ros_stamp=float(i) + 0.5)
    saved_path, frame_count = recorder.stop()
    assert saved_path == path1
    assert frame_count == 5
    assert os.path.exists(path1)

    csv_path = os.path.join(episode_dir, "episode_0001_timestamps.csv")
    with open(csv_path) as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["frame_idx", "wall_time", "ros_stamp"]
    assert len(rows) - 1 == frame_count

    path2 = recorder.start(frame.shape)
    assert path2 == os.path.join(episode_dir, "episode_0002.mp4")
    recorder.stop()


def test_not_recording_before_start(tmp_path):
    recorder = EpisodeRecorder(str(tmp_path / "task"), fps=30.0)
    assert not recorder.is_recording
