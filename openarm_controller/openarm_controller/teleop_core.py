"""Teleop core logic — VR input to IK target, matching openarmx behavior."""

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pinocchio as pin
from scipy.spatial.transform import Rotation

from .ik_solver import PositionIKSolver
from .weighted_filter import WeightedMovingFilter


@dataclass
class ArmState:
    active: bool = False
    anchor_initialized: bool = False
    init_vr_pos: np.ndarray = None
    init_vr_rot: np.ndarray = None
    init_ee_pos: np.ndarray = None
    init_ee_rot: np.ndarray = None
    current_vr_pos: np.ndarray = None
    current_vr_rot: np.ndarray = None
    vr_pose_received: bool = False
    grip_value: float = 0.0
    trigger_value: float = 0.0

    def __post_init__(self):
        self.init_vr_pos = np.zeros(3)
        self.init_vr_rot = np.eye(3)
        self.init_ee_pos = np.zeros(3)
        self.init_ee_rot = np.eye(3)
        self.current_vr_pos = np.zeros(3)
        self.current_vr_rot = np.eye(3)


@dataclass
class TeleopResult:
    target_q: Optional[np.ndarray] = None
    left_active: bool = False
    right_active: bool = False


class TeleopCore:
    """Manages VR→robot teleop: grip activation, anchor, frame transform, IK.

    Matches openarmx PinocchioTeleopCore behavior:
    - Grip > threshold → activate (no motion detection)
    - Anchor set once per arm, never re-anchored
    - VR delta transformed through init_EE_rotation
    - Inactive arm holds current q
    """

    def __init__(self, ik_solver: PositionIKSolver, grip_threshold: float = 0.5,
                 q_filter_weights=(0.4, 0.3, 0.2, 0.1),
                 ee_frame_offset=None, logger=None):
        self.ik = ik_solver
        self.grip_threshold = grip_threshold
        self._logger = logger
        self.arms = [ArmState(), ArmState()]
        self.q_filter = WeightedMovingFilter(q_filter_weights, ik_solver.nq)
        self.joint_q = np.zeros(ik_solver.nq)
        self.joint_received = False
        # EE frame offset: corrects joint7 rotation to match openarmx link7_pico frame
        if ee_frame_offset is not None:
            self.ee_frame_offset = np.asarray(ee_frame_offset, dtype=np.float64).reshape(3, 3)
        else:
            self.ee_frame_offset = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]], dtype=np.float64)

    def update_joint_states(self, q: np.ndarray):
        self.joint_q = np.asarray(q, dtype=np.float64)
        self.joint_received = True

    def update_vr_pose(self, arm_idx: int, position: np.ndarray, orientation_xyzw: tuple):
        arm = self.arms[arm_idx]
        arm.current_vr_pos = np.asarray(position, dtype=np.float64)
        quat = np.array([orientation_xyzw[0], orientation_xyzw[1],
                         orientation_xyzw[2], orientation_xyzw[3]], dtype=np.float64)
        norm = np.linalg.norm(quat)
        if norm > 1e-8:
            quat /= norm
        arm.current_vr_rot = Rotation.from_quat(quat).as_matrix()  # scipy [x,y,z,w]
        arm.vr_pose_received = True

    def update_grip(self, arm_idx: int, value: float):
        self.arms[arm_idx].grip_value = max(0.0, min(1.0, value))

    def update_trigger(self, arm_idx: int, value: float):
        self.arms[arm_idx].trigger_value = max(0.0, min(1.0, value))

    def step(self) -> TeleopResult:
        if not self.joint_received:
            return TeleopResult()

        # FK for current EE positions
        ee_transforms = self.ik.get_end_effector_transforms(self.joint_q)

        # Grip activation (no motion detection, anchor set once)
        any_active = False
        for i in range(2):
            arm = self.arms[i]
            grip_active = arm.grip_value > self.grip_threshold and arm.vr_pose_received

            if grip_active and not arm.active:
                arm.init_vr_pos = arm.current_vr_pos.copy()
                arm.init_vr_rot = arm.current_vr_rot.copy()
                arm.init_ee_pos = ee_transforms[i][:3, 3].copy()
                arm.init_ee_rot = ee_transforms[i][:3, :3].copy()
                self.q_filter.reset()
                for buf in self.q_filter.buffer:
                    buf[:] = self.joint_q
                self.q_filter.count = self.q_filter.window_size
                arm.active = True
                if self._logger:
                    self._logger.info(f'{"Left" if i == 0 else "Right"} arm activated')

            if not grip_active and arm.active:
                arm.active = False
                if self._logger:
                    self._logger.info(f'{"Left" if i == 0 else "Right"} arm deactivated')

            if arm.active:
                any_active = True

        if not any_active:
            return TeleopResult()

        # Compute targets
        targets = []
        for i in range(2):
            if self.arms[i].active:
                targets.append(self._compute_target(i))
            else:
                targets.append(ee_transforms[i])

        # IK solve
        raw_q, error = self.ik.solve(targets[0], targets[1], self.joint_q)

        if not np.all(np.isfinite(raw_q)):
            return TeleopResult()

        # Filter
        filtered_q = self.q_filter.filter(raw_q)

        # Inactive arm keeps current q
        if not self.arms[0].active:
            filtered_q[:7] = self.joint_q[:7]
        if not self.arms[1].active:
            filtered_q[7:] = self.joint_q[7:]

        return TeleopResult(
            target_q=filtered_q,
            left_active=self.arms[0].active,
            right_active=self.arms[1].active,
        )

    def _compute_target(self, arm_idx: int) -> np.ndarray:
        arm = self.arms[arm_idx]
        # Apply ee_frame_offset to match openarmx link7_pico mapping
        R_map = arm.init_ee_rot @ self.ee_frame_offset

        # Position: R_map × vr_delta
        vr_delta_pos = arm.current_vr_pos - arm.init_vr_pos
        world_delta = R_map @ vr_delta_pos

        # Rotation: conjugate through offset, then apply relative to actual EE
        delta_rot = arm.init_vr_rot.T @ arm.current_vr_rot
        remapped_rot = self.ee_frame_offset @ delta_rot @ self.ee_frame_offset.T

        # Re-orthogonalize
        U, _, Vt = np.linalg.svd(remapped_rot)
        clean_rot = U @ Vt
        if np.linalg.det(clean_rot) < 0:
            U[:, -1] *= -1
            clean_rot = U @ Vt

        T = np.eye(4)
        T[:3, 3] = arm.init_ee_pos + world_delta
        T[:3, :3] = arm.init_ee_rot @ clean_rot
        return T
