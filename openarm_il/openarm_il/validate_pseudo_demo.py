"""CLI for Phase 2 pseudo demonstration validation."""

from __future__ import annotations

import argparse

from openarm_il.pseudo_validator import validate_pseudo_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OpenArmIL pseudo demonstrations.")
    parser.add_argument("--raw-dir", required=True)
    args = parser.parse_args()
    report = validate_pseudo_dataset(args.raw_dir)
    print(report.format())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
