# openarm_human_demo

Standalone ROS2 Humble (`ament_python`) package for recording human demonstration
video for the OpenArm imitation-learning pipeline. It is independent of the
teleoperation stack (`openarm_can`, Pinocchio IK, `controller_manager` @ 750Hz) --
it only subscribes to an image topic and writes mp4 episodes with a
frame-timestamp CSV, so it can be run any time a camera is publishing.

Action labeling (thumb-index pinch -> gripper state) and 3D hand-keypoint
extraction (HaMeR) are out of scope for this package; they are a separate
post-processing step over the recorded video.

## Dependencies

- ROS2 Humble, `realsense2_camera` (for the bundled launch file)
- `python3-opencv` (apt) -- video read/write
- `python3-pynput` (apt) or `pip install pynput` -- global space-bar hotkey,
  independent of window focus

```bash
sudo apt install python3-opencv python3-pynput
# or, if apt is unavailable:
pip3 install --user opencv-python pynput
```

`pynput`'s global listener needs an accessible X11 `DISPLAY` (or evdev access
to `/dev/input/event*`, which normally requires the `input` group) to capture
key presses regardless of which window has focus. A headless SSH session
without X forwarding will not receive key events.

## Build

```bash
cd /home/home/Project/OpenarmIL/src
source /opt/ros/humble/setup.bash
colcon build --packages-select openarm_human_demo
source install/setup.bash
```

## Usage

```bash
ros2 launch openarm_human_demo human_data_collection.launch.py \
    task_name:=test_task \
    output_dir:=~/datasets/openarm_human_demo \
    serial_no:="'317222072848'"
```

This starts a D435 (`realsense2_camera`, color only, depth/pointcloud
disabled) plus the recorder node. Leave `serial_no` unset to use whichever
D435 is connected.

| Launch argument | Default | Description |
|---|---|---|
| `task_name` | `default_task` | Episodes are saved under `<output_dir>/<task_name>/`. |
| `output_dir` | `~/datasets/openarm_human_demo` | Episode root directory. |
| `camera_name` | `human_camera` | RealSense `camera_name` (namespace is left empty); also used to derive `image_topic`. |
| `serial_no` | `''` (any) | D435 serial number to open. |
| `fps` | `30` | Capture/record rate; also sets the RealSense color profile. |
| `image_topic` | `/<camera_name>/color/image_raw` (e.g. `/human_camera/color/image_raw`) | Override if the camera is brought up elsewhere. |
| `monitor` | `false` | If `true`, briefly (1.5s) preview the last frame right after an episode is saved. Not a live preview. |

### Controls

- **SPACE** -- toggle recording start/stop (global hotkey, works without terminal focus)
- **q** or **ESC** -- quit (any in-progress episode is saved first)
- Terminal bell: 1 beep on start, 2 beeps on stop (headless feedback, no video window by default)

### Output format

```text
<output_dir>/<task_name>/
    episode_0001.mp4
    episode_0001_timestamps.csv   # frame_idx, wall_time, ros_stamp
    episode_0002.mp4
    episode_0002_timestamps.csv
    ...
```

Episode numbers auto-increment by scanning the task directory for existing
`episode_NNNN.mp4` files. `wall_time` is `time.time()` at frame arrival;
`ros_stamp` is the image message's `header.stamp` (seconds, float). Use these
to align frames against another timestamped stream (e.g. a Quest3 wrist-pose
log) after the fact.

## Verifying a change

```bash
cd /home/home/Project/OpenarmIL/src/openarm_human_demo
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=".:$PYTHONPATH" python3 -m pytest test/ -v
```

To sanity-check the full pipeline without a camera, publish synthetic
`sensor_msgs/Image` messages on the configured `image_topic` and run
`ros2 run openarm_human_demo recorder`; the mp4 frame count (verify with
`cv2.VideoCapture(...).get(cv2.CAP_PROP_FRAME_COUNT)`) should match the CSV
row count exactly.
