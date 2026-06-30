# Hand Pose Format

Phase 2 standardizes all hand pose sources into:

```text
hand_pose/<task>/episode_<episode_id>/
├── metadata.json
├── hand_pose.jsonl
└── arrays/
    ├── left_wrist_pose.npy
    ├── right_wrist_pose.npy
    ├── left_keypoints.npy
    ├── right_keypoints.npy
    ├── left_confidence.npy
    ├── right_confidence.npy
    └── timestamps.npy
```

Wrist pose format is `xyz + quat_xyzw`, shape `[T, 7]`.

Keypoint format is `[T, N, 3]`, default `N=21`.

Missing hands are represented by NaN wrist/keypoint arrays and confidence `0.0`.

## Precomputed Import

```bash
python3 scripts/extract_hand_pose.py \
  --backend precomputed \
  --input ~/datasets/openarm_il/raw_human/handover/episode_0001 \
  --precomputed-file ~/datasets/openarm_il/precomputed_hand_pose/handover_0001.jsonl \
  --output ~/datasets/openarm_il/hand_pose/handover/episode_0001
```

HaMeR is not bundled. Export HaMeR results to this JSONL shape and use the precomputed backend.
