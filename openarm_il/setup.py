from glob import glob
import os

from setuptools import find_packages, setup


package_name = "openarm_il"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(include=["openarm_il", "openarm_il.*"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
    ],
    install_requires=["setuptools", "numpy", "PyYAML", "Pillow"],
    zip_safe=True,
    maintainer="minjae",
    maintainer_email="alswo0300@khu.ac.kr",
    description="OpenArm V10 real demonstration collection and ACT dataset export",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "collect_real_demo = openarm_il.collect_real_demo:main",
            "robot_data_recorder = openarm_il.robot_data_recorder:main",
            "inspect_topics = openarm_il.inspect_topics:main",
            "convert_to_lerobot = openarm_il.convert_to_lerobot:main",
            "validate_dataset = openarm_il.validate_dataset:main",
            "visualize_episode = openarm_il.visualize_episode:main",
            "record_human_rgb = openarm_il.record_human_rgb:main",
            "extract_hand_pose = openarm_il.extract_hand_pose:main",
            "generate_pseudo_demo = openarm_il.generate_pseudo_demo:main",
            "validate_pseudo_demo = openarm_il.validate_pseudo_demo:main",
            "visualize_pseudo_episode = openarm_il.visualize_pseudo_episode:main",
            "train_act_pseudo_real = openarm_il.train_act_pseudo_real:main",
            "evaluate_act = openarm_il.evaluate_act:main",
            "run_ablation = openarm_il.run_ablation:main",
            "dataset_statistics = openarm_il.dataset_statistics:main",
            "check_robot = openarm_il.check_robot:main",
            "view_robot = openarm_il.view_robot:main",
            "print_observation = openarm_il.print_observation:main",
            "send_test_action = openarm_il.send_test_action:main",
        ],
    },
)
