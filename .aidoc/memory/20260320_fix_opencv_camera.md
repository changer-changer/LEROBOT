# 2026-03-20 Fix OpenCV Camera Resolution Issue

## 操作记录
*   **问题描述**: 用户在执行 `lerobot_record_tron2.py` 时终端报错 `❌ 无法连接到机器人: OpenCVCamera(/dev/video14) failed to set capture_width=848 (actual_width=640, width_success=True).`
*   **诊断过程**:
    1.  查阅 `test_camera_opencv.py` 和 `v4l2-ctl --list-devices`，发现 `/dev/video14` 错误指向了笔记本内置的 Integrated RGB Camera 的红外流（仅支持 GREY 640x360），而非 RealSense 摄像头。
    2.  RealSense 设备分布在 3 个 USB controller 节点上。测试和探测后发现对应的 RGB 节点确切为 `/dev/video2` (cam_left)、`/dev/video8` (cam_right)、`/dev/video20` (cam_top)。
    3.  使用 probe 脚本测试 848x480 resolution，发现 `/dev/video8` 默认四字码无法输出 848x480，必须显式指定 `fourcc="UYVY"`。
*   **修复方案**: 
    1.  更正 `cam_left` 索引为 `/dev/video2`。
    2.  在启动命令中的 OpenCV 配置信息中给所有的相机增加 `"fourcc": "UYVY"` 请求，以确保 848x480 均能正常分配并在高速下稳定工作。
