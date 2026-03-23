# 2026-03-20: Tron2 Camera Topics and RGB/BGR Fixes

## 执行了什么操作 / 做了什么改动
1. **修复左右相机图像反转问题**
   - 文件: `src/lerobot/robots/tron2/tron2_config.py`
   - 改动情况: 在 `Tron2RobotConfig` 中，将 `cam_left` 的订阅话题修正为 `/camera/left/color/image_rect_raw`，`cam_right` 修正为 `/camera/right/color/image_rect_raw`。之前这两个主题配对被填反了导致视觉和数据集标签出现交叉。

2. **修复图像“蓝手”（红绿色调反转）的存储问题**
   - 文件: `src/lerobot/cameras/ros2/ros2_camera.py`
   - 改动情况:
     - 在 `image_callback` 中添加基于 ROS2 `msg.encoding` 的检测。如果底层传来的是 `bgr8`，则在存入 `self.latest_frame` 之前直接原位翻转 (`frame[..., ::-1]`) 转化为标准的 RGB 格式发送给下游。
     - 移除了 `read` 和 `read_latest` 中无条件依赖 `self.config.is_bgr` 默认值导致错误翻转的代码强逻辑。原逻辑会将本身就是 `rgb8` 的原本正常图像因为 `is_bgr=True` 的默认设定，二次翻转成错误的 BGR 格式存储进训练集，导致“蓝手”。

3. **梳理与核查录制倍速及视频拼接 Bug**
   - 文件: 逻辑核对，无大幅修改，主要向用户进行机制解释。
   - 分析确认:
     - 以前出现“倍速播放”（掉帧导致的错位压缩）是因为 `robot.get_observation()` 默认使用了阻塞的 `async_read(500)`。在 30帧 (33.3ms) 一个周期的主循环中，如果相机取帧卡死，这一轮循环就消耗了比如 200ms。最后录制了 60秒 的物理时间，其实程序只存下了 300帧 图像。而 Dataset 照常以此 300 帧按照 30FPS 合成视频，最终得到的视频只有 10 秒，看起来就像“超快速倍速快放”。新版本中 `get_observation()` 已经更换为 `read_latest()`（非阻塞），配合计算微秒差的 `busy_wait`，严格确保了时间轴长度正确，问题已解除。
     - 错位拼接的旧帧残余问题，依靠强化的 `dataset.clear_episode_buffer()` 已经兜底清理了缓冲字典内的残留帧集合。
