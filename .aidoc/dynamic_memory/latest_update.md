# 最新更新 (2026-03-15)

## 关键修复：MoveJ 控制方式

### 问题
- 使用 ServoJ 回放数据集时机器人剧烈振荡
- 原因：ServoJ 是实时伺服，数据不平滑时机器人剧烈追赶目标位置

### 解决
- 添加 MoveJ（关节空间插值）控制方式
- MoveJ 发送目标位置 + 运动时间，机器人自动规划平滑轨迹

### 使用
```bash
# 默认使用 MoveJ（不会振荡）
python src/lerobot/scripts/lerobot_replay_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.repo_id="tron2_final" \
    --dataset.episode=0

# 调整速度
--movej_time=0.05    # 更快
--movej_time=0.2     # 更慢更平滑
```

### 对比
| 特性 | MoveJ（新） | ServoJ（旧） |
|------|------------|-------------|
| 平滑性 | 自动规划 | 依赖输入 |
| 振荡风险 | 无 | 高 |
| 适用场景 | 回放数据集 | 实时遥操作 |

## 文件修改
- `tron2_robot.py`: 添加 `send_action_movej()`
- `lerobot_replay_tron2.py`: 默认使用 MoveJ
