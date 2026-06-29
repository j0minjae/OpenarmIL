from setuptools import setup, find_packages
from glob import glob
import os

package_name = 'openarm_controller'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='minjae',
    maintainer_email='alswo0300@khu.ac.kr',
    description='Python IK solver and VR teleop node for OpenArm robot',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'openarm_teleop_node = openarm_controller.teleop_node:main',
        ],
    },
)
