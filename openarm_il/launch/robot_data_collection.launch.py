# Robot teleoperation 데이터 수집 런치파일
#
# 3대 카메라(chest/left_wrist/right_wrist) bringup + OpenArm 실물 bringup
# (CAN-FD, use_fake_hardware:=false) + Quest3 VR teleop + robot_data_recorder를
# 한 번에 실행합니다.
#
# VR teleop 경로는 openarmx_teleop_vr/launch/openarm_controller_real.launch.py의
# 문서화된 실제 사용 절차를 그대로 따릅니다: openarm_controller 패키지의
# openarm_teleop_node(SoT IK solver)가 7 arm joint + gripper를 하나로 합친
# 8-element 배열을 /left,right_forward_position_controller/commands로 publish하므로,
# 반드시 controllers_file:=openarm_bimanual_controllers_vr_teleop.yaml
# (forward_position_controller가 8 joint로 설정되어 있고 별도 gripper_controller가
# 없음)과 짝을 맞춰야 합니다. 기본 openarm_bimanual_controllers.yaml(7 joint
# forward_position_controller + 별도 gripper_controller)과 조합하면
# ForwardCommandController가 array 크기 불일치로 매 cycle ERROR를 뱉습니다.
#
# 참고: openarmx_teleop_vr_node.py(openarm_teleop_vr_real.launch.py 경로)도
# 동일하게 7 arm joint + gripper를 합친 8-element 배열을 publish하도록 설계되어
# 있습니다 (openarmx_sim_controllers.yaml도 8-joint forward_position_controller로
# 구성됨) — 이 노드가 아니라 어떤 controllers_file과 짝을 맞추는지가 핵심입니다.
#
# WARNING: human_camera_bringup.launch.py와 동시에 실행하지 마십시오.
#   left_wrist_camera(serial 317222072848)와 human_camera가 동일한 물리 카메라를
#   사용하므로 USB 디바이스 충돌이 발생합니다.
#
# 저장되는 것은 이미지(3채널) + 관절 각도([2, 8], CAN-FD 원본 값) + 타임스탬프뿐입니다.
# EEF pose, gripper state 정규화값 등 유도 데이터는 여기서 계산하지 않으며,
# 후처리 단계에서 별도로 계산합니다. 저장 포맷은 teleop_episode_writer.py 참고.
#
# 실행 예시:
#   ros2 launch openarm_il robot_data_collection.launch.py \
#       task_name:=pick_and_place output_dir:=~/datasets/openarm_il/raw_teleop \
#       right_can_interface:=can0 left_can_interface:=can1

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    task_name_arg = DeclareLaunchArgument(
        "task_name",
        default_value="default_task",
        description="Task label; episodes are saved under <output_dir>/<task_name>/.",
    )
    output_dir_arg = DeclareLaunchArgument(
        "output_dir",
        default_value="~/datasets/openarm_il/raw_teleop",
        description="Root directory for recorded episodes.",
    )
    monitor_arg = DeclareLaunchArgument(
        "monitor",
        default_value="false",
        description="If true, briefly preview the chest camera's last frame after each episode is saved.",
    )
    use_fake_hardware_arg = DeclareLaunchArgument(
        "use_fake_hardware",
        default_value="false",
        description="Passed through to openarm.bimanual.launch.py. Real teleop collection needs real hardware.",
    )
    robot_controller_arg = DeclareLaunchArgument(
        "robot_controller",
        default_value="forward_position_controller",
        description="Passed through to openarm.bimanual.launch.py; must match what the VR teleop node commands.",
    )
    controllers_file_arg = DeclareLaunchArgument(
        "controllers_file",
        default_value="openarm_bimanual_controllers_vr_teleop.yaml",
        description=(
            "Passed through to openarm.bimanual.launch.py. Must stay paired with "
            "openarm_controller_real.launch.py's openarm_teleop_node, which publishes 8-element "
            "(7 arm + gripper) command arrays; this file's forward_position_controller is the "
            "matching 8-joint config (no separate gripper_controller)."
        ),
    )
    right_can_interface_arg = DeclareLaunchArgument(
        "right_can_interface", default_value="can0", description="CAN interface for the right arm."
    )
    left_can_interface_arg = DeclareLaunchArgument(
        "left_can_interface", default_value="can1", description="CAN interface for the left arm."
    )
    fps_arg = DeclareLaunchArgument(
        "fps",
        default_value="30",
        description=(
            "mp4 container frame rate for the recorder. Must match the cameras' real publish rate "
            "(verify with 'ros2 topic hz') or playback speed will be off; robot_camera_bringup.launch.py "
            "requests a 424,240,30 color profile, confirmed at a stable ~30Hz on real hardware."
        ),
    )

    robot_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("openarm_bringup"), "launch", "openarm.bimanual.launch.py"])
        ),
        launch_arguments={
            "use_fake_hardware": LaunchConfiguration("use_fake_hardware"),
            "robot_controller": LaunchConfiguration("robot_controller"),
            "controllers_file": LaunchConfiguration("controllers_file"),
            "right_can_interface": LaunchConfiguration("right_can_interface"),
            "left_can_interface": LaunchConfiguration("left_can_interface"),
        }.items(),
    )

    teleop_vr = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("openarmx_teleop_vr"), "launch", "openarm_controller_real.launch.py"]
            )
        )
    )

    camera_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("openarm_il"), "launch", "robot_camera_bringup.launch.py"])
        )
    )

    recorder_node = Node(
        package="openarm_il",
        executable="robot_data_recorder",
        name="robot_data_recorder",
        output="screen",
        parameters=[
            {
                "task_name": LaunchConfiguration("task_name"),
                "output_dir": LaunchConfiguration("output_dir"),
                "fps": ParameterValue(LaunchConfiguration("fps"), value_type=float),
                "monitor": ParameterValue(LaunchConfiguration("monitor"), value_type=bool),
            }
        ],
    )

    return LaunchDescription(
        [
            task_name_arg,
            output_dir_arg,
            monitor_arg,
            use_fake_hardware_arg,
            robot_controller_arg,
            controllers_file_arg,
            right_can_interface_arg,
            left_can_interface_arg,
            fps_arg,
            robot_bringup,
            teleop_vr,
            camera_bringup,
            recorder_node,
        ]
    )
