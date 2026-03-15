#!/usr/bin/env python

# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tron2 机器人数据集回放脚本

参数说明:
    --robot.type              机器人类型，固定为 tron2
    --robot.robot_ip          机器人 IP，真机: 10.192.1.2，仿真: 127.0.0.1
    --dataset.repo_id         数据集名称，如 "tron2_demo"
    --dataset.root            数据集根目录，如 "/home/cuizhixing/data/outputs/recordings"
    --dataset.episode         回放第几集，从 0 开始
    --use_movej               使用 MoveJ (推荐), true/false
    --movej_time              每帧运动时间(秒)，默认 0.1，原速建议 0.033

常用示例:

```shell
# 原速回放 (30fps 数据)
python src/lerobot/scripts/lerobot_replay_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.repo_id="tron2_demo" \
    --dataset.root="/home/cuizhixing/data/outputs/recordings" \
    --dataset.episode=0 \
    --use_movej=true \
    --movej_time=0.033

# 快速回放 (跳帧，运动速度保持一致)
python src/lerobot/scripts/lerobot_replay_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --dataset.repo_id="tron2_demo" \
    --dataset.root="/home/cuizhixing/data/outputs/recordings" \
    --dataset.episode=0 \
    --use_movej=true \
    --movej_time=0.1
```

键盘控制:
    Space - 暂停/继续
    ESC   - 停止退出
"""

# 关键：在导入任何其他模块之前设置离线模式
# 防止 LeRobotDataset 尝试连接 HuggingFace Hub
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pprint import pformat
from typing import Any

import numpy as np
from pynput import keyboard

from lerobot.cameras import CameraConfig
from lerobot.cameras.ros2.configs import ROS2CameraConfig
from lerobot.configs import parser
from lerobot.configs.policies import PreTrainedConfig
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.datasets.utils import build_dataset_frame
from lerobot.robots import Robot, RobotConfig, make_robot_from_config
from lerobot.robots.tron2.tron2_config import Tron2RobotConfig
from lerobot.tactile.configs import Tac3DSensorConfig
from lerobot.utils.constants import ACTION
from lerobot.utils.control_utils import is_headless
from lerobot.utils.import_utils import register_third_party_plugins
from lerobot.utils.robot_utils import busy_wait
from lerobot.utils.utils import init_logging, log_say
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data


@dataclass
class Tron2DatasetReplayConfig:
    """数据集配置"""
    repo_id: str              # 数据集名称，如 "tron2_demo"
    episode: int              # 回放第几集，从 0 开始
    root: str | Path | None = None  # 数据集根目录
    fps: int | None = None    # 回放帧率，默认用数据集原帧率
    num_replays: int = 1      # 循环回放次数
    warmup_time_s: float = 3.0 # 回放前等待时间(秒)
    action_smoothing: float = 0.0  # 动作平滑系数(0-1)


@dataclass
class Tron2ReplayConfig:
    """回放主配置"""
    robot: RobotConfig
    dataset: Tron2DatasetReplayConfig
    display_data: bool = False      # 显示数据可视化
    play_sounds: bool = False       # 语音播报
    enable_safety_check: bool = True # 启用安全检查
    max_joint_speed: float = 1.0    # 最大关节速度(rad/s)
    use_movej: bool = True          # 使用 MoveJ(推荐)
    movej_time: float = 0.1         # 每帧运动时间(秒)，原速建议 0.033


def init_keyboard_listener():
    """初始化键盘监听器，用于暂停/停止回放"""
    events = {
        "pause": False,      # 暂停状态
        "stop": False,       # 停止回放
        "step_next": False,  # 单步模式：下一步
    }
    
    def on_press(key):
        try:
            if key == keyboard.Key.space:
                events["pause"] = not events["pause"]
                state = "PAUSED" if events["pause"] else "RESUMED"
                logging.info(f"Playback {state}")
            elif key == keyboard.Key.esc:
                events["stop"] = True
                logging.info("Playback STOP requested")
            elif hasattr(key, 'char') and key.char == 'n':
                events["step_next"] = True
        except AttributeError:
            pass
    
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    return listener, events


def check_action_safety(action: dict, robot, max_speed: float = 1.0) -> tuple[bool, str]:
    """
    检查动作安全性
    
    Returns:
        (is_safe, message)
    """
    # 获取当前状态
    try:
        current_obs = robot.get_observation()
        current_q = np.array([current_obs[f"joint_{i}_pos"] for i in range(16)])
    except Exception as e:
        return False, f"无法获取机器人状态: {e}"
    
    # 构建目标位置数组
    target_q = np.zeros(16)
    for i in range(16):
        key = f"action.joint_{i}_pos"
        target_q[i] = action.get(key, current_q[i])
    
    # 检查关节限位 (简化检查，使用宽松限位)
    joint_limits_low = np.array([
        -3.5, -0.5, -4.0, -3.0, -2.0, -1.0, -1.8,  # 左臂
        -3.5, -0.5, -4.0, -3.0, -2.0, -1.0, -1.8,  # 右臂
        -5, -5  # 夹爪 (百分比，允许小范围超限)
    ])
    joint_limits_high = np.array([
        3.0, 3.2, 1.6, 0.6, 1.5, 0.9, 1.8,   # 左臂
        3.0, 3.2, 1.6, 0.6, 1.5, 0.9, 1.8,   # 右臂
        105, 105  # 夹爪
    ])
    
    for i in range(14):  # 只检查臂部关节
        if target_q[i] < joint_limits_low[i] or target_q[i] > joint_limits_high[i]:
            return False, f"关节 {i} 目标位置 {target_q[i]:.3f} 超出限位 [{joint_limits_low[i]:.3f}, {joint_limits_high[i]:.3f}]"
    
    # 检查夹爪范围
    for i in [14, 15]:
        if target_q[i] < -5 or target_q[i] > 105:
            return False, f"夹爪 {i} 目标位置 {target_q[i]:.1f} 超出有效范围 [0, 100]"
    
    # 检查速度
    joint_speed = np.abs(target_q - current_q) * 30  # 假设 30fps
    max_speed_observed = np.max(joint_speed[:14])  # 只检查臂部
    
    if max_speed_observed > max_speed * 2:  # 允许 2 倍裕量
        return False, f"关节速度 {max_speed_observed:.2f} rad/s 超过限制 {max_speed * 2:.2f} rad/s"
    
    return True, "OK"


def smooth_action(prev_action: dict, target_action: dict, alpha: float) -> dict:
    """动作平滑处理"""
    smoothed = {}
    for key in target_action:
        if key in prev_action:
            smoothed[key] = alpha * target_action[key] + (1 - alpha) * prev_action[key]
        else:
            smoothed[key] = target_action[key]
    return smoothed


def replay_episode(
    robot: Robot,
    dataset: LeRobotDataset,
    episode: int,
    fps: int,
    events: dict,
    display_data: bool = False,
    enable_safety_check: bool = True,
    max_joint_speed: float = 1.0,
    action_smoothing: float = 0.0,
    use_movej: bool = True,
    movej_time: float = 0.1,
):
    """
    回放单个 episode
    
    Args:
        robot: 机器人实例
        dataset: 数据集
        episode: episode 编号
        fps: 回放帧率
        events: 键盘事件字典
        display_data: 是否显示可视化
        enable_safety_check: 是否启用安全检查
        max_joint_speed: 最大关节速度
        action_smoothing: 动作平滑系数
        use_movej: 是否使用 MoveJ（推荐 True）
        movej_time: MoveJ 运动时间（秒）
        enable_safety_check: 是否启用安全检查
        max_joint_speed: 最大关节速度
        action_smoothing: 动作平滑系数
    """
    # 过滤出指定 episode 的帧
    episode_frames = dataset.hf_dataset.filter(lambda x: x["episode_index"] == episode)
    total_frames = len(episode_frames)
    
    if total_frames == 0:
        logging.error(f"Episode {episode} 未找到或为空")
        return
    
    logging.info(f"开始回放 Episode {episode}，共 {total_frames} 帧，{fps} FPS")
    
    # 提取动作和观测
    actions = episode_frames.select_columns(ACTION)
    
    # 如果有观测数据，也提取用于可视化
    has_observation = "observation.state" in episode_frames.column_names
    if has_observation:
        observations = episode_frames.select_columns("observation.state")
    else:
        observations = None
    
    # 获取 action 名称映射
    action_names = dataset.features[ACTION]["names"]
    
    # 初始化上一帧动作（用于平滑）
    prev_action = None
    
    # 回放循环
    for idx in range(total_frames):
        start_loop_t = time.perf_counter()
        
        # 检查停止信号
        if events["stop"]:
            logging.info("回放被用户停止")
            break
        
        # 处理暂停
        while events["pause"] and not events["stop"]:
            time.sleep(0.05)
            if events["step_next"]:
                events["step_next"] = False
                break
        
        # 获取当前帧动作
        action_array = actions[idx][ACTION]
        action = {}
        for i, name in enumerate(action_names):
            action[name] = float(action_array[i])
        
        # 动作平滑
        if action_smoothing > 0 and prev_action is not None:
            action = smooth_action(prev_action, action, action_smoothing)
        prev_action = action.copy()
        
        # 安全检查
        if enable_safety_check:
            is_safe, message = check_action_safety(action, robot, max_joint_speed)
            if not is_safe:
                logging.error(f"安全检查失败: {message}")
                logging.error("回放已停止，请检查数据集和机器人状态")
                break
        
        # 发送动作到机器人
        try:
            if use_movej and hasattr(robot, 'send_action_movej'):
                # 使用 MoveJ（更安全，自动插值）
                # move_time = 帧间隔，保证运动速度与录制一致
                frame_interval = 1.0 / fps
                send_start = time.perf_counter()
                robot.send_action_movej(action, move_time=frame_interval)
                # 精确等待到下一帧（减去发送耗时）
                elapsed = time.perf_counter() - send_start
                sleep_time = max(frame_interval - elapsed, 0)
                if sleep_time > 0:
                    busy_wait(sleep_time)
            else:
                # 使用 ServoJ（实时伺服，需输入平滑）
                robot.send_action(action)
                
                # 帧率控制（仅 ServoJ 模式需要）
                dt_s = time.perf_counter() - start_loop_t
                sleep_time = max(1.0 / fps - dt_s, 0.0)
                if sleep_time > 0:
                    busy_wait(sleep_time)
        except Exception as e:
            logging.error(f"发送动作失败: {e}")
            break
        
        # 可视化
        if display_data:
            try:
                # 尝试获取观测用于可视化
                robot_obs = robot.get_observation()
                log_rerun_data(observation=robot_obs, action=action)
            except Exception as e:
                logging.warning(f"可视化失败: {e}")
        
        # 进度报告
        if (idx + 1) % fps == 0 or idx == total_frames - 1:
            progress = (idx + 1) / total_frames * 100
            logging.info(f"回放进度: {idx + 1}/{total_frames} ({progress:.1f}%)")
    
    logging.info(f"Episode {episode} 回放完成")


@parser.wrap()
def replay_tron2(cfg: Tron2ReplayConfig):
    """Tron2 回放主函数"""
    init_logging()
    logging.info(pformat(asdict(cfg)))
    
    # 初始化机器人
    robot = make_robot_from_config(cfg.robot)
    
    # 加载数据集 (本地模式，HF_HUB_OFFLINE 已在脚本开头设置)
    dataset = LeRobotDataset(
        cfg.dataset.repo_id,
        root=cfg.dataset.root,
        episodes=[cfg.dataset.episode]
    )
    
    # 确定回放帧率
    fps = cfg.dataset.fps if cfg.dataset.fps is not None else dataset.fps
    
    # 验证机器人与数据集兼容性
    logging.info("验证机器人与数据集兼容性...")
    expected_action_dim = len(robot.action_features)
    dataset_action_dim = dataset.features[ACTION]["shape"][0]
    
    if expected_action_dim != dataset_action_dim:
        raise ValueError(
            f"动作维度不匹配: 机器人期望 {expected_action_dim} 维，"
            f"数据集提供 {dataset_action_dim} 维"
        )
    
    logging.info(f"动作维度检查通过: {dataset_action_dim} 维")
    
    # 连接机器人
    robot.connect()
    
    # 初始化键盘监听
    listener, events = None, {"pause": False, "stop": False, "step_next": False}
    if not is_headless():
        listener, events = init_keyboard_listener()
    
    # 初始化可视化
    if cfg.display_data:
        init_rerun(session_name=f"tron2_replay_ep{cfg.dataset.episode}")
    
    try:
        # 预热等待
        if cfg.dataset.warmup_time_s > 0:
            log_say(f"准备回放，等待 {cfg.dataset.warmup_time_s} 秒", cfg.play_sounds)
            logging.info(f"预热等待 {cfg.dataset.warmup_time_s} 秒...")
            time.sleep(cfg.dataset.warmup_time_s)
        
        # 多次回放
        for replay_idx in range(cfg.dataset.num_replays):
            if cfg.dataset.num_replays > 1:
                log_say(f"第 {replay_idx + 1}/{cfg.dataset.num_replays} 次回放", cfg.play_sounds)
                logging.info(f"===== 第 {replay_idx + 1}/{cfg.dataset.num_replays} 次回放 =====")
            
            # 重置事件
            events["pause"] = False
            events["stop"] = False
            
            # 执行回放
            replay_episode(
                robot=robot,
                dataset=dataset,
                episode=cfg.dataset.episode,
                fps=fps,
                events=events,
                display_data=cfg.display_data,
                enable_safety_check=cfg.enable_safety_check,
                max_joint_speed=cfg.max_joint_speed,
                action_smoothing=cfg.dataset.action_smoothing,
                use_movej=cfg.use_movej,
                movej_time=cfg.movej_time,
            )
            
            # 如果不是最后一次回放，等待一下
            if replay_idx < cfg.dataset.num_replays - 1:
                time.sleep(2.0)
        
        log_say("回放完成", cfg.play_sounds)
        
    finally:
        # 清理
        robot.disconnect()
        
        if listener is not None:
            listener.stop()
        
        logging.info("回放结束，资源已释放")


def main():
    register_third_party_plugins()
    replay_tron2()


if __name__ == "__main__":
    main()
