import os
from glob import glob

from setuptools import find_packages, setup

package_name = "openarm_human_demo"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test", "test.*"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="minjae",
    maintainer_email="alswo0300@khu.ac.kr",
    description="Standalone ROS2 tool for recording human demonstration video for OpenArm imitation learning.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "recorder = openarm_human_demo.recorder_node:main",
        ],
    },
)
