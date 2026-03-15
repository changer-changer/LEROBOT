# 项目代码库完整指南

> 本文档详细记录了项目的代码结构、新旧代码区分、关键数据结构和设计决策。
> 
> **项目**: LeRobot + Tron2 + Tac3D 集成  
> **版本**: v3.0 (基于 LeRobot 0.5.1)  
> **更新日期**: 2026-03-15

---

## 一、代码库概览

### 1.1 目录结构

```
lerobot_integrated/
├── src/lerobot/
│   ├── cameras/           # 相机模块
│   ├── robots/            # 机器人模块
│   ├── tactile/           # 【新建】触觉传感器模块
│   ├── datasets/          # 数据集管理
│   ├── policies/          # 策略模型
│   ├── processor/         # 数据处理器
│   ├── scripts/           # 命令行脚本
│   ├── utils/             # 工具函数
│   └── ...
├── docs/                  # 【新建】项目文档
├── .aidoc/                # 【新建】AI记忆系统
└── tests/                 # 测试代码
```

### 1.2 代码分类

| 类别 | 说明 | 文件数 |
|------|------|--------|
| 原有代码 | LeRobot 0.5.1 原始代码 | ~300 |
| 新增代码 | 本项目新增/修改 | ~20 |
| 第三方SDK | Tac3D SDK 等 | ~5 |

---

## 二、新增代码详解

### 2.1 ROS2 相机模块

**文件列表**:
- `src/lerobot/cameras/ros2/configs.py` ⭐
- `src/lerobot/cameras/ros2/ros2_camera.py` ⭐

#### ROS2CameraConfig

```python
@CameraConfig.register_subclass("ros2")
@dataclass(kw_only=True)
class ROS2CameraConfig(CameraConfig):
    """ROS2相机配置"""
    type: str = "ros2"
    topic: str                           # ROS2 Image话题名称
    width: int | None = None             # 目标宽度(可选)
    height: int | None = None            # 目标高度(可选)
    is_bgr: bool = True                  # 是否为BGR格式
    fps: int = 30                        # 帧率
```

#### ROS2Camera

```python
class ROS2Camera(Camera):
    """ROS2相机实现
    
    数据流:
    ROS2 Topic (sensor_msgs/Image) 
        → ROS2CameraNode (rclpy订阅)
        → image_callback (NumPy转换)
        → cv2.resize (可选缩放)
        → latest_frame
        → read()/async_read()
    """
    
    # 核心属性
    config: ROS2CameraConfig
    _node: ROS2CameraNode
    _executor: MultiThreadedExecutor
    _thread: threading.Thread
```

**关键设计**:
- 使用 `rclpy` 订阅 ROS2 Image 话题
- 零拷贝 NumPy 转换 (`np.frombuffer`)
- 支持 `cv2.resize` 动态缩放
- 显式引用管理防止内存泄漏

---

### 2.2 触觉传感器模块 ⭐⭐⭐

**文件列表**:
- `src/lerobot/tactile/__init__.py` ⭐
- `src/lerobot/tactile/configs.py` ⭐
- `src/lerobot/tactile/tactile_sensor.py` ⭐
- `src/lerobot/tactile/direct_connection/tac3d_sensor.py` ⭐
- `src/lerobot/tactile/simulated_sensor.py`
- `src/lerobot/tactile/utils.py`

#### 数据类型定义

```python
class TactileDataType(str, Enum):
    """触觉数据类型"""
    DISPLACEMENT = "displacement"     # 仅形变 (400, 3)
    FORCE = "force"                    # 仅受力 (400, 3)
    FULL = "full"                      # 完整数据 (400, 6)

class PointCloudFormat(str, Enum):
    """点云格式"""
    XYZ = "xyz"                              # 仅位置
    XYZ_DISPLACEMENT = "xyz_displacement"    # 位置+形变
    XYZ_DISPLACEMENT_FORCE = "xyz_displacement_force"  # 完整6维
```

#### TactileSensorConfig (基类)

```python
@dataclass
class TactileSensorConfig:
    """触觉传感器配置基类"""
    type: str
    fps: int = 30
    num_points: int = 400                # 点数(默认400=Tac3D 20x20)
    data_type: TactileDataType = TactileDataType.FULL
    pointcloud_format: PointCloudFormat = PointCloudFormat.XYZ_DISPLACEMENT_FORCE
    
    # 数据归一化
    normalization_range: tuple = (-1.0, 1.0)
    displacement_range: tuple = (-2.0, 3.0)   # mm
    force_range: tuple = (-0.8, 0.8)           # N
    
    # 校准设置
    apply_tare: bool = True
    tare_samples: int = 10
    tare_on_startup: bool = True
```

#### Tac3DSensorConfig

```python
@TactileSensorConfig.register_subclass("tac3d")
@dataclass(kw_only=True)
class Tac3DSensorConfig(TactileSensorConfig):
    """Tac3D传感器配置"""
    type: str = "tac3d"
    udp_port: int = 9988                 # UDP接收端口
    sensor_sn: str | None = None         # 传感器序列号
    timeout_ms: float = 1000.0           # 读取超时
```

#### Tac3DTactileSensor

```python
class Tac3DTactileSensor(TactileSensor):
    """Tac3D触觉传感器实现
    
    数据流:
    Tac3D-Desktop (UDP)
        → PyTac3D.Sensor
        → _on_frame_received (回调)
        → _process_frame (数据拼接)
        → _apply_tare (校准)
        → _frame_queue
        → read()/async_read()
    
    数据格式 (shape: (400, 6)):
        - [:, 0:3]: 3D_Displacements (mm) [dx, dy, dz]
        - [:, 3:6]: 3D_Forces (N) [Fx, Fy, Fz]
    """
    
    # 核心方法
    def connect(self, warmup: bool = True) -> None
    def disconnect(self) -> None
    def read(self) -> NDArray[np.float64]       # 阻塞读取
    def async_read(self, timeout_ms: float) -> NDArray[np.float64]
    def tare(self) -> None                       # 校准
    
    # 数据处理
    def _process_frame(self, frame: dict) -> NDArray[np.float64]:
        """将Tac3D数据拼接为(400, 6)数组"""
        displacements = frame["3D_Displacements"]  # (400, 3)
        forces = frame["3D_Forces"]                 # (400, 3)
        return np.concatenate([displacements, forces], axis=1)
```

---

### 2.3 Tron2 机器人模块 ⭐⭐⭐

**文件列表**:
- `src/lerobot/robots/tron2/__init__.py` ⭐
- `src/lerobot/robots/tron2/tron2_config.py` ⭐
- `src/lerobot/robots/tron2/tron2_robot.py` ⭐

#### Tron2RobotConfig

```python
@RobotConfig.register_subclass("tron2")
@dataclass(kw_only=True)
class Tron2RobotConfig(RobotConfig):
    """Tron2机器人配置
    
    机械结构:
    - 16个电机(左右臂各7个+双爪)
    - 左右RGB相机
    - 触觉传感器(可选)
    """
    type: str = "tron2"
    robot_ip: str = "10.192.1.2"         # 机器人IP
    
    # 关节配置
    init_joint_positions: list[float] = field(
        default_factory=lambda: [0.0] * 16
    )
    
    # 相机配置
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    
    # 触觉传感器配置
    tactile_sensors: dict[str, TactileSensorConfig] = field(default_factory=dict)
    
    # 安全限制
    max_relative_target: float | None = None
```

#### Tron2Robot

```python
class Tron2Robot(Robot):
    """Tron2机器人实现
    
    通信协议:
    - WebSocket (ws://robot_ip:5000)
    - JSON消息格式
    
    数据流:
    1. 连接: WebSocket握手
    2. 状态订阅: subscribeRobotState → q, dq, tau
    3. 命令发送: publishRobotCmd ← action
    4. 相机/触觉: 独立模块管理
    """
    
    # 核心属性
    config: Tron2RobotConfig
    _q: np.ndarray          # 关节位置 (16,)
    _dq: np.ndarray         # 关节速度 (16,)
    _tau: np.ndarray        # 关节力矩 (16,)
    
    # 子系统
    cameras: dict[str, Camera]
    tactile_sensors: dict[str, TactileSensor]
    
    # 动作特征 (16维关节位置)
    action_features: dict = {
        "action": {
            "dtype": "float32",
            "shape": (16,),
            "names": ["joint_0_pos", ..., "joint_15_pos"]
        }
    }
    
    # 观测特征 (48维 = 16关节 × 3)
    # ⚠️ 注意: 这是Tron2独有的设计！其他机器人通常只有位置信息
    observation_features: dict = {
        "observation.state": {
            "dtype": "float32",
            "shape": (48,),
            "names": ["joint_0_pos", "joint_0_vel", "joint_0_tau", ...]
        }
    }
```

**⚠️ 重要设计差异**: Tron2 的 `observation.state` 包含 **pos + vel + tau**（48维），而大多数 LeRobot 机器人（如 Koch、SO100）只有 **pos**（例如6维）。这是由 Tron2 SDK 的 WebSocket API 特性决定的。

**WebSocket API**:
```json
// 状态订阅回调
{
    "stamp": 1234567890,        // 时间戳
    "q": [0.1, 0.2, ...],       // 16维位置
    "dq": [0.01, 0.02, ...],    // 16维速度
    "tau": [0.5, 0.6, ...]      // 16维力矩
}

// 命令发送
{
    "mode": [0, 0, ...],        // 控制模式
    "q": [0.1, 0.2, ...],       // 目标位置
    "dq": [0, 0, ...],          // 目标速度
    "tau": [0, 0, ...],         // 前馈力矩
    "Kp": [...],                // 位置增益
    "Kd": [...]                 // 速度增益
}
```

---

### 2.4 手动录制脚本

**文件列表**:
- `src/lerobot/scripts/lerobot_record_manual.py` ⭐
- `src/lerobot/scripts/lerobot_record_manual_fixed.py` ⭐⭐

#### 关键配置类

```python
@dataclass
class DatasetRecordConfig:
    """数据集录制配置"""
    repo_id: str
    single_task: str
    fps: int = 30
    episode_time_s: float = 60
    num_episodes: int = 50
    video: bool = True
    push_to_hub: bool = False
    
    # 视频编码配置
    vcodec: str = "libsvtav1"          # 编码器选择
    streaming_encoding: bool = False    # 实时编码开关
    encoder_queue_maxsize: int = 30
    encoder_threads: int | None = None

@dataclass
class ManualRecordConfig:
    """手动录制配置"""
    robot: RobotConfig
    dataset: DatasetRecordConfig
    teleop: TeleoperatorConfig | None = None
    policy: PreTrainedConfig | None = None
    display_data: bool = False
    play_sounds: bool = True
    resume: bool = False
```

#### 键盘事件映射

```python
events = {
    "exit_early": False,       # Space键: 停止录制
    "stop_recording": False,   # ESC键: 退出程序
    "start_episode": False,    # S键: 开始录制
    "discard_episode": False,  # Backspace/L键: 丢弃
}
```

---

## 三、修改的文件详解

### 3.1 兼容 Python 3.10

**修改文件**:
- `pyproject.toml`: Python版本 `>=3.12` → `>=3.10`
- `src/lerobot/__init__.py`: 添加 `typing.Unpack` 兼容
- `src/lerobot/utils/io_utils.py`: 修复泛型语法
- `src/lerobot/utils/robot_utils.py`: 添加 `busy_wait` 别名

### 3.2 数据集工具增强

**文件**: `src/lerobot/datasets/utils.py`

**修改内容**:
```python
# 修复: 支持非3D元组特征(如触觉数据)
def validate_feature_numpy_array(...):
    # 将 tuple shape 和 list shape 统一转换为 list 比较
    actual_shape = list(array.shape)
    expected_shape = list(shape)
```

### 3.3 可视化增强

**文件**: `src/lerobot/utils/visualization_utils.py`

**修改内容**:
```python
# 添加: 点云数据可视化支持
def log_rerun_data(...):
    # 使用 rr.Points3D 显示触觉点云
    if array.shape == (400, 6):
        rr.log(key, rr.Points3D(array[:, :3]))
```

---

## 四、关键数据结构

### 4.1 LeRobot Dataset v3.0 格式

```
dataset_root/
├── meta/
│   ├── info.json                   # 数据集信息
│   ├── stats.json                  # 统计信息
│   ├── tasks.parquet               # 任务定义
│   └── episodes/
│       └── chunk-000/
│           └── file-000.parquet    # Episode元数据
├── data/
│   └── chunk-000/
│       └── file-000.parquet        # 帧数据
└── videos/
    └── {video_key}/
        └── chunk-000/
            └── file-000.mp4        # 视频文件
```

### 4.2 info.json 结构

```json
{
    "codebase_version": "v3.0",
    "robot_type": "tron2",
    "total_episodes": 3,
    "total_frames": 795,
    "fps": 30,
    
    "features": {
        "action": {
            "dtype": "float32",
            "shape": [16],
            "names": ["joint_0_pos", ...]
        },
        "observation.state": {
            "dtype": "float32",
            "shape": [48],
            "names": ["joint_0_pos", "joint_0_vel", "joint_0_tau", ...]
        },
        "observation.images.left_rgb": {
            "dtype": "video",
            "shape": [480, 640, 3],
            "info": {"video.codec": "h264", "video.fps": 30}
        },
        "observation.tac3d_sensor": {
            "dtype": "float32",
            "shape": [400, 6]
        }
    }
}
```

### 4.3 Episode Buffer 结构

```python
{
    "size": 150,                              # 帧数
    "task": ["Pick up"] * 150,
    "frame_index": [0, 1, 2, ..., 149],
    "timestamp": [0.0, 0.033, 0.066, ...],
    "episode_index": 0,
    
    # 数据列
    "action": [np.array([...]), ...],         # (16,) x 150
    "observation.state": [np.array([...]), ...],  # (48,) x 150
    "observation.tac3d_sensor": [np.array([...]), ...],  # (400, 6) x 150
    "observation.images.left_rgb": ["path/to/frame_000.png", ...]
}
```

### 4.4 Tac3D 数据结构

```python
# 原始数据 (来自 PyTac3D)
frame = {
    "SN": "TAC3D001",
    "index": 123,
    "sendTimestamp": 1234567890.0,
    "recvTimestamp": 1234567890.1,
    "3D_Positions": np.array([...]),       # (400, 3) mm
    "3D_Normals": np.array([...]),         # (400, 3)
    "3D_Displacements": np.array([...]),   # (400, 3) mm
    "3D_Forces": np.array([...]),          # (400, 3) N
    "3D_ResultantForce": np.array([...]),  # (1, 3) N
    "3D_ResultantMoment": np.array([...])  # (1, 3) N·mm
}

# 处理后数据 (存储到 Dataset)
data = np.concatenate([
    frame["3D_Displacements"],   # [:, 0:3] mm
    frame["3D_Forces"]           # [:, 3:6] N
], axis=1)  # shape: (400, 6)
```

---

## 五、设计决策记录

### 5.1 为什么选择 WebSocket 而非 ROS2 控制 Tron2?

**决策**: Tron2 使用 WebSocket JSON API 而非 ROS2 Topic 进行控制。

**原因**:
1. Tron2 SDK 原生提供 WebSocket 接口
2. 控制命令需要可靠的请求-响应模式
3. 状态订阅通过回调机制更高效

### 5.2 为什么触觉数据存储 (400, 6) 而非分开存储?

**决策**: 将形变和力拼接为6维数组。

**原因**:
1. LeRobot Dataset 期望固定的 shape
2. 便于策略模型统一处理
3. 与 PointNet 编码器输入格式兼容

### 5.3 为什么 ROS2Camera 默认不 resize?

**决策**: 将默认 `width/height` 改为 `None`。

**原因**:
1. 避免强制正方形裁剪导致画面变形
2. 让用户决定是否需要缩放
3. 保持原始分辨率便于后期处理

---

## 六、新人入门指南

### 6.1 阅读顺序

1. **理解基础**: `docs/教学.md`
2. **了解结构**: 本文档
3. **深入代码**:
   - 相机: `ros2_camera.py`
   - 触觉: `tac3d_sensor.py`
   - 机器人: `tron2_robot.py`
   - 录制: `lerobot_record_manual_fixed.py`

### 6.2 调试技巧

```bash
# 检查数据集结构
python -c "from lerobot.datasets.lerobot_dataset import LeRobotDataset; ds = LeRobotDataset('path/to/dataset'); print(ds.meta.features)"

# 检查 Tac3D 数据
python -c "import pandas as pd; df = pd.read_parquet('data.parquet'); print(df['observation.tac3d_sensor'].iloc[0].shape)"

# 查看 ROS2 话题
ros2 topic list | grep camera
ros2 topic hz /camera/left/color/image_rect_raw
```

### 6.3 常见问题

| 问题 | 位置 | 解决方案 |
|------|------|----------|
| busy_wait 错误 | robot_utils.py | 已添加别名 |
| 点云全零 | tac3d_sensor.py | 检查传感器连接和 tare |
| 视频模糊 | 录制配置 | 禁用 streaming_encoding |
| 导入错误 | __init__.py | 检查 Python 版本 |

---

## 七、参考资源

- **师兄代码**: `/home/cuizhixing/WorkspaceBase/lerobot/src/lerobot/scripts/lerobot_record_vr.py`
- **Tac3D SDK**: `/media/cuizhixing/share/workspace/multiversion_lerobot/RESOURCE/Tac3D-SDK-精简版.md`
- **LeRobot 文档**: https://huggingface.co/docs/lerobot

---

**维护者**: AI Agent  
**最后更新**: 2026-03-15  
**状态**: 完整
