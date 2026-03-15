# 2026-03-15 Session Log: Complete Teaching & Documentation

## 用户请求
用户要求复盘所有修复过程，并输出完整教学文档，确保下一个 agent 可以立即接班。

## 执行的操作

### 1. 问题复盘与讲解
详细讲解了 9 大类问题及其解决方案：
1. `busy_wait` 导入错误
2. `is_headless` 缺失
3. `logging` 未定义
4. 视频编码参数缺失
5. 机器人连接无错误处理
6. `warmup_cameras` 缺失
7. `streaming_encoding` 导致模糊
8. 128x128 强制 resize
9. Episode 保存逻辑不透明

### 2. 核心架构教学
- 录制循环数据流
- 键盘事件系统
- Episode Buffer 数据结构
- 视频编码原理（streaming vs batch）

### 3. 文档输出
创建了 `docs/教学.md`，包含：
- 完整架构图
- 代码模板
- 命令行最佳实践
- 调试技巧
- 常见错误速查表

### 4. 配置更新
- 修改 `ROS2CameraConfig` 默认分辨率为 `None`
- 添加详细调试信息到保存逻辑

## 关键发现

### Video Encoding Quality
- **师兄版本**: `streaming_encoding=false` (默认), `vcodec=libsvtav1`
- **质量问题原因**: `streaming_encoding=true` 使用实时编码，压缩率高
- **解决方案**: 使用默认设置，不指定 `streaming_encoding`

### Camera Resolution
```python
# 旧默认（问题）
width: int = 128
height: int = 128

# 新默认（修复）
width: int | None = None
height: int | None = None
```

### Episode Save Logic
```python
# save_episode() 内部逻辑：
1. 验证 buffer
2. 编码视频（如果 streaming_encoding=false）
3. 保存元数据
4. 自动调用 clear_episode_buffer()
5. 递增 num_episodes
```

## 文件变更

### 新建/修改
- `docs/教学.md` (新建) - 完整教学文档
- `.aidoc/PROJECT_CONTEXT.md` - 添加修复记录
- `.aidoc/AI_FEEDBACK.md` - 添加经验教训
- `.aidoc/dynamic_memory/@CurrentState.md` - 更新当前状态
- `.aidoc/memory/20260315_teaching_session.md` (新建) - 本次会话记录

### 代码修复
- `src/lerobot/utils/robot_utils.py` - 添加 `busy_wait`
- `src/lerobot/utils/visualization_utils.py` - 添加 `logging`
- `src/lerobot/cameras/ros2/configs.py` - 修改默认分辨率
- `src/lerobot/scripts/lerobot_record_manual_fixed.py` - 完整修复

## 给下一个 Agent 的交接信息

### 立即可以使用的命令
```bash
# 高质量录制（推荐）
python src/lerobot/scripts/lerobot_record_manual_fixed.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --robot.cameras='{
        "left_rgb": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw", "fps": 30, "width": 640, "height": 480},
        "right_rgb": {"type": "ros2", "topic": "/camera/right/color/image_rect_raw", "fps": 30, "width": 640, "height": 480}
    }' \
    --dataset.repo_id="test/test" \
    --dataset.root="/tmp/test_record" \
    --dataset.fps=10 \
    --dataset.single_task="Test" \
    --dataset.video=true \
    --display_data=true
```

### 关键参考
- 教学文档: `docs/教学.md`
- 参考代码: `/home/cuizhixing/WorkspaceBase/lerobot/src/lerobot/scripts/lerobot_record_vr.py`
- 当前代码: `src/lerobot/scripts/lerobot_record_manual_fixed.py`

### 注意事项
1. 不使用 `--dataset.streaming_encoding=true` 以获得最佳视频质量
2. 相机配置中省略 `width`/`height` 保持原始分辨率
3. 脚本已添加详细调试信息，观察 `💾 保存 episode X` 输出

---
*Session completed by AI Agent (Kimi Code)*
*Ready for handoff to next agent*
