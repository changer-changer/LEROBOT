# Tron2 + LeRobot 项目交接文档

> **创建时间**: 2026-03-15  
> **项目**: Tron2 机器人与 LeRobot 框架集成  
> **状态**: 功能完整，文档完善，待交接

---

## 📋 项目概述

本项目完成了 Tron2 双臂机器人与 HuggingFace LeRobot 框架的完整集成，包括：

1. **机器人控制**: WebSocket 通信控制 16-DOF（14 臂 + 2 爪）
2. **视觉系统**: ROS2 双目相机集成（640×480）
3. **触觉感知**: Tac3D 触觉传感器（400 点，6D 数据）
4. **录制系统**: 手动键盘控制录制脚本

---

## 🔑 关键设计决策（必读）

### 1. 48 维观测状态（Tron2 独有）

```python
# Tron2 的 observation.state 形状: (48,)
# 其他机器人（如 Koch）: (6,) 或 (29,)

observation.state = [
    joint_0_pos, joint_0_vel, joint_0_tau,  # 关节 0
    joint_1_pos, joint_1_vel, joint_1_tau,  # 关节 1
    ...
    joint_15_pos, joint_15_vel, joint_15_tau,  # 关节 15
]
```

**为什么独特？**
- Tron2 的 WebSocket API 同时返回位置、速度、力矩
- 其他 LeRobot 机器人通常只返回位置
- 策略网络需要适配 48 维输入

### 2. Tac3D 触觉数据结构

```python
# 形状: (400, 6)
# 含义: 400 个触点 × [dx, dy, dz, Fx, Fy, Fz]

tactile_data = [
    [dx0, dy0, dz0, Fx0, Fy0, Fz0],  # 点 0
    [dx1, dy1, dz1, Fx1, Fy1, Fz1],  # 点 1
    ...
]
```

**已知问题**: 
- 力和形变符号相反的比例仅 40%（物理上应为相反）
- 建议使用仅形变数据（前 3 维）作为策略输入

### 3. 视频编码配置

```python
# ✅ 推荐配置（高质量）
vcodec="libsvtav1"          # 或 "h264"
streaming_encoding=false    # 必须 false！

# ❌ 避免（会导致模糊）
streaming_encoding=true
```

### 4. ROS2 相机分辨率

```python
# ✅ 保留原始分辨率（推荐）
--robot.cameras='{
    "left_rgb": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw", "fps": 30}
}'

# ❌ 强制 resize（可能导致变形）
--robot.cameras='{
    "left_rgb": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw", 
                 "fps": 30, "width": 128, "height": 128}
}'
```

---

## 📁 核心文件位置

### 新建/修改的文件

| 文件 | 说明 | 重要性 |
|------|------|--------|
| `src/lerobot/robots/tron2/tron2_robot.py` | Tron2 机器人主类 | ⭐⭐⭐ |
| `src/lerobot/robots/tron2/tron2_configs.py` | 配置类 | ⭐⭐⭐ |
| `src/lerobot/tactile/direct_connection/tac3d_sensor.py` | Tac3D 传感器 | ⭐⭐⭐ |
| `src/lerobot/cameras/ros2/ros2_camera.py` | ROS2 相机 | ⭐⭐⭐ |
| `src/lerobot/scripts/lerobot_record_manual_fixed.py` | 录制脚本 | ⭐⭐⭐ |
| `src/lerobot/utils/visualization_utils.py` | 可视化工具 | ⭐⭐ |

### 师兄参考代码

```
/home/cuizhixing/WorkspaceBase/lerobot/src/lerobot/scripts/lerobot_record_vr.py
```

---

## 🚀 快速开始

### 1. 环境激活

```bash
conda activate lerobot
source /opt/ros/humble/setup.bash
```

### 2. 启动录制

```bash
cd /media/cuizhixing/share/workspace/multiversion_lerobot/lerobot_integrated

python src/lerobot/scripts/lerobot_record_manual_fixed.py \
    --robot.type=tron2 \
    --robot.ip_address=192.168.10.171 \
    --robot.cameras='{
        "left_rgb": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw", "fps": 30},
        "right_rgb": {"type": "ros2", "topic": "/camera/right/color/image_rect_raw", "fps": 30}
    }' \
    --robot.tactile_sensors='{
        "tac3d_sensor": {"type": "tac3d", "udp_port": 9988, "fps": 30}
    }' \
    --dataset.repo_id=tron2_demo \
    --dataset.single_task="Pick up the object" \
    --dataset.output_root=/home/cuizhixing/data/outputs/recordings \
    --dataset.fps=30
```

### 3. 键盘控制

| 按键 | 功能 |
|------|------|
| `S` | 开始录制 |
| `Space` | 保存当前 episode |
| `Backspace` | 丢弃当前 episode |
| `ESC` | 退出程序 |

---

## 📊 数据结构示例

### Dataset 目录结构

```
outputs/recordings/tron2_demo/
├── data/
│   └── chunk-000/
│       └── file-000.parquet          # 主数据文件
├── meta/
│   ├── info.json                     # 元数据
│   ├── episodes/
│   │   └── chunk-000/
│   │       └── file-000.parquet      # episode 索引
│   └── stats.json                    # 统计信息
└── videos/
    └── episode_0/
        ├── left_rgb.mp4              # 左相机视频
        └── right_rgb.mp4             # 右相机视频
```

### info.json 关键字段

```json
{
    "robot_type": "tron2",
    "fps": 30,
    "total_episodes": 10,
    "features": {
        "observation.state": {
            "dtype": "float32",
            "shape": [48]          // ⚠️ Tron2 特有
        },
        "action": {
            "dtype": "float32",
            "shape": [16]
        },
        "observation.tac3d_sensor": {
            "dtype": "float32",
            "shape": [400, 6]       // 触觉数据
        }
    }
}
```

---

## 🔧 常见问题速查

### Q1: Episode 3 不存在？
**A**: 索引从 0 开始，"episode 3" 对应 `episode_index=2`

### Q2: 视频文件大小为 0MB？
**A**: 检查 `streaming_encoding` 是否为 `false`，使用 `ffprobe` 验证

### Q3: 点云数据全零？
**A**: 传感器未接触物体或未正确初始化（tare）

### Q4: Python 3.10 语法错误？
**A**: 本项目使用 `from __future__ import annotations` 和 `Generic[T]` 兼容语法

### Q5: 力和形变符号不匹配？
**A**: 已知问题，建议仅使用形变数据（前 3 维）

---

## 📚 详细文档

| 文档 | 位置 | 内容 |
|------|------|------|
| 教学文档 | `docs/教学.md` | 完整开发教程 |
| 代码库文档 | `.aidoc/PROJECT_CODEBASE.md` | 代码结构详解 |
| 项目背景 | `.aidoc/PROJECT_CONTEXT.md` | 上下文信息 |

---

## ⚠️ 待优化事项

1. **Tac3D 数据质量**: 力和形变关系异常，需物理验证
2. **策略适配**: 当前无预训练策略适配 48 维状态
3. **视频编码**: 需进一步测试不同编码器性能

---

## 👥 联系信息

- **师兄参考代码作者**: 原 lerobot_record_vr.py 开发者
- **当前集成开发**: Kimi Code (AI Agent)

---

**最后更新**: 2026-03-15
