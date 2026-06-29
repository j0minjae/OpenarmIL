#!/usr/bin/env python3
"""Simulation launch: openarm model + openarm_controller IK solver + fake hardware."""

import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchContext
from launch.actions import TimerAction, OpaqueFunction
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def spawn_robot_and_control(context: LaunchContext, controllers_file):
    description_pkg = get_package_share_directory("openarm_description")
    xacro_path = os.path.join(
        description_pkg, "assets", "robot", "openarm_v1.0", "urdf",
        "openarm_v10.urdf.xacro",
    )
    robot_description = xacro.process_file(
        xacro_path,
        mappings={
            "arm_type": "v10", "body_type": "v10", "bimanual": "true",
            "ros2_control": "true", "use_fake_hardware": "true",
            "fake_sensor_commands": "false",
        },
    ).toprettyxml(indent="  ")

    robot_description_param = {"robot_description": robot_description}
    controllers_file_str = context.perform_substitution(controllers_file)

    return [
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             output="screen", parameters=[robot_description_param]),
        Node(package="controller_manager", executable="ros2_control_node",
             output="both", parameters=[robot_description_param, controllers_file_str]),
    ]


def generate_launch_description():
    ctrl_pkg = FindPackageShare("openarm_controller")
    desc_pkg = get_package_share_directory("openarm_description")
    teleop_vr_pkg = FindPackageShare("openarmx_teleop_vr")

    controllers_file = PathJoinSubstitution([
        teleop_vr_pkg, "config", "sim_controllers.yaml",
    ])
    teleop_config = PathJoinSubstitution([ctrl_pkg, "config", "teleop_params.yaml"])

    urdf_path = os.path.join(
        desc_pkg, "assets", "robot", "openarm_v1.0", "urdf", "openarm_v10_bimanual.urdf",
    )

    robot_and_control = OpaqueFunction(function=spawn_robot_and_control, args=[controllers_file])

    all_spawner = Node(
        package="controller_manager", executable="spawner",
        arguments=["joint_state_broadcaster", "left_forward_position_controller",
                    "right_forward_position_controller",
                    "-c", "/controller_manager", "--controller-manager-timeout", "30"],
    )

    return LaunchDescription([
        robot_and_control,
        TimerAction(period=5.0, actions=[all_spawner]),
        Node(package="rviz2", executable="rviz2", name="rviz2", output="log",
             arguments=["-d", os.path.join(desc_pkg, "rviz", "bimanual.rviz")]),
        Node(package="openarmx_teleop_bridge_vr", executable="openarmx_teleop_bridge_vr_node",
             name="openarmx_teleop_bridge_vr_node", output="screen"),
        Node(package="openarm_controller", executable="openarm_teleop_node",
             name="openarm_teleop_node", output="screen",
             parameters=[teleop_config, {"urdf_path": urdf_path}]),
    ])
