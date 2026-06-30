"""RGB image conversion helpers for ROS Image messages."""

from __future__ import annotations

from typing import Any

import numpy as np


class CameraReader:
    def __init__(self) -> None:
        self._bridge = None
        try:
            from cv_bridge import CvBridge

            self._bridge = CvBridge()
        except Exception:
            self._bridge = None

    def to_rgb(self, msg: Any) -> np.ndarray:
        if isinstance(msg, np.ndarray):
            return msg
        if self._bridge is None:
            raise RuntimeError("cv_bridge is required to convert ROS Image messages")
        encoding = getattr(msg, "encoding", "rgb8")
        desired = "rgb8"
        if encoding.lower() in {"bgr8", "bgra8"}:
            desired = "bgr8"
        image = self._bridge.imgmsg_to_cv2(msg, desired_encoding=desired)
        if desired == "bgr8":
            image = image[:, :, ::-1]
        return np.asarray(image, dtype=np.uint8)
