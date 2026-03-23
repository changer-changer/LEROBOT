# Tron2 数据集回放 (Replay) 指南

> **版本**: v1.0  
> **日期**: 2026-03-15  
> **脚本**: `lerobot_replay_tron2.py`

---

## 1. 功能概述

`lerobot_replay_tron2.py` 用于将录制好的数据集动作序列回放到 Tron2 机器人上，支持：

- 16 维动作控制（14 臂关节 + 2 夹爪）
- 实时安全检查（关节限位、速度限制）
- 动作平滑处理
- 键盘控制（暂停/继续/停止）
- 多次连续回放
- 可视化数据

---

## 2. 快速开始

### 2.1 基础回放

```bash
# 激活环境
conda activate lerobot
source /opt/ros/humble/setup.bash

# 回放 episode 0
cd /media/cuizhixing/share/workspace/multiversion_lerobot/lerobot_integrated

python src/lerobot/scripts/lerobot_replay_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.repo_id="username/tron2_dataset" \
    --dataset.episode=0
```

### 2.2 完整参数示例

```bash
python src/lerobot/scripts/lerobot_replay_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --robot.cameras='{
        "cam_left": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw", "fps": 30},
        "cam_right": {"type": "ros2", "topic": "/camera/right/color/image_rect_raw", "fps": 30}
    }' \
    --dataset.repo_id="username/tron2_dataset" \
    --dataset.root="/path/to/datasets" \
    --dataset.episode=0 \
    --dataset.fps=30 \
    --dataset.num_replays=1 \
    --dataset.warmup_time_s=3.0 \
    --dataset.action_smoothing=0.0 \
    --enable_safety_check=true \
    --max_joint_speed=1.0 \
    --display_data=false \
    --play_sounds=false
```

---

## 3. 键盘控制

回放过程中可以使用键盘控制：

| 按键 | 功能 |
|------|------|
| `Space` | 暂停/继续回放 |
| `N` | 单步模式（暂停时按 N 执行下一帧）|
| `ESC` | 停止回放并退出 |

---

## 4. 配置参数

### 4.1 机器人配置

```python
robot.type="tron2"                    # 机器人类型
robot.robot_ip="10.192.1.2"           # 机器人 IP 地址
robot.cameras={...}                   # 相机配置（可选，用于可视化）
```

### 4.2 数据集配置

```python
dataset.repo_id="username/dataset"    # 数据集标识符
dataset.root="/path/to/data"          # 数据集根目录（可选）
dataset.episode=0                     # 要回放的 episode 编号
dataset.fps=30                        # 回放帧率（默认使用数据集帧率）
dataset.num_replays=1                 # 回放次数
dataset.warmup_time_s=3.0             # 回放前等待时间
dataset.action_smoothing=0.0          # 动作平滑系数 (0-1)
```

### 4.3 安全配置

```python
enable_safety_check=true              # 启用安全检查
max_joint_speed=1.0                   # 最大关节速度 (rad/s)
```

### 4.4 其他配置

```python
display_data=false                    # 显示数据可视化
play_sounds=false                     # 启用语音播报
```

---

## 5. 安全检查机制

### 5.1 检查内容

回放过程中会自动检查以下安全项：

1. **关节限位检查**
   - 左臂关节: [-3.5, 3.0] rad (宽松限位)
   - 右臂关节: [-3.5, 3.0] rad
   - 夹爪: [-5, 105] %

2. **速度限制检查**
   - 计算目标与当前位置的速度
   - 超过 `max_joint_speed * 2` 时停止

3. **通信状态检查**
   - 确保机器人连接正常
   - 动作发送失败时停止

### 5.2 安全响应

当安全检查失败时：
- 立即打印错误信息
- 停止回放
- 保持机器人当前状态（不会自动回零）

---

## 6. 动作平滑

### 6.1 平滑公式

```python
smoothed_action = alpha * target_action + (1 - alpha) * prev_action
```

### 6.2 参数建议

| alpha | 效果 | 适用场景 |
|-------|------|---------|
| 0.0 | 无平滑 | 精确复现、调试 |
| 0.3 | 轻度平滑 | 一般操作 |
| 0.5 | 中度平滑 | 快速动作 |
| 0.7 | 重度平滑 | 非常平滑但延迟大 |

### 6.3 使用示例

```bash
# 轻度平滑
--dataset.action_smoothing=0.3
```

---

## 7. 多次回放

### 7.1 连续回放

```bash
# 连续回放 3 次
--dataset.num_replays=3
```

### 7.2 间隔时间

每次回放之间自动等待 2 秒。

---

## 8. 可视化

### 8.1 启用可视化

```bash
--display_data=true
```

### 8.2 可视化内容

- 机器人实时观测
- 当前执行的动作
- 图像数据（如果有相机）

### 8.3 Rerun 查看

```bash
# 回放时自动启动 rerun 服务器
# 在浏览器中访问 http://localhost:9090 查看
```

---

## 9. 常见问题

### Q1: 动作维度不匹配

**错误**: `动作维度不匹配: 机器人期望 16 维，数据集提供 X 维`

**原因**: 数据集不是 Tron2 格式

**解决**: 使用正确的 Tron2 数据集

### Q2: 安全检查失败

**错误**: `关节 X 目标位置 Y 超出限位`

**原因**: 数据集中的动作超出安全范围

**解决**:
1. 检查数据集质量
2. 临时禁用安全检查（不推荐）: `--enable_safety_check=false`
3. 调整限位范围（修改代码）

### Q3: 速度过快

**错误**: `关节速度 X rad/s 超过限制`

**原因**: 相邻帧动作差异过大

**解决**:
1. 启用动作平滑: `--dataset.action_smoothing=0.3`
2. 降低回放帧率: `--dataset.fps=15`
3. 提高速度限制: `--max_joint_speed=2.0`

### Q4: 回放卡顿

**原因**: 系统负载过高

**解决**:
1. 关闭可视化: `--display_data=false`
2. 降低帧率: `--dataset.fps=15`
3. 关闭相机连接（如果不需要可视化）

---

## 10. 使用流程

### 10.1 准备工作

1. **启动机器人**
   ```bash
   # 确保机器人已开机并连接
   ping 10.192.1.2
   ```

2. **准备环境**
   ```bash
   conda activate lerobot
   source /opt/ros/humble/setup.bash
   ```

3. **确认数据集**
   ```bash
   # 检查数据集是否存在
   ls /path/to/datasets/username/tron2_dataset
   ```

### 10.2 执行回放

1. **首次回放**（建议先不使用可视化）
   ```bash
   python src/lerobot/scripts/lerobot_replay_tron2.py \
       --robot.type=tron2 \
       --robot.robot_ip="10.192.1.2" \
       --dataset.repo_id="username/tron2_dataset" \
       --dataset.episode=0 \
       --dataset.warmup_time_s=5.0
   ```

2. **观察执行**
   - 注意机器人动作是否流畅
   - 如有异常立即按 `ESC` 停止

3. **调优参数**
   - 根据实际效果调整平滑系数
   - 如需可视化，添加 `--display_data=true`

---

## 11. 代码结构

### 11.1 主函数流程

```
replay_tron2()
    ├── 初始化机器人
    ├── 加载数据集
    ├── 验证兼容性（16维动作）
    ├── 连接机器人
    ├── 预热等待
    └── 执行回放（可多次）
        └── replay_episode()
            ├── 读取动作序列
            ├── 安全检查
            ├── 发送动作
            ├── 可视化（可选）
            └── 帧率控制
```

### 11.2 关键函数

| 函数 | 功能 |
|------|------|
| `check_action_safety()` | 动作安全检查 |
| `smooth_action()` | 动作平滑处理 |
| `init_keyboard_listener()` | 键盘监听 |
| `replay_episode()` | 单 episode 回放 |

---

## 12. 与原版 replay 的区别

| 特性 | 原版 replay | Tron2 replay |
|------|------------|--------------|
| 适用机器人 | 通用 | Tron2 专用 |
| 动作维度 | 自动适配 | 固定 16 维 |
| 安全检查 | 无 | 有（限位、速度）|
| 动作平滑 | 无 | 有 |
| 键盘控制 | 无 | 有（暂停/继续/停止）|
| 多次回放 | 无 | 有 |
| 预热等待 | 无 | 有 |

---

## 13. 调试技巧

### 13.1 单步调试

```bash
# 1. 启动回放并暂停
# 2. 按 Space 暂停
# 3. 按 N 逐帧执行
```

### 13.2 日志级别

```bash
# 查看详细日志
python -m logging_level=DEBUG src/lerobot/scripts/lerobot_replay_tron2.py ...
```

### 13.3 测试模式

```python
# 修改代码，添加测试模式（不发送动作，仅打印）
# 在 replay_episode() 中添加:
if test_mode:
    logging.info(f"[TEST] 动作: {action}")
    continue
```

### 13.4 SSL/网络连接错误

**错误信息**:
```
httpx.ConnectError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol
```

**原因**: LeRobotDataset 默认尝试从 HuggingFace Hub 下载数据集元数据，但网络连接失败或数据集只在本地。

**解决**:
1. **已自动修复**: 脚本已设置 `HF_HUB_OFFLINE=1`，默认只使用本地数据集
2. **检查数据集路径**:
   ```bash
   # 查看默认位置
   ls ~/.cache/huggingface/lerobot/{repo_id}/
   
   # 或使用自定义路径
   --dataset.root="/path/to/your/datasets"
   ```
3. **手动设置环境变量**:
   ```bash
   export HF_HUB_OFFLINE=1
   python src/lerobot/scripts/lerobot_replay_tron2.py ...
   ```

---

**最后更新**: 2026-03-15

## 14. MoveJ 模式（推荐）

### 14.1 什么是 MoveJ？

MoveJ（Move Joint）是**关节空间插值运动**：
- 你发送：目标关节角度 + 运动时间
- 机器人：自动规划平滑轨迹，内部插值执行

### 14.2 为什么用 MoveJ？

**ServoJ（老方法）的问题**：
- 需要高频发送目标位置（50-100Hz）
- 数据不平滑会导致振荡
- 回放数据集容易抖动

**MoveJ（新方法）的优势**：
- 机器人自己规划轨迹，保证平滑
- 低频发送即可（10-30Hz）
- 回放数据集不会振荡

### 14.3 使用方法

MoveJ 现在是**默认模式**，无需额外配置：

```bash
python src/lerobot/scripts/lerobot_replay_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.root="/home/cuizhixing/data/outputs/recordings" \
    --dataset.repo_id="tron2_final" \
    --dataset.episode=0
```

### 14.4 调整运动速度

如果运动太慢，减小 `movej_time`：
```bash
--movej_time=0.05    # 更快（0.05秒完成每步）
```

如果还振荡，增加 `movej_time`：
```bash
--movej_time=0.2     # 更慢更平滑（0.2秒完成每步）
```

### 14.5 禁用 MoveJ（回到 ServoJ）

如果你确定要用 ServoJ：
```bash
--use_movej=false
```

**注意**：使用 ServoJ 时需要确保数据集动作平滑，否则可能振荡。
