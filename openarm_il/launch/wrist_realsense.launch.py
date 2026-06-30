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
            "camera_namespace": camera_name,
            "serial_no": f"'{serial_no}'",
            "enable_color": "true", 
            "enable_depth": "false",
            "rgb_camera.color_profile": "424,240,15",
        }.items(),
    )


def generate_launch_description():
    return LaunchDescription(
        [
            _realsense_camera_include("camera", "332322072253"),
            _realsense_camera_include("left_wrist_camera", "317222072848"),
            _realsense_camera_include("right_wrist_camera", "327122079310"),
        ]
    )
