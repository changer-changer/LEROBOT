# Tron2 机器人数据集完整指南

> **版本**: v1.0  
> **日期**: 2026-03-15  
> **适用机器人**: DACH_TRON2A (双臂形态 + 逐际二指夹爪)  
> **固件版本**: r-1.2.25  
> **LeRobot 版本**: 0.5.1+

---

## 目录

1. [数据集总览](#1-数据集总览)
2. [机器人关节系统](#2-机器人关节系统)
3. [Observation State 详解](#3-observation-state-详解)
4. [Action 详解](#4-action-详解)
5. [图像数据](#5-图像数据)
6. [触觉传感器数据](#6-触觉传感器数据)
7. [数据存储格式](#7-数据存储格式)
8. [数据读取示例](#8-数据读取示例)
9. [训练策略注意事项](#9-训练策略注意事项)
10. [故障排查](#10-故障排查)

---

## 1. 数据集总览

### 1.1 数据组成

Tron2 数据集是一个多模态机器人数据集，包含以下数据流：

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Tron2 Dataset Structure                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Observation (观测数据)                                             │
│  ├── observation.state: (48,) float32      # 关节状态              │
│  ├── observation.images.cam_left: video    # 左相机图像            │
│  ├── observation.images.cam_right: video   # 右相机图像            │
│  └── observation.tac3d_sensor: (400, 6)    # 触觉数据 (可选)       │
│                                                                     │
│  Action (动作数据)                                                  │
│  └── action: (16,) float32                 # 关节目标位置          │
│                                                                     │
│  Metadata (元数据)                                                  │
│  ├── episode_index: int                    # Episode 编号          │
│  ├── frame_index: int                      # 帧编号                │
│  ├── timestamp: float64                    # 时间戳                │
│  └── task: string                          # 任务描述              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 数据采集频率

| 数据类型 | 频率 | 说明 |
|---------|------|------|
| 关节状态 | 50Hz | WebSocket 查询频率 |
| 相机图像 | 30Hz | ROS2 话题订阅 |
| 触觉数据 | 30Hz | Tac3D UDP 接收 |
| 数据集存储 | 30Hz | 统一降采样到 30FPS |

---

## 2. 机器人关节系统

### 2.1 机械结构

Tron2 双臂机器人由以下部分组成：

- **左臂**: 7 自由度串联机械臂
- **右臂**: 7 自由度串联机械臂
- **左夹爪**: 逐际二指平行夹爪
- **右夹爪**: 逐际二指平行夹爪

总计 **16 个控制维度**。

### 2.2 关节详细定义

#### 左臂关节 (0-6)

| 索引 | 名称 | 类型 | 描述 | 单位 | 下限 (rad) | 上限 (rad) | 零位 |
|:----:|------|------|------|:----:|:----------:|:----------:|:----:|
| 0 | left_arm_joint_0 | 旋转 | 根部旋转 (Base Rotation) | rad | -3.1416 | 2.5994 | 0 |
| 1 | left_arm_joint_1 | 旋转 | 大臂俯仰 (Shoulder Pitch) | rad | -0.2618 | 2.9671 | 0 |
| 2 | left_arm_joint_2 | 旋转 | 大臂旋转 (Upper Arm Roll) | rad | -3.6652 | 1.4835 | 0 |
| 3 | left_arm_joint_3 | 旋转 | 肘部俯仰 (Elbow Pitch) | rad | -2.6180 | 0.5236 | 0 |
| 4 | left_arm_joint_4 | 旋转 | 前臂旋转 (Forearm Roll) | rad | -1.7453 | 1.3963 | 0 |
| 5 | left_arm_joint_5 | 旋转 | 腕部俯仰 (Wrist Pitch) | rad | -0.7854 | 0.7854 | 0 |
| 6 | left_arm_joint_6 | 旋转 | 腕部旋转 (Wrist Roll) | rad | -1.5708 | 1.5708 | 0 |

#### 右臂关节 (7-13)

| 索引 | 名称 | 类型 | 描述 | 单位 | 下限 (rad) | 上限 (rad) | 零位 |
|:----:|------|------|------|:----:|:----------:|:----------:|:----:|
| 7 | right_arm_joint_0 | 旋转 | 根部旋转 (Base Rotation) | rad | -3.1416 | 2.5994 | 0 |
| 8 | right_arm_joint_1 | 旋转 | 大臂俯仰 (Shoulder Pitch) | rad | -0.2618 | 2.9671 | 0 |
| 9 | right_arm_joint_2 | 旋转 | 大臂旋转 (Upper Arm Roll) | rad | -3.6652 | 1.4835 | 0 |
| 10 | right_arm_joint_3 | 旋转 | 肘部俯仰 (Elbow Pitch) | rad | -2.6180 | 0.5236 | 0 |
| 11 | right_arm_joint_4 | 旋转 | 前臂旋转 (Forearm Roll) | rad | -1.7453 | 1.3963 | 0 |
| 12 | right_arm_joint_5 | 旋转 | 腕部俯仰 (Wrist Pitch) | rad | -0.7854 | 0.7854 | 0 |
| 13 | right_arm_joint_6 | 旋转 | 腕部旋转 (Wrist Roll) | rad | -1.5708 | 1.5708 | 0 |

#### 夹爪 (14-15)

| 索引 | 名称 | 类型 | 描述 | 单位 | 下限 | 上限 | 零位 |
|:----:|------|------|------|:----:|:----:|:----:|:----:|
| 14 | left_gripper | 平行夹爪 | 左夹爪开口度 | % | 0 | 100 | 0 |
| 15 | right_gripper | 平行夹爪 | 右夹爪开口度 | % | 0 | 100 | 0 |

**夹爪说明**:
- 0% = 完全闭合
- 100% = 完全张开
- 控制命令通过 `request_set_limx_2fclaw_cmd` 发送
- 反馈通过 `request_get_limx_2fclaw_state` 获取

### 2.3 工作空间

#### 左臂工作空间 (单位: 米)

```
X: [0.250, 0.732]  (前后)
Y: [-0.213, 0.900] (左右，正方向指向机器人左侧)
Z: [-0.673, 0.500] (上下，负方向向下)
```

#### 右臂工作空间 (单位: 米)

```
X: [0.250, 0.732]  (前后)
Y: [-0.900, 0.213] (左右，负方向指向机器人右侧)
Z: [-0.673, 0.500] (上下)
```

---

## 3. Observation State 详解

### 3.1 数据格式

Observation State 是一个 **48 维的 float32 数组**，包含所有 16 个关节的位置、速度和力矩信息。

```python
observation_state = np.zeros(48, dtype=np.float32)
```

### 3.2 数组索引映射

```python
# 数组索引 = joint_index * 3 + offset
# offset: 0=pos, 1=vel, 2=tau

# 左臂 (joints 0-6)
obs[0]   # joint_0_pos  (rad)
obs[1]   # joint_0_vel  (rad/s)
obs[2]   # joint_0_tau  (Nm)
obs[3]   # joint_1_pos  (rad)
obs[4]   # joint_1_vel  (rad/s)
obs[5]   # joint_1_tau  (Nm)
...
obs[18]  # joint_6_pos  (rad)
obs[19]  # joint_6_vel  (rad/s)
obs[20]  # joint_6_tau  (Nm)

# 右臂 (joints 7-13)
obs[21]  # joint_7_pos  (rad)
obs[22]  # joint_7_vel  (rad/s)
obs[23]  # joint_7_tau  (Nm)
...
obs[39]  # joint_13_pos (rad)
obs[40]  # joint_13_vel (rad/s)
obs[41]  # joint_13_tau (Nm)

# 夹爪 (joints 14-15)
obs[42]  # joint_14_pos (%)
obs[43]  # joint_14_vel
obs[44]  # joint_14_tau
obs[45]  # joint_15_pos (%)
obs[46]  # joint_15_vel
obs[47]  # joint_15_tau
```

### 3.3 数据获取流程

```python
# 1. WebSocket 发送查询请求
request_get_joint_state       # 获取关节 0-13
request_get_limx_2fclaw_state # 获取夹爪 14-15

# 2. 异步接收响应
response_get_joint_state:
    - q: [q0, q1, ..., q13]      # 14 个关节位置
    - dq: [dq0, dq1, ..., dq13]  # 14 个关节速度
    - tau: [tau0, ..., tau13]    # 14 个关节力矩

response_get_limx_2fclaw_state:
    - left_opening: 0-100   # joint_14_pos
    - right_opening: 0-100  # joint_15_pos
```

### 3.4 数据特点

- **位置 (pos)**:
  - 关节 0-13: 弧度 (rad)，范围见关节限位表
  - 关节 14-15: 百分比 (%)，范围 [0, 100]

- **速度 (vel)**:
  - 关节 0-13: rad/s
  - 关节 14-15: %/s (估算值)

- **力矩 (tau)**:
  - 关节 0-13: Nm
  - 关节 14-15: 夹爪力反馈 (近似值)

---

## 4. Action 详解

### 4.1 数据格式

Action 是一个 **16 维的 float32 数组**，仅包含目标关节位置。

```python
action = np.zeros(16, dtype=np.float32)
```

### 4.2 数组索引映射

```python
# 左臂目标位置
action[0]   # joint_0 目标位置 (rad)
action[1]   # joint_1 目标位置 (rad)
...
action[6]   # joint_6 目标位置 (rad)

# 右臂目标位置
action[7]   # joint_7 目标位置 (rad)
...
action[13]  # joint_13 目标位置 (rad)

# 夹爪目标位置
action[14]  # 左夹爪目标开口度 (0-100)
action[15]  # 右夹爪目标开口度 (0-100)
```

### 4.3 数据发送流程

```python
# 1. 构建目标数组
targets = [q0, q1, ..., q15]  # 16 个值

# 2. 分离臂和夹爪
arm_q = targets[0:14]     # 关节 0-13
gripper = targets[14:16]  # 关节 14-15

# 3. 发送臂控制命令 (ServoJ)
request_servoj:
    q: arm_q (14 values in rad)
    v: [0]*14
    kp: [150]*14
    kd: [10]*14
    tau: [0]*14

# 4. 发送夹爪控制命令
request_set_limx_2fclaw_cmd:
    left_opening: int(targets[14])
    right_opening: int(targets[15])
```

### 4.4 与 Observation 的区别

| 特性 | Observation State | Action |
|------|-------------------|--------|
| 维度 | 48 | 16 |
| 内容 | pos + vel + tau | 仅 pos |
| 用途 | 策略输入 | 策略输出/机器人控制 |
| 数据来源 | 传感器反馈 | 策略预测/遥操作 |

---

## 5. 图像数据

### 5.1 相机配置

#### 默认配置

| 参数 | 左相机 | 右相机 |
|------|--------|--------|
| ROS2 话题 | `/camera/left/color/image_rect_raw` | `/camera/right/color/image_rect_raw` |
| 分辨率 | 640×480 | 640×480 |
| 帧率 | 30 FPS | 30 FPS |
| 编码格式 | rgb8 | rgb8 |
| 色彩空间 | RGB | RGB |

#### 图像预处理

```python
# 1. ROS2 Image → NumPy (零拷贝)
frame = np.frombuffer(msg.data, dtype=np.uint8)
frame = frame.reshape((msg.height, msg.width, 3))

# 2. 可选缩放 (INTER_AREA 算法)
if target_size:
    frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
```

### 5.2 图像存储

```
dataset/
└── videos/
    └── episode_0/
        ├── cam_left.mp4    # 左相机视频
        └── cam_right.mp4   # 右相机视频
```

#### 视频编码参数

```python
# 推荐配置 (高质量)
vcodec = "libsvtav1"        # 或 "h264"
preset = "slow"             # 编码速度/质量权衡
streaming_encoding = False  # 必须为 False！

# 避免使用 (会导致模糊)
streaming_encoding = True
```

### 5.3 图像读取

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset("path/to/dataset")

# 获取第 0 个 episode 的所有帧
episode_data = dataset.get_episode(0)

# 图像以视频路径形式存储
# 实际像素数据在训练时从视频解码
```

---

## 6. 触觉传感器数据

### 6.1 Tac3D 传感器概述

- **型号**: Tac3D 高分辨率触觉传感器
- **感应阵列**: 20×20 = 400 个触觉点
- **数据维度**: 6D (3D 形变 + 3D 力)
- **通信方式**: UDP (端口 9988)
- **数据频率**: 30Hz

### 6.2 数据格式

#### 原始数据结构

```python
tactile_data = np.zeros((400, 6), dtype=np.float32)

# 第 i 个触觉点
tactile_data[i, 0]  # dx: X 方向形变 (mm)
tactile_data[i, 1]  # dy: Y 方向形变 (mm)
tactile_data[i, 2]  # dz: Z 方向形变 (mm)
tactile_data[i, 3]  # Fx: X 方向力 (N)
tactile_data[i, 4]  # Fy: Y 方向力 (N)
tactile_data[i, 5]  # Fz: Z 方向力 (N)
```

#### 触觉点布局

```
Tac3D 传感器表面 (20×20 阵列)

      Col 0   Col 1   ...   Col 19
     ┌─────┬─────┬─────┬─────┐
Row 0│  0  │  1  │ ... │ 19  │
     ├─────┼─────┼─────┼─────┤
Row 1│ 20  │ 21  │ ... │ 39  │
     ├─────┼─────┼─────┼─────┤
     │ ... │ ... │ ... │ ... │
     ├─────┼─────┼─────┼─────┤
Row 19│ 380 │ 381 │ ... │ 399 │
     └─────┴─────┴─────┴─────┘

索引计算: index = row * 20 + col
```

### 6.3 数据类型配置

| data_type | 形状 | 内容 | 用途 |
|-----------|------|------|------|
| DISPLACEMENT | (400, 3) | [dx, dy, dz] | 仅形变 |
| FORCE | (400, 3) | [Fx, Fy, Fz] | 仅力 |
| FULL | (400, 6) | [dx, dy, dz, Fx, Fy, Fz] | 完整数据 |

### 6.4 物理意义

#### 形变 (Displacement)
- 单位: 毫米 (mm)
- 含义: 传感器表面相对于无接触状态的位移
- 方向: 向外为正，向内为负

#### 力 (Force)
- 单位: 牛顿 (N)
- 含义: 作用在传感器表面的接触力
- 方向: 根据传感器坐标系定义

#### 已知问题
- 力和形变符号相反的比例仅约 40%
- 物理上应相反 (F = -kx)
- 建议训练时优先使用形变数据 (前 3 维)

### 6.5 数据校准 (Tare)

```python
# 零位校准 - 消除传感器偏移
sensor.tare()  # 发送校准命令到 Tac3D-Desktop

# 校准后，无接触时数据应接近零
```

---

## 7. 数据存储格式

### 7.1 目录结构

```
dataset/
├── data/                           # 主数据 (Parquet)
│   └── chunk-000/
│       └── file-000.parquet
├── meta/                           # 元数据
│   ├── info.json                   # 数据集信息
│   ├── stats.json                  # 统计信息
│   └── episodes/                   # Episode 索引
│       └── chunk-000/
│           └── file-000.parquet
└── videos/                         # 视频文件
    └── episode_0/
        ├── cam_left.mp4
        └── cam_right.mp4
```

### 7.2 info.json 结构

```json
{
    "repo_id": "username/dataset_name",
    "robot_type": "tron2",
    "fps": 30,
    "total_episodes": 10,
    "total_frames": 1500,
    "total_videos": 20,
    "chunks_size": 1000,
    "video": true,
    "features": {
        "observation.state": {
            "dtype": "float32",
            "shape": [48],
            "names": ["joint_0_pos", "joint_0_vel", ...]
        },
        "action": {
            "dtype": "float32",
            "shape": [16],
            "names": ["action.joint_0_pos", ...]
        },
        "observation.images.cam_left": {
            "dtype": "video",
            "shape": [480, 640, 3],
            "info": {"video.codec": "libsvtav1", "video.fps": 30}
        },
        "observation.tac3d_sensor": {
            "dtype": "float32",
            "shape": [400, 6],
            "names": ["dx", "dy", "dz", "Fx", "Fy", "Fz"]
        }
    }
}
```

### 7.3 Parquet 文件结构

| 列名 | 类型 | 形状 | 说明 |
|------|------|------|------|
| `observation.state` | float32 | (48,) | 关节状态 |
| `action` | float32 | (16,) | 目标位置 |
| `observation.images.cam_left` | string | () | 视频文件路径 |
| `observation.images.cam_right` | string | () | 视频文件路径 |
| `observation.tac3d_sensor` | float32 | (400, 6) | 触觉数据 |
| `episode_index` | int64 | () | Episode 编号 |
| `frame_index` | int64 | () | 帧编号 |
| `timestamp` | float64 | () | 时间戳 (秒) |
| `task` | string | () | 任务描述 |

---

## 8. 数据读取示例

### 8.1 读取数据集

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

# 加载数据集
dataset = LeRobotDataset("path/to/tron2_dataset")

# 查看基本信息
print(f"Episodes: {dataset.num_episodes}")
print(f"Total frames: {dataset.num_frames}")
print(f"Features: {list(dataset.features.keys())}")
```

### 8.2 读取 Observation

```python
# 获取第 0 帧的数据
frame = dataset[0]

# Observation State
obs_state = frame["observation.state"]
print(f"State shape: {obs_state.shape}")  # (48,)

# 提取关节 0 的信息
joint_0_pos = obs_state[0]   # 位置
joint_0_vel = obs_state[1]   # 速度
joint_0_tau = obs_state[2]   # 力矩
```

### 8.3 读取 Action

```python
action = frame["action"]
print(f"Action shape: {action.shape}")  # (16,)

# 左臂动作
left_arm_action = action[0:7]

# 右臂动作
right_arm_action = action[7:14]

# 夹爪动作
left_gripper = action[14]   # 0-100
right_gripper = action[15]  # 0-100
```

### 8.4 读取触觉数据

```python
if "observation.tac3d_sensor" in frame:
    tactile = frame["observation.tac3d_sensor"]
    print(f"Tactile shape: {tactile.shape}")  # (400, 6)
    
    # 提取形变
    displacement = tactile[:, 0:3]  # (400, 3)
    
    # 提取力
    force = tactile[:, 3:6]  # (400, 3)
    
    # 计算接触区域
    contact_mask = np.linalg.norm(displacement, axis=1) > 0.1  # mm
    print(f"Contact points: {contact_mask.sum()}")
```

### 8.5 可视化触觉数据

```python
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# 读取触觉数据
tactile = frame["observation.tac3d_sensor"]
displacement = tactile[:, 0:3]
force = tactile[:, 3:6]

# 重建 20×20 网格
rows, cols = 20, 20
Z = displacement[:, 2].reshape(rows, cols)  # Z方向形变

# 绘制热力图
plt.figure(figsize=(8, 6))
plt.imshow(Z, cmap='hot', interpolation='bilinear')
plt.colorbar(label='Displacement Z (mm)')
plt.title('Tac3D Tactile Sensor')
plt.xlabel('Column')
plt.ylabel('Row')
plt.show()
```

---

## 9. 训练策略注意事项

### 9.1 Observation 维度适配

Tron2 的 observation.state 是 **48 维**，而大多数预训练模型期望 6 维或 29 维。

**解决方案 1: 训练新模型**
```python
# 使用 Tron2 数据集从头训练
python src/lerobot/scripts/train.py \
    --policy.type=act \
    --dataset.repo_id=your_tron2_dataset
```

**解决方案 2: 使用投影层适配**
```python
# 在策略网络前添加投影层
# 48维 → 隐藏层 → 策略期望维度
```

### 9.2 触觉数据使用建议

```python
# 推荐：仅使用形变数据
tactile_input = tactile[:, 0:3]  # (400, 3)

# 或者：降采样到更低维度
# 例如：20×20 → 10×10 池化
```

### 9.3 夹爪动作范围

```python
# 夹爪动作需要在训练时归一化
# 原始范围 [0, 100] → 归一化到 [-1, 1] 或 [0, 1]
```

---

## 10. 故障排查

### 10.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| observation.state 全零 | 机器人未连接 | 检查 WebSocket 连接 |
| 图像黑屏 | ROS2 话题错误 | 确认话题名称和权限 |
| 触觉数据全零 | 传感器未接触/未校准 | 执行 tare() 并触碰传感器 |
| 夹爪不响应 | 值超出范围 | 确保值在 [0, 100] |
| 视频模糊 | streaming_encoding=true | 设置为 false |

### 10.2 调试命令

```bash
# 检查 ROS2 话题
ros2 topic list | grep camera
ros2 topic hz /camera/left/color/image_rect_raw

# 检查 Tac3D 数据
python -c "
import pandas as pd
df = pd.read_parquet('data.parquet')
print(df['observation.tac3d_sensor'].iloc[0].shape)
"

# 查看视频信息
ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,codec_name \
    -of default=noprint_wrappers=1 videos/episode_0/cam_left.mp4
```

---

**文档版本**: 1.0  
**最后更新**: 2026-03-15
