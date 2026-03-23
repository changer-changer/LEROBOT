# @TechSpec

- **Schemas**: 
  - LimX Tron2 Robot instantiation and control schemas as per `limxsdk`
  - LeRobot standard Camera Base Class constraints.
- **Constraints**: 
  - Must use virtual environments, no main env modification.
  - No `rm -rf` or destructive actions.
  - Always update `.aidoc` after operations.
- **Environment**: 
  - OS: Ubuntu Linux (22.04 LTS)
  - Python: 3.10 (STRICTLY REQUIRED for ROS2 Humble `rclpy` binding).
  - ROS2: Humble (`source /opt/ros/humble/setup.bash`).
  - **Syntax Note**: LeRobot 0.5.1 uses Python 3.12+ features; these have been MANUALLY BACKPORTED to 3.10.
  - **Registration Rule**: New hardware configs MUST use `@ChoiceRegistry.register_subclass` and be imported in the entry script for `draccus` to parse them.
  - **Local Workflow**: Manual recording defaults to `--dataset.push_to_hub=false` to avoid auth blockers.

- **Performance Constraints**: 
  - Manual recording loop target: **10Hz - 30Hz**.
  - Background `SaveWorker` must handle `PriorityQueue` with non-blocking puts to prevent main loop lag.
- **Visualization Rules (Rerun)**:
  - **NEVER** log multi-dimensional arrays (like tactile point clouds) as individual scalars if they exceed 64 elements.
  - Use `rr.Points3D` for PointCloud data to avoid buffer saturation and OOM.
  - Do not use `static=True` for real-time camera feeds as it breaks dynamic updates in Rerun.

- **Video Encoding Rules**:
  - Default `streaming_encoding=false` for best video quality (batch encoding after episode).
  - Use `streaming_encoding=true` only when save speed is critical (sacrifices quality).
  - Preferred codec order for quality: `libsvtav1` > `h264` > `hevc`.
  - Hardware encoders (`h264_nvenc`, `h264_vaapi`) for performance, not quality.

- **Camera Configuration Rules**:
  - ROS2Camera: Set `width`/`height` to `None` to keep original resolution from topic.
  - Avoid forced square aspect ratios (e.g., 128x128) unless specifically required.
  - Common working resolution: 640x480 (maintains 4:3 aspect ratio).

- **Recording Workflow Rules**:
  - Episode save is atomic: `save_episode()` auto-clears buffer and increments counter.
  - Check `dataset.num_episodes` after save to confirm success.
  - Keyboard events: `S`=start, `Space`=save, `Backspace`=discard, `ESC`=quit.
  - Reference implementation: `/home/cuizhixing/WorkspaceBase/lerobot/src/lerobot/scripts/lerobot_record_vr.py`.
