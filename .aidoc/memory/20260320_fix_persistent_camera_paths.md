# 2026-03-20 Fix Dynamic Device Nodes for RealSense

## 操作记录
*   **问题描述**: 用户提到 `/dev/videoX` 数字经常发生变化，每次填写数字非常繁琐且容易填错。
*   **修复方案**: 
    1.  查阅 `/dev/v4l/by-path/` 下的系统默认生成的基于 USB 拓扑结构的固定物理路径链接。
    2.  找到对应 3 个相机的永久链接，不受热插拔和系统重启时内核分配序号变动的影响：
        *   `cam_left`: `/dev/v4l/by-path/pci-0000:00:14.0-usb-0:1.2:1.0-video-index2`
        *   `cam_right`: `/dev/v4l/by-path/pci-0000:00:14.0-usb-0:1.1:1.0-video-index2`
        *   `cam_top`: `/dev/v4l/by-path/pci-0000:00:14.0-usb-0:1.4:1.3-video-index0`
    3.  已直接将这些绝对固定地址写入到 `README_TRON2.md` 的示教命令中。
