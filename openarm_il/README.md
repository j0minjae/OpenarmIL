# OpenarmIL Phase 1: Real Demonstration Collection

`openarm_il` is a ROS2 Humble `ament_python` package for passive OpenArm V10 bimanual real-robot demonstration collection, raw episode validation, visualization, and offline LeRobot-style export for ACT imitation learning.

Phase 1 scope is intentionally narrow:

- OpenArm real robot demonstration recording
- Raw episode storage
- Dataset validation
- Headless visualization
- LeRobot-style ACT-ready export

Out of scope for Phase 1: human RGB collection, hand pose tracking, pseudo demonstrations, retargeting, GR00T, and VLA features.

## Install And Build

```bash
cd /home/home/Project/OpenarmIL/src
source /opt/ros/humble/setup.bash
colcon build --packages-select openarm_il
source install/setup.bash
```

Python-only checks can be run from the package root:

```bash
cd /home/home/Project/OpenarmIL/src/openarm_il
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -v
```

## Phase 1 사용법

아래 순서대로 진행하면 실제 OpenArm V10 bimanual 로봇 데모를 수집하고, raw episode 검증 후 ACT 학습용 LeRobot-style dataset으로 변환할 수 있습니다.

### 1. ROS2 환경 빌드

```bash
cd /home/home/Project/OpenarmIL/src
source /opt/ros/humble/setup.bash
colcon build --packages-select openarm_il
source install/setup.bash
```

엔트리포인트가 설치됐는지 확인합니다.

```bash
ros2 pkg executables openarm_il
```

정상 출력 예시는 다음과 같습니다.

```text
openarm_il collect_real_demo
openarm_il convert_to_lerobot
openarm_il inspect_topics
openarm_il validate_dataset
openarm_il visualize_episode
```

### 2. 설정 파일 확인

기본 설정 파일은 패키지 내부에 있습니다.

```text
openarm_il/config/real_collection.yaml
openarm_il/config/camera_topics.yaml
openarm_il/config/dataset_schema.yaml
```

주요 기본값:

- `action_source: next_state`
- `sync_tolerance_sec: 0.05`
- required streams: `joint_states`, `chest`
- optional streams: `left_wrist`, `right_wrist`, `actions`
- FK disabled by default: `fk.enable_fk: false`

로봇/카메라 토픽 이름이 실제 시스템과 다르면 `config/camera_topics.yaml`을 수정합니다.

### 3. 실제 로봇 bringup 및 카메라 실행

`openarm_il`은 로봇 명령을 publish하지 않는 passive recorder입니다. 먼저 별도 터미널에서 OpenArm bringup, ros2_control controller, RealSense camera driver를 실행해야 합니다.

필수 확인 토픽:

```bash
ros2 topic echo /joint_states --once
ros2 topic list | grep image_raw
```

### 4. 토픽 상태 점검

```bash
ros2 run openarm_il inspect_topics
```

필수 토픽은 다음 두 개입니다.

- `/joint_states`
- chest RGB camera topic: 기본값 `/camera/camera/color/image_raw`

left/right wrist camera와 action command topic은 optional입니다. wrist camera가 없으면 chest image와 같은 크기의 zero image가 저장됩니다.

### 5. Timed recording

지정한 시간 동안 자동으로 episode를 기록합니다.

```bash
ros2 run openarm_il collect_real_demo \
  --task handover \
  --episode-id 0001 \
  --duration 30 \
  --output-dir ~/datasets/openarm_il/raw_real
```

저장 경로:

```text
~/datasets/openarm_il/raw_real/handover/episode_0001/
```

### 6. Keyboard recording

키보드로 시작/종료를 제어합니다.

```bash
ros2 run openarm_il collect_real_demo \
  --task handover \
  --episode-id 0001 \
  --output-dir ~/datasets/openarm_il/raw_real \
  --keyboard
```

키 입력:

```text
s : start recording
q : stop and save
x : cancel episode
```

### 7. Raw episode 검증

단일 episode를 검증합니다.

```bash
cd /home/home/Project/OpenarmIL/src/openarm_il
python3 scripts/validate_dataset.py \
  --raw-dir ~/datasets/openarm_il/raw_real/handover/episode_0001
```

전체 raw dataset root를 검증할 수도 있습니다.

```bash
python3 scripts/validate_dataset.py \
  --raw-dir ~/datasets/openarm_il/raw_real
```

정상 출력 예시:

```text
ok: True
episodes: 1
frames: 900
```

### 8. Episode 시각화

GUI 없이 plot 파일로 저장합니다.

```bash
python3 scripts/visualize_episode.py \
  --episode-dir ~/datasets/openarm_il/raw_real/handover/episode_0001 \
  --save-dir /tmp/openarm_il_plots
```

생성 파일:

```text
/tmp/openarm_il_plots/trajectories.png
/tmp/openarm_il_plots/first_chest_frame.png
```

### 9. LeRobot-style dataset export

raw episode들을 ACT 학습용 local LeRobot-style dataset으로 변환합니다.

```bash
python3 scripts/convert_to_lerobot.py \
  --raw-dir ~/datasets/openarm_il/raw_real \
  --output-dir ~/datasets/openarm_il/lerobot_real
```

출력 구조:

```text
lerobot_real/
├── meta/
│   ├── info.json
│   └── episodes.jsonl
└── data/
    ├── frames.jsonl
    └── <task>/episode_<episode_id>/
```

### 10. 테스트

개발/수정 후 unit test를 실행합니다. 이 환경에서는 pytest plugin 충돌을 피하기 위해 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`을 사용합니다.

```bash
cd /home/home/Project/OpenarmIL/src/openarm_il
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -v
```

## Real Demo Collection

Inspect expected topics:

```bash
ros2 run openarm_il inspect_topics
```

Timed recording:

```bash
ros2 run openarm_il collect_real_demo \
  --task handover \
  --episode-id 0001 \
  --duration 30 \
  --output-dir ~/datasets/openarm_il/raw_real
```

Keyboard recording:

```bash
ros2 run openarm_il collect_real_demo \
  --task handover \
  --episode-id 0001 \
  --output-dir ~/datasets/openarm_il/raw_real \
  --keyboard
```

Keyboard controls are `s` start, `q` stop and save, and `x` cancel.

## Raw Episode Format

Episodes are saved under:

```text
raw_real/<task>/episode_<episode_id>/
```

Each episode contains `metadata.json`, `data.jsonl`, `images/<camera>/*.png`, and arrays for `observation_state`, `observation_ee_pose`, `action`, and `timestamps`.

## Validation, Visualization, Export

```bash
python3 scripts/validate_dataset.py --raw-dir ~/datasets/openarm_il/raw_real
python3 scripts/visualize_episode.py \
  --episode-dir ~/datasets/openarm_il/raw_real/handover/episode_0001 \
  --save-dir /tmp/openarm_il_plots
python3 scripts/convert_to_lerobot.py \
  --raw-dir ~/datasets/openarm_il/raw_real \
  --output-dir ~/datasets/openarm_il/lerobot_real
```

## Expected Topics

Defaults are configured in `config/camera_topics.yaml`:

- `/joint_states`
- `/camera/camera/color/image_raw`
- `/left_wrist_camera/color/image_raw`
- `/right_wrist_camera/color/image_raw`
- `/left_forward_position_controller/commands`
- `/right_forward_position_controller/commands`
- `/left_gripper_controller/joint_trajectory`
- `/right_gripper_controller/joint_trajectory`

## Troubleshooting

- RealSense camera not publishing: run `ros2 topic list` and confirm the camera driver is launched before recording.
- Missing wrist cameras: wrist cameras are optional; the recorder writes zero images matching the chest image size and logs missing optional streams.
- `/joint_states` not available: start OpenArm bringup first; this stream is required and frames are dropped until it is present.
- Action command topics unavailable: keep `action_source: next_state` in `config/real_collection.yaml`; this is the Phase 1 default.
- FK disabled: `observation.ee_pose` is zero-filled unless `fk.enable_fk` and FK frames are configured.
- Timestamp sync drops too many frames: increase `sync_tolerance_sec` or reduce `record_rate_hz` in `config/real_collection.yaml`.

Additional docs:

- `docs/DATA_COLLECTION.md`
- `docs/LEROBOT_SCHEMA.md`
- `docs/ACT_TRAINING_NOTES.md`

## Phase 2: Human RGB to Pseudo Robot Demonstration

Phase 2 converts human RGB manipulation recordings into pseudo OpenArm demonstrations. Human RGB frames are not used directly for policy learning; they are only used to extract hand pose, which is retargeted into OpenArm-compatible pseudo robot observations/actions.

### 1. Record human RGB

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

### 2. Import precomputed hand pose

```bash
python3 scripts/extract_hand_pose.py \
  --backend precomputed \
  --input ~/datasets/openarm_il/raw_human/handover/episode_0001 \
  --precomputed-file ~/datasets/openarm_il/precomputed_hand_pose/handover_0001.jsonl \
  --output ~/datasets/openarm_il/hand_pose/handover/episode_0001
```

HaMeR is intentionally not bundled. Export HaMeR/MediaPipe results to the documented JSONL format and import with `--backend precomputed`.

### 3. Generate pseudo demo

```bash
python3 scripts/generate_pseudo_demo.py \
  --human-episode ~/datasets/openarm_il/raw_human/handover/episode_0001 \
  --hand-pose ~/datasets/openarm_il/hand_pose/handover/episode_0001 \
  --output-dir ~/datasets/openarm_il/raw_pseudo \
  --task handover \
  --episode-id 0001
```

Default IK is disabled. The pipeline still writes `action.npy` with shape `[T,16]`, marks `action_valid=false`, and stores confidence/uncertainty arrays.

### 4. Validate and visualize pseudo demo

```bash
python3 scripts/validate_pseudo_demo.py \
  --raw-dir ~/datasets/openarm_il/raw_pseudo/handover/episode_0001

python3 scripts/visualize_pseudo_episode.py \
  --episode-dir ~/datasets/openarm_il/raw_pseudo/handover/episode_0001 \
  --save-dir ~/datasets/openarm_il/plots/pseudo_0001
```

### 5. Export real and pseudo together

```bash
python3 scripts/convert_to_lerobot.py \
  --real-dir ~/datasets/openarm_il/raw_real \
  --pseudo-dir ~/datasets/openarm_il/raw_pseudo \
  --output-dir ~/datasets/openarm_il/lerobot_pseudo_real
```

Additional Phase 2 docs:

- `docs/HUMAN_RGB_COLLECTION.md`
- `docs/HAND_POSE_FORMAT.md`
- `docs/RETARGETING.md`
- `docs/PSEUDO_DEMONSTRATION.md`
