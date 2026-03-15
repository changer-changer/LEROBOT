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
记录数据集，支持手动键盘控制开始/停止/丢弃

控制方式:
    - 按 'S': 开始录制当前 episode
    - 按 'Space': 停止并保存当前 episode
    - 按 'Backspace' 或 'L': 停止并丢弃当前 episode
    - 按 'ESC': 退出脚本

示例:
    python src/lerobot/scripts/lerobot_record_manual.py \\
        --robot.type=tron2 \\
        --robot.robot_ip="10.192.1.2" \\
        --dataset.repo_id=my_username/my_dataset \\
        --dataset.single_task="Pick up the ball"
"""

import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pprint import pformat
from typing import Any

from lerobot.cameras import CameraConfig
from lerobot.cameras.ros2.configs import ROS2CameraConfig
from lerobot.tactile.configs import Tac3DSensorConfig
from lerobot.robots.tron2.tron2_config import Tron2RobotConfig
from lerobot.configs import parser
from lerobot.configs.policies import PreTrainedConfig
from lerobot.datasets.image_writer import safe_stop_image_writer
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.datasets.pipeline_features import aggregate_pipeline_dataset_features, create_initial_features
from lerobot.datasets.utils import build_dataset_frame, combine_feature_dicts
from lerobot.datasets.video_utils import VideoEncodingManager
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.policies.pretrained import PreTrainedPolicy
from lerobot.policies.utils import make_robot_action
from lerobot.processor import (
    PolicyAction,
    PolicyProcessorPipeline,
    RobotAction,
    RobotObservation,
    RobotProcessorPipeline,
    make_default_processors,
)
from lerobot.processor.rename_processor import rename_stats
from lerobot.robots import Robot, RobotConfig, make_robot_from_config
from lerobot.teleoperators import Teleoperator, TeleoperatorConfig, make_teleoperator_from_config
from lerobot.utils.constants import ACTION, OBS_STR
from lerobot.utils.control_utils import (
    init_keyboard_listener,
    is_headless,
    predict_action,
    sanity_check_dataset_name,
    sanity_check_dataset_robot_compatibility,
)
from lerobot.utils.import_utils import register_third_party_plugins
from lerobot.utils.robot_utils import busy_wait, precise_sleep
from lerobot.utils.utils import get_safe_torch_device, init_logging, log_say
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data


@dataclass
class DatasetRecordConfig:
    """数据集录制配置"""
    repo_id: str
    single_task: str
    root: str | Path | None = None
    fps: int = 30
    episode_time_s: int | float = 60  # 默认60秒，防止内存爆炸
    reset_time_s: int | float = 15
    num_episodes: int = 50
    video: bool = True
    push_to_hub: bool = False
    private: bool = False
    tags: list[str] | None = None
    num_image_writer_processes: int = 0
    num_image_writer_threads_per_camera: int = 4
    video_encoding_batch_size: int = 1
    # Video codec for encoding videos. Options: 'h264', 'hevc', 'libsvtav1', 'auto',
    # or hardware-specific: 'h264_videotoolbox', 'h264_nvenc', 'h264_vaapi', 'h264_qsv'.
    vcodec: str = "libsvtav1"
    # Enable streaming video encoding: encode frames in real-time during capture
    streaming_encoding: bool = False
    # Maximum number of frames to buffer per camera when using streaming encoding.
    encoder_queue_maxsize: int = 30
    # Number of threads per encoder instance. None = auto (codec default).
    encoder_threads: int | None = None
    rename_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.single_task is None:
            raise ValueError("必须提供 `single_task` 参数描述任务")


@dataclass
class ManualRecordConfig:
    """手动录制配置"""
    robot: RobotConfig
    dataset: DatasetRecordConfig = field(default_factory=lambda: DatasetRecordConfig(
        repo_id="placeholder",
        single_task="placeholder",
        fps=30,
        episode_time_s=60,  # 限制单个episode时长防止内存问题
    ))
    teleop: TeleoperatorConfig | None = None
    policy: PreTrainedConfig | None = None
    display_data: bool = False
    play_sounds: bool = True
    resume: bool = False
    display_ip: str | None = None
    display_port: int | None = None
    display_compressed_images: bool = False

    def __post_init__(self):
        policy_path = parser.get_path_arg("policy")
        if policy_path:
            cli_overrides = parser.get_cli_overrides("policy")
            self.policy = PreTrainedConfig.from_pretrained(policy_path, cli_overrides=cli_overrides)
            self.policy.pretrained_path = policy_path


@safe_stop_image_writer
def manual_record_loop(
    robot: Robot,
    dataset: LeRobotDataset,
    events: dict,
    fps: int,
    teleop_action_processor: RobotProcessorPipeline,
    robot_action_processor: RobotProcessorPipeline,
    robot_observation_processor: RobotProcessorPipeline,
    teleop: Teleoperator | None = None,
    policy: PreTrainedPolicy | None = None,
    preprocessor: PolicyProcessorPipeline | None = None,
    postprocessor: PolicyProcessorPipeline | None = None,
    control_time_s: float = 60,
    single_task: str | None = None,
    display_data: bool = False,
    display_compressed_images: bool = False,
):
    """
    手动录制循环 - 简化版本，参考师兄的 lerobot_record_vr.py
    """
    if policy is not None and preprocessor is not None and postprocessor is not None:
        policy.reset()
        preprocessor.reset()
        postprocessor.reset()

    timestamp = 0
    start_episode_t = time.perf_counter()
    logging.info(
        "开始录制: control_time_s=%s, fps=%s",
        control_time_s,
        fps,
    )
    
    while timestamp < control_time_s:
        start_loop_t = time.perf_counter()

        # 检查退出信号
        if events.get("exit_early", False):
            events["exit_early"] = False
            break

        # 获取机器人观测 - 使用无阻塞观测，保证循环严格贴合fps
        try:
            obs = robot.get_observation()
        except Exception as e:
            logging.warning(f"获取观测失败: {e}，重试...")
            continue

        # 处理观测
        obs_processed = robot_observation_processor(obs)
        observation_frame = build_dataset_frame(dataset.features, obs_processed, prefix=OBS_STR)

        # 获取动作（来自 policy 或 teleop）
        action_values = None
        
        if policy is not None and preprocessor is not None and postprocessor is not None:
            # Policy 模式
            action_values_raw = predict_action(
                observation=observation_frame,
                policy=policy,
                device=get_safe_torch_device(policy.config.device),
                preprocessor=preprocessor,
                postprocessor=postprocessor,
                use_amp=policy.config.use_amp,
                task=single_task,
                robot_type=robot.robot_type,
            )
            action_values = make_robot_action(action_values_raw, dataset.features)
            robot_action_to_send = robot_action_processor((action_values, obs))
            robot.send_action(robot_action_to_send)
            
        elif teleop is not None:
            # Teleop 模式
            act = teleop.get_action()
            action_values = teleop_action_processor((act, obs))
            robot_action_to_send = robot_action_processor((action_values, obs))
            robot.send_action(robot_action_to_send)
            
        else:
            # 手动模式：使用当前观测作为动作（记录状态）
            action_values = obs
            # 不发送动作，仅记录

        # 写入数据集 - 关键：使用 LeRobot 原生的 add_frame
        try:
            action_frame = build_dataset_frame(dataset.features, action_values, prefix=ACTION)
            frame = {**observation_frame, **action_frame, "task": single_task}
            dataset.add_frame(frame)
        except Exception as e:
            logging.error(f"添加帧到数据集失败: {e}")
            print(f"\n[错误] 帧捕获失败: {e}")
            events["exit_early"] = True
            break

        # 显示数据（可选）
        if display_data:
            log_rerun_data(
                observation=obs_processed, 
                action=action_values, 
                compress_images=display_compressed_images
            )

        # 精确时间控制
        dt_s = time.perf_counter() - start_loop_t
        sleep_time_s = max(0, 1 / fps - dt_s)
        busy_wait(sleep_time_s)
        
        timestamp = time.perf_counter() - start_episode_t
        
        # 每秒打印一次状态
        frames_recorded = dataset.episode_buffer["size"] if dataset.episode_buffer else 0
        if frames_recorded > 0 and frames_recorded % max(1, int(fps)) == 0:
            print(f"  > 已录制: {frames_recorded} 帧", end="\r", flush=True)
    
    print()  # 换行
    logging.info(f"录制结束，共 {dataset.episode_buffer['size'] if dataset.episode_buffer else 0} 帧")


@parser.wrap()
def record(cfg: ManualRecordConfig) -> LeRobotDataset:
    """主录制函数"""
    init_logging()
    logging.info(pformat(asdict(cfg)))
    
    if cfg.display_data:
        init_rerun(session_name="recording")

    # 创建机器人和遥操作器
    robot = make_robot_from_config(cfg.robot)
    teleop = make_teleoperator_from_config(cfg.teleop) if cfg.teleop is not None else None

    # 创建处理器
    teleop_action_processor, robot_action_processor, robot_observation_processor = make_default_processors()

    # 组合数据集特征
    dataset_features = combine_feature_dicts(
        aggregate_pipeline_dataset_features(
            pipeline=teleop_action_processor,
            initial_features=create_initial_features(action=robot.action_features),
            use_videos=cfg.dataset.video,
        ),
        aggregate_pipeline_dataset_features(
            pipeline=robot_observation_processor,
            initial_features=create_initial_features(observation=robot.observation_features),
            use_videos=cfg.dataset.video,
        ),
    )

    dataset = None
    listener = None
    dataset_path = Path(cfg.dataset.root) if cfg.dataset.root else Path("data") / cfg.dataset.repo_id
    
    # 警告：streaming_encoding 可能影响视频质量
    if cfg.dataset.streaming_encoding:
        print("\n⚠️  WARNING: streaming_encoding=true 可能导致视频质量下降")
        print("   如需高质量视频，建议移除 --dataset.streaming_encoding 参数")
        print("   师兄版本使用默认设置 (streaming_encoding=false)\n")
        time.sleep(2)

    try:
        # 恢复或创建数据集
        if cfg.resume:
            if not dataset_path.exists():
                raise ValueError(f"无法恢复: {dataset_path} 不存在")
            
            dataset = LeRobotDataset(
                cfg.dataset.repo_id,
                root=cfg.dataset.root,
                batch_encoding_size=cfg.dataset.video_encoding_batch_size,
                vcodec=cfg.dataset.vcodec,
                streaming_encoding=cfg.dataset.streaming_encoding,
                encoder_queue_maxsize=cfg.dataset.encoder_queue_maxsize,
                encoder_threads=cfg.dataset.encoder_threads,
            )
            logging.info(f"从 episode {dataset.num_episodes} 恢复录制")
            
            if hasattr(robot, "cameras") and len(robot.cameras) > 0:
                dataset.start_image_writer(
                    num_processes=cfg.dataset.num_image_writer_processes,
                    num_threads=cfg.dataset.num_image_writer_threads_per_camera * len(robot.cameras),
                )
            sanity_check_dataset_robot_compatibility(dataset, robot, cfg.dataset.fps, dataset_features)
        else:
            if dataset_path.exists():
                print("\n" + "!" * 80)
                print(f"错误: 目录 {dataset_path} 已存在")
                print("请使用 '--resume=true' 追加到现有数据集，或删除该目录")
                print("!" * 80 + "\n")
                return

            sanity_check_dataset_name(cfg.dataset.repo_id, cfg.policy)
            dataset = LeRobotDataset.create(
                cfg.dataset.repo_id,
                cfg.dataset.fps,
                root=cfg.dataset.root,
                robot_type=robot.name,
                features=dataset_features,
                use_videos=cfg.dataset.video,
                image_writer_processes=cfg.dataset.num_image_writer_processes,
                image_writer_threads=cfg.dataset.num_image_writer_threads_per_camera * len(robot.cameras),
                batch_encoding_size=cfg.dataset.video_encoding_batch_size,
                vcodec=cfg.dataset.vcodec,
                streaming_encoding=cfg.dataset.streaming_encoding,
                encoder_queue_maxsize=cfg.dataset.encoder_queue_maxsize,
                encoder_threads=cfg.dataset.encoder_threads,
            )

        # 加载策略（如果有）
        policy = None if cfg.policy is None else make_policy(cfg.policy, ds_meta=dataset.meta)
        preprocessor = None
        postprocessor = None
        if cfg.policy is not None:
            preprocessor, postprocessor = make_pre_post_processors(
                policy_cfg=cfg.policy,
                pretrained_path=cfg.policy.pretrained_path,
                dataset_stats=rename_stats(dataset.meta.stats, cfg.dataset.rename_map),
                preprocessor_overrides={
                    "device_processor": {"device": cfg.policy.device},
                    "rename_observations_processor": {"rename_map": cfg.dataset.rename_map},
                },
            )

        # 连接设备
        try:
            robot.connect()
        except Exception as e:
            logging.error(f"无法连接到机器人: {e}")
            print(f"\n❌ 无法连接到机器人: {e}")
            print("请检查:")
            print("  1. 机器人是否已开机")
            print("  2. 网络连接是否正常 (ping 10.192.1.2)")
            print("  3. 机器人IP地址是否正确")
            return
            
        if teleop is not None:
            try:
                teleop.connect()
            except Exception as e:
                logging.error(f"无法连接到遥操作器: {e}")
                print(f"\n❌ 无法连接到遥操作器: {e}")
                robot.disconnect()
                return

        # 相机预热
        warmup_cameras(robot, duration_s=1.5)

        # 初始化键盘监听
        listener, events = init_keyboard_listener()

        print("\n" + "="*50)
        print("  手动录制脚本已加载")
        print("  控制方式:")
        print("    - 按 'S'      : 开始录制")
        print("    - 按 'Space'  : 保存 episode")
        print("    - 按 'BKSPC'  : 丢弃 episode")
        print("    - 按 'ESC'    : 退出")
        print("="*50 + "\n")

        # 录制循环
        with VideoEncodingManager(dataset):
            while dataset.num_episodes < cfg.dataset.num_episodes and not events["stop_recording"]:
                
                print(f"\n--- [Episode {dataset.num_episodes + 1}/{cfg.dataset.num_episodes}] ---")
                print("等待按 'S' 开始录制...")
                
                # 等待开始信号
                while not events["start_episode"]:
                    if events["stop_recording"]:
                        break
                    time.sleep(0.05)
                
                if events["stop_recording"]:
                    break
                
                events["start_episode"] = False
                events["exit_early"] = False
                events["discard_episode"] = False

                # 确保在开始新episode之前彻底清空buffer，防止旧帧拼接到新episode中
                if dataset.episode_buffer:
                    dataset.clear_episode_buffer()

                log_say(f"开始录制 episode {dataset.num_episodes + 1}", cfg.play_sounds)
                print("录制中... (按 Space 保存，BKSPC 丢弃)")

                try:
                    manual_record_loop(
                        robot=robot,
                        dataset=dataset,
                        events=events,
                        fps=cfg.dataset.fps,
                        teleop_action_processor=teleop_action_processor,
                        robot_action_processor=robot_action_processor,
                        robot_observation_processor=robot_observation_processor,
                        teleop=teleop,
                        policy=policy,
                        preprocessor=preprocessor,
                        postprocessor=postprocessor,
                        control_time_s=cfg.dataset.episode_time_s,
                        single_task=cfg.dataset.single_task,
                        display_data=cfg.display_data,
                        display_compressed_images=cfg.display_compressed_images,
                    )
                except KeyboardInterrupt:
                    events["stop_recording"] = True
                    break

                if events["stop_recording"]:
                    break

                # 处理录制结果
                print(f"\n[DEBUG] 录制结束，当前 episode_buffer size: {dataset.episode_buffer.get('size', 0) if dataset.episode_buffer else 0}")
                print(f"[DEBUG] discard_episode: {events.get('discard_episode', False)}")
                
                if events.get("discard_episode", False):
                    print("\n🗑️ 丢弃当前 episode...")
                    logging.warning(f"用户丢弃 episode {dataset.num_episodes + 1}")
                    buffer_size = dataset.episode_buffer.get('size', 0) if dataset.episode_buffer else 0
                    dataset.clear_episode_buffer()
                    print(f"✅ 已清空 buffer (原 {buffer_size} 帧)")
                    events["discard_episode"] = False
                    
                elif dataset.episode_buffer and dataset.episode_buffer["size"] > 0:
                    # 保存 episode - 使用 LeRobot 原生方法
                    episode_idx = dataset.num_episodes
                    buffer_size = dataset.episode_buffer["size"]
                    print(f"\n💾 保存 episode {episode_idx + 1} (buffer 中有 {buffer_size} 帧)...")
                    try:
                        dataset.save_episode()
                        print(f"✅ 已保存 episode {episode_idx + 1} -> 现在共有 {dataset.num_episodes} 个 episodes")
                        log_say("Episode 已保存", cfg.play_sounds)
                    except Exception as e:
                        logging.error(f"保存 episode 失败: {e}")
                        print(f"❌ 保存失败: {e}")
                else:
                    print("\n⚠️ episode_buffer 为空，没有数据可保存")

    except KeyboardInterrupt:
        print("\n用户中断 (Ctrl+C)")
    finally:
        log_say("停止录制", cfg.play_sounds, blocking=True)
        
        if listener and not is_headless():
            listener.stop()

        if dataset:
            dataset.finalize()
            if cfg.dataset.push_to_hub:
                try:
                    dataset.push_to_hub(tags=cfg.dataset.tags, private=cfg.dataset.private)
                except Exception as e:
                    logging.error(f"推送到 HuggingFace Hub 失败: {e}")

        if robot.is_connected:
            robot.disconnect()
        if teleop and teleop.is_connected:
            teleop.disconnect()

        print("\n机器人已断开连接 ✅")
        log_say("退出", cfg.play_sounds)

    return dataset


def warmup_cameras(robot, duration_s: float = 1.5) -> None:
    """相机预热 - 从师兄版本复制"""
    cams = getattr(robot, "cameras", None)
    if not cams:
        return

    try:
        if hasattr(cams, "items"):
            cam_items = list(cams.items())
            cam_names = [k for k, _ in cam_items]
            cam_list = [v for _, v in cam_items]
        else:
            cam_list = list(cams)
            cam_names = [str(i) for i in range(len(cam_list))]
    except Exception:
        cam_list = cams
        cam_names = None

    logging.info(f"Warming up {len(cam_list)} camera(s) for {duration_s}s")
    start = time.perf_counter()

    if cam_names is not None:
        success_counts = {name: 0 for name in cam_names}
    else:
        success_counts = {i: 0 for i in range(len(cam_list))}

    while time.perf_counter() - start < duration_s:
        for i, c in enumerate(cam_list):
            name = cam_names[i] if cam_names is not None else i
            try:
                if hasattr(c, "async_read"):
                    try:
                        c.async_read(timeout_ms=500)
                    except Exception:
                        continue
                    else:
                        success_counts[name] += 1
                else:
                    frame = c.read()
                    if frame is not None:
                        success_counts[name] += 1
            except Exception as e:
                logging.debug(f"Camera warmup read error for camera {name}: {e}")
                continue
        time.sleep(0.02)

    failed = [n for n, cnt in success_counts.items() if cnt == 0]
    if failed:
        logging.warning(
            "Camera warmup: some cameras had no successful reads during warmup: %s. Success counts: %s",
            failed,
            success_counts,
        )
    else:
        logging.info(f"Camera warmup successful. Success counts: {success_counts}")


def main():
    register_third_party_plugins()
    record()


if __name__ == "__main__":
    main()
