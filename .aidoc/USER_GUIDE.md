# Tron2 + LeRobot 用户指南

> **版本**: v1.0  
> **日期**: 2026-03-15  
> **适用**: DACH_TRON2A 机器人 + ROS2 相机 + Tac3D 触觉

---

## 目录

1. [快速开始](#1-快速开始)
2. [环境配置](#2-环境配置)
3. [机器人连接](#3-机器人连接)
4. [数据录制](#4-数据录制)
5. [数据集规范](#5-数据集规范)
6. [常见问题](#6-常见问题)
7. [技术参考](#7-技术参考)

---

## 1. 快速开始

### 1.1 环境检查清单

- [ ] 机器人已开机并连接 Wi-Fi
- [ ] 开发机 IP 设置为 10.192.1.x 网段
- [ ] ROS2 Humble 已 source
- [ ] conda 环境 `lerobot` 已激活
- [ ] Tac3D-Desktop 软件已运行 (如使用触觉)

### 1.2 一键启动录制

```bash
# 激活环境
conda activate lerobot
source /opt/ros/humble/setup.bash

# 启动录制
cd /media/cuizhixing/share/workspace/multiversion_lerobot/lerobot_integrated

python src/lerobot/scripts/lerobot_record_manual_fixed.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --robot.cameras='{
        "cam_left": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw", "fps": 30, "width": 640, "height": 480},
        "cam_right": {"type": "ros2", "topic": "/camera/right/color/image_rect_raw", "fps": 30, "width": 640, "height": 480}
    }' \
    --robot.tactile_sensors='{
        "tac3d_sensor": {"type": "tac3d", "udp_port": 9988, "fps": 30}
    }' \
    --dataset.repo_id="username/tron2_demo" \
    --dataset.single_task="Pick up the object" \
    --dataset.fps=30 \
    --dataset.vcodec="libsvtav1" \
    --dataset.output_root="/path/to/output"
```

### 1.3 键盘控制

| 按键 | 功能 |
|------|------|
| `S` | 开始录制 |
| `Space` | 保存当前 episode |
| `Backspace` 或 `L` | 丢弃当前 episode |
| `ESC` | 退出程序 |

---

## 2. 环境配置

### 2.1 初始化环境

```bash
# 创建 conda 环境 (Python 3.10 for ROS2 Humble)
conda create -n lerobot python=3.10
conda activate lerobot

# 安装 LeRobot
pip install -e ".[all]"

# 安装 ROS2 依赖
pip install rclpy sensor_msgs

# 安装 Tac3D SDK (可选)
pip install /path/to/PyTac3D-*.whl
```

### 2.2 网络配置

```bash
# 设置静态 IP (Ubuntu)
nmcli connection modify "Wired Connection" ipv4.addresses 10.192.1.10/24
nmcli connection modify "Wired Connection" ipv4.method manual
```

### 2.3 验证安装

```bash
# 测试 ROS2 话题
ros2 topic list | grep camera

# 测试机器人连接
python -c "
from lerobot.robots import make_robot_from_config
from lerobot.robots.tron2.tron2_config import Tron2RobotConfig
cfg = Tron2RobotConfig(robot_ip='10.192.1.2')
robot = make_robot_from_config(cfg)
robot.connect()
print('Connected!')
robot.disconnect()
"
```

---

## 3. 机器人连接

### 3.1 Tron2 机器人配置

```python
from lerobot.robots.tron2.tron2_config import Tron2RobotConfig
from lerobot.cameras.ros2.configs import ROS2CameraConfig
from lerobot.tactile.configs import Tac3DSensorConfig

config = Tron2RobotConfig(
    robot_ip="10.192.1.2",  # 机器人 IP
    cameras={
        "cam_left": ROS2CameraConfig(
            topic="/camera/left/color/image_rect_raw",
            fps=30,
            width=640,
            height=480
        ),
        "cam_right": ROS2CameraConfig(
            topic="/camera/right/color/image_rect_raw",
            fps=30,
            width=640,
            height=480
        )
    },
    tactile_sensors={
        "tac3d_sensor": Tac3DSensorConfig(
            udp_port=9988,
            fps=30,
            data_type="full"  # "displacement", "force", or "full"
        )
    }
)
```

### 3.2 关节限位

| 关节 | 名称 | 下限 | 上限 | 单位 |
|:----:|------|:----:|:----:|:----:|
| 0-6 | 左臂 | -3.14 | 2.60 | rad |
| 7-13 | 右臂 | -3.14 | 2.60 | rad |
| 14 | 左夹爪 | 0 | 100 | % |
| 15 | 右夹爪 | 0 | 100 | % |

### 3.3 状态读取

```python
# 获取观测
obs = robot.get_observation()

# 关节状态
joint_0_pos = obs["joint_0_pos"]   # 位置 (rad)
joint_0_vel = obs["joint_0_vel"]   # 速度 (rad/s)
joint_0_tau = obs["joint_0_tau"]   # 力矩 (Nm)

# 图像
left_image = obs["cam_left"]       # (480, 640, 3) uint8

# 触觉
tactile = obs["tac3d_sensor"]      # (400, 6) float32
```

### 3.4 动作发送

```python
# 构建动作 (16维)
action = {
    "action.joint_0_pos": 0.5,     # 左臂关节 0
    "action.joint_1_pos": 0.3,
    ...
    "action.joint_14_pos": 50,     # 左夹爪 0-100
    "action.joint_15_pos": 50,     # 右夹爪 0-100
}

# 发送动作
robot.send_action(action)
```

---

## 4. 数据录制与回放

### 4.1 录制配置

```python
@dataclass
class DatasetRecordConfig:
    repo_id: str                    # 数据集ID，如 "username/dataset_name"
    single_task: str               # 任务描述
    fps: int = 30                  # 采样频率
    episode_time_s: int = 60       # 单 episode 最大时长 (防内存爆炸)
    vcodec: str = "libsvtav1"      # 编码器: h264, libsvtav1
    streaming_encoding: bool = False  # 必须为 False！
    output_root: str = "./outputs"  # 输出根目录
```

### 4.2 最佳实践

**视频质量**
```bash
# ✅ 推荐 (高质量)
--dataset.vcodec="libsvtav1" --dataset.streaming_encoding=false

# ❌ 避免 (模糊)
--dataset.streaming_encoding=true
```

**相机分辨率**
```bash
# ✅ 推荐 (保持原始分辨率)
--robot.cameras='{"cam_left": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw", "fps": 30}}'

# ❌ 避免 (强制 resize 可能变形)
--robot.cameras='{"cam_left": {"type": "ros2", ..., "width": 128, "height": 128}}'
```

**触觉传感器**
```bash
# 使用前必须 tare (校准)
# Tac3D-Desktop 软件中点击 "Tare" 按钮
# 或在代码中调用 sensor.tare()
```

### 4.3 录制流程

```
1. 启动脚本
2. 按 'S' 开始录制
3. 执行操作任务
4. 按 'Space' 保存 或 'Backspace' 丢弃
5. 重复 2-4 录制多个 episodes
6. 按 'ESC' 退出
```

---

## 5. 数据集规范

### 5.1 数据格式

#### Observation State (48维)
```python
obs[0:3]    # joint_0: [pos, vel, tau]
obs[3:6]    # joint_1: [pos, vel, tau]
...
obs[42:45]  # joint_14 (左夹爪): [pos, vel, tau]
obs[45:48]  # joint_15 (右夹爪): [pos, vel, tau]
```

#### Action (16维)
```python
action[0:7]   # 左臂 7 关节目标位置
action[7:14]  # 右臂 7 关节目标位置
action[14]    # 左夹爪目标 (0-100)
action[15]    # 右夹爪目标 (0-100)
```

#### 触觉数据 (400, 6)
```python
[:, 0:3]  # 形变 [dx, dy, dz] mm
[:, 3:6]  # 力 [Fx, Fy, Fz] N
```

### 5.2 目录结构

```
dataset/
├── data/chunk-000/file-000.parquet     # 主数据
├── meta/info.json                       # 元数据
├── meta/episodes/...                    # episode 索引
└── videos/episode_N/                    # 视频
    ├── cam_left.mp4
    └── cam_right.mp4
```

### 5.3 读取数据集

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset("path/to/dataset")

# 获取第 0 帧
frame = dataset[0]
obs = frame["observation.state"]   # (48,)
action = frame["action"]           # (16,)

# 查看 episode 信息
episode_data = dataset.get_episode(0)
```

---

## 6. 常见问题

### Q1: 无法连接到机器人

**错误**: `RuntimeError: Could not connect to Tron2`

**排查**:
```bash
# 1. 检查网络
ping 10.192.1.2

# 2. 检查 WebSocket 端口
curl http://10.192.1.2:5000  # 应该返回 WebSocket 握手错误

# 3. 检查机器人状态
# 访问 http://10.192.1.2:8080 查看 Web 界面
```

### Q2: 相机图像黑屏

**排查**:
```bash
# 1. 检查 ROS2 话题
ros2 topic list | grep camera
ros2 topic hz /camera/left/color/image_rect_raw

# 2. 检查话题权限
ros2 topic echo /camera/left/color/image_rect_raw  # 应该显示图像数据

# 3. 检查 rclpy
python -c "import rclpy; print(rclpy.__version__)"
```

### Q3: 触觉数据全零

**原因**: 
- 传感器未接触物体
- 未执行 tare 校准
- Tac3D-Desktop 未运行

**解决**:
1. 确保 Tac3D-Desktop 运行
2. 点击 "Tare" 按钮校准
3. 触碰传感器表面

### Q4: 视频模糊

**原因**: `streaming_encoding=true`

**解决**:
```bash
--dataset.streaming_encoding=false
--dataset.vcodec="libsvtav1"
```

### Q5: 内存不足

**原因**: episode 太长，帧数过多

**解决**:
```bash
# 限制 episode 时长
--dataset.episode_time_s=60

# 或减少录制帧率
--dataset.fps=15
```

### Q6: ImportError: busy_wait

**原因**: 使用了旧版本的 robot_utils

**解决**: 已修复，请更新代码

---

## 7. 技术参考

### 7.1 关键文件位置

| 文件 | 用途 |
|------|------|
| `src/lerobot/robots/tron2/tron2_robot.py` | 机器人主类 |
| `src/lerobot/robots/tron2/tron2_config.py` | 配置类 |
| `src/lerobot/cameras/ros2/ros2_camera.py` | ROS2 相机 |
| `src/lerobot/tactile/direct_connection/tac3d_sensor.py` | Tac3D 传感器 |
| `src/lerobot/scripts/lerobot_record_manual_fixed.py` | 录制脚本 |

### 7.2 调试命令

```bash
# 查看视频信息
ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,codec_name \
    videos/episode_0/cam_left.mp4

# 查看 Parquet 数据
python -c "
import pandas as pd
df = pd.read_parquet('data/chunk-000/file-000.parquet')
print(df.columns)
print(df['observation.state'].iloc[0].shape)
"

# 播放视频
ffplay videos/episode_0/cam_left.mp4
```

### 7.3 联系信息

- **师兄参考代码**: `/home/cuizhixing/WorkspaceBase/lerobot/src/lerobot/scripts/lerobot_record_vr.py`
- **项目文档**: `.aidoc/`
- **数据集规范**: `.aidoc/TRON2_DATASET_GUIDE.md`

---

**文档版本**: 1.0  
**最后更新**: 2026-03-15

## 8. 数据回放

录制完成后，可以使用 `lerobot_replay_tron2.py` 脚本将数据集回放到机器人上。

### 8.1 快速回放

```bash
python src/lerobot/scripts/lerobot_replay_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.repo_id="username/tron2_dataset" \
    --dataset.episode=0
```

### 8.2 键盘控制

回放过程中：
- `Space`: 暂停/继续
- `N`: 单步执行（暂停时）
- `ESC`: 停止回放

### 8.3 详细文档

详见 [REPLAY_GUIDE.md](REPLAY_GUIDE.md)
