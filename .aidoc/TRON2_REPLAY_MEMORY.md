# Tron2 机器人回放项目记忆

> 创建时间: 2026-03-15  
> 项目目标: 实现 Tron2 双臂机器人的数据集动作回放，支持初始位置过渡

---

## 1. 项目背景

- **机器人型号**: DACH_TRON2A (16 DOF: 14 臂关节 + 2 夹爪)
- **控制方式**: WebSocket API (ws://10.192.1.2:5000)
- **SDK 版本**: r-1.2.25 (2026-01-13)
- **数据集帧率**: 30 FPS

## 2. 关键发现

### 2.1 MoveJ 时间单位
- **关键修复**: `time` 参数单位是 **秒**，不是毫秒
- SDK 示例: `{"time": 5, "joint": [...]}` 表示 5 秒
- 之前错误: `int(move_time * 1000)` 导致时间过短

### 2.2 数据集 Episode 索引
- **正确字段**: `dataset_from_index` / `dataset_to_index`
- **错误字段**: `start_index` (不存在)
- Episode 0: from=0, to=313, length=313

### 2.3 帧率控制逻辑
```python
# 精确控制：减去发送耗时
loop_start = time.perf_counter()
robot.send_action_movej(action, move_time=frame_interval)
elapsed = time.perf_counter() - loop_start
sleep_time = frame_interval - elapsed
if sleep_time > 0:
    time.sleep(sleep_time)
```

## 3. 文件清单

| 文件 | 功能 | 状态 |
|------|------|------|
| `lerobot_replay_tron2_with_init.py` | 完整回放脚本（带初始位置过渡） | ✅ 推荐 |
| `tron2_test_init_pos.py` | 仅测试初始位置运动 | ✅ 辅助 |
| `tron2_get_joint_pos.py` | 获取当前关节位置 | ✅ 辅助 |
| `lerobot_replay_tron2.py` | 旧版回放脚本 | ❌ 废弃 |
| `lerobot_replay_tron2_smooth.py` | 早期平滑版本 | ❌ 废弃 |

## 4. 默认位置配置

### Side Position（过渡位置 - 两臂展开）
```python
SIDE_POSITION = [
    0.0849, 0.4159, 0.6814, -1.1422, 0.3621, -0.1473, 0.4774,   # 左臂
    -0.1292, -0.5084, -0.7813, -0.6478, -0.4898, -0.4773, -0.4136,  # 右臂
    2.0, 2.0  # 夹爪
]
```
- **作用**: 避开桌子，准备过渡
- **时间**: 3秒（默认）

### Start Position（起始位置 - 双臂前伸）
```python
START_POSITION = [
    0.0199, 0.2429, -0.004, -1.552, 0.237, 0.0018, -0.001,   # 左臂
    0.0136, -0.2408, 0.0046, -1.5502, -0.2359, 0.0051, 0.0004,  # 右臂
    2.0, 2.0  # 夹爪
]
```
- **作用**: 回放起始状态（遥操作起点）
- **时间**: 3秒（默认）

## 5. 使用命令

### 完整命令（自定义位置和时间）
```bash
python src/lerobot/scripts/lerobot_replay_tron2_with_init.py \
    --robot_ip="10.192.1.2" \
    --repo_id="deeptouch/tron2_tactile_test" \
    --dataset_root="/home/cuizhixing/data/outputs/recordings/tron2_final" \
    --episode=0 \
    --side_time=3.0 \
    --start_time=3.0 \
    --side_pos="0.0849,0.4159,0.6814,-1.1422,0.3621,-0.1473,0.4774,-0.1292,-0.5084,-0.7813,-0.6478,-0.4898,-0.4773,-0.4136,2.0,2.0" \
    --start_pos="0.0199,0.2429,-0.004,-1.552,0.237,0.0018,-0.001,0.0136,-0.2408,0.0046,-1.5502,-0.2359,0.0051,0.0004,2.0,2.0"
```

### 简化命令（使用默认位置）
```bash
python src/lerobot/scripts/lerobot_replay_tron2_with_init.py \
    --robot_ip="10.192.1.2" \
    --repo_id="deeptouch/tron2_tactile_test" \
    --dataset_root="/home/cuizhixing/data/outputs/recordings/tron2_final" \
    --episode=0
```

### 获取当前位置
```bash
python src/lerobot/scripts/tron2_get_joint_pos.py \
    --robot_ip="10.192.1.2" \
    --name="custom_position"
```

### 测试初始位置
```bash
python src/lerobot/scripts/tron2_test_init_pos.py \
    --robot_ip="10.192.1.2" \
    --stage=0
```

## 6. 参数格式注意事项

| 正确 | 错误 |
|------|------|
| `--robot_ip` | `--robot.ip` |
| `--dataset_root` | `--dataset.root` |
| `--repo_id` | `--dataset.repo_id` |
| `--episode` | `--dataset.episode` |

**所有参数使用下划线 `_`，不要用点号！**

## 7. 执行流程

```
[1/4] 连接机器人
        ↓ 自动
[2/4] 加载数据集
        ↓ 按回车确认
[3/4] 阶段1: 运动到 side_pos（两臂展开，避开桌子）
        用时: --side_time 秒
        ↓ 按回车确认
[4/4] 阶段2: 运动到 start_pos（双臂前伸，回放起点）
        用时: --start_time 秒
        ↓ 按回车确认
[5/5] 开始回放数据集
        帧率: --fps FPS（默认30）
        逐帧连续播放
```

## 8. 关键问题解决记录

### 问题1: MoveJ 时间单位错误
- **现象**: 机器人不动或运动过快
- **原因**: `time` 参数误用毫秒
- **修复**: 改为秒单位

### 问题2: 帧率控制双重等待
- **现象**: 回放速度变慢
- **原因**: `send_action_movej` + `sleep` 双重等待
- **修复**: 精确计算发送耗时，只等待剩余时间

### 问题3: Episode 索引 KeyError
- **现象**: `KeyError: 'start_index'`
- **原因**: 数据集使用 `dataset_from_index` / `dataset_to_index`
- **修复**: 更新字段名并添加 episode 查找逻辑

## 9. 调试模式

```bash
# 步进模式：每帧按回车
python src/lerobot/scripts/lerobot_replay_tron2_with_init.py \
    ... \
    --step_mode

# 步进模式命令:
#   回车 = 下一帧
#   c    = 连续播放
#   q    = 退出
```

## 10. 关节顺序

| 索引 | 关节 |
|------|------|
| 0-6 | 左臂 j0-j6 |
| 7-13 | 右臂 j7-j13 |
| 14 | 左夹爪 (0.0~2.0) |
| 15 | 右夹爪 (0.0~2.0) |

---

**环境信息:**
- Python: 3.10
- ROS2: Humble
- OS: Ubuntu 22.04 LTS
- HF_HUB_OFFLINE: 1 (离线模式)
