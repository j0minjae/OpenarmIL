from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    camera_name_arg = DeclareLaunchArgument(
        "camera_name",
        default_value="human_camera",
        description="RealSense camera_name/camera_namespace (also used to derive the default image_topic).",
    )
    serial_no_arg = DeclareLaunchArgument(
        "serial_no",
        default_value="''",
        description="Serial number of the D435 to open. Leave empty to use whichever camera is connected.",
    )
    task_name_arg = DeclareLaunchArgument(
        "task_name",
        default_value="default_task",
        description="Task label; episodes are saved under <output_dir>/<task_name>/.",
    )
    output_dir_arg = DeclareLaunchArgument(
        "output_dir",
        default_value="/home/home/Project/OpenarmIL/datasets/openarm_human_demo",
        description="Root directory for recorded episodes.",
    )
    fps_arg = DeclareLaunchArgument(
        "fps",
        default_value="30",
        description="Capture/record frame rate, also used to configure the RealSense color profile.",
    )
    monitor_arg = DeclareLaunchArgument(
        "monitor",
        default_value="false",
        description="If true, briefly preview the last frame after each episode is saved.",
    )
    image_topic_arg = DeclareLaunchArgument(
        "image_topic",
        default_value=[
            "/",
            LaunchConfiguration("camera_name"),
            "/color/image_raw",
        ],
        description="Image topic to record. Defaults to the RealSense color topic for camera_name.",
    )

    camera_name = LaunchConfiguration("camera_name")

    realsense_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("realsense2_camera"), "launch", "rs_launch.py"])
        ),
        launch_arguments={
            "camera_name": camera_name,
            "camera_namespace": "",
            "serial_no": LaunchConfiguration("serial_no"),
            "enable_color": "true",
            "enable_depth": "false",
            "pointcloud.enable": "false",
            "rgb_camera.color_profile": ["424,240,", LaunchConfiguration("fps")],
        }.items(),
    )

    recorder_node = Node(
        package="openarm_human_demo",
        executable="recorder",
        name="human_demo_recorder",
        output="screen",
        parameters=[
            {
                "image_topic": LaunchConfiguration("image_topic"),
                "task_name": LaunchConfiguration("task_name"),
                "output_dir": LaunchConfiguration("output_dir"),
                "fps": ParameterValue(LaunchConfiguration("fps"), value_type=float),
                "monitor": ParameterValue(LaunchConfiguration("monitor"), value_type=bool),
            }
        ],
    )

    return LaunchDescription(
        [
            camera_name_arg,
            serial_no_arg,
            task_name_arg,
            output_dir_arg,
            fps_arg,
            monitor_arg,
            image_topic_arg,
            realsense_node,
            recorder_node,
        ]
    )
