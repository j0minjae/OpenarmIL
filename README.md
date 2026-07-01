# OpenarmIL Workspace

OpenArm V10 bimanual robot 관련 ROS2 패키지와 imitation learning 데이터 수집 패키지를 포함하는 워크스페이스입니다.

## 패키지 구성

| 패키지 | 설명 |
|--------|------|
| `openarm_il` | Phase 1 real robot demonstration collection, validation, visualization, LeRobot-style export |
| `openarm_human_demo` | 로봇과 무관한 독립 human demonstration 영상 수집 도구 (space bar 토글, D435) |
| `openarm_controller` | Python IK solver and VR teleop node |
| `openarm_description` | OpenArm URDF/mesh/RViz assets |
| `openarm_ros2` | OpenArm bringup and ros2_control hardware interface |
| `openarm_can` | CAN communication library |
| `openarmx_description` | OpenArmX description assets |
| `openarmx_teleop_vr` | VR teleoperation utilities |

상세 Phase 1 문서는 `openarm_il/README.md`를 기준으로 관리합니다. 새 LeRobot `record` 기반 Robot API 경로는 `openarm_il/docs/LEROBOT_RECORD.md`와 `openarm_il/docs/OPENARM_ROBOT_API.md`에 정리되어 있습니다.

## Phase 1 사용법

Phase 1은 실제 OpenArm V10 bimanual 로봇 demonstration을 passive 방식으로 수집하고, raw episode를 검증/시각화한 뒤 ACT 학습용 LeRobot-style dataset으로 변환합니다.

Phase 1에서 하지 않는 것:

- human RGB collection
- hand pose tracking
- pseudo demonstration generation
- retargeting
- GR00T/VLA feature

### 1. 빌드

```bash
cd /home/home/Project/OpenarmIL/src
source /opt/ros/humble/setup.bash
colcon build --packages-select openarm_il
source install/setup.bash
```

설치된 실행 파일 확인:

```bash
ros2 pkg executables openarm_il
```

정상 출력 예시:

```text
openarm_il collect_real_demo
openarm_il convert_to_lerobot
openarm_il inspect_topics
openarm_il validate_dataset
openarm_il visualize_episode
```

### 2. 설정 파일 확인

기본 설정 파일:

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

실제 카메라/컨트롤러 토픽이 다르면 `openarm_il/config/camera_topics.yaml`을 먼저 수정합니다.

### 3. 토픽 상태 점검

OpenArm bringup, ros2_control controller, RealSense camera driver를 먼저 실행한 뒤 확인합니다.

```bash
ros2 run openarm_il inspect_topics
```

필수 토픽:

- `/joint_states`
- chest RGB camera topic, 기본값 `/camera/camera/color/image_raw`

`openarm_il`은 recorder이며 로봇 command를 publish하지 않습니다.

### 4. Timed recording

```bash
ros2 run openarm_il collect_real_demo \
  --task handover \
  --episode-id 0001 \
  --duration 30 \
  --output-dir ~/datasets/openarm_il/raw_real
```

저장 위치:

```text
~/datasets/openarm_il/raw_real/handover/episode_0001/
```

### 5. Keyboard recording

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

### 6. Raw episode 검증

```bash
cd /home/home/Project/OpenarmIL/src/openarm_il
python3 scripts/validate_dataset.py \
  --raw-dir ~/datasets/openarm_il/raw_real/handover/episode_0001
```

전체 raw dataset root 검증:

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

### 7. Episode 시각화

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

### 8. LeRobot-style dataset export

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

### 9. 테스트

```bash
cd /home/home/Project/OpenarmIL/src/openarm_il
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -v
```

## 데이터 수집 런치파일 실행 방법

세 가지 독립적인 데이터 수집 경로가 있습니다. 서로 다른 물리 카메라/토픽을
쓰지 않는 한 **동시에 실행하지 마십시오** (특히 아래 첫 두 개는 left_wrist_camera와
human_camera가 동일한 물리 카메라, serial 317222072848을 공유합니다).

**1. 사람 시연 영상만 단독 수집** (로봇/teleop 파이프라인과 무관, `openarm_human_demo`)

```bash
ros2 launch openarm_human_demo human_data_collection.launch.py \
    task_name:=test_task \
    output_dir:=~/datasets/openarm_human_demo
```

상세: `openarm_human_demo/README.md`

**2. Chest 카메라 1대로 사람 시연 수집** (`openarm_il`, robot data 수집용 카메라와 serial 공유하므로 동시 실행 금지)

```bash
ros2 launch openarm_il human_camera_bringup.launch.py \
    task_name:=handover \
    output_dir:=~/datasets/openarm_human_demo
```

**3. Quest3 teleop 중 로봇 데모 수집** (카메라 3대 + OpenArm CAN-FD bringup + Quest3 VR teleop + recorder를 한 번에 실행, `openarm_il`)

```bash
sudo ip link set can0 type can bitrate 1000000 dbitrate 5000000 fd on && sudo ip link set can0 up
sudo ip link set can1 type can bitrate 1000000 dbitrate 5000000 fd on && sudo ip link set can1 up
ip -details link show can0
ip -details link show can1


ros2 launch openarm_il robot_data_collection.launch.py \
    task_name:=pick_and_place \
    output_dir:=~/datasets/openarm_il/raw_teleop \
    right_can_interface:=can0 \
    left_can_interface:=can1
```

공통 조작: `SPACE`로 녹화 시작/중지(전역 핫키, 터미널 포커스 무관), `q`/`ESC`로
종료, headless 기본 + 터미널 벨(시작 1회/종료 2회) 피드백. 저장 포맷/토픽/검증
절차 상세는 `openarm_il/README.md`의 "Robot Teleop Data Collection" 절을
참고합니다.

## Troubleshooting

- RealSense camera not publishing: camera driver 실행 여부와 `ros2 topic list | grep image_raw`를 확인합니다.
- Missing wrist cameras: optional stream이므로 zero image로 padding됩니다.
- `/joint_states` not available: OpenArm bringup과 controller 상태를 먼저 확인합니다.
- Action command topics unavailable: Phase 1 기본값인 `action_source: next_state`를 사용합니다.
- FK disabled: 기본적으로 `observation.ee_pose`는 zero-filled입니다.
- Sync drops too many frames: `sync_tolerance_sec`를 키우거나 `record_rate_hz`를 낮춥니다.

## Phase 2 요약

Phase 2는 human RGB를 직접 학습 데이터로 쓰지 않고, hand pose 추출용으로만 사용합니다. 최종 산출물은 Phase 1과 같은 raw episode schema를 따르는 `raw_pseudo` dataset입니다.

기본 흐름:

```bash
cd /home/home/Project/OpenarmIL/src/openarm_il

python3 scripts/record_human_rgb.py \
  --camera /dev/video0 \
  --task handover \
  --episode-id 0001 \
  --output-dir ~/datasets/openarm_il/raw_human \
  --duration 30

python3 scripts/extract_hand_pose.py \
  --backend precomputed \
  --input ~/datasets/openarm_il/raw_human/handover/episode_0001 \
  --precomputed-file ~/datasets/openarm_il/precomputed_hand_pose/handover_0001.jsonl \
  --output ~/datasets/openarm_il/hand_pose/handover/episode_0001

python3 scripts/generate_pseudo_demo.py \
  --human-episode ~/datasets/openarm_il/raw_human/handover/episode_0001 \
  --hand-pose ~/datasets/openarm_il/hand_pose/handover/episode_0001 \
  --output-dir ~/datasets/openarm_il/raw_pseudo \
  --task handover \
  --episode-id 0001

python3 scripts/validate_pseudo_demo.py \
  --raw-dir ~/datasets/openarm_il/raw_pseudo/handover/episode_0001

python3 scripts/convert_to_lerobot.py \
  --real-dir ~/datasets/openarm_il/raw_real \
  --pseudo-dir ~/datasets/openarm_il/raw_pseudo \
  --output-dir ~/datasets/openarm_il/lerobot_pseudo_real
```

상세 문서:

- `openarm_il/docs/HUMAN_RGB_COLLECTION.md`
- `openarm_il/docs/HAND_POSE_FORMAT.md`
- `openarm_il/docs/RETARGETING.md`
- `openarm_il/docs/PSEUDO_DEMONSTRATION.md`

## Phase 3 요약

Phase 3는 LeRobot-compatible real/pseudo dataset을 ACT 학습 파이프라인에 넣기 위한 wrapper입니다. ACT architecture, Transformer, CVAE, encoder/decoder, action chunking은 수정하지 않습니다.

기본 명령:

```bash
cd /home/home/Project/OpenarmIL/src/openarm_il

python3 training/dataset_statistics.py \
  --dataset-path ~/datasets/openarm_il/lerobot_pseudo_real

python3 training/train_act_pseudo_real.py \
  --config config/phase3_act_real_only.yaml

python3 training/train_act_pseudo_real.py \
  --config config/phase3_act_pseudo_real.yaml

python3 training/run_ablation.py \
  --config config/phase3_ablation.yaml

python3 training/evaluate_act.py \
  --checkpoint runs/openarm_il_phase3/best.ckpt \
  --dataset-path ~/datasets/openarm_il/lerobot_pseudo_real
```

상세 문서:

- `openarm_il/docs/PHASE3_ACT_COTRAINING.md`
