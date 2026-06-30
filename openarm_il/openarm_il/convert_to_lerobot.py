"""CLI for offline LeRobot-style export."""

from __future__ import annotations

import argparse

from openarm_il.lerobot_exporter import export_lerobot_dataset, export_lerobot_mixed_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert OpenArmIL raw_real/raw_pseudo episodes to a local LeRobot-style dataset.")
    parser.add_argument("--raw-dir", help="Backward-compatible single raw_real directory input.")
    parser.add_argument("--real-dir", help="Raw real dataset root.")
    parser.add_argument("--pseudo-dir", help="Raw pseudo dataset root.")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.raw_dir:
        output_dir = export_lerobot_dataset(args.raw_dir, args.output_dir)
    else:
        output_dir = export_lerobot_mixed_dataset(output_dir=args.output_dir, real_dir=args.real_dir, pseudo_dir=args.pseudo_dir)
    print(f"exported: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
