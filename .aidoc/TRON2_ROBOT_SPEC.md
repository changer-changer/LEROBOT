# Tron2 机器人数据集标准与关节定义

> **版本**: v1.0  
> **日期**: 2026-03-15  
> **适用机器人**: DACH_TRON2A (双臂形态)  
> **固件版本**: r-1.2.25

---

## 1. 机器人关节定义

### 1.1 16 个关节组成

Tron2 双臂机器人共有 **16 个控制维度**，分布如下：

| 关节索引 | 名称 | 类型 | 说明 | 单位 |
|:--------:|------|------|------|------|
| 0 | `left_arm_joint_0` | 旋转关节 | 左臂根部旋转 (Base) | rad |
| 1 | `left_arm_joint_1` | 旋转关节 | 左臂大臂俯仰 (Shoulder) | rad |
| 2 | `left_arm_joint_2` | 旋转关节 | 左臂大臂旋转 (Upper Arm) | rad |
| 3 | `left_arm_joint_3` | 旋转关节 | 左臂肘部俯仰 (Elbow) | rad |
| 4 | `left_arm_joint_4` | 旋转关节 | 左臂前臂旋转 (Forearm) | rad |
| 5 | `left_arm_joint_5` | 旋转关节 | 左臂腕部俯仰 (Wrist Pitch) | rad |
| 6 | `left_arm_joint_6` | 旋转关节 | 左臂腕部旋转 (Wrist Roll) | rad |
| 7 | `right_arm_joint_0` | 旋转关节 | 右臂根部旋转 (Base) | rad |
| 8 | `right_arm_joint_1` | 旋转关节 | 右臂大臂俯仰 (Shoulder) | rad |
| 9 | `right_arm_joint_2` | 旋转关节 | 右臂大臂旋转 (Upper Arm) | rad |
| 10 | `right_arm_joint_3` | 旋转关节 | 右臂肘部俯仰 (Elbow) | rad |
| 11 | `right_arm_joint_4` | 旋转关节 | 右臂前臂旋转 (Forearm) | rad |
| 12 | `right_arm_joint_5` | 旋转关节 | 右臂腕部俯仰 (Wrist Pitch) | rad |
| 13 | `right_arm_joint_6` | 旋转关节 | 右臂腕部旋转 (Wrist Roll) | rad |
| 14 | `left_gripper` | 夹爪 | 左夹爪开口度 | 0-100 (%) |
| 15 | `right_gripper` | 夹爪 | 右夹爪开口度 | 0-100 (%) |

### 1.2 关节运动范围

#### 左臂关节限位 (0-6)

| 关节 | 下限 (rad) | 上限 (rad) | 说明 |
|------|------------|------------|------|
| 0 | -3.1416 | 2.5994 | 根部旋转 |
| 1 | -0.2618 | 2.9671 | 大臂俯仰 |
| 2 | -3.6652 | 1.4835 | 大臂旋转 |
| 3 | -2.6180 | 0.5236 | 肘部俯仰 |
| 4 | -1.7453 | 1.3963 | 前臂旋转 |
| 5 | -0.7854 | 0.7854 | 腕部俯仰 |
| 6 | -1.5708 | 1.5708 | 腕部旋转 |

#### 右臂关节限位 (7-13)

| 关节 | 下限 (rad) | 上限 (rad) | 说明 |
|------|------------|------------|------|
| 7 | -3.1416 | 2.5994 | 根部旋转 |
| 8 | -0.2618 | 2.9671 | 大臂俯仰 |
| 9 | -3.6652 | 1.4835 | 大臂旋转 |
| 10 | -2.6180 | 0.5236 | 肘部俯仰 |
| 11 | -1.7453 | 1.3963 | 前臂旋转 |
| 12 | -0.7854 | 0.7854 | 腕部俯仰 |
| 13 | -1.5708 | 1.5708 | 腕部旋转 |

#### 夹爪 (14-15)

| 关节 | 下限 | 上限 | 说明 |
|------|------|------|------|
| 14 | 0 | 100 | 左夹爪开口度 (0=闭合, 100=张开) |
| 15 | 0 | 100 | 右夹爪开口度 (0=闭合, 100=张开) |

### 1.3 工作空间限制

#### 左臂工作空间 (m)
- X: [0.250, 0.732]
- Y: [-0.213, 0.900]
- Z: [-0.673, 0.500]

#### 右臂工作空间 (m)
- X: [0.250, 0.732]
- Y: [-0.900, 0.213]
- Z: [-0.673, 0.500]

---

## 2. 数据集标准

### 2.1 Observation Features (观测数据)

观测数据包含 **48 维关节状态** + **图像** + **触觉**（可选）：

```python
{
    # 关节状态 (48维 = 16关节 × 3)
    "joint_0_pos": float,    # 关节0位置 (rad)
    "joint_0_vel": float,    # 关节0速度 (rad/s)
    "joint_0_tau": float,    # 关节0力矩 (Nm)
    "joint_1_pos": float,
    "joint_1_vel": float,
    "joint_1_tau": float,
    ...
    "joint_15_pos": float,   # 关节15位置 (%, 夹爪)
    "joint_15_vel": float,   # 关节15速度
    "joint_15_tau": float,   # 关节15力矩
    
    # 图像 (可选，取决于相机配置)
    "cam_left": (H, W, 3),   # 左相机图像 (uint8)
    "cam_right": (H, W, 3),  # 右相机图像 (uint8)
    
    # 触觉传感器 (可选)
    "tac3d_sensor": (400, 6),  # Tac3D 触觉数据
}
```

### 2.2 Action Features (动作数据)

动作数据仅包含 **16 维关节目标位置**：

```python
{
    "action.joint_0_pos": float,   # 目标位置 (rad)
    "action.joint_1_pos": float,
    ...
    "action.joint_14_pos": float,  # 左夹爪目标 (0-100)
    "action.joint_15_pos": float,  # 右夹爪目标 (0-100)
}
```

**注意**:  
- 关节 0-13 的单位是 **弧度 (rad)**
- 关节 14-15 (夹爪) 的单位是 **百分比 (%)**

### 2.3 Dataset 存储结构

```
dataset/
├── data/
│   └── chunk-000/
│       └── file-000.parquet      # 主数据文件
├── meta/
│   ├── info.json                 # 元数据
│   ├── episodes/                 # episode 索引
│   └── stats.json                # 统计信息
└── videos/                       # 视频文件
    └── episode_N/
        ├── cam_left.mp4
        └── cam_right.mp4
```

### 2.4 Parquet 数据格式

| 列名 | 类型 | 形状 | 说明 |
|------|------|------|------|
| `observation.state` | float32 | (48,) | 所有关节的 pos+vel+tau |
| `action` | float32 | (16,) | 目标关节位置 |
| `observation.images.cam_left` | video | (H, W, 3) | 左相机视频 |
| `observation.images.cam_right` | video | (H, W, 3) | 右相机视频 |
| `observation.tac3d_sensor` | float32 | (400, 6) | 触觉数据 (可选) |
| `episode_index` | int64 | () | Episode 编号 |
| `frame_index` | int64 | () | 帧编号 |
| `timestamp` | float64 | () | 时间戳 |
| `task` | string | () | 任务描述 |

---

## 3. 数据映射关系

### 3.1 Observation.state 数组索引

```python
observation.state = [
    # 左臂 (关节 0-6)
    joint_0_pos, joint_0_vel, joint_0_tau,  # [0, 1, 2]
    joint_1_pos, joint_1_vel, joint_1_tau,  # [3, 4, 5]
    joint_2_pos, joint_2_vel, joint_2_tau,  # [6, 7, 8]
    joint_3_pos, joint_3_vel, joint_3_tau,  # [9, 10, 11]
    joint_4_pos, joint_4_vel, joint_4_tau,  # [12, 13, 14]
    joint_5_pos, joint_5_vel, joint_5_tau,  # [15, 16, 17]
    joint_6_pos, joint_6_vel, joint_6_tau,  # [18, 19, 20]
    
    # 右臂 (关节 7-13)
    joint_7_pos, joint_7_vel, joint_7_tau,   # [21, 22, 23]
    joint_8_pos, joint_8_vel, joint_8_tau,   # [24, 25, 26]
    joint_9_pos, joint_9_vel, joint_9_tau,   # [27, 28, 29]
    joint_10_pos, joint_10_vel, joint_10_tau, # [30, 31, 32]
    joint_11_pos, joint_11_vel, joint_11_tau, # [33, 34, 35]
    joint_12_pos, joint_12_vel, joint_12_tau, # [36, 37, 38]
    joint_13_pos, joint_13_vel, joint_13_tau, # [39, 40, 41]
    
    # 夹爪 (关节 14-15)
    joint_14_pos, joint_14_vel, joint_14_tau, # [42, 43, 44]
    joint_15_pos, joint_15_vel, joint_15_tau, # [45, 46, 47]
]
```

### 3.2 Action 数组索引

```python
action = [
    # 左臂
    joint_0_target,   # [0]
    joint_1_target,   # [1]
    joint_2_target,   # [2]
    joint_3_target,   # [3]
    joint_4_target,   # [4]
    joint_5_target,   # [5]
    joint_6_target,   # [6]
    
    # 右臂
    joint_7_target,   # [7]
    joint_8_target,   # [8]
    joint_9_target,   # [9]
    joint_10_target,  # [10]
    joint_11_target,  # [11]
    joint_12_target,  # [12]
    joint_13_target,  # [13]
    
    # 夹爪
    left_gripper_target,   # [14]  0-100
    right_gripper_target,  # [15]  0-100
]
```

---

## 4. 通信接口

### 4.1 WebSocket API

- **地址**: `ws://{robot_ip}:5000`
- **协议**: WebSocket + JSON

### 4.2 控制指令

#### ServoJ - 实时关节控制 (关节 0-13)
```json
{
  "title": "request_servoj",
  "data": {
    "q": [q0, q1, ..., q13],      // 14个关节位置 (rad)
    "v": [0, 0, ..., 0],           // 速度
    "kp": [150, ..., 150],         // 位置增益
    "kd": [10, ..., 10],           // 速度增益
    "tau": [0, ..., 0],            // 力矩
    "mode": [0, ..., 0],           // 模式
    "na": 0
  }
}
```

#### 夹爪控制 (关节 14-15)
```json
{
  "title": "request_set_limx_2fclaw_cmd",
  "data": {
    "left_opening": 0-100,    // 左夹爪 0=闭合, 100=张开
    "left_speed": 0-100,
    "left_force": 0-100,
    "right_opening": 0-100,   // 右夹爪
    "right_speed": 0-100,
    "right_force": 0-100
  }
}
```

---

## 5. 训练策略时的注意事项

### 5.1 Observation 输入

- 策略模型输入为 **48 维 observation.state**
- 包含 pos + vel + tau，频率 30Hz
- 需要与训练时的数据分布一致

### 5.2 Action 输出

- 策略模型输出为 **16 维 action**
- 仅包含目标位置 (pos)
- 频率 30Hz

### 5.3 夹爪特殊处理

- 夹爪 (14, 15) 虽然单位是 %，但在训练时会被归一化
- 推理输出也是归一化后的值，需要反归一化到 0-100

---

## 6. 与标准 LeRobot 机器人的差异

| 特性 | Tron2 | 标准机器人 (如 Koch) |
|------|-------|---------------------|
| 关节数 | 16 | 6 |
| Observation 维度 | 48 | 6 |
| 包含 vel/tau | 是 | 否 |
| 双臂 | 是 | 否 |
| 夹爪 | 2个 | 1个或无 |

---

## 7. 快速参考

### 关节索引速查表

```
索引:  0  1  2  3  4  5  6 | 7  8  9  10 11 12 13 | 14 15
       -------------------|----------------------|------
       左 臂  (7 joints)  | 右 臂  (7 joints)   | 夹爪
```

### 数据形状速查表

| 数据 | 形状 | 说明 |
|------|------|------|
| observation.state | (48,) | 16×3 (pos, vel, tau) |
| action | (16,) | 16 关节位置 |
| 左图像 | (480, 640, 3) | RGB uint8 |
| 右图像 | (480, 640, 3) | RGB uint8 |
| 触觉 | (400, 6) | [dx, dy, dz, Fx, Fy, Fz] |

---

**最后更新**: 2026-03-15
