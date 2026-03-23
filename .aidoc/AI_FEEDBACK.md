# AI Feedback & Reflection

- **经验与踩坑**:
  - ROS2 环境下，不一定总是能安装 `cv_bridge`（尤其是在较新的 Python 3.12 环境下），直接使用 numpy 反序列化 ROS2 Image `msg.data` 会更加稳定（如 `ros2_camera.py` 的实现）。
  - **【混合环境经验】**：若遇到 ROS2 C++ 绑定库（如 `rclpy`），强烈建议 Conda 环境 Python 版本与宿主机系统源 Python 版本一致（Ubuntu 22.04 必须为 3.10）。如果 LeRobot 强行要求 `>=3.12`，可退回到 `3.10` 修改 `pyproject.toml` 来获得 ROS2 原生支持。
  - **【依赖冲突处理】**：`limxsdk` 需要的 numpy 版本较老 (`<1.26.4`)，LeRobot 原生需求 numpy 2.0，建议优先降级 numpy 满足底层驱动 SDK 以免运行时 Segment Fault。
  - **【状态位重置机制】**：在循环录制多个 Episode 时，必须在每一轮循环开始前显式重置键盘监听器的状态位（如 `exit_early`, `start_episode`）。如果不重置，上一轮的按键事件（如按下 Space 结束录制）会被带入下一轮，导致下一轮录制瞬间闪退。
  - **【Draccus 注册机制】**：在新版本 LeRobot 中，添加自定义相机（如 `ros2`）或机器人配置时，必须在对应的 `Config` 类上使用 `@CameraConfig.register_subclass("ros2")` 装饰器。此外，为了确保注册生效，必须在入口脚本中显式 `import` 该配置类，否则 `draccus` 无法识别命令行参数中的子类。
  - **【校验绕过策略】**：LeRobot 的 `RecordConfig` 包含严格的 `__post_init__` 校验。针对非标准录制流程（如由外部系统控制的纯示教录制），最稳健的做法是定义一个子类（如 `ManualRecordConfig`）并重写 `__post_init__` 方法。这比修改框架源码更安全且更具可维护性。
  - **【Hub 同步容错】**：在本地开发/测试环境下，网络不通导致的 Hub 上传失败会直接 crash 掉整个录制循环。脚本应默认设置 `push_to_hub=False`，并在 `finally` 块中加入 `NoneType` 检查 and 异常捕获，确保本地数据已刷盘且脚本能优雅退出。

- **【Rerun 记录陷阱】**：Rerun 的 `rr.log` 函数在接收标量数组时，如果处理逻辑不当（如逐个元素循环），会造成严重的 Python 虚拟机阻塞。在大规模点云 (N > 64) 场景下，**必须**使用 `rr.Points3D` 等二进制格式进行批量记录，否则主循环频率会直接崩溃。
- **【异步写磁盘必要性】**：LeRobot 的 `save_episode` 涉及视频编码和大量小文件写入，这是一个典型的 I/O Bound 操作。在高性能（10Hz+）录制中，必须通过 `SaveWorker` 线程将保存逻辑移出主循环，并使用 `PriorityQueue` 保证紧急保存（如内存溢出自动切分）的响应速度。
- **【内存碎片清理】**：Numpy 频繁申请/释放大片图像内存会导致 glibc 产生碎片。在主循环或 `SaveWorker` 中定期调用 `libc.malloc_trim(0)` 对保持长时录制的内存稳定性至关重要。
- **【视频编码质量】**：`streaming_encoding=true` 虽然能加快保存速度，但会显著降低视频质量（实时编码压缩率高）。如需高质量视频，应使用默认的 `streaming_encoding=false` 配合 `libsvtav1` 编码器。
- **【相机分辨率处理】**：ROS2Camera 默认配置会强制 resize 到 128x128。如需保持原始分辨率，应将 `width` 和 `height` 设为 `None` 或在命令行中省略这两个参数。
- **【Episode 保存机制】**：`dataset.save_episode()` 方法会自动处理 buffer 清理，无需手动调用 `clear_episode_buffer()`（除非要丢弃 episode）。保存后会自动递增 `dataset.num_episodes`。
- **【教学文档重要性】**：复杂的修复过程应该同步输出教学文档（如 `docs/教学.md`），包含问题现象、原因分析、解决方案和代码模板，方便后续开发者理解和维护。
- **【录制帧率与阻塞陷阱】**：当数据集假设按 30FPS 保存，而 `get_observation()` (若其内部调用多路相机的阻塞式 `async_read(timeout)`) 导致抓取循环仅能达到 20FPS 时，最终合成视频的播放速度将会变快。必须使用 `get_observation_latest()` 获取非阻塞最新帧。
- **【Buffer 状态残留陷阱】**：手动控制脚本在取消或报错时，`LeRobotDataset.episode_buffer` 会累积垃圾帧并顺延至下一个 episode（出现错乱拼接）。必须在新 episode启动的严格入口处显式调用 `clear_episode_buffer()`。
- **【多传感器同步读取的木桶效应】**：在多传感器（尤其是多相机）同步采集的循环中，使用 `threading.Event` 实现阻塞读取时，必须在获取数据后（`wait()` 之后）而不是获取数据前执行 `event.clear()`。如果在 `wait()` 之前提前 `clear()`，会强行丢弃在等待其他传感器时其实已经到达的帧，强制必须重新等待下一帧的到来。这会导致顺序读取时的累积延迟（即“木桶效应”），使整体采集帧率大幅下降（如 30Hz 掉到 10Hz 以下）。
