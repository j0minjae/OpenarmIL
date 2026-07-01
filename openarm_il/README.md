# OpenarmIL Phase 1: Real Demonstration Collection

`openarm_il` is a ROS2 Humble `ament_python` package for passive OpenArm V10 bimanual real-robot demonstration collection, raw episode validation, visualization, and offline LeRobot-style export for ACT imitation learning.

The current Phase 1 interface also exposes an `OpenArmRobot` adapter for LeRobot `record`-style collection. LeRobot is not installed in this workspace, so the integration is implemented through a local compatibility shim and mockable Robot API instead of depending on live LeRobot imports during tests.

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

### 0. LeRobot Robot API 기반 수집 경로

새 SRS 기준의 권장 경로는 `OpenArmRobot`을 LeRobot `record`에서 사용하는 것입니다.

```bash
cd /home/home/Project/OpenarmIL/src
source /opt/ros/humble/setup.bash
colcon build --packages-select openarm_il
source install/setup.bash
ros2 run openarm_il check_robot --mock
ros2 run openarm_il print_observation --mock
```

Python factory:

```python
from openarm_il.lerobot_compat import create_openarm_robot

robot = create_openarm_robot()
robot.connect()
obs = robot.read_observation()
robot.send_action(action_16d)
robot.disconnect()
```

LeRobot이 설치된 환경에서는 해당 버전의 `record` CLI/registry 방식에 맞춰 `openarm_il.openarm_robot.OpenArmRobot` 또는 `openarm_il.lerobot_compat.create_openarm_robot`을 등록해 사용합니다. 현재 로컬 환경에는 LeRobot Python package가 없어 실제 LeRobot CLI smoke test는 수행하지 않았습니다.

관련 문서:

- `docs/PHASE1_OVERVIEW.md`
- `docs/LEROBOT_RECORD.md`
- `docs/OPENARM_ROBOT_API.md`
- `docs/ROS_TOPICS.md`
- `docs/TROUBLESHOOTING.md`

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

`openarm_il`은 로봇 명령을 publish하지 않는 passive recorder입니다. 먼저 별도 터미널에서 OpenArm bringup, ros2_control controller, 카메라 드라이버를 실행해야 합니다.

**Robot data 수집용 카메라 bringup (3대)**

```bash
ros2 launch openarm_il robot_camera_bringup.launch.py
```

발행 토픽:
- `/chest_camera/color/image_raw`
- `/left_wrist_camera/color/image_raw`
- `/right_wrist_camera/color/image_raw`

**Human data 수집용 카메라 bringup (1대 + recorder)**

robot data 수집과 동시에 실행하면 안 됩니다 (동일 물리 카메라 serial 317222072848 충돌).

```bash
ros2 launch openarm_il human_camera_bringup.launch.py \
    task_name:=handover \
    output_dir:=~/datasets/openarm_human_demo
```

발행 토픽: `/human_camera/color/image_raw`
키 조작: `SPACE` 녹화 시작/중지, `q` / `ESC` 종료

필수 토픽 확인:

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
- chest RGB camera topic: 기본값 `/chest_camera/color/image_raw`

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

## 카메라 Bringup 런치파일

카메라 bringup은 용도에 따라 두 런치파일로 완전히 분리되어 있습니다.
**두 런치파일을 동시에 실행하면 안 됩니다** — serial 317222072848 카메라를 공유하므로 USB 디바이스 충돌이 발생합니다.

### Robot data 수집용 (3대)

```bash
ros2 launch openarm_il robot_camera_bringup.launch.py
```

| 카메라 | 시리얼 번호 | 토픽 |
|--------|------------|------|
| `chest_camera` | 332322072253 | `/chest_camera/color/image_raw` |
| `left_wrist_camera` | 317222072848 | `/left_wrist_camera/color/image_raw` |
| `right_wrist_camera` | 327122079310 | `/right_wrist_camera/color/image_raw` |

### Human data 수집용 (1대 + recorder)

robot data 수집 시 left_wrist_camera로 쓰던 물리 카메라 1대를 `human_camera`라는 이름으로 재사용하며, space bar로 start/stop하는 recorder 노드를 함께 기동합니다.

```bash
ros2 launch openarm_il human_camera_bringup.launch.py \
    task_name:=handover \
    output_dir:=~/datasets/openarm_human_demo
```

| 런치 인자 | 기본값 | 설명 |
|-----------|--------|------|
| `task_name` | `default_task` | 에피소드 저장 경로 내 task 레이블 |
| `output_dir` | `~/datasets/openarm_human_demo` | 에피소드 루트 디렉토리 |
| `monitor` | `false` | 에피소드 저장 후 마지막 프레임 미리보기 |

발행 토픽: `/human_camera/color/image_raw`
키 조작: `SPACE` 녹화 시작/중지, `q` / `ESC` 종료

### 확정 카메라 파라미터

| 파라미터 | 값 | 근거 |
|----------|-----|------|
| 해상도 | 424×240 | USB2 환경에서 640×480×15fps×3대는 대역폭 초과로 disconnect 발생 → 최소 안정 해상도 확정 |
| fps | 15 | USB 대역폭 제약 |
| 포맷 | RGB8 | RealSense D435 기본 컬러 포맷 |
| enable_depth | false | 불필요한 스트림 차단으로 대역폭 절약 |
| enable_infra1/2 | false | 〃 |
| enable_rgbd | false | 〃 |
| enable_sync | false | 〃 |
| align_depth.enable | false | 〃 |
| pointcloud.enable | false | 〃 |
| rgb_camera.global_time_enabled | 기본값(true) | 카메라 간 타임스탬프 정합성을 위해 명시적으로 건드리지 않음 |

재시작 시 이전 프로세스를 먼저 정리합니다.

```bash
pkill -9 -f "realsense"
```

## Troubleshooting

**"Frames didn't arrived within 5 seconds" 경고가 반복되는 경우**

USB 대역폭 부족이 원인입니다. 640×480×15fps×3대는 단일 USB 버스를 포화시킵니다. 현재 런치파일은 424×240×15fps로 고정되어 있습니다. 카메라 3대를 서로 다른 USB 컨트롤러에 분산 연결하면 해상도를 높일 수 있습니다.

```bash
lsusb -t  # USB 컨트롤러 분산 여부 확인
```

**USB autosuspend로 인한 주기적 disconnect**

D435 자체는 udev 규칙(`/etc/udev/rules.d/99-realsense-usb-power.rules`, `idVendor=8086 idProduct=0b07`)으로 autosuspend가 비활성화되어 있습니다. 그러나 상위 USB 허브의 autosuspend가 `auto`로 남아있으면 주기적으로 disconnect가 발생할 수 있습니다. 세션마다 아래 명령으로 허브 경로를 확인하고 필요시 수동으로 고정합니다(영구 적용 아님).

```bash
cat /sys/bus/usb/devices/<hub-path>/power/control   # auto 이면 suspend 활성
echo on | sudo tee /sys/bus/usb/devices/<hub-path>/power/control
```

**wrist/human 카메라 이미지가 수신되지 않는 경우**

RealSense는 `BEST_EFFORT` QoS로 publish합니다. subscriber가 `RELIABLE` QoS를 사용하면 메시지를 수신하지 못합니다. `collect_real_demo`는 `qos_profile_sensor_data`(BEST_EFFORT)를 사용하도록 수정되어 있습니다. 다른 subscriber를 추가할 때도 동일하게 적용해야 합니다.

**토픽은 존재하지만 이미지가 안 보이는 경우**

이전 realsense 프로세스가 남아 동일 시리얼 번호 카메라를 두 노드가 점유하는 경우입니다. `pkill -9 -f "realsense"` 후 재launch합니다.

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

## Phase 3: ACT Pseudo-Real Co-Training Wrapper

Phase 3 trains ACT on exported real and pseudo robot demonstrations while keeping ACT internals unchanged. The wrapper preserves `sample_type` and `confidence`, builds real/pseudo-balanced batches, and applies:

```text
L = lambda_real * L_real + lambda_pseudo * L_pseudo
```

Default weights:

```text
lambda_real = 1.0
lambda_pseudo = 0.3
```

Dataset statistics:

```bash
python3 training/dataset_statistics.py \
  --dataset-path ~/datasets/openarm_il/lerobot_pseudo_real
```

Train real only:

```bash
python3 training/train_act_pseudo_real.py \
  --config config/phase3_act_real_only.yaml
```

Train pseudo-real:

```bash
python3 training/train_act_pseudo_real.py \
  --config config/phase3_act_pseudo_real.yaml
```

Run ablations:

```bash
python3 training/run_ablation.py \
  --config config/phase3_ablation.yaml
```

Evaluate:

```bash
python3 training/evaluate_act.py \
  --checkpoint runs/openarm_il_phase3/best.ckpt \
  --dataset-path ~/datasets/openarm_il/lerobot_pseudo_real
```

Phase 3 documentation:

- `docs/PHASE3_ACT_COTRAINING.md`
