"""Validation for raw OpenArm real demonstration episodes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np

from openarm_il.schema import ACTION_DIM, EE_POSE_DIM, STATE_DIM


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    episode_count: int = 0
    frame_count: int = 0

    def format(self) -> str:
        lines = [
            f"ok: {self.ok}",
            f"episodes: {self.episode_count}",
            f"frames: {self.frame_count}",
        ]
        lines.extend(f"ERROR: {error}" for error in self.errors)
        lines.extend(f"WARNING: {warning}" for warning in self.warnings)
        return "\n".join(lines)


def _episode_dirs(path: Path) -> Iterable[Path]:
    if (path / "metadata.json").exists():
        yield path
        return
    for metadata_path in sorted(path.glob("*/episode_*/metadata.json")):
        yield metadata_path.parent


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _check_array(
    report: ValidationReport,
    episode_dir: Path,
    rel_path: str,
    expected_frames: int,
    expected_dim: int,
    label: str,
) -> np.ndarray | None:
    path = episode_dir / rel_path
    if not path.exists():
        report.errors.append(f"{episode_dir}: missing array {rel_path}")
        return None
    array = np.load(path)
    if array.ndim != 2 or array.shape[0] != expected_frames:
        report.errors.append(f"{episode_dir}: {label} length mismatch, got {array.shape}")
    if array.ndim != 2 or array.shape[1] != expected_dim:
        report.errors.append(f"{episode_dir}: {label} dimension must be {expected_dim}, got {array.shape}")
    if np.isnan(array).any():
        report.errors.append(f"{episode_dir}: {label} contains NaN")
    return array


def _validate_episode(episode_dir: Path, report: ValidationReport) -> None:
    required_files = ["metadata.json", "data.jsonl"]
    for rel_path in required_files:
        if not (episode_dir / rel_path).exists():
            report.errors.append(f"{episode_dir}: missing required file {rel_path}")
            return

    metadata = json.loads((episode_dir / "metadata.json").read_text(encoding="utf-8"))
    rows = _load_jsonl(episode_dir / "data.jsonl")
    frame_count = len(rows)
    report.episode_count += 1
    report.frame_count += frame_count

    if metadata.get("frame_count") != frame_count:
        report.errors.append(f"{episode_dir}: metadata frame_count does not match data.jsonl")
    if metadata.get("sample_type") != "real":
        report.errors.append(f"{episode_dir}: metadata sample_type must be real")

    timestamps = []
    for expected_index, row in enumerate(rows):
        if row.get("frame_index") != expected_index:
            report.errors.append(f"{episode_dir}: frame_index mismatch at row {expected_index}")
        if row.get("sample_type") != "real":
            report.errors.append(f"{episode_dir}: sample_type must be real at frame {expected_index}")
        if float(row.get("confidence", -1.0)) != 1.0:
            report.errors.append(f"{episode_dir}: confidence must be 1.0 at frame {expected_index}")
        timestamps.append(float(row.get("timestamp", 0.0)))
        images = row.get("images", {})
        if not isinstance(images, dict) or "chest" not in images:
            report.errors.append(f"{episode_dir}: missing chest image in frame {expected_index}")
        for camera, rel_path in images.items():
            image_path = episode_dir / rel_path
            if not image_path.exists():
                report.errors.append(f"{episode_dir}: missing image {camera} at {rel_path}")

    if any(next_ts < this_ts for this_ts, next_ts in zip(timestamps, timestamps[1:])):
        report.errors.append(f"{episode_dir}: timestamps are not monotonic")

    arrays_ts = episode_dir / "arrays" / "timestamps.npy"
    if arrays_ts.exists():
        saved_timestamps = np.load(arrays_ts)
        if saved_timestamps.shape != (frame_count,):
            report.errors.append(f"{episode_dir}: timestamps length mismatch, got {saved_timestamps.shape}")
        if np.isnan(saved_timestamps).any():
            report.errors.append(f"{episode_dir}: timestamps contain NaN")
        if np.any(np.diff(saved_timestamps) < 0):
            report.errors.append(f"{episode_dir}: saved timestamps are not monotonic")
    else:
        report.errors.append(f"{episode_dir}: missing array arrays/timestamps.npy")

    _check_array(report, episode_dir, "arrays/observation_state.npy", frame_count, STATE_DIM, "observation.state")
    _check_array(report, episode_dir, "arrays/observation_ee_pose.npy", frame_count, EE_POSE_DIM, "observation.ee_pose")
    _check_array(report, episode_dir, "arrays/action.npy", frame_count, ACTION_DIM, "action")


def validate_raw_dataset(raw_dir: str | Path) -> ValidationReport:
    root = Path(raw_dir).expanduser()
    report = ValidationReport(ok=True)
    episode_dirs = list(_episode_dirs(root))
    if not episode_dirs:
        report.errors.append(f"{root}: no raw episodes found")
    for episode_dir in episode_dirs:
        _validate_episode(episode_dir, report)
    report.ok = not report.errors
    return report
