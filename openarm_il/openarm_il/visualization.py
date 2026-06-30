"""Headless visualization helpers for raw OpenArm episodes."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def visualize_episode(episode_dir: str | Path, save_dir: str | Path | None = None, show: bool = False) -> Path | None:
    import matplotlib

    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(episode_dir).expanduser()
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    states = np.load(root / "arrays" / "observation_state.npy")
    actions = np.load(root / "arrays" / "action.npy")
    ee_pose = np.load(root / "arrays" / "observation_ee_pose.npy")
    timestamps = np.load(root / "arrays" / "timestamps.npy")

    out = Path(save_dir).expanduser() if save_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    print(json.dumps(metadata, indent=2, sort_keys=True))

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    axes[0].plot(timestamps, states)
    axes[0].set_title("observation.state")
    axes[0].set_ylabel("rad / gripper")
    axes[1].plot(timestamps, actions)
    axes[1].set_title("action")
    axes[1].set_ylabel("target")
    axes[2].plot(timestamps, ee_pose)
    axes[2].set_title("observation.ee_pose")
    axes[2].set_xlabel("time [s]")
    fig.tight_layout()
    if out:
        fig.savefig(out / "trajectories.png")
    if show:
        plt.show()
    plt.close(fig)

    rows = [json.loads(line) for line in (root / "data.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if rows and out:
        from PIL import Image

        image_path = root / rows[0]["images"]["chest"]
        Image.open(image_path).save(out / "first_chest_frame.png")
    return out
