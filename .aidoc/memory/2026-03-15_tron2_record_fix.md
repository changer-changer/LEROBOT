# 2026-03-15 时间线日志: Tron2录制脚本修复

- **19:35** 分析 `lerobot_record_tron2.py`，定位到其获取观测调用的 `robot.get_observation()` 是阻塞式的，会导致循环跟不上设定的 30FPS（例如降到 20FPS）。但保存数据时仍以 30FPS 写入，导致播放视频时速度过快。修改为 `robot.get_observation_latest()` 后解决阻塞。
- **19:38** 检查 `lerobot_dataset` 源码后发现如果有保存失败（或者中途打断），上一段录像积累的 `episode_buffer` 没有被清空，从而带入了下一段录制中。在按 'S' 键确定开始新 episode 前加上了 `dataset.clear_episode_buffer()` 清理残留。
- **19:40** 修改 `tron2_config.py` 中的 `cam_left` 设置为 `/camera/right/color/image_rect_raw`，`cam_right` 设置为 `/camera/left/color/image_rect_raw`，解决用户反馈的左右手视频文件夹保存反转的问题。
- **19:50+** （架构讨论与迭代）与用户就“阻塞等待以换取100%帧非重复(原 Realman 做法)” vs “非阻塞极速快照以换取绝不掉帧与视觉-本体完美同步对齐”进行讨论。用户拍板：采用非阻塞极速快照的方案。同时为了保持后续调用接口的向后兼容，**移除绕弯的 `get_observation_latest`，直接将原生的 `get_observation` 改写为非阻塞**。此权衡及决策已经同步到 `PROJECT_CONTEXT.md` 中。
