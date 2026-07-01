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
    output_dir:=/home/home/Project/OpenarmIL/datasets/openarm_human_demo \
    serial_no:="'317222072848'"
```

This starts a D435 (`realsense2_camera`, color only, depth/pointcloud
disabled) plus the recorder node. Leave `serial_no` unset to use whichever
D435 is connected.

| Launch argument | Default | Description |
|---|---|---|
| `task_name` | `default_task` | Episodes are saved under `<output_dir>/<task_name>/`. |
| `output_dir` | `/home/home/Project/OpenarmIL/datasets/openarm_human_demo` | Episode root directory. |
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

## Post-processing: HaMeR hand-mesh extraction

Recorded chest mp4 episodes are not used directly for policy learning -- they
are post-processed with [HaMeR](https://github.com/geopavlakos/hamer) to
extract per-frame 3D hand keypoints/mesh, which are then retargeted into
OpenArm-compatible actions in a separate alignment step. This package only
produces the raw mp4 + timestamp CSV; HaMeR extraction happens outside this
package's venv, using its own Python 3.10 virtualenv.

### One-time setup

```bash
cd /home/home/Project/OpenarmIL
python3.10 -m venv .hamer
source .hamer/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

git clone --recursive https://github.com/geopavlakos/hamer.git .hamer_repo
cd .hamer_repo

# setuptools must be a version that supports PEP 660 editable installs (build_editable
# hook) AND still bundles pkg_resources (removed in the newest releases) -- 69.5.1
# satisfies both. Also install with --no-build-isolation so detectron2's setup.py can
# see the already-installed torch (pip's isolated build env otherwise cannot).
pip install "setuptools==69.5.1"
pip install -e .[all] --no-build-isolation
pip install -v -e third-party/ViTPose

# mmcv/xtcocotools (2021-era) were compiled against the numpy 1.x ABI; numpy 2.x
# breaks their compiled extensions, and the newest opencv-python requires numpy>=2,
# so both need pinning together.
pip install "numpy<2" "opencv-python<4.10"

bash fetch_demo_data.sh   # downloads HaMeR + ViTPose checkpoints (~6GB), NOT MANO
```

**MANO model files require manual registration** at
[mano.is.tue.mpg.de](https://mano.is.tue.mpg.de/) (account + license
agreement -- this cannot be automated). Download the MANO model archive from
the site's Download page after logging in, then place the files at:

```text
.hamer_repo/_DATA/data/mano/MANO_RIGHT.pkl
.hamer_repo/_DATA/data/mano/MANO_LEFT.pkl   # only if left-hand detection is needed
```

Verify the full install with `python demo.py --img_folder example_data
--out_folder demo_out --batch_size=8` -- it should render overlay images
without error once MANO is in place.

### Running extraction

`scripts/hamer_extract_npz.py` in this package is the version-controlled copy
(the runtime copy must live inside `.hamer_repo/`, outside this git repo,
since it does `from vitpose_model import ViTPoseModel` -- a script-relative
import that only resolves next to HaMeR's own `vitpose_model.py`). It mirrors
`demo.py`'s actual model loading, ViTDet detectron2 config (via `LazyConfig`,
not the older `get_cfg()` style), and the `pred_cam` left/right sign-flip
before camera projection, but saves `(keypoints_3d, vertices, is_right,
cam_t)` npz per detected hand instead of rendering images. One npz per hand
per frame: `<frame_id>_<person_id>_<L|R>.npz`, where `frame_id` matches the
CSV `frame_idx` column for later alignment.

```bash
cp /home/home/Project/OpenarmIL/src/openarm_human_demo/scripts/hamer_extract_npz.py \
   /home/home/Project/OpenarmIL/.hamer_repo/hamer_extract_npz.py

cd /home/home/Project/OpenarmIL/.hamer_repo
source /home/home/Project/OpenarmIL/.hamer/bin/activate

# 1. mp4 -> frame images (frame_idx must match the recorder's timestamp CSV rows)
ffmpeg -i <episode>.mp4 -start_number 0 -q:v 2 <frames_dir>/%06d.jpg

# 2. HaMeR inference -> npz
python hamer_extract_npz.py \
    --img_folder <frames_dir> \
    --out_folder <hamer_raw_dir>
```

Frames with no detected person/hand are silently skipped (no npz written) --
this is expected for frames where the demonstrator's hands are out of the
chest camera's field of view, not a failure. Checkpoints are cached after the
first run, so subsequent invocations skip re-downloading.

The npz schema matches what `hamer_postprocess_pipeline.py` (the downstream
alignment step, out of scope for this package) expects. See
`/home/home/Project/OpenarmIL/datasets/hamer_execution_guide.md` and
`/home/home/Project/OpenarmIL/datasets/capture_data_quality_validation_guide.md`
for the full pipeline and L0-L3 quality gates.

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
