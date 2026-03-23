# @CurrentState (March 15, 2026)

*   **Status**: Documentation Complete / Ready for Handoff
*   **Focus**: Fixed OpenCVCamera resolution and device node issues.
*   **Blockers**: None.

## Current Progress:

### ✅ 代码分析完成
* [x] 全面浏览项目代码结构 (337 Python files)
* [x] 识别新创建的文件 (~20 files)
* [x] 识别修改的文件 (~15 files)
* [x] 分析关键数据结构和格式

### ✅ 文档创建完成
* [x] Created `docs/教学.md` - 完整开发教学文档
* [x] Created `.aidoc/PROJECT_CODEBASE.md` - 代码库完整指南
* [x] Updated `.aidoc/dynamic_memory/@ProjectStructure.md` - 项目结构
* [x] Created `.aidoc/memory/20260315_dataset_inspection.md` - 数据检查报告

### ✅ 关键发现记录
* [x] LeRobot Dataset v3.0 数据结构
* [x] Tac3D 触觉数据格式 (400, 6) = [dx, dy, dz, Fx, Fy, Fz]
* [x] Tron2 WebSocket API 规范
* [x] ROS2Camera 数据流设计
* [x] Python 3.10 兼容性修改点

## Key Documents for New Agent:

| 文档 | 路径 | 内容 |
|------|------|------|
| 教学文档 | `docs/教学.md` | 完整使用教学，包含修复的问题 |
| 代码库指南 | `.aidoc/PROJECT_CODEBASE.md` | 新旧代码区分，数据结构详解 |
| 项目结构 | `.aidoc/dynamic_memory/@ProjectStructure.md` | 目录结构和模块依赖 |
| 技术规范 | `.aidoc/dynamic_memory/@TechSpec.md` | 约束和规则 |
| 经验教训 | `.aidoc/AI_FEEDBACK.md` | 踩坑记录和最佳实践 |

## Critical Knowledge:

### 数据格式
```python
# Tac3D 点云 (400, 6)
# [:, 0:3] = 形变 (mm) [dx, dy, dz]
# [:, 3:6] = 受力 (N)  [Fx, Fy, Fz]

# Tron2 动作 (16,) - 关节位置
# Tron2 观测 (48,) - 16关节 × 3 (pos/vel/tau)
```

### 关键配置
```bash
# 高质量录制命令
python src/lerobot/scripts/lerobot_record_manual_fixed.py \
    --robot.type=tron2 \
    --robot.cameras='{"left_rgb": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw"}}' \
    --dataset.vcodec=libsvtav1 \
    --dataset.streaming_encoding=false  # 关键！禁用实时编码
```

### 已知问题
1. 点云数据中形变和受力不成比例（物理关系异常）
2. Episode 1/2 视频文件为空（streaming_encoding 问题）
3. Tac3D 需要正确 tare 校准

## Next Steps for New Agent:
- [ ] Review `docs/教学.md` for comprehensive understanding
- [ ] Check `.aidoc/PROJECT_CODEBASE.md` for code details
- [ ] Run `tests/test_full_system.py` to verify environment
- [ ] Test with actual hardware if available

---
*Last updated: 2026-03-15*
*Status: Ready for handoff to next agent*
