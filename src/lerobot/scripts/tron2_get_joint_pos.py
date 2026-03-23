#!/usr/bin/env python3
"""
获取 Tron2 机器人当前关节位置

Usage:
    python src/lerobot/scripts/tron2_get_joint_pos.py \
        --robot_ip="10.192.1.2" \
        --name="side_position"
"""

import argparse
import sys
import time

sys.path.insert(0, "/media/cuizhixing/share/workspace/multiversion_lerobot/lerobot_integrated/src")

from lerobot.robots.tron2.tron2_robot import Tron2Robot
from lerobot.robots.tron2.tron2_config import Tron2RobotConfig


def main():
    parser = argparse.ArgumentParser(description="获取 Tron2 关节位置")
    parser.add_argument("--robot_ip", type=str, default="10.192.1.2", help="机器人 IP")
    parser.add_argument("--name", type=str, default="position", help="位置名称标记")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"获取 Tron2 关节位置 - {args.name}")
    print(f"{'='*60}")
    
    # 创建配置并连接
    config = Tron2RobotConfig(robot_ip=args.robot_ip)
    robot = Tron2Robot(config=config)
    print(f"连接机器人 {args.robot_ip}...")
    robot.connect()
    print("连接成功！\n")
    
    # 等待状态更新
    time.sleep(1.0)
    
    # 获取关节位置
    obs = robot.get_observation()
    if hasattr(obs, 'joint_positions'):
        joint_pos = obs.joint_positions.tolist()
    elif isinstance(obs, dict) and 'joint_positions' in obs:
        joint_pos = list(obs['joint_positions'])
    else:
        joint_pos = robot._q.tolist() if hasattr(robot, '_q') else []
    
    robot.disconnect()
    
    # 格式化输出
    print(f"关节数量: {len(joint_pos)}")
    print(f"\n关节角度（弧度）:")
    print(f"  左臂 (j0-j6):  {[round(j, 4) for j in joint_pos[0:7]]}")
    print(f"  右臂 (j7-j13): {[round(j, 4) for j in joint_pos[7:14]]}")
    print(f"  左夹爪: {round(joint_pos[14], 4) if len(joint_pos) > 14 else 'N/A'}")
    print(f"  右夹爪: {round(joint_pos[15], 4) if len(joint_pos) > 15 else 'N/A'}")
    
    print(f"\n{'='*60}")
    print("Python 代码格式（复制给我）:")
    print(f"{'='*60}")
    print(f"{args.name} = {joint_pos}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
