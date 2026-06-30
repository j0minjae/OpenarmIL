"""Human RGB recording/import utilities for Phase 2."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np
from PIL import Image


def write_human_rgb_episode(
    frames: list[np.ndarray],
    timestamps: np.ndarray,
    output_dir: str | Path,
    task: str,
    episode_id: str,
    camera: str,
    fps: float,
    width: int,
    height: int,
) -> Path:
    episode_dir = Path(output_dir).expanduser() / task / f"episode_{episode_id}"
    if episode_dir.exists():
        shutil.rmtree(episode_dir)
    frames_dir = episode_dir / "frames"
    frames_dir.mkdir(parents=True)
    for index, frame in enumerate(frames):
        image = Image.fromarray(np.asarray(frame, dtype=np.uint8), mode="RGB")
        if image.size != (width, height):
            image = image.resize((width, height), Image.BILINEAR)
        image.save(frames_dir / f"{index:06d}.png")
    np.save(episode_dir / "timestamps.npy", np.asarray(timestamps, dtype=np.float64))
    metadata = {
        "task": task,
        "episode_id": str(episode_id),
        "fps": float(fps),
        "width": int(width),
        "height": int(height),
        "num_frames": len(frames),
        "camera": camera,
        "data_type": "human_rgb",
    }
    (episode_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return episode_dir


def record_from_opencv_camera(
    camera: str,
    output_dir: str | Path,
    task: str,
    episode_id: str,
    fps: float,
    width: int,
    height: int,
    duration: float,
) -> Path:
    import cv2

    source = int(camera) if str(camera).isdigit() else camera
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise RuntimeError(f"failed to open camera: {camera}")
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_FPS, fps)
    frames: list[np.ndarray] = []
    timestamps: list[float] = []
    start = time.monotonic()
    period = 1.0 / max(float(fps), 1.0)
    try:
        while time.monotonic() - start < duration:
            ok, frame_bgr = capture.read()
            if not ok:
                raise RuntimeError("camera frame read failed")
            frames.append(frame_bgr[:, :, ::-1])
            timestamps.append(time.monotonic() - start)
            sleep_for = period - ((time.monotonic() - start) % period)
            if sleep_for > 0:
                time.sleep(min(sleep_for, period))
    finally:
        capture.release()
    return write_human_rgb_episode(frames, np.asarray(timestamps), output_dir, task, episode_id, camera, fps, width, height)
