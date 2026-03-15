# 2026-03-13 19:55 - Memory & Workflow Optimization

## Context

User reported memory exhaustion (OOM) during long recordings and requested image compression (128x128) and workflow refinements (keyboard triggers).

## Changes

- **ROS2 Camera**:
  - Updated `ROS2CameraConfig` in `configs.py` to include `width` and `height` (default 128x128).
  - Updated `ROS2CameraNode` and `ROS2Camera` in `ros2_camera.py` to implement bilinear resizing using `PIL.Image`.

## 2026-03-13 20:50 (Debug Log)
*   **Observation**: Ran optimized `lerobot_record_manual.py` on local SSD (`~/data`).
*   **Result**: 
    - Loop slowed down to **0.2Hz** instantly.
    - RAM spiked from **81% to 95.8%** in 4 seconds.
    - Triggered **[CRITICAL] MEMORY SAFETY STOP**.
*   **Analysis**: 
    - Even with `get_observation_latest`, the loop is blocked.
    - Resized images (128x128) should not consume 15% RAM (approx 2GB) in 4 seconds.
    - Suspect: `VideoEncodingManager` or `imshow` is blocking the main loop or leaking memory.
    - Note: x264 logs appearing in terminal suggest encoder is starting/stopping frequently or batch size 1 is inefficient.
- **Manual Recording Script**:
  - Integrated `psutil` for real-time RAM monitoring.
  - Added safety thresholds:
    - 90% RAM: Trigger emergency save.
    - 95% RAM: Trigger immediate discard to prevent system crash.
  - Refined keyboard workflow:
    - Pressing 'S' during recording properly discards and starts new episode immediately.
    - Pressing 'S' right after Space (during save decision) now discards current buffer and starts new episode.
    - Unified 'start_episode' and 'discard_episode' feedback.
- **UI/UX**:
  - Added RAM usage percentage to the terminal status lines.

## Impact

- Reduced memory footprint per frame.
- Automated protection against computer freeze/crash due to RAM exhaustion.
- Smoother recording experience for manual lead-through.
