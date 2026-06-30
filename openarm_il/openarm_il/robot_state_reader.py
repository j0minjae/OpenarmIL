"""Robot state extraction from ROS JointState messages."""

from __future__ import annotations

from typing import Any


def stamp_to_sec(stamp: Any) -> float:
    return float(getattr(stamp, "sec", 0)) + float(getattr(stamp, "nanosec", 0)) * 1e-9


def joint_state_positions(msg: Any) -> dict[str, float]:
    return {name: float(position) for name, position in zip(msg.name, msg.position)}


def message_timestamp(msg: Any, fallback_time: float) -> float:
    stamp = getattr(getattr(msg, "header", None), "stamp", None)
    value = stamp_to_sec(stamp) if stamp is not None else 0.0
    return value if value > 0.0 else float(fallback_time)
