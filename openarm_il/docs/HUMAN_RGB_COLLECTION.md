# Human RGB Collection

Phase 2 records human manipulation RGB only as an intermediate source for hand pose extraction.

Human RGB frames are not used directly for policy learning. The Phase 2 learning-facing output is a pseudo robot demonstration with the same raw schema as Phase 1.

## Timed Recording

```bash
python3 scripts/record_human_rgb.py \
  --camera /dev/video0 \
  --task handover \
  --episode-id 0001 \
  --output-dir ~/datasets/openarm_il/raw_human \
  --fps 30 \
  --width 640 \
  --height 480 \
  --duration 30
```

Output:

```text
raw_human/<task>/episode_<episode_id>/
├── metadata.json
├── frames/
└── timestamps.npy
```

The recorder uses OpenCV for the initial implementation. ROS2 image topic recording and video import are reserved for later adapters.
