# Pseudo Demonstration Generation

Phase 2 converts:

```text
human RGB episode -> hand pose -> retargeted OpenArm EE pose -> pseudo raw episode
```

The output schema matches Phase 1 raw episodes where possible:

```text
raw_pseudo/<task>/episode_<episode_id>/
├── metadata.json
├── data.jsonl
├── images/
├── arrays/
│   ├── observation_state.npy
│   ├── observation_ee_pose.npy
│   ├── action.npy
│   ├── confidence.npy
│   ├── uncertainty_terms.npy
│   └── timestamps.npy
```

Pseudo-specific behavior:

- `sample_type` is `pseudo`.
- `observation.images.chest` is the human RGB frame.
- wrist camera images are zero-padded.
- `observation.state` is zero.
- IK is disabled by default, so joint action is zero except gripper values and `action_valid=false`.
- confidence is computed from tracking uncertainty, IK residual, workspace violation, and temporal jump.

## Generate

```bash
python3 scripts/generate_pseudo_demo.py \
  --human-episode ~/datasets/openarm_il/raw_human/handover/episode_0001 \
  --hand-pose ~/datasets/openarm_il/hand_pose/handover/episode_0001 \
  --output-dir ~/datasets/openarm_il/raw_pseudo \
  --task handover \
  --episode-id 0001
```

## Validate

```bash
python3 scripts/validate_pseudo_demo.py \
  --raw-dir ~/datasets/openarm_il/raw_pseudo/handover/episode_0001
```

## Visualize

```bash
python3 scripts/visualize_pseudo_episode.py \
  --episode-dir ~/datasets/openarm_il/raw_pseudo/handover/episode_0001 \
  --save-dir ~/datasets/openarm_il/plots/pseudo_0001
```

## Mixed Export

```bash
python3 scripts/convert_to_lerobot.py \
  --real-dir ~/datasets/openarm_il/raw_real \
  --pseudo-dir ~/datasets/openarm_il/raw_pseudo \
  --output-dir ~/datasets/openarm_il/lerobot_pseudo_real
```

This preserves `sample_type` and `confidence` for downstream Phase 3 work.
