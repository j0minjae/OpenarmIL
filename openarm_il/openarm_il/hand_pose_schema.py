"""Standard hand-pose format for Phase 2 human RGB processing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class HandData:
    wrist_pose: np.ndarray
    keypoints: np.ndarray
    confidence: float

    @classmethod
    def from_json(cls, data: dict[str, Any] | None, num_keypoints: int = 21) -> "HandData | None":
        if data is None:
            return None
        wrist = np.asarray(data.get("wrist_pose", [np.nan] * 7), dtype=np.float32)
        keypoints = np.asarray(data.get("keypoints", np.full((num_keypoints, 3), np.nan)), dtype=np.float32)
        if wrist.shape != (7,):
            raise ValueError(f"wrist_pose must have shape (7,), got {wrist.shape}")
        if keypoints.ndim != 2 or keypoints.shape[1] != 3:
            raise ValueError(f"keypoints must have shape (N, 3), got {keypoints.shape}")
        return cls(wrist_pose=wrist, keypoints=keypoints, confidence=float(data.get("confidence", 0.0)))

    def to_json(self) -> dict[str, Any]:
        return {
            "wrist_pose": self.wrist_pose.astype(float).tolist(),
            "keypoints": self.keypoints.astype(float).tolist(),
            "confidence": float(self.confidence),
        }


@dataclass(frozen=True)
class HandPoseFrame:
    timestamp: float
    frame_index: int
    left: HandData | None
    right: HandData | None

    @classmethod
    def from_json(cls, row: dict[str, Any], num_keypoints: int = 21) -> "HandPoseFrame":
        return cls(
            timestamp=float(row["timestamp"]),
            frame_index=int(row["frame_index"]),
            left=HandData.from_json(row.get("left"), num_keypoints),
            right=HandData.from_json(row.get("right"), num_keypoints),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "timestamp": float(self.timestamp),
            "frame_index": int(self.frame_index),
            "left": None if self.left is None else self.left.to_json(),
            "right": None if self.right is None else self.right.to_json(),
        }


def _nan_hand(num_keypoints: int) -> tuple[np.ndarray, np.ndarray, float]:
    return np.full(7, np.nan, dtype=np.float32), np.full((num_keypoints, 3), np.nan, dtype=np.float32), 0.0


def write_hand_pose_episode(precomputed_file: str | Path, output_dir: str | Path, num_keypoints: int = 21) -> Path:
    source = Path(precomputed_file).expanduser()
    out = Path(output_dir).expanduser()
    arrays = out / "arrays"
    arrays.mkdir(parents=True, exist_ok=True)

    frames: list[HandPoseFrame] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.strip():
            frames.append(HandPoseFrame.from_json(json.loads(line), num_keypoints=num_keypoints))

    left_wrist, right_wrist = [], []
    left_keypoints, right_keypoints = [], []
    left_confidence, right_confidence, timestamps = [], [], []
    with (out / "hand_pose.jsonl").open("w", encoding="utf-8") as handle:
        for frame in frames:
            lw, lk, lc = _nan_hand(num_keypoints) if frame.left is None else (
                frame.left.wrist_pose,
                frame.left.keypoints,
                frame.left.confidence,
            )
            rw, rk, rc = _nan_hand(num_keypoints) if frame.right is None else (
                frame.right.wrist_pose,
                frame.right.keypoints,
                frame.right.confidence,
            )
            left_wrist.append(lw)
            right_wrist.append(rw)
            left_keypoints.append(lk)
            right_keypoints.append(rk)
            left_confidence.append(lc)
            right_confidence.append(rc)
            timestamps.append(frame.timestamp)
            handle.write(json.dumps(frame.to_json(), sort_keys=True) + "\n")

    metadata = {
        "data_type": "hand_pose",
        "num_frames": len(frames),
        "num_keypoints": num_keypoints,
        "pose_format": "xyz_quat_xyzw",
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    np.save(arrays / "left_wrist_pose.npy", np.asarray(left_wrist, dtype=np.float32))
    np.save(arrays / "right_wrist_pose.npy", np.asarray(right_wrist, dtype=np.float32))
    np.save(arrays / "left_keypoints.npy", np.asarray(left_keypoints, dtype=np.float32))
    np.save(arrays / "right_keypoints.npy", np.asarray(right_keypoints, dtype=np.float32))
    np.save(arrays / "left_confidence.npy", np.asarray(left_confidence, dtype=np.float32))
    np.save(arrays / "right_confidence.npy", np.asarray(right_confidence, dtype=np.float32))
    np.save(arrays / "timestamps.npy", np.asarray(timestamps, dtype=np.float64))
    return out
