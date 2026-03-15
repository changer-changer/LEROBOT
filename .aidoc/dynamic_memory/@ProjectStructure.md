# @ProjectStructure

`lerobot_integrated/`: [Core Workspace] -> [Integration of Tac3D and Tron2 with LeRobot v3.0]

## 📁 完整目录结构

```
lerobot_integrated/
├── src/lerobot/                    # 主代码库
│   ├── cameras/                    # 相机模块
│   │   ├── ros2/                   # 【新增】ROS2相机
│   │   │   ├── configs.py          # ROS2CameraConfig
│   │   │   └── ros2_camera.py      # ROS2Camera实现
│   │   └── ...                     # 其他相机类型
│   ├── robots/                     # 机器人模块
│   │   ├── tron2/                  # 【新增】Tron2机器人
│   │   │   ├── tron2_config.py     # Tron2RobotConfig
│   │   │   ├── tron2_robot.py      # Tron2Robot实现
│   │   │   └── __init__.py
│   │   └── ...                     # 其他机器人类型
│   ├── tactile/                    # 【新增】触觉传感器模块
│   │   ├── direct_connection/      # 直连模式
│   │   │   └── tac3d_sensor.py     # Tac3DTactileSensor
│   │   ├── configs.py              # 触觉传感器配置
│   │   ├── tactile_sensor.py       # 抽象基类
│   │   └── utils.py                # 工厂函数
│   ├── datasets/                   # 数据集管理
│   │   ├── lerobot_dataset.py      # 核心数据集类
│   │   └── utils.py                # 【修改】支持触觉数据
│   ├── scripts/                    # 命令行脚本
│   │   ├── lerobot_record_manual_fixed.py  # 【新增】手动录制
│   │   └── ...
│   └── utils/                      # 工具函数
│       ├── robot_utils.py          # 【修改】添加busy_wait
│       └── visualization_utils.py  # 【修改】支持点云
├── docs/                           # 【新增】文档
│   └── 教学.md                     # 完整教学文档
├── .aidoc/                         # 【新增】AI记忆系统
│   ├── PROJECT_CONTEXT.md          # 项目演进记录
│   ├── PROJECT_CODEBASE.md         # 代码库完整指南
│   ├── AI_FEEDBACK.md              # 经验教训
│   └── dynamic_memory/             # 动态记忆
│       ├── @CurrentState.md
│       ├── @ProjectStructure.md    # 本文件
│       ├── @TechSpec.md
│       └── memory/                 # 会话记录
└── tests/                          # 测试代码
    └── test_full_system.py         # 【新增】集成测试
```

## 🆕 新增模块详解

### 1. ROS2 相机模块 (`cameras/ros2/`)

**目的**: 支持订阅 ROS2 Image 话题

**核心类**:
- `ROS2CameraConfig`: 配置话题名称、分辨率、格式
- `ROS2Camera`: 实现相机接口，通过 rclpy 订阅数据

**数据流**:
```
ROS2 Topic → rclpy订阅 → NumPy转换 → 可选缩放 → 返回帧
```

### 2. 触觉传感器模块 (`tactile/`)

**目的**: 统一触觉传感器接口

**核心类**:
- `TactileSensorConfig`: 配置基类
- `Tac3DSensorConfig`: Tac3D专用配置
- `TactileSensor`: 抽象基类
- `Tac3DTactileSensor`: Tac3D实现

**数据格式**:
```python
(400, 6)  # 400点 x [dx, dy, dz, Fx, Fy, Fz]
```

### 3. Tron2 机器人模块 (`robots/tron2/`)

**目的**: 集成 Tron2 双臂机器人

**核心类**:
- `Tron2RobotConfig`: 配置IP、关节、相机、触觉
- `Tron2Robot`: WebSocket通信，16自由度

**通信**:
```
WebSocket (ws://10.192.1.2:5000)
├── 订阅: RobotState (q, dq, tau)
└── 发送: RobotCmd (target_q, Kp, Kd)
```

### 4. 手动录制脚本 (`scripts/lerobot_record_manual_fixed.py`)

**目的**: 支持键盘控制录制

**控制方式**:
- S: 开始录制
- Space: 保存
- Backspace: 丢弃

## 🔧 修改的文件

### Python 3.10 兼容性
- `pyproject.toml`: 降级 Python 版本要求
- `src/lerobot/__init__.py`: 添加 typing.Unpack
- `src/lerobot/utils/robot_utils.py`: 添加 busy_wait

### 功能增强
- `datasets/utils.py`: 支持非3D特征（触觉数据）
- `utils/visualization_utils.py`: 支持点云可视化
- `utils/control_utils.py`: 添加手动录制事件

## 📊 关键数据结构

### 数据集结构 (LeRobot v3.0)
```
dataset_root/
├── meta/
│   ├── info.json              # 数据集信息
│   ├── stats.json             # 统计信息
│   └── episodes/              # Episode元数据
├── data/                      # 传感器数据
└── videos/                    # 视频文件
```

### 触觉数据 (Tac3D)
```python
{
    "observation.tac3d_sensor": {
        "dtype": "float32",
        "shape": (400, 6)  # [dx, dy, dz, Fx, Fy, Fz]
    }
}
```

### Tron2 动作空间
```python
{
    "action": {
        "dtype": "float32",
        "shape": (16,),  # 16关节位置
        "names": ["joint_0_pos", ..., "joint_15_pos"]
    }
}
```

## 🔗 模块依赖关系

```
lerobot_record_manual_fixed.py
    ├── Tron2Robot
    │   ├── ROS2Camera (left_rgb, right_rgb)
    │   └── Tac3DTactileSensor (tac3d_sensor)
    └── LeRobotDataset
        └── VideoEncodingManager
```

## 📚 新人阅读指南

### 快速入门
1. 阅读 `docs/教学.md` 了解整体架构
2. 查看 `.aidoc/PROJECT_CODEBASE.md` 了解代码细节
3. 运行 `tests/test_full_system.py` 验证环境

### 深入理解
1. **相机**: `cameras/ros2/ros2_camera.py`
2. **触觉**: `tactile/direct_connection/tac3d_sensor.py`
3. **机器人**: `robots/tron2/tron2_robot.py`
4. **录制**: `scripts/lerobot_record_manual_fixed.py`

### 调试工具
```bash
# 检查数据集
python -c "import pandas as pd; df=pd.read_parquet('data.parquet'); print(df.columns)"

# 检查 Tac3D
python -c "import numpy as np; arr=np.load('tactile.npy'); print(arr.shape)"

# ROS2 话题
ros2 topic list | grep -E "camera|tactile"
```

## 📞 参考资源

- **教学文档**: `docs/教学.md`
- **代码指南**: `.aidoc/PROJECT_CODEBASE.md`
- **师兄代码**: `/home/cuizhixing/WorkspaceBase/lerobot/src/lerobot/scripts/lerobot_record_vr.py`
- **Tac3D文档**: `/media/cuizhixing/share/workspace/multiversion_lerobot/RESOURCE/Tac3D-SDK-精简版.md`

---
*Last updated: 2026-03-15*
