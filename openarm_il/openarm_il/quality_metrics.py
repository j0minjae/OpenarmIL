"""Confidence and uncertainty metrics for pseudo demonstrations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml


@dataclass(frozen=True)
class ConfidenceConfig:
    alpha: float = 1.0
    beta: float = 2.0
    gamma: float = 1.0
    delta: float = 1.0
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    default_ik_residual: float = 0.0


@dataclass(frozen=True)
class ConfidenceResult:
    confidence: np.ndarray
    uncertainty_terms: np.ndarray


def load_confidence_config(path: str | Path | None) -> ConfidenceConfig:
    if path is None:
        return ConfidenceConfig()
    data = yaml.safe_load(Path(path).expanduser().read_text(encoding="utf-8")) or {}
    confidence = data.get("confidence", data)
    return ConfidenceConfig(
        alpha=float(confidence.get("alpha", 1.0)),
        beta=float(confidence.get("beta", 2.0)),
        gamma=float(confidence.get("gamma", 1.0)),
        delta=float(confidence.get("delta", 1.0)),
        min_confidence=float(confidence.get("min_confidence", 0.0)),
        max_confidence=float(confidence.get("max_confidence", 1.0)),
    )


def compute_confidence(
    actions: np.ndarray,
    hand_confidence: np.ndarray,
    workspace_violation: np.ndarray,
    config: ConfidenceConfig,
    ik_residual: np.ndarray | None = None,
) -> ConfidenceResult:
    action_array = np.asarray(actions, dtype=np.float32)
    tracking = 1.0 - np.nanmean(np.asarray(hand_confidence, dtype=np.float32), axis=1)
    tracking = np.nan_to_num(tracking, nan=1.0)
    ik = np.full(action_array.shape[0], config.default_ik_residual, dtype=np.float32) if ik_residual is None else np.asarray(
        ik_residual, dtype=np.float32
    )
    workspace = np.asarray(workspace_violation, dtype=np.float32)
    jumps = np.zeros(action_array.shape[0], dtype=np.float32)
    if action_array.shape[0] > 1:
        jumps[1:] = np.linalg.norm(np.diff(action_array, axis=0), axis=1)
    uncertainty = config.alpha * tracking + config.beta * ik + config.gamma * workspace + config.delta * jumps
    confidence = np.clip(np.exp(-uncertainty), config.min_confidence, config.max_confidence).astype(np.float32)
    return ConfidenceResult(
        confidence=confidence,
        uncertainty_terms=np.stack([tracking, ik, workspace, jumps], axis=1).astype(np.float32),
    )
