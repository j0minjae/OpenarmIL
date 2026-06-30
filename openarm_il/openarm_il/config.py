"""YAML-backed configuration for OpenArm real demonstration collection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ImageConfig:
    width: int = 640
    height: int = 480
    save_format: str = "png"


@dataclass(frozen=True)
class FKConfig:
    enable_fk: bool = False
    urdf_path: str = ""
    left_ee_frame: str = ""
    right_ee_frame: str = ""


@dataclass(frozen=True)
class CollectionConfig:
    output_dir: str
    task: str
    episode_id: str
    duration: float
    sync_tolerance_sec: float
    record_rate_hz: float
    action_source: str
    image: ImageConfig
    required_streams: list[str]
    optional_streams: list[str]
    fk: FKConfig


@dataclass(frozen=True)
class TopicConfig:
    joint_states: str
    cameras: dict[str, str]
    actions: dict[str, str]


@dataclass(frozen=True)
class DatasetSchema:
    state_dim: int
    action_dim: int
    ee_pose_dim: int
    left_arm_joints: list[str]
    right_arm_joints: list[str]
    left_gripper_joint: str
    right_gripper_joint: str
    features: dict[str, str]


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_yaml(path: Path) -> dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def load_collection_config(path: str | Path | None = None) -> CollectionConfig:
    data = _read_yaml(Path(path) if path else package_root() / "config" / "real_collection.yaml")
    image = data.get("image", {})
    fk = data.get("fk", {})
    return CollectionConfig(
        output_dir=str(data.get("output_dir", "~/datasets/openarm_il/raw_real")),
        task=str(data.get("task", "default_task")),
        episode_id=str(data.get("episode_id", "0000")),
        duration=float(data.get("duration", 30.0)),
        sync_tolerance_sec=float(data.get("sync_tolerance_sec", 0.05)),
        record_rate_hz=float(data.get("record_rate_hz", 30.0)),
        action_source=str(data.get("action_source", "next_state")),
        image=ImageConfig(
            width=int(image.get("width", 640)),
            height=int(image.get("height", 480)),
            save_format=str(image.get("save_format", "png")),
        ),
        required_streams=list(data.get("required_streams", ["joint_states", "chest"])),
        optional_streams=list(data.get("optional_streams", ["left_wrist", "right_wrist", "actions"])),
        fk=FKConfig(
            enable_fk=bool(fk.get("enable_fk", False)),
            urdf_path=str(fk.get("urdf_path", "")),
            left_ee_frame=str(fk.get("left_ee_frame", "")),
            right_ee_frame=str(fk.get("right_ee_frame", "")),
        ),
    )


def load_topic_config(path: str | Path | None = None) -> TopicConfig:
    data = _read_yaml(Path(path) if path else package_root() / "config" / "camera_topics.yaml")
    return TopicConfig(
        joint_states=str(data.get("joint_states", "/joint_states")),
        cameras=dict(data.get("cameras", {})),
        actions=dict(data.get("actions", {})),
    )


def load_dataset_schema(path: str | Path | None = None) -> DatasetSchema:
    data = _read_yaml(Path(path) if path else package_root() / "config" / "dataset_schema.yaml")
    return DatasetSchema(
        state_dim=int(data.get("state_dim", 16)),
        action_dim=int(data.get("action_dim", 16)),
        ee_pose_dim=int(data.get("ee_pose_dim", 16)),
        left_arm_joints=list(data.get("left_arm_joints", [])),
        right_arm_joints=list(data.get("right_arm_joints", [])),
        left_gripper_joint=str(data.get("left_gripper_joint", "")),
        right_gripper_joint=str(data.get("right_gripper_joint", "")),
        features=dict(data.get("features", {})),
    )
