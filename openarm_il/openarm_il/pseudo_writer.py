"""Writer for Phase 2 pseudo robot demonstrations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from openarm_il.episode_writer import EpisodeWriter


class PseudoEpisodeWriter(EpisodeWriter):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._confidence: list[float] = []
        self._uncertainty_terms: list[np.ndarray] = []
        self._action_valid: list[bool] = []

    def add_pseudo_frame(
        self,
        timestamp: float,
        chest_image: np.ndarray,
        observation_state: np.ndarray,
        observation_ee_pose: np.ndarray,
        action: np.ndarray,
        confidence: float,
        uncertainty_terms: np.ndarray,
        action_valid: bool,
    ) -> None:
        super().add_frame(
            timestamp=timestamp,
            images={"chest": chest_image},
            observation_state=observation_state,
            observation_ee_pose=observation_ee_pose,
            action=action,
        )
        self._rows[-1]["sample_type"] = "pseudo"
        self._rows[-1]["confidence"] = float(confidence)
        self._confidence.append(float(confidence))
        self._uncertainty_terms.append(np.asarray(uncertainty_terms, dtype=np.float32))
        self._action_valid.append(bool(action_valid))

    def close(self, metadata_extra: dict | None = None) -> Path:
        extra = {
            "sample_type": "pseudo",
            "action_valid": bool(all(self._action_valid)) if self._action_valid else False,
            "data_type": "pseudo_robot_demo",
        }
        if metadata_extra:
            extra.update(metadata_extra)
        path = super().close(metadata_extra=extra)
        np.save(self.arrays_dir / "confidence.npy", np.asarray(self._confidence, dtype=np.float32))
        np.save(self.arrays_dir / "uncertainty_terms.npy", np.asarray(self._uncertainty_terms, dtype=np.float32))
        np.save(self.arrays_dir / "action_valid.npy", np.asarray(self._action_valid, dtype=bool))
        metadata_path = path / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["action_valid"] = bool(all(self._action_valid)) if self._action_valid else False
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        return path
