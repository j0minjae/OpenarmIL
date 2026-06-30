# ACT Training Notes

Phase 1 exports real OpenArm V10 bimanual demonstrations for ACT-style behavior cloning.

Use `action_source: next_state` for the first reliable dataset. In this mode each frame action is the next synchronized robot state, giving a 16D target aligned with `observation.state`.

Validate before training:

```bash
python3 scripts/validate_dataset.py --raw-dir ~/datasets/openarm_il/raw_real
python3 scripts/convert_to_lerobot.py \
  --raw-dir ~/datasets/openarm_il/raw_real \
  --output-dir ~/datasets/openarm_il/lerobot_real
```

Keep Phase 1 datasets real-only. Do not mix pseudo demonstrations, retargeted human data, or VLA labels into this dataset root.
