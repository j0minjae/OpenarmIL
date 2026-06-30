"""CLI for Phase 2 pseudo demonstration generation."""

from __future__ import annotations

import argparse

from openarm_il.ik_solver import load_ik_config
from openarm_il.pseudo_generator import generate_pseudo_episode
from openarm_il.quality_metrics import load_confidence_config
from openarm_il.retargeting import load_retarget_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pseudo OpenArm demonstrations from human RGB and hand pose.")
    parser.add_argument("--human-episode", required=True)
    parser.add_argument("--hand-pose", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--retarget-config")
    parser.add_argument("--pseudo-config")
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()
    episode_dir = generate_pseudo_episode(
        human_episode_dir=args.human_episode,
        hand_pose_dir=args.hand_pose,
        output_dir=args.output_dir,
        task=args.task,
        episode_id=args.episode_id,
        skip_validation=args.skip_validation,
        retarget_config=load_retarget_config(args.retarget_config),
        ik_config=load_ik_config(args.pseudo_config),
        confidence_config=load_confidence_config(args.pseudo_config),
    )
    print(f"pseudo_episode: {episode_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
