"""Optional FK wrapper. Pinocchio is intentionally optional for Phase 1."""

from __future__ import annotations

import logging

import numpy as np

from openarm_il.config import FKConfig
from openarm_il.schema import EE_POSE_DIM, zero_ee_pose

LOGGER = logging.getLogger(__name__)


class FKSolver:
    def __init__(self, config: FKConfig) -> None:
        self.config = config
        self.enabled = False
        if config.enable_fk:
            try:
                import pinocchio  # noqa: F401

                self.enabled = True
            except Exception as exc:  # pragma: no cover - depends on optional runtime package
                LOGGER.warning("FK requested but Pinocchio is unavailable; using zero ee_pose: %s", exc)

    def compute(self, _state: np.ndarray) -> np.ndarray:
        if not self.enabled:
            return zero_ee_pose()
        LOGGER.warning("FK is enabled but frame-specific computation is not configured in Phase 1; using zeros")
        return np.zeros(EE_POSE_DIM, dtype=np.float32)
