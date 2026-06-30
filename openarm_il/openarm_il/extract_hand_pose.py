"""CLI for Phase 2 hand-pose extraction adapters."""

from __future__ import annotations

import argparse
from pathlib import Path

from openarm_il.hand_pose_interface import HaMeRHandPoseExtractor, MediaPipeHandPoseExtractor, PrecomputedHandPoseExtractor


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract or import hand pose into the OpenArmIL standard format.")
    parser.add_argument("--backend", choices=["precomputed", "mediapipe", "hamer"], default="precomputed")
    parser.add_argument("--input", required=True)
    parser.add_argument("--precomputed-file")
    parser.add_argument("--output", required=True)
    parser.add_argument("--num-keypoints", type=int, default=21)
    args = parser.parse_args()
    if args.backend == "precomputed":
        if not args.precomputed_file:
            raise SystemExit("--precomputed-file is required for --backend precomputed")
        extractor = PrecomputedHandPoseExtractor(args.precomputed_file, num_keypoints=args.num_keypoints)
    elif args.backend == "mediapipe":
        extractor = MediaPipeHandPoseExtractor()
    else:
        extractor = HaMeRHandPoseExtractor()
    extractor.extract_episode(Path(args.input).expanduser(), Path(args.output).expanduser())
    print(f"hand_pose: {Path(args.output).expanduser()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
