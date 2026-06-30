# Retargeting

Phase 2 retargets human wrist pose into pseudo OpenArm end-effector pose.

Formula:

```python
p_ee = p_ee_init + scale * R_align @ (p_wrist - p_wrist_init)
R_ee = R_offset @ R_wrist
```

The current implementation supports anchoring, scale, missing hand handling, and workspace clipping. RPY alignment fields are stored in config for compatibility; the initial implementation uses identity alignment.

Configuration:

```text
config/retargeting.yaml
```

Pseudo EE output is packed into `observation.ee_pose`:

```text
left_xyz[3], left_quat_xyzw[4], right_xyz[3], right_quat_xyzw[4], left_gripper[1], right_gripper[1]
```

Gripper values come from thumb-index keypoint distance.
