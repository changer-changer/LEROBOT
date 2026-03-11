# Tron2遥操作与触觉数据采集方案

**分析日期**: 2026-03-11  
**目标**: 在Tron2遥操作系统中集成触觉数据采集

---

## 📋 Tron2现有系统分析

### 1. Tron2架构概述

```
Tron2遥操作系统 (基于LimX SDK)
├── limxsdk.robot.Robot          # 底层SDK接口
├── Tron2Robot (LeRobot封装)     # 我们的封装层
│   ├── 16-DOF关节控制
│   ├── RGB相机支持
│   └── 异步状态读取
└── 数据采集                     # 通过LeRobot Dataset
```

### 2. 现有数据流

```python
# 当前观测数据 (Tron2Robot.get_observation)
obs = {
    # 16个关节状态
    "joint_0_pos": float, ..., "joint_15_pos": float,
    "joint_0_vel": float, ..., "joint_15_vel": float,
    "joint_0_tau": float, ..., "joint_15_tau": float,
    
    # RGB相机
    "wrist_camera": (H, W, 3),  # 或 "camera_name"
}

# 动作输出
action = {
    "action.joint_0_pos": float, ..., "action.joint_15_pos": float,
}
```

### 3. 数据采集方式

**当前流程**:
1. LimX SDK 通过UDP与机器人通信
2. `subscribeRobotState()` 异步接收状态
3. LeRobot相机独立采集图像
4. `record_data.py` 同步记录到LeRobot Dataset格式

**问题**: Tron2的遥操作软件是**封闭系统**，数据只能通过SDK获取

---

## 🎯 触觉数据集成方案

### 方案对比

| 方案 | 复杂度 | 数据质量 | 实时性 | 推荐度 |
|-----|-------|---------|-------|-------|
| A. Tac3D直接集成 | 中 | ⭐⭐⭐ | ⭐⭐⭐ | ✅ **首选** |
| B. RGB触觉图像 | 低 | ⭐⭐ | ⭐⭐ | 备选 |
| C. 外部录制再对齐 | 高 | ⭐⭐ | ⭐ | 不推荐 |

---

## ✅ 方案A: Tac3D直接集成 (推荐)

### 架构设计

```
Tron2WithTactileRobot (LeRobot)
├── Tron2Robot (原有)
│   ├── LimX SDK (16-DOF关节)
│   └── RGB相机
│
└── Tac3DTactileSensor (新增)
    ├── Tac3D-SDK (UDP接收)
    ├── 400点 6D数据
    └── 30Hz独立线程
```

### 数据流

```python
# 整合后的观测数据
obs = {
    # Tron2原有数据
    "joint_0_pos"..."joint_15_pos": float,
    "joint_0_vel"..."joint_15_vel": float,
    "joint_0_tau"..."joint_15_tau": float,
    "wrist_camera": (H, W, 3),
    
    # 新增触觉数据 ⭐
    "tactile": (400, 6),  # [dx, dy, dz, Fx, Fy, Fz]
}
```

### 实施步骤

#### 步骤1: 硬件连接确认

**Tac3D配置**:
- Tac3D传感器通过USB连接到采集PC
- Tac3D-Desktop软件运行 (必需!)
- 配置UDP端口 (默认9988)
- 确认传感器SN号

**检查清单**:
```bash
# 1. 检查Tac3D-Desktop是否运行
# 2. 确认UDP端口开放
netstat -an | grep 9988

# 3. 测试数据接收
python -c "from lerobot.tactile import Tac3DTactileSensor; print('OK')"
```

#### 步骤2: 使用已集成的代码

我们已经在 `feature/integration` 分支完成了集成：

```python
# lerobot/lerobot/robots/tron2_with_tactile.py
from lerobot.robots.tron2_with_tactile import (
    Tron2WithTactileConfig,
    Tron2WithTactileRobot,
)

# 配置
config = Tron2WithTactileConfig(
    robot_ip="10.192.1.2",          # Tron2 IP
    use_tactile=True,                # 启用触觉
    tactile_config={
        "udp_port": 9988,            # Tac3D UDP端口
        "sensor_sn": None,           # 传感器SN (可选)
        "data_type": "full",         # "displacement" | "force" | "full"
    },
    cameras={
        "wrist_camera": {
            "type": "opencv",
            "width": 640,
            "height": 480,
            "fps": 30,
        }
    },
)

# 创建机器人
robot = Tron2WithTactileRobot(config)

# 连接
robot.connect()  # 会自动连接Tac3D并执行tare

# 数据采集
obs = robot.get_observation()
print(obs["tactile"].shape)  # (400, 6)

# 断开
robot.disconnect()
```

#### 步骤3: 数据采集脚本

```python
#!/usr/bin/env python
"""Tron2 + Tac3D数据采集脚本"""

import time
from pathlib import Path
from lerobot.datasets import Dataset
from lerobot.robots.tron2_with_tactile import Tron2WithTactileConfig, Tron2WithTactileRobot

# 配置
config = Tron2WithTactileConfig(
    robot_ip="10.192.1.2",
    use_tactile=True,
)

# 创建数据集
dataset = Dataset.create(
    repo_id="your_name/tron2_tactile_task",
    robot_type="tron2_with_tactile",
    features=Tron2WithTactileRobot().observation_features,
)

# 连接机器人
robot = Tron2WithTactileRobot(config)
robot.connect()

print("开始数据采集... 按Ctrl+C停止")

episode = []
try:
    while True:
        # 获取观测
        obs = robot.get_observation()
        
        # 记录数据
        episode.append(obs)
        
        # 显示状态
        if len(episode) % 30 == 0:  # 每秒显示一次
            print(f"已采集 {len(episode)} 帧 | "
                  f"Tactile shape: {obs['tactile'].shape}")
        
        time.sleep(1/30)  # 30Hz
        
except KeyboardInterrupt:
    print(f"\n采集完成，共 {len(episode)} 帧")
    
    # 保存到数据集
    dataset.add_episode(episode)
    dataset.save()
    
finally:
    robot.disconnect()
```

### 数据格式说明

| 字段 | 形状 | 说明 | 单位 |
|-----|------|-----|------|
| `tactile` | (400, 6) | 触觉点云 | - |
| `tactile[:, 0:3]` | (400, 3) | 位移 [dx, dy, dz] | mm |
| `tactile[:, 3:6]` | (400, 3) | 力 [Fx, Fy, Fz] | N |
| `tactile[i, :]` | (6,) | 第i个点的完整数据 | - |

**Tac3D空间布局**:
- 400点 = 20×20 网格
- 每个点对应传感器阵列中的一个像素位置
- 数据通过UDP从Tac3D-Desktop接收

---

## 📷 方案B: RGB触觉图像 (备选)

如果无法直接使用Tac3D-SDK，可以考虑**RGB触觉相机**：

### 硬件方案

**GelSight Mini** (或其他视觉触觉传感器):
- 直接输出RGB图像
- 通过标准相机接口接入
- LeRobot已有相机支持

### 集成方式

```python
config = Tron2RobotConfig(
    robot_ip="10.192.1.2",
    cameras={
        "wrist_camera": {...},           # 原有手腕相机
        "tactile_left": {                # 新增触觉相机
            "type": "opencv",
            "width": 240,
            "height": 320,
            "fps": 30,
        },
        "tactile_right": {...},          # 可选: 双手
    },
)
```

**优点**: 简单，无需额外SDK  
**缺点**: 失去6D物理信息，只有2D形变图像

---

## ⚙️ 实施检查清单

### 硬件准备

- [ ] Tron2机器人开机并连接网络
- [ ] Tac3D传感器连接到采集PC
- [ ] Tac3D-Desktop软件安装并运行
- [ ] RGB相机连接并测试
- [ ] 确认所有设备IP可达

### 软件准备

- [ ] 切换到 `feature/integration` 分支
- [ ] 安装Tac3D-SDK (`pip install PyTac3D` 或按官方说明)
- [ ] 测试Tac3D数据接收
- [ ] 测试Tron2连接
- [ ] 运行整合测试脚本

### 验证测试

```bash
cd /home/cuizhixing/.openclaw/workspace-scientist/lerobot

# 1. 切换分支
git checkout feature/integration

# 2. 测试数据流 (mock模式)
python test_tron2_tactile_integration.py --mock

# 3. 真机测试 (需要连接硬件)
python test_tron2_tactile_integration.py --robot-ip 10.192.1.2
```

---

## 🔧 常见问题

### Q1: Tac3D-Desktop必须运行吗？
**A**: 是的！Tac3D-SDK通过UDP与Tac3D-Desktop通信，不启动桌面软件无法获取数据。

### Q2: 数据频率不匹配怎么办？
**A**: 
- Tron2关节状态: ~100Hz (LimX SDK)
- Tac3D触觉: 30Hz (固定)
- RGB相机: 30Hz (可配置)

我们已经处理了频率对齐，以最低频率(30Hz)为基准。

### Q3: 如何可视化触觉数据？
**A**: 
```python
# 将400点reshape为20x20可视化
tactile_image = obs["tactile"][:, :3].reshape(20, 20, 3)  # 位移作为RGB
```

### Q4: 遥操作时如何实时看到触觉？
**A**: 需要运行Tac3D-Desktop的实时可视化，或在采集脚本中添加可视化代码。

---

## 📚 相关代码位置

```
lerobot/
├── lerobot/robots/tron2/              # Tron2基础支持
│   ├── tron2_robot.py
│   └── tron2_config.py
│
├── lerobot/robots/tron2_with_tactile.py  # ⭐ 整合支持
│
├── lerobot/tactile/                   # Tac3D支持
│   ├── configs.py
│   ├── tactile_sensor.py
│   └── direct_connection/tac3d_sensor.py
│
└── test_tron2_tactile_integration.py  # ⭐ 测试脚本
```

---

## 🎯 推荐实施路径

### Phase 1: 硬件验证 (今天)
1. 确认Tac3D-Desktop能正常接收数据
2. 测试Tron2连接
3. 运行 `test_tron2_tactile_integration.py --mock`

### Phase 2: 真机测试 (明天)
1. 连接所有硬件
2. 运行 `test_tron2_tactile_integration.py --robot-ip 10.192.1.2`
3. 验证数据格式正确

### Phase 3: 数据采集 (本周)
1. 录制第一条演示轨迹
2. 验证数据集格式
3. 开始训练策略

---

**建议**: 直接使用 **方案A (Tac3D直接集成)**，代码已经完成，只需验证硬件连接！

