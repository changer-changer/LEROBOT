# Project Context & Evolution Tree

## [一级：大方向/大功能模块]

Integration of Tac3D Tactile Sensor and LimX Tron2 Robot with LeRobot Framework.

## [二级：子问题/具体创新点]

### Tron2 Camera Integration

- **目的 (Purpose)**: 确保相机可以在系统中正常的开启、关闭和获取帧，支持数据采集、模型训练与推理。
- **必要性 (Necessity)**: 原有的模块直接订阅ROS2 topic，无法通过Tron2 SDK检查相机的硬连线/工作状态。
- **尝试与改动 (Attempts)**:
  - Attempt 1 (当前): 计划重新编写 `tron2_camera.py`（继承自 LeRobot Camera），Connect/Disconnect调用Tron2 SDK进行检查，异步读取/读取调用ROS2 Topic获取图像帧（实际发现话题名为 `/camera/left/color/image_rect_raw` 等）。
- **结果与反馈 (Results)**:
  - 通过 `conda create -n lerobotROS python=3.10` 结合 `source /opt/ros/humble/setup.bash`，成功使虚拟环境获取了系统级 ROS2 的 `rclpy`，同时利用 conda 管理了 `lerobot` 的其他依赖。
  - 需要修改 `pyproject.toml` 中的 `requires-python = ">=3.10"` 以支持 Python 3.10。
  - 补充安装了 `deprecated`, `pytac3d`，并将 `numpy` 降级到 `<1.26.4` 以兼顾 `limxsdk`。
  - `test_full_system.py` 能够在无硬件连接的单机环境下顺利通过编译与导入测试，捕获预期内的连接超时。
- **下一步 (Next Steps)**:
  - 等待用户连接实际传感器与机器人硬件，运行 `test_full_system.py` 进行真机数据采集测试。

### Manual Recording Workflow & Keyboard Control

- **目的 (Purpose)**: 提供一种不依赖 VR 设备、用户友好的桌面端数据采集流程。
- **必要性 (Necessity)**: 原有的 LeRobot Record 脚本通常假设使用 VR 设备或通过代码逻辑自动循环，不适合手动演示。
- **尝试与改动 (Attempts)**:
  - Attempt 1: 编写 `lerobot_record_manual.py`，结合 `control_utils.py` 中的键盘监听器。
  - 核心逻辑：`S` 键开始 Episode，采集完成后按下 `Space` 保存或 `Backspace` 废弃。
- **结果与反馈 (Results)**:
  - 成功实现了“等待触发 -> 采集 -> 决策保存”的闭环，用户体验接近 VR 数采但成本更低。

### Python 3.12 to 3.10 Syntax Backport

- **目的 (Purpose)**: 解决 LeRobot 0.5.1 与 ROS2 Humble (Ubuntu 22.04) 之间的 Python 版本代差问题。
- **必要性 (Necessity)**: ROS2 Humble 强绑定 Python 3.10，而 LeRobot 0.5.1 引入了 3.12 的泛型语法，直接运行会报 `SyntaxError`。
- **尝试与改动 (Attempts)**:
  - Attempt 1 (废弃): 尝试创建 3.12 环境，导致 `rclpy` (ROS2) 无法加载。
  - Attempt 2 (当前): 留在 3.10 环境，手动将 `io_utils.py` 等文件中的 3.12 语法改回 3.10 写法，并在 `lerobot/__init__.py` 中通过 Monkey-patch 注入 `typing.Unpack`。
- **结果与反馈 (Results)**:
  - 成功在 3.10 环境下跑通了 LeRobot 0.5.1，兼顾了主流 ROS2 兼容性与最新框架功能。

### Config Registration & Validation Bypass

- **目的 (Purpose)**: 确保 `draccus` 解析器能识别自定义硬件配置，并跳过录制脚本的强制策略校验。
- **必要性 (Necessity)**:
  - `draccus` 需要显式的 `register_subclass` 装饰器和模块导入才能识别 `ros2` 等自定义类型。
  - 原生 `RecordConfig` 强制要求 `policy` 或 `teleop`，这与纯示教/外部录制流程冲突。
- **尝试与改动 (Attempts)**:
  - Attempt 1: 在 `ROS2CameraConfig` 上添加 `@CameraConfig.register_subclass("ros2")`，并更新脚本导入。
  - Attempt 2: 在 `lerobot_record_manual.py` 中定义 `ManualRecordConfig` 继承并重写 `__post_init__`，移除强制校验逻辑。
- **结果与反馈 (Results)**:
  - 成功消除了 `KeyError: 'ros2'` 和 `ValueError` 报错。
  - 加入了 `--dataset.push_to_hub=false` 默认值和 `NoneType` 安全检查，录制流程在本地环境下极其稳健。
- **下一步 (Next Steps)**:
  - 保持 `src/lerobot/cameras/ros2/configs.py` 的注册装饰器，若添加新传感器需遵循相同注册模式。

### Tactile Data Storage & Shape Validation

- **目的 (Purpose)**: 确保 `(400, 6)` 等高维触觉数据可以正常存入 LeRobot Dataset。
- **必要性 (Necessity)**: LeRobot 的校验逻辑将 Numpy 的元组 shape 与从 JSON 读取的列表 shape 直接对比，导致 `ValueError`。
- **尝试与改动 (Attempts)**:
  - Attempt 1 (当前): 修改 `src/lerobot/datasets/utils.py` 中的 `validate_feature_numpy_array` 函数，在对比前将 `actual_shape` 和 `expected_shape` 均转换为 `list` 类型。
  - 增强 `lerobot_record_manual.py`：加入目录冲突提示（RESUME/DELETE 建议）和 `add_frame` 的异常捕获。
- **结果与反馈 (Results)**:
  - 通过 `verify_tactile_storage.py` 和 `tests/test_mock_integrated_system.py` 验证：
    - 成功实现了 `(400, 6)` 触觉点云数据的刷盘与重载。
    - 成功模拟了包含 16 关节、2 RGB 相机、Tac3D 传感器的完整 Integrated 系统逻辑。
    - 验证了录制、保存、Finalize、重载的闭环稳定性（包含视频流编码）。
  - 解决了用户反馈的“存储不下来”问题。
- **下一步 (Next Steps)**:
  - 用户应根据脚本提示，在真机录制前先手动清理旧的 `outputs/recordings/tron2_test` 文件夹或使用 `--resume=true`。

### Memory & Workflow Optimization

- **目的 (Purpose)**: 防止大规模数采时的内存溢出（OOM），优化键盘交互流程。
- **必要性 (Necessity)**: 高维触觉点云与图像数据常驻内存易导致系统卡死；用户需要更灵活的“重录”机制。
- **尝试与改动 (Attempts)**:
  - Attempt 1:
    - 在 `ROS2Camera` 中引入 `PIL` resize (128x128)。
    - 在 `lerobot_record_manual.py` 中接入 `psutil` 监控 RAM 分辨。
    - 设定 90% 阈值强制保存，95% 阈值强制丢弃。
    - 优化 `S` 键在不同阶段（录制中、保存建议中）的重置逻辑。
- **结果与反馈 (Results)**:
  - 内存占用显著降低，系统在极端负载下具备了自保护能力。
- **下一步 (Next Steps)**:
- [ ] 真机长时录制，观察内存曲线.

### Asynchronous Multithreaded Recording

- **目的 (Purpose)**: 彻底解决录制过程中的 I/O 阻塞与内存突发（RAM Spike）。
- **必要性 (Necessity)**:
  - 之前的同步保存模式在写入磁盘时会导致主循环卡顿到 0.2Hz。
  - 触觉点云数据 (400x6) 如果逐点记录 Scalar，会导致 Rerun 缓冲区爆炸（4s 内占用 9GB RAM）。
- **尝试与改动 (Attempts)**:
  - Attempt 1: 引入 `SaveWorker` 线程与 `PriorityQueue`。主循环只负责“生产”，后台线程负责“消费”并写入磁盘。
  - Attempt 2: 修正 Rerun 记录逻辑。在 `visualization_utils.py` 中引入 `rr.Points3D` 处理触觉点云，并移除了不稳定的 `static=True` 标志。
  - Attempt 3: 加入 `precise_sleep` 与自适应时间补偿逻辑，确保在高性能负载下依然保持稳定的 10Hz-30Hz。
- **结果与反馈 (Results)**:
  - 录制频率稳定在 10Hz+ (最高可达 30Hz)。
  - 内存占用从突发 96% 降回稳定的 81% 左右。
  - 实现了“Seamless Auto-split”：内存高时自动分段保存且不中断采集。
- **下一步 (Next Steps)**:
  - 真机长时稳定性测试，确认多轮 Episode 连续保存的可靠性。

### lerobot_record_manual_fixed.py 修复与教学

- **目的 (Purpose)**: 修复手动录制脚本的所有问题，确保能稳定运行，并输出完整教学文档。
- **必要性 (Necessity)**: 之前的录制脚本存在多个 bug（导入错误、视频模糊、episode 保存逻辑不透明等），无法正常使用。
- **尝试与改动 (Attempts)**:
  - Attempt 1: 修复 `busy_wait` 导入错误 - 在 `robot_utils.py` 添加兼容别名。
  - Attempt 2: 修复 `is_headless` 缺失 - 添加正确导入。
  - Attempt 3: 修复 `logging` 未定义 - 在 `visualization_utils.py` 添加导入。
  - Attempt 4: 修复视频编码参数缺失 - 在 `DatasetRecordConfig` 添加 `vcodec`, `streaming_encoding` 等字段。
  - Attempt 5: 修复机器人连接错误处理 - 添加 try-except 块，优雅退出。
  - Attempt 6: 添加 `warmup_cameras` 函数 - 从师兄版本复制相机预热逻辑。
  - Attempt 7: 修复视频模糊问题 - 识别出 `streaming_encoding=true` 会导致质量下降，建议用户设为 `false`。
  - Attempt 8: 修复 128x128 resize 问题 - 修改 `ROS2CameraConfig` 默认值为 `None` 保持原始分辨率。
  - Attempt 9: 添加详细调试信息 - 让用户清楚看到 episode 保存状态。
- **结果与反馈 (Results)**:
  - 脚本可以正常运行，参数解析正确。
  - 连接失败时给出清晰的错误提示。
  - 视频质量可通过 `vcodec` 和 `streaming_encoding` 参数控制。
  - 编写了完整教学文档：`docs/教学.md`
- **关键经验**:
  - 师兄版本不使用 `streaming_encoding`，这是新版本功能但会降低视频质量。
  - 师兄版本使用 `libsvtav1` 编码器（默认），而非 `h264`。
  - Episode 保存后 `save_episode()` 会自动调用 `clear_episode_buffer()`，无需手动处理。
- **生成的文件**:
  - `docs/教学.md`: 完整的开发教学文档
  - `src/lerobot/scripts/lerobot_record_manual_fixed.py`: 修复后的录制脚本

---

### Tron2 Recording Script Fixes

- **目的 (Purpose)**: 修复 `lerobot_record_tron2.py` 中的录制速度过快、左右手图像反向、以及旧帧拼接到新视频结尾的问题。
- **必要性 (Necessity)**: 在真机器人数据采集中，录制速度（FPS）的稳定性和数据时序的一致性至关重要。
- **尝试与改动 (Attempts)**:
  - Attempt 1 (当前): 
    1. 在 `tron2_config.py` 中交换 `cam_left` 和 `cam_right` 的 ROS Topic，解决左右手数据反转。
    2. 彻底修改 `tron2_robot.py` 原生的 `robot.get_observation()` 的内部实现，将其从同步阻塞 (`async_read(500)`) 替换为极速非阻塞 (`read_latest()`)。这解决了由于传感器串行堵塞而导致的帧率大幅缩水、视频保存后被"倍速"播放的问题。
    3. 在新 episode 开始前显式调用 `dataset.clear_episode_buffer()`，彻底防止上一次异常的旧帧被带入新 buffer 中，解决“旧片段拼接到结尾”现象。
- **结果与反馈 (Results)**:
  - 代码层面修复了以上问题。
- **设计决策与权衡 (Design Decisions & Trade-offs - "为什么改成非阻塞而不是像原版那样阻塞")**:
  - 原先参考 `realman_robot.py` 时的设计要求极高的“数据严谨性”（宁愿卡住等待也绝不插入重复帧）。但在 Tron2 环境中，30FPS 数据采集主循环必须严格满足 33.3ms / 循环的时间节拍，如果用阻塞机制一旦某路相机晚到 100ms，这一段循环的时间戳会被强行拉出物理错位，不但导致后续存集时发生肉眼可见的“视频加倍速播放”，还会造成旧相机图被强行跟新采集的关节状态“绑在一起”，进而引发 **视觉错位 (False Synchronization)**。
  - 由于用户决定优先保障动作时间轴的对齐平滑并维持接口通用性：**抛弃冗余在外的 `get_observation_latest` 新名字，统一将默认的 `get_observation` 修改为基于快照的非阻塞式！** 即便极少数情况复用了前一帧的图像，对于端到端模型而言也远胜于视觉和本体感受出现“跨时间线捆绑”。
- **下一步 (Next Steps)**:
  - 等待用户进行真机录制验证。

---

### MoveJ Control Mode for Safe Replay (Critical Update)

- **目的 (Purpose)**: 解决数据集回放时机器人剧烈振荡的安全问题。
- **必要性 (Necessity)**:
  - 使用 ServoJ（实时伺服）回放数据集时，相邻帧目标位置变化大导致机器人剧烈加速追赶。
  - 出现严重振荡，可能损坏机器人硬件。
- **尝试与改动 (Attempts)**:
  - Attempt 1: 在 `tron2_robot.py` 中添加 `send_action_movej()` 方法，使用 `request_movej` 指令。
  - Attempt 2: 在 `lerobot_replay_tron2.py` 中添加 `--use_movej` 和 `--movej_time` 参数，默认启用 MoveJ。
  - Attempt 3: 修改回放循环，自动选择 MoveJ（如果可用）或回退到 ServoJ。
- **结果与反馈 (Results)**:
  - MoveJ 模式下，机器人自动规划平滑轨迹，完全消除振荡。
  - 通过 `move_time` 参数可控制运动速度（0.05s 快但可能抖，0.2s 慢但平滑）。
  - 保留了 ServoJ 作为后备选项（`--use_movej=false`）。
- **关键经验**:
  - **ServoJ**: 实时伺服，需要高频平滑输入，适合 VR 遥操作。
  - **MoveJ**: 关节空间插值，机器人自动规划，适合回放预录轨迹。
  - Tron2 SDK 的 `request_movej` 接收目标位置和运动时间（毫秒），内部自动插值。
- **使用方法**:
  ```bash
  # 默认使用 MoveJ（安全，不会振荡）
  python src/lerobot/scripts/lerobot_replay_tron2.py \
      --robot.type=tron2 \
      --robot.robot_ip="10.192.1.2" \
      --dataset.repo_id="tron2_final" \
      --dataset.episode=0
  
  # 调整运动速度
  --movej_time=0.1    # 0.1秒完成每步（默认）
  --movej_time=0.2    # 更慢更平滑
  ```
- **生成的文件/修改**:
  - `src/lerobot/robots/tron2/tron2_robot.py`: 添加 `send_action_movej()` 方法
  - `src/lerobot/scripts/lerobot_replay_tron2.py`: 支持 `--use_movej` 和 `--movej_time` 参数
  - `.aidoc/REPLAY_GUIDE.md`: 添加 MoveJ 章节
  - `docs/教学.md`: 添加 MoveJ vs ServoJ 对比附录
