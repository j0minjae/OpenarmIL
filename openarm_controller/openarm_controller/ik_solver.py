"""Position IK solver using pinocchio — Stack of Tasks (SoT) approach.

Matches openarmx behavior:
  Level 1: Orientation task (3D) — solved first (highest priority)
  Level 2: Position task (3D) — solved in orientation null-space
  Level 3: Joint regularization — toward q_home in remaining null-space

1-step per call. Convergence happens over multiple control cycles.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pinocchio as pin


@dataclass
class IKConfig:
    damping: float = 0.05
    position_weight: float = 50.0
    rotation_weight: float = 1.0
    joint_regularization_weight: float = 0.2
    joint3_regularization_weight: float = 0.05
    joint4_regularization_weight: float = 0.12
    q_home: Optional[np.ndarray] = None


class PositionIKSolver:
    """Hierarchical IK solver (Stack of Tasks, 1-step per call).

    Level 1: Orientation — highest priority
    Level 2: Position — in orientation null-space
    Level 3: Joint regularization — in remaining null-space
    """

    def __init__(
        self,
        urdf_path: str,
        left_ee_frame: str = "openarm_left_joint7",
        right_ee_frame: str = "openarm_right_joint7",
        locked_joints: Optional[List[str]] = None,
        config: Optional[IKConfig] = None,
    ):
        self.config = config or IKConfig()

        self.model, self.data = self._load_model(urdf_path, locked_joints or [
            "openarm_left_finger_joint1", "openarm_left_finger_joint2",
            "openarm_right_finger_joint1", "openarm_right_finger_joint2",
        ])
        self.nq = self.model.nq

        self.ee_joint_ids = []
        for name in [left_ee_frame, right_ee_frame]:
            if self.model.existJointName(name):
                self.ee_joint_ids.append(self.model.getJointId(name))
            else:
                raise ValueError(f"Joint not found: {name}")

        self.q_lower = self.model.lowerPositionLimit
        self.q_upper = self.model.upperPositionLimit

        self._build_regularization_weights()

        if self.config.q_home is not None:
            self.q_home = np.asarray(self.config.q_home, dtype=np.float64)
        else:
            self.q_home = np.zeros(self.nq, dtype=np.float64)

    def _load_model(self, urdf_path: str, locked_joints: List[str]):
        full_model = pin.buildModelFromUrdf(urdf_path)
        joints_to_lock = []
        for name in locked_joints:
            if full_model.existJointName(name):
                joints_to_lock.append(full_model.getJointId(name))
        q_ref = np.zeros(full_model.nq)
        reduced = pin.buildReducedModel(full_model, joints_to_lock, q_ref)
        return reduced, pin.Data(reduced)

    def _build_regularization_weights(self):
        n_arms = len(self.ee_joint_ids)
        arm_nq = self.nq // max(n_arms, 1)
        self.reg_weights = np.zeros(self.nq, dtype=np.float64)
        for a in range(n_arms):
            for j in range(arm_nq):
                w = self.config.joint_regularization_weight
                if j == 2:
                    w = self.config.joint3_regularization_weight
                if j == 3:
                    w = self.config.joint4_regularization_weight
                self.reg_weights[a * arm_nq + j] = w

    def get_end_effector_transforms(self, q: np.ndarray):
        pin.forwardKinematics(self.model, self.data, q)
        transforms = []
        for jid in self.ee_joint_ids:
            T = np.eye(4)
            T[:3, :3] = self.data.oMi[jid].rotation
            T[:3, 3] = self.data.oMi[jid].translation
            transforms.append(T)
        return transforms

    def solve(
        self,
        left_target: np.ndarray,
        right_target: np.ndarray,
        current_q: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        targets = [left_target, right_target]
        n_arms = len(self.ee_joint_ids)
        arm_nq = self.nq // n_arms
        cfg = self.config
        d = cfg.damping

        pin.forwardKinematics(self.model, self.data, current_q)
        pin.computeJointJacobians(self.model, self.data, current_q)

        # Compute errors and Jacobians per arm
        J_rot = np.zeros((3 * n_arms, self.nq))
        J_pos = np.zeros((3 * n_arms, self.nq))
        e_rot = np.zeros(3 * n_arms)
        e_pos = np.zeros(3 * n_arms)

        for i in range(n_arms):
            current_se3 = self.data.oMi[self.ee_joint_ids[i]]
            target_se3 = pin.SE3(targets[i][:3, :3], targets[i][:3, 3])
            log6 = pin.log6(current_se3.actInv(target_se3)).vector

            J_full = pin.getJointJacobian(
                self.model, self.data, self.ee_joint_ids[i], pin.LOCAL)
            J_arm = J_full[:, arm_nq * i: arm_nq * (i + 1)]

            e_rot[3*i:3*(i+1)] = log6[:3] * cfg.rotation_weight
            e_pos[3*i:3*(i+1)] = log6[3:] * cfg.position_weight
            J_rot[3*i:3*(i+1), arm_nq*i:arm_nq*(i+1)] = J_arm[:3] * cfg.rotation_weight
            J_pos[3*i:3*(i+1), arm_nq*i:arm_nq*(i+1)] = J_arm[3:] * cfg.position_weight

        # ─── Level 1: Orientation ───
        JJt1 = J_rot @ J_rot.T + d**2 * np.eye(3 * n_arms)
        dq1 = J_rot.T @ np.linalg.solve(JJt1, e_rot)
        J1_pinv = J_rot.T @ np.linalg.solve(JJt1, np.eye(3 * n_arms))
        N1 = np.eye(self.nq) - J1_pinv @ J_rot

        # ─── Level 2: Position (in orientation null-space) ───
        J_pos_proj = J_pos @ N1
        JJt2 = J_pos_proj @ J_pos_proj.T + d**2 * np.eye(3 * n_arms)
        dq2 = N1 @ (J_pos_proj.T @ np.linalg.solve(JJt2, e_pos))

        # ─── Level 3: Joint regularization (in remaining null-space) ───
        J_combined = np.vstack([J_rot, J_pos])
        JJtc = J_combined @ J_combined.T + d**2 * np.eye(6 * n_arms)
        Jc_pinv = J_combined.T @ np.linalg.solve(JJtc, np.eye(6 * n_arms))
        N12 = np.eye(self.nq) - Jc_pinv @ J_combined
        q_reg = -(self.reg_weights * (current_q - self.q_home))
        dq3 = N12 @ q_reg

        q = current_q + dq1 + dq2 + dq3
        q = np.clip(q, self.q_lower, self.q_upper)

        return q, np.concatenate([e_rot, e_pos])
