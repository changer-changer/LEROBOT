# 2026-03-15 Session: Complete Codebase Analysis & Documentation

## 任务
用户要求全面理解项目代码结构，区分新写代码和原有代码，理解数据格式，确保所有关键信息存储在 .aidoc 中，让新人能理解项目全部细节。

## 执行内容

### 1. 代码库全面分析

**统计**:
- 总 Python 文件: 337 个
- 新增文件: ~20 个
- 修改文件: ~15 个
- 原有 LeRobot 代码: ~300 个

**新增模块识别**:

#### 1.1 ROS2 相机模块
```
src/lerobot/cameras/ros2/
├── configs.py          # ROS2CameraConfig
└── ros2_camera.py      # ROS2Camera
```

**功能**: 通过 rclpy 订阅 ROS2 Image 话题，支持动态缩放

#### 1.2 触觉传感器模块
```
src/lerobot/tactile/
├── __init__.py
├── configs.py              # TactileSensorConfig, Tac3DSensorConfig
├── tactile_sensor.py       # TactileSensor 基类
├── simulated_sensor.py
├── dataset_integration.py
├── utils.py
└── direct_connection/
    └── tac3d_sensor.py     # Tac3DTactileSensor 实现
```

**数据格式**: `(400, 6)` = [dx, dy, dz, Fx, Fy, Fz] (mm, N)

#### 1.3 Tron2 机器人模块
```
src/lerobot/robots/tron2/
├── __init__.py
├── tron2_config.py     # Tron2RobotConfig
└── tron2_robot.py      # Tron2Robot
```

**通信**: WebSocket (ws://10.192.1.2:5000)
**动作空间**: 16维关节位置
**观测空间**: 48维 (16关节 × 3)

#### 1.4 手动录制脚本
```
src/lerobot/scripts/
├── lerobot_record_manual.py        # 原版
└── lerobot_record_manual_fixed.py  # 修复版
```

**控制**: S(开始), Space(保存), Backspace(丢弃)

### 2. 修改的文件分析

#### Python 3.10 兼容性修改
- `pyproject.toml`: Python版本 `>=3.12` → `>=3.10`
- `src/lerobot/__init__.py`: 添加 `typing.Unpack` monkey-patch
- `src/lerobot/utils/io_utils.py`: 修复泛型语法
- `src/lerobot/utils/robot_utils.py`: 添加 `busy_wait` 别名

#### 功能增强
- `src/lerobot/datasets/utils.py`: 支持非3D特征（触觉数据）
- `src/lerobot/utils/visualization_utils.py`: 点云可视化
- `src/lerobot/utils/control_utils.py`: 手动录制键盘事件

### 3. 关键数据结构文档化

#### LeRobot Dataset v3.0 结构
```
dataset_root/
├── meta/
│   ├── info.json                   # 数据集信息
│   │   └── features: {             # 特征定义
│   │       "action": {shape: [16]},
│   │       "observation.state": {shape: [48]},
│   │       "observation.tac3d_sensor": {shape: [400, 6]},
│   │       "observation.images.left_rgb": {dtype: "video"}
│   │   }
│   ├── stats.json                  # 统计信息 (min/max/mean/std)
│   ├── tasks.parquet               # 任务定义
│   └── episodes/                   # Episode元数据
├── data/                           # 传感器数据 (parquet)
└── videos/                         # 视频数据 (mp4)
```

#### Episode Buffer 结构
```python
{
    "size": 150,                      # 帧数
    "task": ["Pick up"] * 150,
    "frame_index": [0, 1, ..., 149],
    "timestamp": [0.0, 0.033, ...],   # frame_index / fps
    "episode_index": 0,
    
    # 数据列
    "action": [np.array(...), ...],           # (16,)
    "observation.state": [np.array(...), ...], # (48,)
    "observation.tac3d_sensor": [np.array(...), ...],  # (400, 6)
}
```

### 4. 创建/更新的文档

#### 新建文档
1. `docs/教学.md` (23,777 bytes)
   - 项目背景
   - 核心架构
   - LeRobot Dataset v3.0 完整规范
   - 修复的问题汇总
   - 关键代码模板
   - 命令行最佳实践
   - 数据集检查工具

2. `.aidoc/PROJECT_CODEBASE.md` (15,355 bytes)
   - 代码库概览
   - 新增代码详解 (ROS2/触觉/Tron2/录制)
   - 修改的文件详解
   - 关键数据结构
   - 设计决策记录
   - 新人入门指南

3. `.aidoc/memory/20260315_codebase_analysis_complete.md`
   - 本次分析完整记录

#### 更新文档
1. `.aidoc/dynamic_memory/@ProjectStructure.md`
   - 完整目录结构
   - 模块依赖关系
   - 新人阅读指南

2. `.aidoc/dynamic_memory/@CurrentState.md`
   - 当前状态标记为 "Ready for Handoff"
   - 关键发现总结
   - 下一步建议

### 5. 关键发现

#### 数据质量问题
1. **点云数据异常**: 形变和受力不成比例（物理关系异常）
   - 符号一致率仅 ~60%（应接近0%）
   - 刚度比例变异系数 > 6（极不稳定）

2. **视频文件问题**: Episode 1/2 视频大小为 0MB
   - 原因: streaming_encoding=true
   - 解决: 使用默认的 streaming_encoding=false

#### 代码设计决策
1. **为什么 WebSocket 而非 ROS2 控制 Tron2?**
   - Tron2 SDK 原生提供 WebSocket 接口
   - 控制命令需要可靠的请求-响应模式

2. **为什么触觉数据存储 (400, 6) 而非分开?**
   - LeRobot Dataset 期望固定的 shape
   - 便于策略模型统一处理
   - 与 PointNet 编码器输入格式兼容

3. **为什么 ROS2Camera 默认不 resize?**
   - 避免强制正方形裁剪导致画面变形
   - 让用户决定是否需要缩放

## 交付物

| 文档 | 路径 | 大小 | 说明 |
|------|------|------|------|
| 教学文档 | `docs/教学.md` | 23KB | 完整使用教学 |
| 代码库指南 | `.aidoc/PROJECT_CODEBASE.md` | 15KB | 新旧代码区分，数据结构 |
| 项目结构 | `.aidoc/dynamic_memory/@ProjectStructure.md` | 6KB | 目录结构和依赖 |
| 当前状态 | `.aidoc/dynamic_memory/@CurrentState.md` | 2.5KB | 状态标记 |
| 会话记录 | `.aidoc/memory/20260315_codebase_analysis_complete.md` | 本文件 | 分析过程 |

## 给新人的信息

### 必须阅读
1. `docs/教学.md` - 理解整体架构和使用方法
2. `.aidoc/PROJECT_CODEBASE.md` - 理解代码结构和数据结构
3. `.aidoc/dynamic_memory/@ProjectStructure.md` - 理解模块关系

### 快速开始
```bash
# 检查环境
python tests/test_full_system.py

# 查看数据集
python -c "import pandas as pd; df=pd.read_parquet('data.parquet'); print(df.columns)"

# 运行录制
python src/lerobot/scripts/lerobot_record_manual_fixed.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.single_task="Test"
```

### 关键知识
- Tac3D 数据格式: (400, 6) = [dx, dy, dz, Fx, Fy, Fz]
- Tron2 动作: 16维关节位置
- 禁用 streaming_encoding 以获得高质量视频
- 使用 libsvtav1 编码器（默认）

---
*Session completed by AI Agent (Kimi Code)*
*Ready for handoff to next agent*
