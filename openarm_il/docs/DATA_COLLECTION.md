# OpenArmIL Real Data Collection

Phase 1 records passive real robot demonstrations from OpenArm V10 bimanual ROS2 topics.

## Safety Boundary

`openarm_il` does not publish robot commands. It only subscribes to `/joint_states`, RGB image topics, and optional command topics for observation.

## Topic Check

```bash
source /opt/ros/humble/setup.bash
ros2 run openarm_il inspect_topics
```

Required streams are `/joint_states` and the chest RGB camera. Wrist cameras and action command topics are optional.

## Timed Recording

```bash
ros2 run openarm_il collect_real_demo \
  --task handover \
  --episode-id 0001 \
  --duration 30 \
  --output-dir ~/datasets/openarm_il/raw_real
```

## Keyboard Recording

```bash
ros2 run openarm_il collect_real_demo \
  --task handover \
  --episode-id 0001 \
  --output-dir ~/datasets/openarm_il/raw_real \
  --keyboard
```

Controls:

```text
s : start recording
q : stop and save
x : cancel episode
```

## Output

Episodes are written under `raw_real/<task>/episode_<episode_id>/` with metadata, JSONL frame rows, PNG images, and NumPy arrays.
