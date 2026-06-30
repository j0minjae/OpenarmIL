# OpenArmIL LeRobot-Style Schema

The Phase 1 exporter writes an offline LeRobot-style directory that does not require internet access or installed LeRobot APIs.

Features:

```python
{
    "observation.images.chest": "image",
    "observation.images.left_wrist": "image",
    "observation.images.right_wrist": "image",
    "observation.state": "float32[16]",
    "observation.ee_pose": "float32[16]",
    "action": "float32[16]",
    "sample_type": "string",
    "confidence": "float32",
    "task": "string",
    "episode_index": "int64",
    "frame_index": "int64",
    "timestamp": "float64",
}
```

`observation.state` and `action` are ordered as left arm 7 joints, right arm 7 joints, left gripper, right gripper. If gripper joints are not present in `/joint_states`, the values are zero.

`observation.ee_pose` is zero-filled unless FK is explicitly enabled and configured.
