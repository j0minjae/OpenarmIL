"""Validation for Phase 2 pseudo demonstrations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from openarm_il.schema import ACTION_DIM, EE_POSE_DIM, STATE_DIM
from openarm_il.validator import ValidationReport


def _episode_dirs(path: Path) -> list[Path]:
    if (path / "metadata.json").exists():
        return [path]
    return [item.parent for item in sorted(path.glob("*/episode_*/metadata.json"))]


def validate_pseudo_dataset(raw_dir: str | Path) -> ValidationReport:
    root = Path(raw_dir).expanduser()
    report = ValidationReport(ok=True)
    episodes = _episode_dirs(root)
    if not episodes:
        report.errors.append(f"{root}: no pseudo episodes found")
    for episode in episodes:
        metadata = json.loads((episode / "metadata.json").read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in (episode / "data.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        count = len(rows)
        report.episode_count += 1
        report.frame_count += count
        if metadata.get("sample_type") != "pseudo":
            report.errors.append(f"{episode}: metadata sample_type must be pseudo")
        timestamps = []
        for index, row in enumerate(rows):
            if row.get("sample_type") != "pseudo":
                report.errors.append(f"{episode}: sample_type must be pseudo at frame {index}")
            confidence = float(row.get("confidence", -1.0))
            if confidence < 0.0 or confidence > 1.0:
                report.errors.append(f"{episode}: confidence outside [0,1] at frame {index}")
            timestamps.append(float(row.get("timestamp", 0.0)))
            for camera in ["chest", "left_wrist", "right_wrist"]:
                rel_path = row.get("images", {}).get(camera)
                if not rel_path or not (episode / rel_path).exists():
                    report.errors.append(f"{episode}: missing image {camera} at frame {index}")
        if any(b < a for a, b in zip(timestamps, timestamps[1:])):
            report.errors.append(f"{episode}: timestamps are not monotonic")
        arrays = episode / "arrays"
        checks = [
            ("observation_state.npy", STATE_DIM, "observation.state"),
            ("observation_ee_pose.npy", EE_POSE_DIM, "observation.ee_pose"),
            ("action.npy", ACTION_DIM, "action"),
        ]
        for filename, dim, label in checks:
            arr = np.load(arrays / filename)
            if arr.shape != (count, dim):
                report.errors.append(f"{episode}: {label} shape must be ({count}, {dim}), got {arr.shape}")
            if label == "action" and bool(metadata.get("action_valid", False)) and np.isnan(arr).any():
                report.errors.append(f"{episode}: action contains NaN while action_valid is true")
        confidence_arr = np.load(arrays / "confidence.npy")
        if confidence_arr.shape != (count,) or np.any((confidence_arr < 0.0) | (confidence_arr > 1.0)):
            report.errors.append(f"{episode}: confidence.npy must be shape ({count},) in [0,1]")
        state = np.load(arrays / "observation_state.npy")
        if not np.allclose(state, 0.0):
            report.errors.append(f"{episode}: pseudo observation_state must be zero")
        for camera in ["left_wrist", "right_wrist"]:
            first = episode / "images" / camera / "000000.png"
            if first.exists() and np.asarray(Image.open(first)).sum() != 0:
                report.errors.append(f"{episode}: {camera} image must be zero padded")
        if not bool(metadata.get("action_valid", False)):
            report.warnings.append(f"{episode}: action_valid is false, likely because IK is disabled")
    report.ok = not report.errors
    return report
