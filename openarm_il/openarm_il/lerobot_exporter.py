"""Offline LeRobot-style export for OpenArm raw real and pseudo episodes."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from openarm_il.config import load_dataset_schema
from openarm_il.pseudo_validator import validate_pseudo_dataset
from openarm_il.validator import validate_raw_dataset


def _episode_dirs(raw_dir: Path) -> list[Path]:
    if (raw_dir / "metadata.json").exists():
        return [raw_dir]
    return [path.parent for path in sorted(raw_dir.glob("*/episode_*/metadata.json"))]


def export_lerobot_dataset(raw_dir: str | Path, output_dir: str | Path) -> Path:
    return export_lerobot_mixed_dataset(real_dir=raw_dir, pseudo_dir=None, output_dir=output_dir, source_prefix=False)


def export_lerobot_mixed_dataset(
    output_dir: str | Path,
    real_dir: str | Path | None = None,
    pseudo_dir: str | Path | None = None,
    source_prefix: bool = True,
) -> Path:
    if real_dir is None and pseudo_dir is None:
        raise ValueError("at least one of real_dir or pseudo_dir is required")
    output_root = Path(output_dir).expanduser()
    sources: list[tuple[str, Path]] = []
    episode_count = 0
    frame_count = 0
    if real_dir is not None:
        real_root = Path(real_dir).expanduser()
        report = validate_raw_dataset(real_root)
        if not report.ok:
            raise ValueError("raw real dataset validation failed before export:\n" + report.format())
        sources.append(("real", real_root))
        episode_count += report.episode_count
        frame_count += report.frame_count
    if pseudo_dir is not None:
        pseudo_root = Path(pseudo_dir).expanduser()
        report = validate_pseudo_dataset(pseudo_root)
        if not report.ok:
            raise ValueError("raw pseudo dataset validation failed before export:\n" + report.format())
        sources.append(("pseudo", pseudo_root))
        episode_count += report.episode_count
        frame_count += report.frame_count

    if output_root.exists():
        shutil.rmtree(output_root)
    (output_root / "meta").mkdir(parents=True)
    (output_root / "data").mkdir(parents=True)

    schema = load_dataset_schema()
    info = {
        "codebase_version": "openarm_il_local_v1",
        "robot_type": "openarm_v10_bimanual",
        "fps": None,
        "features": schema.features,
        "episode_count": episode_count,
        "frame_count": frame_count,
    }
    (output_root / "meta" / "info.json").write_text(json.dumps(info, indent=2, sort_keys=True), encoding="utf-8")

    frame_global_index = 0
    with (output_root / "meta" / "episodes.jsonl").open("w", encoding="utf-8") as episode_handle, (
        output_root / "data" / "frames.jsonl"
    ).open("w", encoding="utf-8") as frame_handle:
        for source_name, source_root in sources:
            for episode_dir in _episode_dirs(source_root):
                metadata = json.loads((episode_dir / "metadata.json").read_text(encoding="utf-8"))
                task = metadata["task"]
                episode_name = episode_dir.name
                rel_episode_dir = Path("data") / source_name / task / episode_name if source_prefix else Path("data") / task / episode_name
                dst_episode_dir = output_root / rel_episode_dir
                dst_episode_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(episode_dir, dst_episode_dir)

                episode_row = {
                    "episode_index": int(metadata["episode_index"]),
                    "episode_id": metadata["episode_id"],
                    "task": task,
                    "sample_type": metadata.get("sample_type", source_name),
                    "frame_count": int(metadata["frame_count"]),
                    "path": rel_episode_dir.as_posix(),
                }
                episode_handle.write(json.dumps(episode_row, sort_keys=True) + "\n")

                with (episode_dir / "data.jsonl").open("r", encoding="utf-8") as source_frames:
                    for line in source_frames:
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        row["index"] = frame_global_index
                        row["episode_path"] = rel_episode_dir.as_posix()
                        frame_handle.write(json.dumps(row, sort_keys=True) + "\n")
                        frame_global_index += 1

    return output_root
