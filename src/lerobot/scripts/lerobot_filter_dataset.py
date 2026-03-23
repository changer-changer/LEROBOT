#!/usr/bin/env python3

"""
高维/复杂传感器数据集专用过滤脚本 (搬运法)

由于官方的 lerobot_edit_dataset.py 使用 pandas 会导致高维特征（如 Tac3D 的 400x6 矩阵、点云等）切片报错。
本脚本采用“安全搬运”模式：
逐帧读取原数据集，跳过不需要的 episodes，并将其写入新的数据集中。这能保证：
1. 规避所有 pandas 的底层类型报错。
2. 自动完美对齐底层 Parquet 数据和视频帧。
3. 视频会被自动重新压制，不会出现音画/数据不同步。

使用示例:
    python src/lerobot/scripts/lerobot_filter_dataset.py \
        --repo_id="deeptouchczx/tron2_peg_in_hole_cuboid3" \
        --root="/home/cuizhixing/data/outputs/start2026.3.22/tron2_peg_in_hole_cuboid3" \
        --exclude_episodes 1 3 \
        --new_repo_id="deeptouchczx/tron2_peg_in_hole_cuboid3_filtered" \
        --new_root="/home/cuizhixing/data/outputs/start2026.3.22/tron2_peg_in_hole_cuboid3_filtered"
"""

import argparse
import logging
import time
from pathlib import Path
from tqdm import tqdm
import torch

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.datasets.video_utils import VideoEncodingManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Filter out bad episodes from a LeRobot dataset containing high-dimensional data.")
    parser.add_argument("--repo_id", type=str, required=True, help="原数据集的 repo_id")
    parser.add_argument("--root", type=str, required=True, help="原数据集的本地绝对路径")
    parser.add_argument("--exclude_episodes", type=int, nargs='+', required=True, help="要剔除的 episode 索引列表 (例如: 1 3)")
    parser.add_argument("--new_repo_id", type=str, required=True, help="新数据集的 repo_id")
    parser.add_argument("--new_root", type=str, required=True, help="新数据集的本地绝对路径")
    
    args = parser.parse_args()
    
    exclude_set = set(args.exclude_episodes)
    logger.info(f"准备过滤数据集: {args.repo_id}")
    logger.info(f"计划剔除的 episodes: {exclude_set}")
    
    new_root_path = Path(args.new_root)
    if new_root_path.exists():
        logger.error(f"目标路径 {args.new_root} 已经存在！请先删除或指定新的路径。")
        return

    # 1. 加载原数据集
    logger.info("正在加载原数据集...")
    import os
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    src_dataset = LeRobotDataset(args.repo_id, root=args.root)
    total_episodes = src_dataset.num_episodes
    
    if max(exclude_set) >= total_episodes:
        logger.error(f"指定的剔除索引 {max(exclude_set)} 超出了数据集最大 episode 数量 ({total_episodes})！")
        return

    # 2. 准备新数据集 (克隆原数据集的特征配置)
    logger.info(f"正在创建新数据集: {args.new_repo_id} 于 {args.new_root}")
    
    # 获取原始数据集的特征字典
    features = src_dataset.features.copy()
    
    # 检查原始数据集是否使用了视频压缩
    use_videos = False
    for feat_name, feat_info in features.items():
        if feat_info.get("dtype") == "video":
            use_videos = True
            break
            
    dst_dataset = LeRobotDataset.create(
        repo_id=args.new_repo_id,
        fps=src_dataset.fps,
        root=args.new_root,
        robot_type=src_dataset.meta.robot_type,
        features=features,
        use_videos=use_videos,
        # 保持与原始配置兼容的视频编码设置
        image_writer_threads=12,
        image_writer_processes=0,
    )

    # 3. 开始搬运数据
    logger.info("开始搬运数据，请耐心等待 (视频会自动重新压制)...")
    start_time = time.time()
    
    # 获取原始任务名称
    task_name = src_dataset.meta.tasks.iloc[0].name if src_dataset.meta.tasks is not None and len(src_dataset.meta.tasks) > 0 else "default_task"
    
    with VideoEncodingManager(dst_dataset):
        for ep_idx in tqdm(range(total_episodes), desc="Episodes processing"):
            if ep_idx in exclude_set:
                logger.info(f" -> 跳过 Episode {ep_idx}")
                continue
                
            # 确定这一集的帧范围
            ep_dict = src_dataset.meta.episodes[ep_idx]
            if "frame_index" in ep_dict:
                start_frame = ep_dict["frame_index"][0]
                end_frame = ep_dict["frame_index"][1]
            elif "episode_frame_index" in ep_dict:
                start_frame = ep_dict["episode_frame_index"][0]
                end_frame = ep_dict["episode_frame_index"][1]
            elif "episode_data_index" in ep_dict:
                # 兼容不同版本的 LeRobot
                start_frame = ep_dict["episode_data_index"]["from"]
                end_frame = ep_dict["episode_data_index"]["to"]
            else:
                # 如果都没有，根据 fps 和 length 估算
                logger.error(f"Cannot find frame range in episode dict: {ep_dict.keys()}")
                break
            
            logger.info(f" -> 正在搬运 Episode {ep_idx} (共 {end_frame - start_frame} 帧)")
            
            # 确保 buffer 是空的
            if dst_dataset.episode_buffer:
                dst_dataset.clear_episode_buffer()
                
            # 逐帧读取并写入
            for frame_idx in range(start_frame, end_frame):
                # 从原数据集读取这一帧
                frame = src_dataset[frame_idx]
                
                # LeRobotDataset 返回的往往是 Torch Tensor，且带有批量维度或者需要转回 numpy
                # 我们需要将其清洗为 add_frame 接受的干净字典
                clean_frame = {"task": task_name}
                
                for k, v in frame.items():
                    if k in ["index", "episode_index", "frame_index", "timestamp", "task_index"]:
                        continue # 这些元数据 add_frame 会自动生成
                    
                    if isinstance(v, torch.Tensor):
                        # 降维：LeRobot __getitem__ 有时会返回 (1, ...) 的 tensor
                        val = v.squeeze(0).numpy() if v.ndim > 0 and v.shape[0] == 1 else v.numpy()
                    else:
                        val = v
                        
                    clean_frame[k] = val
                
                # 写入新数据集的 buffer
                dst_dataset.add_frame(clean_frame)
                
            # 保存这一集
            dst_dataset.save_episode()
            
    # 4. 收尾
    dst_dataset.finalize()
    elapsed = time.time() - start_time
    logger.info(f"✅ 搬运完成！耗时: {elapsed:.2f} 秒")
    logger.info(f"原数据集 episodes: {total_episodes}")
    logger.info(f"新数据集 episodes: {dst_dataset.num_episodes}")
    logger.info(f"新数据集已保存在: {args.new_root}")

if __name__ == "__main__":
    main()
