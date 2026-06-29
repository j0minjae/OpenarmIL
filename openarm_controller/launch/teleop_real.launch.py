#!/usr/bin/env python3
"""Real robot launch: openarm_bringup must be running separately.

Usage:
  Terminal 1: ros2 launch openarm_bringup openarm.bimanual.launch.py \
      use_fake_hardware:=false robot_controller:=forward_position_controller \
      controllers_file:=openarm_bimanual_controllers_vr_teleop.yaml \
      right_can_interface:=can0 left_can_interface:=can1

  Terminal 2: ros2 launch openarm_controller teleop_real.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ctrl_pkg = FindPackageShare("openarm_controller")
    desc_pkg = get_package_share_directory("openarm_description")

    teleop_config = PathJoinSubstitution([ctrl_pkg, "config", "teleop_params.yaml"])
    urdf_path = os.path.join(
        desc_pkg, "assets", "robot", "openarm_v1.0", "urdf", "openarm_v10_bimanual.urdf",
    )

    return LaunchDescription([
        Node(package="openarmx_teleop_bridge_vr", executable="openarmx_teleop_bridge_vr_node",
             name="openarmx_teleop_bridge_vr_node", output="screen"),
        Node(package="openarm_controller", executable="openarm_teleop_node",
             name="openarm_teleop_node", output="screen",
             parameters=[teleop_config, {"urdf_path": urdf_path}]),
    ])
