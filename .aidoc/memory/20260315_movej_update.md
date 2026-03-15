# 2026-03-15 MoveJ 控制方式更新

## 关键更新

### 1. 新增 MoveJ 控制方式

**问题**: 使用 ServoJ 回放数据集时，机器人出现剧烈振荡。

**原因**: 
- ServoJ 是实时伺服控制，需要高频平滑输入
- 数据集相邻帧目标位置变化大时，机器人会剧烈加速追赶

**解决方案**: 添加 MoveJ（Move Joint）控制方式

### 2. MoveJ vs ServoJ 对比

| 特性 | MoveJ（新） | ServoJ（旧） |
|------|------------|-------------|
| 控制方式 | 发送目标+时间，机器人自己插值 | 实时发送目标位置 |
| 平滑性 | 自动规划平滑轨迹 | 依赖输入平滑 |
| 振荡风险 | 无 | 高（数据不平滑时）|
| 适用场景 | 回放数据集 | 实时遥操作 |

### 3. 代码修改

#### tron2_robot.py
```python
def send_action_movej(self, action: dict, move_time: float = 0.1):
    """使用 MoveJ 发送动作（更安全）"""
    movej_data = {
        "time": int(move_time * 1000),  # 毫秒
        "joint": arm_q
    }
    self._send_request("request_movej", movej_data)
```

#### lerobot_replay_tron2.py
```python
# 默认使用 MoveJ
use_movej: bool = True
movej_time: float = 0.1

# 发送动作时自动选择
if use_movej and hasattr(robot, 'send_action_movej'):
    robot.send_action_movej(action, move_time=movej_time)
else:
    robot.send_action(action)
```

### 4. 使用方法

```bash
# 默认使用 MoveJ（推荐）
python src/lerobot/scripts/lerobot_replay_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.repo_id="tron2_final" \
    --dataset.episode=0

# 调整运动速度
--movej_time=0.05    # 更快
--movej_time=0.2     # 更慢更平滑
```

### 5. 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| use_movej | true | 是否使用 MoveJ |
| movej_time | 0.1s | 每步运动时间 |

### 6. 文档更新

- `.aidoc/REPLAY_GUIDE.md` - 添加 MoveJ 章节
- `docs/教学.md` - 添加 MoveJ vs ServoJ 对比附录

---

**状态**: 已完成  
**测试**: 待测试（用户即将测试）  
**重要性**: 高（解决振荡安全问题）
