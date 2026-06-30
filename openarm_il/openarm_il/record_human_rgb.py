"""CLI for Phase 2 human RGB recording."""

from __future__ import annotations

import argparse

from openarm_il.human_rgb_recorder import record_from_opencv_camera


def main() -> int:
    parser = argparse.ArgumentParser(description="Record human RGB manipulation video for OpenArmIL Phase 2.")
    parser.add_argument("--camera", default="/dev/video0")
    parser.add_argument("--task", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--keyboard", action="store_true", help="Reserved for interactive recording; timed recording is used in this implementation.")
    args = parser.parse_args()
    episode_dir = record_from_opencv_camera(args.camera, args.output_dir, args.task, args.episode_id, args.fps, args.width, args.height, args.duration)
    print(f"recorded: {episode_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
