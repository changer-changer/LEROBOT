#!/usr/bin/env python3
"""
Tron2 回放脚本 - 带初始位置过渡

自动执行:
  1. 运动到过渡位置（两臂展开，避开桌子）
  2. 运动到回放起始位置（双臂前伸）
  3. 开始回放数据集动作

参数说明:
  --side_pos      过渡位置关节角度 (16个值, 逗号分隔)
  --start_pos     起始位置关节角度 (16个值, 逗号分隔)
  --side_time     到过渡位置的时间(秒), 默认3秒
  --start_time    到起始位置的时间(秒), 默认3秒
  --step_mode     步进模式：每帧动作需按回车确认

Usage:
    # 使用默认位置（连续播放）
    python src/lerobot/scripts/lerobot_replay_tron2_with_init.py \
        --robot_ip="10.192.1.2" \
        --dataset_root="/home/cuizhixing/data/outputs/recordings/tron2_final" \
        --repo_id="deeptouch/tron2_tactile_test" \
        --episode=0
    
    # 步进模式（每帧按回车，安全可靠）
    python src/lerobot/scripts/lerobot_replay_tron2_with_init.py \
        --robot_ip="10.192.1.2" \
        --dataset_root="/home/cuizhixing/data/outputs/recordings/tron2_final" \
        --repo_id="deeptouch/tron2_tactile_test" \
        --episode=0 \
        --step_mode
    
    # 自定义位置和时间
    python src/lerobot/scripts/lerobot_replay_tron2_with_init.py \
        --robot_ip="10.192.1.2" \
        --dataset_root="/home/cuizhixing/data/outputs/recordings/tron2_final" \
        --repo_id="deeptouch/tron2_tactile_test" \
        --episode=0 \
        --side_pos="0.1,0.4,0.7,-1.1,0.4,-0.1,0.5,-0.1,-0.5,-0.8,-0.6,-0.5,-0.5,-0.4,2.0,2.0" \
        --start_pos="0.0,0.2,0.0,-1.6,0.2,0.0,0.0,0.0,-0.2,0.0,-1.6,-0.2,0.0,0.0,2.0,2.0" \
        --side_time=5.0 \
        --start_time=5.0 \
        --step_mode

步进模式命令:
    回车    - 执行下一帧
    c       - 切换到连续播放
    q       - 退出回放
"""

import os
import sys
import time
import argparse

import numpy as np

# 离线模式
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

sys.path.insert(0, "/media/cuizhixing/share/workspace/multiversion_lerobot/lerobot_integrated/src")

import torch
from lerobot.robots.tron2.tron2_robot import Tron2Robot
from lerobot.robots.tron2.tron2_config import Tron2RobotConfig
from lerobot.datasets.lerobot_dataset import LeRobotDataset


# ========== 默认位置 ==========
# 这些位置可以通过命令行参数覆盖
DEFAULT_SIDE_POSITION = [0.0849, 0.4159, 0.6814, -1.1422, 0.3621, -0.1473, 0.4774,
                         -0.1292, -0.5084, -0.7813, -0.6478, -0.4898, -0.4773, -0.4136,
                         2.0, 2.0]

DEFAULT_START_POSITION = [0.0199, 0.2429, -0.004, -1.552, 0.237, 0.0018, -0.001,
                          0.0136, -0.2408, 0.0046, -1.5502, -0.2359, 0.0051, 0.0004,
                          2.0, 2.0]


def move_to_position(robot, target_joints, duration=3.0):
    """
    使用 MoveJ 运动到目标位置
    
    Args:
        robot: Tron2Robot 实例
        target_joints: 16维关节目标位置
        duration: 运动时间（秒）
    """
    action = {
        "action.joint_0_pos": target_joints[0],
        "action.joint_1_pos": target_joints[1],
        "action.joint_2_pos": target_joints[2],
        "action.joint_3_pos": target_joints[3],
        "action.joint_4_pos": target_joints[4],
        "action.joint_5_pos": target_joints[5],
        "action.joint_6_pos": target_joints[6],
        "action.joint_7_pos": target_joints[7],
        "action.joint_8_pos": target_joints[8],
        "action.joint_9_pos": target_joints[9],
        "action.joint_10_pos": target_joints[10],
        "action.joint_11_pos": target_joints[11],
        "action.joint_12_pos": target_joints[12],
        "action.joint_13_pos": target_joints[13],
        "action.joint_14_pos": target_joints[14],
        "action.joint_15_pos": target_joints[15],
    }
    
    print(f"  发送 MoveJ 命令...")
    robot.send_action_movej(action, move_time=duration)
    
    # 等待运动完成
    print(f"  等待 {duration} 秒...")
    time.sleep(duration)
    print(f"  到达目标位置！")


def replay_episode(robot, dataset, episode_idx, fps=30, step_mode=False):
    """回放指定 episode - 带精确帧率控制和统计
    
    Args:
        robot: Tron2Robot 实例
        dataset: LeRobotDataset
        episode_idx: episode 编号
        fps: 回放帧率
        step_mode: 是否步进模式（每帧按回车继续）
    """
    import numpy as np
    
    # 获取 episode 帧范围
    if hasattr(dataset, 'meta') and hasattr(dataset.meta, 'episodes'):
        # 找到对应 episode_index 的数据
        episodes = dataset.meta.episodes
        episode_data = None
        for ep in episodes:
            if ep['episode_index'] == episode_idx:
                episode_data = ep
                break
        
        if episode_data is None:
            raise ValueError(f"Episode {episode_idx} 不存在")
        
        # 使用 dataset_from_index 和 dataset_to_index
        start_idx = episode_data['dataset_from_index']
        end_idx = episode_data['dataset_to_index']
    else:
        start_idx = 0
        end_idx = len(dataset)
    
    total_frames = end_idx - start_idx
    frame_interval = 1.0 / fps
    total_duration = total_frames * frame_interval
    
    print(f"\n开始回放 Episode {episode_idx}")
    print(f"  帧范围: {start_idx} - {end_idx} (共 {total_frames} 帧)")
    print(f"  帧间隔: {frame_interval*1000:.2f} ms ({fps} FPS)")
    print(f"  预计时长: {total_duration:.2f} 秒")
    
    if step_mode:
        print(f"  模式: 步进模式（每帧按回车继续）")
        print(f"  命令: 回车=下一帧, c=连续播放, q=退出")
    else:
        print(f"  模式: 连续播放")
        print(f"  按 Ctrl+C 停止")
    print()
    
    # 回放统计
    continuous = False
    frame_count = 0
    actual_intervals = []
    delayed_frames = 0
    replay_start = time.time()
    
    try:
        for idx in range(start_idx, end_idx):
            frame_num = idx - start_idx + 1
            loop_start = time.perf_counter()
            
            # 步进模式：等待用户输入
            if step_mode and not continuous:
                prompt = f"帧 {frame_num}/{total_frames} - 按回车继续, c=连续, q=退出: "
                user_input = input(prompt).strip().lower()
                
                if user_input == 'q':
                    print("用户退出回放")
                    break
                elif user_input == 'c':
                    continuous = True
                    print("切换到连续播放模式...")
            
            # 获取动作
            frame_data = dataset[idx]
            action_tensor = torch.as_tensor(frame_data["action"])
            
            # 构建动作字典
            action = {}
            for i in range(16):
                action[f"action.joint_{i}_pos"] = float(action_tensor[i])
            
            # 发送动作（MoveJ，时间=帧间隔）
            robot.send_action_movej(action, move_time=frame_interval)
            
            frame_count += 1
            
            # 精确等待到下一帧（减去发送耗时）
            elapsed = time.perf_counter() - loop_start
            sleep_time = frame_interval - elapsed
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                delayed_frames += 1
                if frame_num % 30 == 0:  # 每30帧警告一次避免刷屏
                    print(f"  警告: 帧 {frame_num} 发送延迟 {-sleep_time*1000:.1f} ms")
            
            actual_intervals.append(time.perf_counter() - loop_start)
            
            # 进度显示
            if not step_mode or continuous:
                if frame_num % 30 == 0 or frame_num == total_frames:
                    progress = frame_num / total_frames * 100
                    elapsed_total = time.time() - replay_start
                    print(f"  进度: {frame_num}/{total_frames} ({progress:.1f}%) | "
                          f"已用: {elapsed_total:.1f}s")
                
    except KeyboardInterrupt:
        print("\n用户中断回放")
    
    # 统计信息
    actual_duration = time.time() - replay_start
    print(f"\n{'='*60}")
    print("回放统计")
    print(f"{'='*60}")
    print(f"  计划帧数: {total_frames}")
    print(f"  实际发送: {frame_count}")
    print(f"  计划时长: {total_duration:.2f} 秒")
    print(f"  实际时长: {actual_duration:.2f} 秒")
    if actual_intervals:
        print(f"  平均间隔: {np.mean(actual_intervals)*1000:.2f} ms (目标: {frame_interval*1000:.2f} ms)")
        print(f"  间隔标准差: {np.std(actual_intervals)*1000:.2f} ms")
        print(f"  延迟帧数: {delayed_frames}/{frame_count} ({100*delayed_frames/max(frame_count,1):.1f}%)")
    print(f"{'='*60}")


def parse_joint_list(value):
    """解析关节角度列表 'j0,j1,j2,...' 或 '[j0,j1,j2,...]'"""
    if value.startswith('[') and value.endswith(']'):
        value = value[1:-1]
    return [float(x.strip()) for x in value.split(',')]


def main():
    parser = argparse.ArgumentParser(description="Tron2 回放 - 带初始过渡")
    parser.add_argument("--robot_ip", type=str, default="10.192.1.2", help="机器人 IP")
    parser.add_argument("--dataset_root", type=str, required=True, help="数据集根目录")
    parser.add_argument("--repo_id", type=str, required=True, help="数据集 repo_id")
    parser.add_argument("--episode", type=int, default=0, help="回放 episode 编号")
    
    # 初始位置参数
    parser.add_argument("--side_pos", type=parse_joint_list, default=None,
                        help="过渡位置关节角度 (16个值, 逗号分隔, 如 '0.1,0.4,0.7,...')")
    parser.add_argument("--start_pos", type=parse_joint_list, default=None,
                        help="起始位置关节角度 (16个值, 逗号分隔)")
    
    # 模式控制参数
    parser.add_argument("--skip_init", action="store_true",
                        help="跳过初始的两段位置过渡，直接在当前位置开始回放（注意安全！）")
    
    # 时间参数
    parser.add_argument("--side_time", type=float, default=3.0, help="到过渡位置的时间(秒), 默认3秒")
    parser.add_argument("--start_time", type=float, default=3.0, help="到起始位置的时间(秒), 默认3秒")
    parser.add_argument("--fps", type=float, default=30.0, help="回放帧率")
    
    # 步进模式
    parser.add_argument("--step_mode", action="store_true",
                        help="步进模式：每帧动作需按回车确认")
    args = parser.parse_args()
    
    # 使用命令行参数或默认值
    side_position = args.side_pos if args.side_pos else DEFAULT_SIDE_POSITION
    start_position = args.start_pos if args.start_pos else DEFAULT_START_POSITION
    
    print("=" * 60)
    print("Tron2 回放脚本 - 带初始位置过渡")
    print("=" * 60)
    
    # 连接机器人
    print(f"\n[1/4] 连接机器人 {args.robot_ip}...")
    config = Tron2RobotConfig(robot_ip=args.robot_ip)
    robot = Tron2Robot(config=config)
    robot.connect()
    print("机器人连接成功！")
    
    # 等待状态稳定
    time.sleep(1.0)
    
    # 加载数据集
    print(f"\n[2/4] 加载数据集 {args.repo_id}...")
    dataset = LeRobotDataset(
        repo_id=args.repo_id,
        root=args.dataset_root,
    )
    print(f"数据集加载成功: {len(dataset)} 帧")
    
    if not args.skip_init:
        # 阶段1: 运动到 side_position
        print(f"\n[3/4] 阶段1: 运动到过渡位置...")
        print(f"  目标: 两臂展开，避开桌子")
        print(f"  运动时间: {args.side_time} 秒")
        print(f"  目标角度: {[round(x, 3) for x in side_position]}")
        input("  按回车开始...")
        move_to_position(robot, side_position, args.side_time)
        
        # 阶段2: 运动到 start_position
        print(f"\n[4/4] 阶段2: 运动到回放起始位置...")
        print(f"  目标: 双臂前伸")
        print(f"  运动时间: {args.start_time} 秒")
        print(f"  目标角度: {[round(x, 3) for x in start_position]}")
        input("  按回车开始...")
        move_to_position(robot, start_position, args.start_time)
    else:
        print(f"\n[3/4] 跳过初始位置过渡 (--skip_init 已启用)")
        print(f"  警告: 机器人将直接从当前位置移动到数据集的第一帧位置，请注意安全！")
    
    # 阶段3: 开始回放
    print(f"\n准备就绪！")
    if args.step_mode:
        print("步进模式已启用：每帧动作需按回车确认")
        print("命令: 回车=下一帧, c=连续播放, q=退出")
    input("按回车开始回放数据集...")
    replay_episode(robot, dataset, args.episode, args.fps, step_mode=args.step_mode)
    
    print("\n回放完成！断开连接...")
    robot.disconnect()
    print("完成！")


if __name__ == "__main__":
    main()
