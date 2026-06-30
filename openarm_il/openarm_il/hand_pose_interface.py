"""Pluggable hand-pose extraction backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from openarm_il.hand_pose_schema import write_hand_pose_episode


class HandPoseExtractor(ABC):
    @abstractmethod
    def extract_episode(self, episode_dir: Path, output_dir: Path) -> None:
        raise NotImplementedError


class PrecomputedHandPoseExtractor(HandPoseExtractor):
    def __init__(self, precomputed_file: str | Path, num_keypoints: int = 21) -> None:
        self.precomputed_file = Path(precomputed_file).expanduser()
        self.num_keypoints = int(num_keypoints)

    def extract_episode(self, episode_dir: Path, output_dir: Path) -> None:
        del episode_dir
        write_hand_pose_episode(self.precomputed_file, output_dir, num_keypoints=self.num_keypoints)


class MediaPipeHandPoseExtractor(HandPoseExtractor):
    def extract_episode(self, episode_dir: Path, output_dir: Path) -> None:
        try:
            import mediapipe  # noqa: F401
        except Exception as exc:
            raise RuntimeError("MediaPipe backend requires the mediapipe package. Use --backend precomputed for Phase 2 offline flow.") from exc
        raise NotImplementedError("MediaPipe extraction adapter is available as an optional future backend; precomputed is the supported Phase 2 path.")


class HaMeRHandPoseExtractor(HandPoseExtractor):
    def extract_episode(self, episode_dir: Path, output_dir: Path) -> None:
        raise NotImplementedError(
            "HaMeR is not bundled in Phase 2. Export HaMeR results to the standard hand_pose.jsonl format and use --backend precomputed."
        )
