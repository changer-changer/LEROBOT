# Action Log (2026-03-20 22:54:00)

## Operation
Changed camera configurations in README_TRON2.md to utilize `intelrealsense` native SDK in LeRobot framework.

## Changes Made
- Located the `intelrealsense` configuration parser in `src/lerobot/cameras/realsense/configuration_realsense.py`.
- Translated the hardware profile to json format mapping using accurate serial numbers:
  - Left Camera: D405 (SN: 427622272146) -> `cam_left` (848x480)
  - Right Camera: D405 (SN: 427622271245) -> `cam_right` (848x480)
  - Top Camera: D455 (SN: 244222301571) -> `cam_top` (640x480)
- Updated `README_TRON2.md` command for testing. Maintained commented-out `ros2` configs as an established fallback.
