"""Generate pseudo OpenArm demonstrations from human RGB and hand pose."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from openarm_il.gripper_mapping import GripperConfig, gripper_sequence
from openarm_il.hand_pose_loader import load_hand_pose_episode
from openarm_il.ik_solver import IKConfig, solve_pseudo_actions
from openarm_il.pseudo_validator import validate_pseudo_dataset
from openarm_il.pseudo_writer import PseudoEpisodeWriter
from openarm_il.quality_metrics import ConfidenceConfig, compute_confidence
from openarm_il.retargeting import RetargetConfig, retarget_wrist_poses
from openarm_il.schema import EE_POSE_DIM, STATE_DIM


def _load_human_frames(human_episode_dir: Path) -> list[np.ndarray]:
    frame_paths = sorted((human_episode_dir / "frames").glob("*.png"))
    return [np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8) for path in frame_paths]


def _ee_pose16(left_pose7: np.ndarray, right_pose7: np.ndarray, left_gripper: float, right_gripper: float) -> np.ndarray:
    pose = np.zeros(EE_POSE_DIM, dtype=np.float32)
    pose[:7] = np.nan_to_num(left_pose7, nan=0.0)
    pose[7:14] = np.nan_to_num(right_pose7, nan=0.0)
    pose[14] = float(left_gripper)
    pose[15] = float(right_gripper)
    return pose


def generate_pseudo_episode(
    human_episode_dir: str | Path,
    hand_pose_dir: str | Path,
    output_dir: str | Path,
    task: str,
    episode_id: str,
    skip_validation: bool = False,
    retarget_config: RetargetConfig | None = None,
    ik_config: IKConfig | None = None,
    confidence_config: ConfidenceConfig | None = None,
) -> Path:
    human_dir = Path(human_episode_dir).expanduser()
    metadata = json.loads((human_dir / "metadata.json").read_text(encoding="utf-8"))
    frames = _load_human_frames(human_dir)
    hand_pose = load_hand_pose_episode(hand_pose_dir)
    count = min(len(frames), hand_pose.timestamps.shape[0])
    if count == 0:
        raise ValueError("cannot generate pseudo episode with zero frames")

    retargeted = retarget_wrist_poses(
        hand_pose.left_wrist_pose[:count],
        hand_pose.right_wrist_pose[:count],
        retarget_config or RetargetConfig.default(),
    )
    left_gripper = gripper_sequence(hand_pose.left_keypoints[:count], GripperConfig())
    right_gripper = gripper_sequence(hand_pose.right_keypoints[:count], GripperConfig())
    ik = solve_pseudo_actions(retargeted.left_ee_pose, retargeted.right_ee_pose, left_gripper, right_gripper, ik_config or IKConfig())
    hand_confidence = np.stack([hand_pose.left_confidence[:count], hand_pose.right_confidence[:count]], axis=1)
    confidence = compute_confidence(ik.action, hand_confidence, retargeted.workspace_violation[:count], confidence_config or ConfidenceConfig())

    writer = PseudoEpisodeWriter(
        output_dir=output_dir,
        task=task,
        episode_id=episode_id,
        episode_index=int(str(episode_id).lstrip("0") or "0"),
        camera_names=["chest", "left_wrist", "right_wrist"],
        image_size=(int(metadata.get("width", frames[0].shape[1])), int(metadata.get("height", frames[0].shape[0]))),
    )
    zero_state = np.zeros(STATE_DIM, dtype=np.float32)
    for index in range(count):
        writer.add_pseudo_frame(
            timestamp=float(hand_pose.timestamps[index]),
            chest_image=frames[index],
            observation_state=zero_state,
            observation_ee_pose=_ee_pose16(retargeted.left_ee_pose[index], retargeted.right_ee_pose[index], left_gripper[index], right_gripper[index]),
            action=ik.action[index],
            confidence=float(confidence.confidence[index]),
            uncertainty_terms=confidence.uncertainty_terms[index],
            action_valid=bool(ik.valid[index]),
        )
    episode_dir = writer.close(
        metadata_extra={
            "source_human_episode": str(human_dir),
            "source_hand_pose": str(Path(hand_pose_dir).expanduser()),
            "ik_enabled": bool((ik_config or IKConfig()).enable),
        }
    )
    if not skip_validation:
        report = validate_pseudo_dataset(episode_dir)
        if not report.ok:
            raise ValueError("pseudo validation failed:\n" + report.format())
    return episode_dir
