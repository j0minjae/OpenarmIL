# Robot data 수집용 카메라 bringup 런치파일
#
# chest_camera / left_wrist_camera / right_wrist_camera 3대를 동시에 기동합니다.
#
# WARNING: human_camera_bringup.launch.py와 동시에 실행하지 마십시오.
#   left_wrist_camera(serial 317222072848)와 human_camera가 동일한 물리 카메라를
#   사용하므로, 두 런치를 동시에 실행하면 USB 디바이스 충돌이 발생합니다.
#
# 발행 토픽:
#   /chest_camera/color/image_raw
#   /left_wrist_camera/color/image_raw
#   /right_wrist_camera/color/image_raw

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def _realsense_camera_include(camera_name: str, serial_no: str) -> IncludeLaunchDescription:
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("realsense2_camera"),
                    "launch",
                    "rs_launch.py",
                ]
            )
        ),
        launch_arguments={
            "camera_name": camera_name,
            "camera_namespace": "",
            "serial_no": f"'{serial_no}'",
            "enable_color": "true",
            "enable_depth": "false",
            "enable_infra1": "false",
            "enable_infra2": "false",
            "enable_rgbd": "false",
            "enable_sync": "false",
            "align_depth.enable": "false",
            "pointcloud.enable": "false",
            "rgb_camera.color_profile": "424,240,15",
        }.items(),
    )


def generate_launch_description():
    return LaunchDescription(
        [
            _realsense_camera_include("chest_camera", "332322072253"),
            _realsense_camera_include("left_wrist_camera", "317222072848"),
            _realsense_camera_include("right_wrist_camera", "327122079310"),
        ]
    )
