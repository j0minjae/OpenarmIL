"""Pseudo episode visualization."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def visualize_pseudo_episode(episode_dir: str | Path, save_dir: str | Path | None = None, show: bool = False) -> Path | None:
    import matplotlib

    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(episode_dir).expanduser()
    out = Path(save_dir).expanduser() if save_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    timestamps = np.load(root / "arrays" / "timestamps.npy")
    ee_pose = np.load(root / "arrays" / "observation_ee_pose.npy")
    actions = np.load(root / "arrays" / "action.npy")
    confidence = np.load(root / "arrays" / "confidence.npy")
    terms_path = root / "arrays" / "uncertainty_terms.npy"
    terms = np.load(terms_path) if terms_path.exists() else None

    rows = 5 if terms is not None else 4
    fig, axes = plt.subplots(rows, 1, figsize=(12, 12), sharex=True)
    axes[0].plot(timestamps, ee_pose[:, :3], label=["left_x", "left_y", "left_z"])
    axes[0].plot(timestamps, ee_pose[:, 7:10], linestyle="--", label=["right_x", "right_y", "right_z"])
    axes[0].set_title("pseudo EE trajectory")
    axes[0].legend(loc="upper right")
    axes[1].plot(timestamps, ee_pose[:, 14:16])
    axes[1].set_title("pseudo gripper")
    axes[2].plot(timestamps, actions)
    axes[2].set_title("pseudo action")
    axes[3].plot(timestamps, confidence)
    axes[3].set_ylim(-0.05, 1.05)
    axes[3].set_title("confidence")
    if terms is not None:
        axes[4].plot(timestamps, terms, label=["tracking", "ik", "workspace", "temporal"])
        axes[4].set_title("uncertainty terms")
        axes[4].legend(loc="upper right")
    axes[-1].set_xlabel("time [s]")
    fig.tight_layout()
    if out:
        fig.savefig(out / "pseudo_summary.png")
    if show:
        plt.show()
    plt.close(fig)
    return out
