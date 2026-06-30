"""Raw episode writer for OpenArm real demonstrations."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from openarm_il.schema import ACTION_DIM, EE_POSE_DIM, STATE_DIM, ensure_vector


class EpisodeWriter:
    """Write one raw real-robot episode to disk."""

    def __init__(
        self,
        output_dir: str | Path,
        task: str,
        episode_id: str,
        episode_index: int,
        camera_names: list[str],
        image_size: tuple[int, int],
        overwrite: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir).expanduser()
        self.task = task
        self.episode_id = str(episode_id)
        self.episode_index = int(episode_index)
        self.camera_names = list(camera_names)
        self.image_size = image_size
        self.episode_dir = self.output_dir / task / f"episode_{self.episode_id}"
        self.images_dir = self.episode_dir / "images"
        self.arrays_dir = self.episode_dir / "arrays"
        self._rows: list[dict[str, Any]] = []
        self._states: list[np.ndarray] = []
        self._ee_poses: list[np.ndarray] = []
        self._actions: list[np.ndarray] = []
        self._timestamps: list[float] = []

        if self.episode_dir.exists() and overwrite:
            shutil.rmtree(self.episode_dir)
        self.arrays_dir.mkdir(parents=True, exist_ok=True)
        for camera in self.camera_names:
            (self.images_dir / camera).mkdir(parents=True, exist_ok=True)

    def _normalize_image(self, image: np.ndarray | None) -> np.ndarray:
        width, height = self.image_size
        if image is None:
            return np.zeros((height, width, 3), dtype=np.uint8)
        array = np.asarray(image)
        if array.ndim == 2:
            array = np.repeat(array[:, :, None], 3, axis=2)
        if array.shape[-1] == 4:
            array = array[:, :, :3]
        if array.dtype != np.uint8:
            array = np.clip(array, 0, 255).astype(np.uint8)
        pil = Image.fromarray(array, mode="RGB")
        if pil.size != (width, height):
            pil = pil.resize((width, height), Image.BILINEAR)
        return np.asarray(pil, dtype=np.uint8)

    def add_frame(
        self,
        timestamp: float,
        images: dict[str, np.ndarray],
        observation_state: np.ndarray,
        observation_ee_pose: np.ndarray,
        action: np.ndarray,
    ) -> None:
        frame_index = len(self._rows)
        state = ensure_vector("observation.state", observation_state, STATE_DIM)
        ee_pose = ensure_vector("observation.ee_pose", observation_ee_pose, EE_POSE_DIM)
        action_vector = ensure_vector("action", action, ACTION_DIM)

        image_paths: dict[str, str] = {}
        for camera in self.camera_names:
            image = self._normalize_image(images.get(camera))
            rel_path = Path("images") / camera / f"{frame_index:06d}.png"
            Image.fromarray(image, mode="RGB").save(self.episode_dir / rel_path)
            image_paths[camera] = rel_path.as_posix()

        self._states.append(state)
        self._ee_poses.append(ee_pose)
        self._actions.append(action_vector)
        self._timestamps.append(float(timestamp))
        self._rows.append(
            {
                "timestamp": float(timestamp),
                "episode_index": self.episode_index,
                "frame_index": frame_index,
                "sample_type": "real",
                "images": image_paths,
                "observation_state_index": frame_index,
                "observation_ee_pose_index": frame_index,
                "action_index": frame_index,
                "confidence": 1.0,
                "task": self.task,
            }
        )

    def close(self, metadata_extra: dict[str, Any] | None = None) -> Path:
        with (self.episode_dir / "data.jsonl").open("w", encoding="utf-8") as handle:
            for row in self._rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        np.save(self.arrays_dir / "observation_state.npy", np.asarray(self._states, dtype=np.float32))
        np.save(self.arrays_dir / "observation_ee_pose.npy", np.asarray(self._ee_poses, dtype=np.float32))
        np.save(self.arrays_dir / "action.npy", np.asarray(self._actions, dtype=np.float32))
        np.save(self.arrays_dir / "timestamps.npy", np.asarray(self._timestamps, dtype=np.float64))

        metadata = {
            "task": self.task,
            "episode_id": self.episode_id,
            "episode_index": self.episode_index,
            "sample_type": "real",
            "frame_count": len(self._rows),
            "camera_names": self.camera_names,
            "image_width": self.image_size[0],
            "image_height": self.image_size[1],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata_extra:
            metadata.update(metadata_extra)
        (self.episode_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        return self.episode_dir

    def cancel(self) -> None:
        if self.episode_dir.exists():
            shutil.rmtree(self.episode_dir)
