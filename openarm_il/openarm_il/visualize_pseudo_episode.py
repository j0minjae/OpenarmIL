"""CLI for Phase 2 pseudo episode visualization."""

from __future__ import annotations

import argparse

from openarm_il.pseudo_visualization import visualize_pseudo_episode


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize an OpenArmIL pseudo episode.")
    parser.add_argument("--episode-dir", required=True)
    parser.add_argument("--save-dir")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()
    visualize_pseudo_episode(args.episode_dir, args.save_dir, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
