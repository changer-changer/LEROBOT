# Tron2 + LeRobot 项目进展记录 (AI 记忆)

> **创建时间**: 2026-03-15  
> **项目**: LeRobot + Tron2 机器人 + Tac3D 触觉传感器集成  
> **基础版本**: LeRobot 0.5.1  
> **状态**: 功能完整，文档完善

---

## 1. 项目概述

### 1.1 项目目标

将 DACH_TRON2A 双臂机器人集成到 HuggingFace LeRobot 框架，实现：
- 机器人控制 (WebSocket)
- 双目视觉 (ROS2)
- 触觉感知 (Tac3D)
- 数据集录制与训练

### 1.2 核心技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 机器人通信 | WebSocket + JSON | - |
| 视觉系统 | ROS2 Humble | rclpy |
| 触觉传感器 | Tac3D-SDK | PyTac3D |
| 机器人 SDK | limxsdk-lowlevel | - |
| 录制控制 | pynput | - |

---

## 2. 新增模块清单

### 2.1 新建文件列表

#### 机器人模块
```
src/lerobot/robots/tron2/
├── __init__.py              # 模块初始化
├── tron2_config.py          # 配置类 (Tron2RobotConfig)
└── tron2_robot.py           # 机器人主类 (Tron2Robot)
```

#### 触觉传感器模块
```
src/lerobot/tactile/
├── __init__.py              # 模块导出
├── configs.py               # 触觉传感器配置基类
├── dataset_integration.py   # 数据集集成工具
├── simulated_sensor.py      # 模拟传感器
├── tactile_sensor.py        # 传感器抽象基类
├── TACTILE_CONTRIBUTION.md  # 贡献文档
├── utils.py                 # 工具函数
├── direct_connection/
│   ├── PyTac3D/             # Tac3D SDK
│   └── tac3d_sensor.py      # Tac3D 传感器实现
└── ros2_bridge/
    └── pointcloud2_sensor.py # ROS2 PointCloud2 传感器
```

#### 相机模块
```
src/lerobot/cameras/ros2/
├── configs.py               # ROS2CameraConfig
└── ros2_camera.py           # ROS2 相机实现
```

#### 录制脚本
```
src/lerobot/scripts/
└── lerobot_record_manual_fixed.py  # 手动录制脚本
```

### 2.2 修改的文件列表

| 文件 | 修改内容 |
|------|---------|
| `src/lerobot/utils/robot_utils.py` | 添加 `busy_wait()` 函数作为 `precise_sleep` 的别名 |
| `src/lerobot/utils/visualization_utils.py` | 添加 `import logging` 修复 NameError |
| `src/lerobot/datasets/utils.py` | 修复非3D元组特征的验证问题 |
| `src/lerobot/__init__.py` | 添加 tactile 模块导出 |
| `tests/test_full_system.py` | 添加系统测试 |

---

## 3. 技术实现细节

### 3.1 Tron2 机器人 (tron2_robot.py)

#### 类定义
```python
class Tron2Robot(Robot):
    config_class = Tron2RobotConfig
    name = "tron2"
```

#### 核心功能

**状态缓冲**
```python
self._q = np.zeros(16, dtype=np.float32)     # 位置
self._dq = np.zeros(16, dtype=np.float32)    # 速度
self._tau = np.zeros(16, dtype=np.float32)   # 力矩
```

**Observation Features (48维)**
```python
for i in range(16):
    features[f"joint_{i}_pos"] = float  # 位置
    features[f"joint_{i}_vel"] = float  # 速度
    features[f"joint_{i}_tau"] = float  # 力矩
```

**Action Features (16维)**
```python
for i in range(16):
    features[f"action.joint_{i}_pos"] = float  # 仅位置
```

#### 通信协议

**WebSocket 连接**
- 地址: `ws://{robot_ip}:5000`
- 协议: JSON over WebSocket
- 心跳: 50Hz 状态查询

**控制命令**
```python
# 臂部控制 (关节 0-13)
request_servoj:
    q: [q0, ..., q13]      # 目标角度
    v: [0]*14              # 目标速度
    kp: [150]*14           # 位置增益
    kd: [10]*14            # 速度增益
    tau: [0]*14            # 目标力矩
    mode: [0]*14           # 控制模式

# 夹爪控制 (关节 14-15)
request_set_limx_2fclaw_cmd:
    left_opening: 0-100
    right_opening: 0-100
```

**状态查询**
```python
request_get_joint_state        # 获取关节 0-13 状态
request_get_limx_2fclaw_state  # 获取夹爪 14-15 状态
```

### 3.2 ROS2 相机 (ros2_camera.py)

#### 核心特性

**零拷贝转换**
```python
# 直接从 ROS2 Image 消息转换为 NumPy，无需 cv_bridge
frame = np.frombuffer(msg.data, dtype=dtype)
frame = frame.reshape((msg.height, msg.width, channels))
```

**支持格式**
- rgb8 / bgr8 → (H, W, 3)
- mono8 → (H, W)
- 16UC1 → (H, W), uint16

**可选缩放**
```python
if target_size:
    frame = cv2.resize(
        frame, target_size,
        interpolation=cv2.INTER_AREA  # 适合下采样
    )
```

**颜色空间转换**
```python
if self.config.is_bgr:
    frame = frame[..., ::-1]  # BGR → RGB
```

#### 线程模型
```
Main Thread
    └── ROS2Camera.connect()
        └── MultiThreadedExecutor.spin() [New Thread]
            └── ROS2CameraNode
                └── subscription.callback (image_callback)
```

### 3.3 Tac3D 触觉传感器 (tac3d_sensor.py)

#### 数据格式

**原始数据**
```python
frame = {
    "3D_Displacements": (400, 3),  # [dx, dy, dz] in mm
    "3D_Forces": (400, 3),          # [Fx, Fy, Fz] in N
    "SN": "TAC3D001",               # 序列号
    "...": "..."
}
```

**处理后数据**
```python
# TactileDataType.FULL
output.shape = (400, 6)  # [dx, dy, dz, Fx, Fy, Fz]

# TactileDataType.DISPLACEMENT
output.shape = (400, 3)  # [dx, dy, dz]

# TactileDataType.FORCE
output.shape = (400, 3)  # [Fx, Fy, Fz]
```

#### 通信协议

**UDP 接收**
- 端口: 9988 (可配置)
- 频率: 30Hz
- 数据来源: Tac3D-Desktop 软件

**回调机制**
```python
def _on_frame_received(self, frame: dict, callback_param: Any):
    processed = self._process_frame(frame)
    # 存入队列和最新帧缓冲
```

#### 校准 (Tare)
```python
sensor.tare()  # 发送校准命令到 Tac3D-Desktop
# 零接触时读数归零
```

### 3.4 手动录制脚本 (lerobot_record_manual_fixed.py)

#### 键盘控制映射

| 按键 | 功能 |
|------|------|
| `S` | 开始录制当前 episode |
| `Space` | 停止并保存 episode |
| `Backspace` / `L` | 停止并丢弃 episode |
| `ESC` | 退出程序 |

#### 配置类

```python
@dataclass
class DatasetRecordConfig:
    repo_id: str                    # 数据集ID
    single_task: str               # 任务描述
    fps: int = 30                  # 采样频率
    episode_time_s: int = 60       # 单 episode 时长限制
    vcodec: str = "libsvtav1"      # 视频编码器
    streaming_encoding: bool = False  # 必须为 False！
```

#### 数据流
```
键盘事件 → record_loop()
    ├── robot.get_observation() → observation
    ├── teleop.get_action() / predict_action() → action
    ├── dataset.add_frame(observation + action)
    └── robot.send_action(action)
```

---

## 4. 数据集规范

### 4.1 数据格式

#### Observation State (48维 float32)
```
[0:3]   = joint_0 [pos, vel, tau]
[3:6]   = joint_1 [pos, vel, tau]
...
[42:45] = joint_14 [pos, vel, tau]  # 左夹爪
[45:48] = joint_15 [pos, vel, tau]  # 右夹爪
```

#### Action (16维 float32)
```
[0:7]   = left_arm [q0, ..., q6]
[7:14]  = right_arm [q7, ..., q13]
[14]    = left_gripper
[15]    = right_gripper
```

#### 图像数据
```python
# 存储为视频文件
videos/episode_N/cam_left.mp4   # (480, 640, 3), 30fps
videos/episode_N/cam_right.mp4  # (480, 640, 3), 30fps
```

#### 触觉数据 (400, 6) float32
```python
[:, 0:3]  # 3D 形变 [dx, dy, dz] in mm
[:, 3:6]  # 3D 力 [Fx, Fy, Fz] in N
```

### 4.2 存储结构

```
dataset/
├── data/
│   └── chunk-000/
│       └── file-000.parquet      # 主数据 (state, action, tactile)
├── meta/
│   ├── info.json                 # 元数据
│   ├── stats.json                # 统计信息
│   └── episodes/                 # episode 索引
│       └── chunk-000/
│           └── file-000.parquet
└── videos/                       # 视频文件
    └── episode_N/
        ├── cam_left.mp4
        └── cam_right.mp4
```

### 4.3 Parquet Schema

| 列名 | 类型 | 形状 |
|------|------|------|
| observation.state | float32 | (48,) |
| action | float32 | (16,) |
| observation.images.cam_left | string | () # 视频路径 |
| observation.images.cam_right | string | () # 视频路径 |
| observation.tac3d_sensor | float32 | (400, 6) |
| episode_index | int64 | () |
| frame_index | int64 | () |
| timestamp | float64 | () |
| task | string | () |

---

## 5. Bug 修复记录

### 5.1 robot_utils.py - busy_wait 函数

**问题**: `ImportError: cannot import name 'busy_wait' from 'lerobot.utils.robot_utils'`

**修复**:
```python
def busy_wait(seconds):
    """Compatible alias for precise_sleep."""
    precise_sleep(seconds)
```

### 5.2 visualization_utils.py - logging 导入

**问题**: `NameError: name 'logging' is not defined`

**修复**:
```python
import logging  # 添加导入
```

### 5.3 datasets/utils.py - 非3D特征验证

**问题**: 触觉数据 (400, 6) 被错误识别为图像特征

**修复**: 修改 `validate_feature_numpy_array` 支持非3D元组特征

### 5.4 Python 3.10 兼容性

**问题**: `type[X]` 语法在 Python 3.10 不支持

**修复**: 添加 `from __future__ import annotations`

---

## 6. 关键技术决策

### 6.1 Observation 48 维设计

**决策**: Tron2 同时返回 pos/vel/tau，共 48 维

**原因**:
- WebSocket API 天然提供完整状态
- 策略网络可以利用速度/力矩信息
- 与其他机器人 (如 Koch 6 维) 区分

**影响**:
- 预训练模型需要适配或重新训练
- 数据集格式与标准 LeRobot 不同

### 6.2 触觉数据 (400, 6) 格式

**决策**: 将形变和力拼接为 6 维数组

**原因**:
- 保持空间结构 (400 点)
- 便于 CNN 处理
- 与 LeRobot 特征系统兼容

**替代方案**: 分离存储 (未采用)
- observation.tactile_displacement: (400, 3)
- observation.tactile_force: (400, 3)

### 6.3 ROS2 相机零拷贝

**决策**: 使用 `np.frombuffer` 直接转换，不使用 cv_bridge

**原因**:
- 避免 cv_bridge 依赖问题
- 性能更好 (零拷贝)
- 代码更简洁

### 6.4 视频编码配置

**决策**: 默认 `streaming_encoding=false`, `vcodec=libsvtav1`

**原因**:
- streaming_encoding=true 会导致视频模糊
- libsvtav1 质量/压缩比优秀
- 后期编码比实时编码更稳定

---

## 7. 已知问题与限制

### 7.1 Tac3D 数据质量

**问题**: 力和形变符号不匹配

**数据**: ~40% 的数据点力和形变同号 (物理上应相反)

**建议**: 训练时优先使用形变数据 (前 3 维)

### 7.2 夹爪状态反馈

**问题**: 夹爪 vel/tau 为估算值

**原因**: SDK 只返回开口度，速度/力矩是差分计算

### 7.3 相机分辨率

**默认**: 640×480

**注意**: 强制 resize 到 128×128 会导致画面变形

**建议**: 保持原始分辨率或等比例缩放

---

## 8. 测试与验证

### 8.1 系统测试

```bash
python tests/test_full_system.py
```

### 8.2 数据集验证

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset("path/to/dataset")
assert dataset.num_episodes > 0
assert "observation.state" in dataset.features
assert dataset.features["observation.state"].shape == (48,)
```

---

## 9. 后续优化方向

1. **策略适配**: 创建 48 维 → 低维的投影层，适配预训练模型
2. **触觉预处理**: 添加触觉数据滤波/归一化
3. **相机同步**: 实现多相机硬件同步
4. **数据压缩**: 探索更高效的视频/触觉压缩

---

## 10. 关键更新记录

### 2026-03-15: MoveJ 控制方式

**背景**: 使用 ServoJ 回放数据集时机器人出现剧烈振荡。

**问题分析**:
- ServoJ 是实时伺服控制，需要高频平滑输入
- 数据集相邻帧目标位置变化大时，机器人剧烈加速追赶
- 导致振荡，可能损坏机器人

**解决方案**: 添加 MoveJ（关节空间插值）控制方式

**实现**:
1. `tron2_robot.py` 添加 `send_action_movej()` 方法
2. `lerobot_replay_tron2.py` 默认使用 MoveJ
3. MoveJ 发送目标位置 + 运动时间，机器人自动规划平滑轨迹

**使用**:
```python
# 默认使用 MoveJ（安全，不会振荡）
--use_movej=true --movej_time=0.1

# 回到 ServoJ（实时性高，但需确保数据平滑）
--use_movej=false
```

**效果**: MoveJ 自动插值保证平滑，完全消除振荡问题。

---

**文档版本**: 1.1  
**最后更新**: 2026-03-15
