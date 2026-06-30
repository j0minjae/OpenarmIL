"""Action command extraction from supported ROS command messages."""

from __future__ import annotations

from typing import Any

import numpy as np


def command_vector(msg: Any) -> np.ndarray:
    if hasattr(msg, "data"):
        return np.asarray(msg.data, dtype=np.float32)
    points = getattr(msg, "points", None)
    if points:
        return np.asarray(points[-1].positions, dtype=np.float32)
    return np.asarray([], dtype=np.float32)
