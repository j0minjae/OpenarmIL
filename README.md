# OpenarmXR 워크스페이스

VR 헤드셋(Pico / Meta Quest)을 이용한 OpenArm 양팔 로봇 텔레오퍼레이션 시스템.

## 패키지 구성

| 패키지 | 설명 |
|--------|------|
| `openarm_controller` | **자체 Python IK 솔버(SoT) + VR teleop 노드 (오픈소스)** |
| `openarm_description` | openarm v1.0 URDF/메쉬/RViz 설정 |
| `openarmx_description` | openarmx URDF/메쉬/RViz 설정 |
| `openarmx_teleop_vr` | VR UDP bridge + launch 파일 모음 |
| `openarmx_teleop_vr_apk` | VR 헤드셋용 APK (Pico, Meta Quest) |
| `openarm_ros2` | 로봇 bringup + hardware interface (ros2_control) |
| `openarm_can` | CAN 통신 라이브러리 |

## IK 솔버 종류

| 솔버 | 패키지 | 방식 | URDF | 특징 |
|------|--------|------|------|------|
| **openarm_controller** | `openarm_controller` | SoT (Stack of Tasks) | openarm_ 직접 | 오픈소스, q_home 수정 가능, remapper 불필요 |
| openarmx_arm_driver | `openarmx_teleop_vr` | 비공개 | openarmx_ 필요 | 바이너리, 수정 불가, remapper 필요 |

> 상세 IK 방법론은 `IK방법론.md` 참조

## 사전 요구사항

```bash
source /opt/ros/humble/setup.bash
pip3 install "numpy<2"
sudo apt install adb
# openarmx IK 사용 시에만 필요:
# pip3 install openarmx-arm-driver
```

## VR 헤드셋 APK 설치

### Pico
```bash
adb install openarmx_teleop_vr_apk/openarmx-vr-pico.apk
```

### Meta Quest
```bash
adb install openarmx_teleop_vr_apk/openarmx-vr-quest.apk
```

## 빌드

```bash
cd ~/Project/OpenarmXR
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

## 실행 방법

> launch 전에 잔류 프로세스 정리:
```bash
pkill -9 -f "ros2_control_node|controller_manager|rviz2|bridge_vr|vr_teleop|robot_state_publisher|spawner|openarmx_teleop|openarm_teleop"
```

### 1. 로봇 모델 시각화 (RViz + GUI 슬라이더)

```bash
ros2 launch openarmx_description display_openarmx.launch.py arm_type:=v10 bimanual:=true
ros2 launch openarm_description display_openarm.launch.py arm_type:=v10 bimanual:=true
```

### 2. VR 시뮬레이션 (RViz + fake hardware)

| 명령어 | IK 솔버 | 모델 |
|--------|---------|------|
| `ros2 launch openarm_controller teleop_sim.launch.py` | **openarm_controller (SoT)** | openarm |
| `ros2 launch openarmx_teleop_vr openarm_teleop_vr_sim.launch.py` | openarmx_arm_driver | openarm (변환 URDF) |
| `ros2 launch openarmx_teleop_vr openarmx_teleop_vr_sim.launch.py` | openarmx_arm_driver | openarmx |

### 3. 안전 테스트 (fake hardware + 실제 파이프라인)

실제 로봇 적용 전, CAN/모터 없이 전체 경로를 검증합니다.

**openarm_controller 사용 시:**
```bash
# 터미널 1
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    use_fake_hardware:=true \
    robot_controller:=forward_position_controller \
    controllers_file:=openarm_bimanual_controllers_vr_teleop.yaml

# 터미널 2
ros2 launch openarmx_teleop_vr openarm_controller_real.launch.py
```

**openarmx_arm_driver 사용 시:**
```bash
# 터미널 1
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    use_fake_hardware:=true \
    robot_controller:=forward_position_controller \
    controllers_file:=openarm_bimanual_controllers_vr_teleop.yaml

# 터미널 2
ros2 launch openarmx_teleop_vr openarm_teleop_vr_real.launch.py
```

**검증 항목:**
```bash
ros2 topic echo /joint_states --once | grep "name:" -A 16
ros2 topic echo /left_forward_position_controller/commands
ros2 topic hz /left_forward_position_controller/commands
```

### 4. 실제 로봇 VR 텔레오퍼레이션

**CAN 초기화 (공통):**
```bash
sudo ip link set can0 type can bitrate 1000000 dbitrate 5000000 fd on && sudo ip link set can0 up
sudo ip link set can1 type can bitrate 1000000 dbitrate 5000000 fd on && sudo ip link set can1 up
ip -details link show can0
ip -details link show can1
```

**openarm_controller 사용 (권장):**
```bash
# 터미널 1: bringup
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    use_fake_hardware:=false \
    robot_controller:=forward_position_controller \
    controllers_file:=openarm_bimanual_controllers_vr_teleop.yaml \
    right_can_interface:=can0 left_can_interface:=can1

# 터미널 2: VR teleop
ros2 launch openarmx_teleop_vr openarm_controller_real.launch.py
```

**openarmx_arm_driver 사용:**
```bash
# 터미널 1: bringup
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    use_fake_hardware:=false \
    robot_controller:=forward_position_controller \
    controllers_file:=openarm_bimanual_controllers_vr_teleop.yaml \
    right_can_interface:=can0 left_can_interface:=can1

# 터미널 2: VR teleop (remapper 포함)
ros2 launch openarmx_teleop_vr openarm_teleop_vr_real.launch.py
```

## 런치 파일 요약

| 런치 파일 | IK 솔버 | 용도 |
|-----------|---------|------|
| `openarm_controller/teleop_sim.launch.py` | openarm_controller (SoT) | 시뮬레이션 |
| `openarm_controller_real.launch.py` | openarm_controller (SoT) | **실제 로봇 (권장)** |
| `openarm_teleop_vr_sim.launch.py` | openarmx_arm_driver | 시뮬레이션 (변환 URDF) |
| `openarm_teleop_vr_real.launch.py` | openarmx_arm_driver | 실제 로봇 (remapper) |
| `openarmx_teleop_vr_sim.launch.py` | openarmx_arm_driver | 시뮬레이션 (openarmx) |

## 데이터 흐름

```
VR 헤드셋 (Pico / Meta Quest)
    │  UDP (port 5100)
    ▼
openarmx_teleop_bridge_vr_node (C++)
    │  ROS2 토픽 (PoseStamped, Float32, Bool)
    ▼
openarm_teleop_node (openarm_controller, SoT IK)
    │  Float64MultiArray (openarm_ prefix 직접 사용)
    ▼
forward_position_controller (ros2_control)
    │  관절 명령
    ▼
로봇 하드웨어 또는 fake hardware → joint_states → RViz
```
