"""CLI for raw dataset validation."""

from __future__ import annotations

import argparse

from openarm_il.validator import validate_raw_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OpenArmIL raw real episodes.")
    parser.add_argument("--raw-dir", required=True, help="Episode directory or raw_real root.")
    args = parser.parse_args()
    report = validate_raw_dataset(args.raw_dir)
    print(report.format())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
