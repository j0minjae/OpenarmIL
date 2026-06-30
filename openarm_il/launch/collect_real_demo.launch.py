from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("task", default_value="default_task"),
            DeclareLaunchArgument("episode_id", default_value="0000"),
            DeclareLaunchArgument("duration", default_value="30.0"),
            DeclareLaunchArgument("output_dir", default_value="~/datasets/openarm_il/raw_real"),
            Node(
                package="openarm_il",
                executable="collect_real_demo",
                name="openarm_il_real_demo_recorder",
                output="screen",
                arguments=[
                    "--task",
                    LaunchConfiguration("task"),
                    "--episode-id",
                    LaunchConfiguration("episode_id"),
                    "--duration",
                    LaunchConfiguration("duration"),
                    "--output-dir",
                    LaunchConfiguration("output_dir"),
                ],
            ),
        ]
    )
