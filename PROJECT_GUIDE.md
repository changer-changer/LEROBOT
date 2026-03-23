# Tron2 + LeRobot 项目指南

> **项目**: LeRobot + Tron2 双臂机器人 + Tac3D 触觉传感器集成  
> **版本**: v1.0  
> **日期**: 2026-03-15

---

## 📚 文档导航

本项目包含以下文档：

### 快速入门
- **README_TRON2.md** - Tron2 数据集标准与关节定义
- **PROJECT_GUIDE.md** (本文件) - 项目总览与导航

### 详细文档 (位于 `.aidoc/`)

| 文档 | 用途 | 目标读者 |
|------|------|---------|
| [TRON2_ROBOT_SPEC.md](.aidoc/TRON2_ROBOT_SPEC.md) | 机器人规格与数据集标准 | 所有人 |
| [TRON2_DATASET_GUIDE.md](.aidoc/TRON2_DATASET_GUIDE.md) | 数据集完整指南 | 开发者 |
| [USER_GUIDE.md](.aidoc/USER_GUIDE.md) | 录制功能用户指南 | 用户/操作员 |
| [REPLAY_GUIDE.md](.aidoc/REPLAY_GUIDE.md) | 回放功能用户指南 | 用户/操作员 |
| [PROJECT_PROGRESS.md](.aidoc/PROJECT_PROGRESS.md) | 项目进展记录 | AI/开发者 |
| [PROJECT_CODEBASE.md](.aidoc/PROJECT_CODEBASE.md) | 代码库结构 | 开发者 |

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活环境
conda activate lerobot
source /opt/ros/humble/setup.bash
```

### 2. 启动录制

```bash
python src/lerobot/scripts/lerobot_record_manual_fixed.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.repo_id="username/dataset" \
    --dataset.single_task="Task description"
```

### 3. 键盘控制

| 按键 | 功能 |
|------|------|
| `S` | 开始录制 |
| `Space` | 保存 episode |
| `Backspace` | 丢弃 episode |
| `ESC` | 退出 |

---

## 📁 项目结构

```
lerobot_integrated/
├── src/lerobot/
│   ├── robots/tron2/           # Tron2 机器人驱动
│   ├── cameras/ros2/           # ROS2 相机
│   ├── tactile/                # 触觉传感器
│   └── scripts/lerobot_record_manual_fixed.py  # 录制脚本
├── .aidoc/                     # 项目文档
│   ├── USER_GUIDE.md           # 用户指南
│   ├── TRON2_DATASET_GUIDE.md  # 数据集指南
│   └── PROJECT_PROGRESS.md     # 项目进展
└── README_TRON2.md             # 数据集标准
```

---

## 🔑 关键技术点

### 48 维 Observation

```python
observation.state.shape = (48,)  # 16 关节 × [pos, vel, tau]
```

### 16 维 Action

```python
action.shape = (16,)  # 仅目标位置
```

### 触觉数据

```python
tactile.shape = (400, 6)  # [dx, dy, dz, Fx, Fy, Fz]
```

---

## 📖 推荐阅读顺序

1. **新用户**: README_TRON2.md → USER_GUIDE.md
2. **开发者**: TRON2_DATASET_GUIDE.md → PROJECT_CODEBASE.md
3. **AI 助手**: PROJECT_PROGRESS.md → PROJECT_CONTEXT.md

---

## ⚠️ 重要提示

1. **视频编码**: 必须使用 `streaming_encoding=false`，否则视频模糊
2. **Python 版本**: 使用 Python 3.10 (ROS2 Humble 兼容)
3. **触觉校准**: 使用前必须在 Tac3D-Desktop 中执行 Tare
4. **网络配置**: 开发机 IP 必须设置为 10.192.1.x 网段

---

**最后更新**: 2026-03-15
