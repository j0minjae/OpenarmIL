# Human data 수집용 카메라 bringup + recorder 런치파일
#
# robot data 수집용 left_wrist_camera(serial 317222072848)와 동일한 물리 카메라
# 1대를 human_camera라는 이름으로 기동하고, human_data_recorder 노드를 함께 실행합니다.
#
# WARNING: robot_camera_bringup.launch.py와 동시에 실행하지 마십시오.
#   serial 317222072848 카메라를 두 런치가 동시에 요청하면 USB 디바이스 충돌이
#   발생합니다. robot data 수집과 human data 수집은 반드시 별도 세션에서 실행하십시오.
#
# 발행 토픽:
#   /human_camera/color/image_raw
#
# 실행 예시:
#   ros2 launch openarm_il human_camera_bringup.launch.py \
#       task_name:=handover output_dir:=~/datasets/openarm_human_demo

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

_HUMAN_CAMERA_SERIAL = "317222072848"
_COLOR_PROFILE = "424,240,15"
_IMAGE_TOPIC = "/human_camera/color/image_raw"


def generate_launch_description():
    task_name_arg = DeclareLaunchArgument(
        "task_name",
        default_value="default_task",
        description="Task label; episodes are saved under <output_dir>/<task_name>/.",
    )
    output_dir_arg = DeclareLaunchArgument(
        "output_dir",
        default_value="~/datasets/openarm_human_demo",
        description="Root directory for recorded episodes.",
    )
    monitor_arg = DeclareLaunchArgument(
        "monitor",
        default_value="false",
        description="If true, briefly preview the last frame after each episode is saved.",
    )

    camera_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("realsense2_camera"), "launch", "rs_launch.py"]
            )
        ),
        launch_arguments={
            "camera_name": "human_camera",
            "camera_namespace": "",
            "serial_no": f"'{_HUMAN_CAMERA_SERIAL}'",
            "enable_color": "true",
            "enable_depth": "false",
            "enable_infra1": "false",
            "enable_infra2": "false",
            "enable_rgbd": "false",
            "enable_sync": "false",
            "align_depth.enable": "false",
            "pointcloud.enable": "false",
            "rgb_camera.color_profile": _COLOR_PROFILE,
        }.items(),
    )

    recorder_node = Node(
        package="openarm_human_demo",
        executable="recorder",
        name="human_demo_recorder",
        output="screen",
        parameters=[
            {
                "image_topic": _IMAGE_TOPIC,
                "task_name": LaunchConfiguration("task_name"),
                "output_dir": LaunchConfiguration("output_dir"),
                "fps": ParameterValue(15.0, value_type=float),
                "monitor": ParameterValue(LaunchConfiguration("monitor"), value_type=bool),
            }
        ],
    )

    return LaunchDescription(
        [
            task_name_arg,
            output_dir_arg,
            monitor_arg,
            camera_node,
            recorder_node,
        ]
    )
