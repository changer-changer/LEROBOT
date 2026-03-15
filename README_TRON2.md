# Tron2 Integrated System Usage Guide (RGB + Tac3D + Joints)

This guide provides the necessary commands for data recording, dataset playback, model training, and inference using the integrated Tron2 system.

## 1. Data Recording (Manual Control)

We provide a specialized script `lerobot_record_manual.py` that allows you to control the recording workflow using your keyboard.

### Key Controls:
- **Press `S`**: START recording an episode.
- **Press `SPACE`**: STOP and **SAVE** the current episode.
- **Press `Backspace` or `L`**: STOP and **DISCARD (Trash)** the episode (useful for failed trials).
- **Press `ESC`**: Quit the recording session.

### Command Line:
Run the following command in your Conda environment (ensure ROS2 is sourced):

```bash
# 进入环境并 Source ROS2
conda activate lerobot
source /opt/ros/humble/setup.bash

# 开启手动录制
python src/lerobot/scripts/lerobot_record_tron2.py \
    --robot.type=tron2 \
    --robot.robot_ip="10.192.1.2" \
    --robot.cameras='{
        "left_rgb": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw", "fps": 30, "width": 640, "height": 480 },
        "right_rgb": {"type": "ros2", "topic": "/camera/right/color/image_rect_raw", "fps": 30, "width": 640, "height": 480}
    }' \
    --robot.tactile_sensors='{
        "tac3d_sensor": {"type": "tac3d", "udp_port": 9988}
    }' \
    --dataset.repo_id="deeptouch/tron2_tactile_test" \
    --dataset.root="/home/cuizhixing/data/outputs/recordings/tron2_final" \
    --dataset.fps=30 \
    --dataset.single_task="Pick up the objects" \
    --dataset.video=true \
    --dataset.streaming_encoding=false \
    --dataset.vcodec=h264 \
    --display_data=true


```

- **--robot.cameras**: 配置相机参数。注意 `width` 和 `height` 是**最终存储与训练的像素尺寸**。默认已设为 `128x128` 以节省内存（即使物理相机是 640x480，系统也会自动在内存中完成缩放再存储）。
- **--dataset.streaming_encoding**: 开启流式编码，减少内存峰值压力。
- **--dataset.fps**: 数采频率，建议 10-30。

---

## 2. Dataset Replay

To verify the recorded data (RGB videos, tactile signals, and joints), use the replay script:

```bash

  python src/lerobot/scripts/lerobot_replay_tron2_with_init.
  py \
      --robot_ip="10.192.1.2" \
      --dataset_root="/home/cuizhixing/data/outputs/recordin
  gs/tron2_final" \
      --repo_id="deeptouch/tron2_tactile_test" \
      --episode=0 \
      --side_time=3.0 \
      --start_time=3.0 \
      --side_pos="0.0849,0.4159,0.6814,-1.1422,0.3621,-0.147
  3,0.4774,-0.1292,-0.5084,-0.7813,-0.6478,-0.4898,-0.4773,-
  0.4136,2.0,2.0" \
      --start_pos="0.0199,0.2429,-0.004,-1.552,0.237,0.0018,
  -0.001,0.0136,-0.2408,0.0046,-1.5502,-0.2359,0.0051,0.0004
  ,2.0,2.0"
```


lerobot_replay_tron2_with_init.py 参数列表

  连接参数

   参数         类型   默认值         必填   描述
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   --robot_ip   str    "10.192.1.2"   否     机器人 WebSock
                                             et IP 地址。真
                                             机使用 10.192.
                                             1.2，仿真使用
                                             127.0.0.1

  数据集参数

   参数             类型   默认值   必填   描述
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   --dataset_root   str    -        是     数据集根目录路径
                                           。例如："/home/c
                                           uizhixing/data/o
                                           utputs/recording
                                           s/tron2_final"
   --repo_id        str    -        是     数据集名称/标识
                                           符。例如："deept
                                           ouch/tron2_tacti
                                           le_test"
   --episode        int    0        否     要回放的 episod…
                                           编号，从 0 开始

  初始位置参数

   参数          类型          默认值   必填   描述
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   --side_pos    list[float]   预设值   否     过渡位置关节
                                               角度，16 个
                                               值用逗号分隔
                                               。机器人先运
                                               动到此位置（
                                               两臂展开，避
                                               开桌子）
   --start_pos   list[float]   预设值   否     起始位置关节
                                               角度，16 个
                                               值用逗号分隔
                                               。最终回放起
                                               始位置（双臂
                                               前伸）

  默认位置值：

  # --side_pos 默认值（两臂展开，避开桌子）
  [0.0849, 0.4159, 0.6814, -1.1422, 0.3621, -0.1473, 0.4774,
   -0.1292, -0.5084, -0.7813, -0.6478, -0.4898, -0.4773, -0.
  4136,
   2.0, 2.0]

  # --start_pos 默认值（双臂前伸，回放起点）
  [0.0199, 0.2429, -0.004, -1.552, 0.237, 0.0018, -0.001,
   0.0136, -0.2408, 0.0046, -1.5502, -0.2359, 0.0051, 0.0004
  ,
   2.0, 2.0]

  时间参数

   参数           类型    默认值   必填   描述
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   --side_time    float   3.0      否     从当前位置运动到
                                          过渡位置的时间（
                                          秒）。范围建议 0.
                                          5~10，太小会运动
                                          过快
   --start_time   float   3.0      否     从过渡位置运动到
                                          起始位置的时间（
                                          秒）。范围建议 0.
                                          5~10
   --fps          float   30.0     否     回放帧率。建议与
                                          数据集录制帧率一
                                          致。决定每帧发送
                                          间隔 (1/fps 秒)

  模式参数

   参数          类型   默认值   必填   描述
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   --step_mode   flag   False    否     启用步进模式。每帧
                                        动作需按回车确认，
                                        用于调试和检查

  步进模式命令：

   按键   功能
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━
   回车   执行下一帧
   c      切换到连续播放模式
   q      退出回放

  ──────────────────────────────────────────────────────────
  16 个关节说明

   索引   关节     说明
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   0-6    j0-j6    左臂 7 个关节（从底座到末端）
   7-13   j7-j13   右臂 7 个关节（从底座到末端）
   14     -        左夹爪开度（0~100 映射为 0.0~2.0）
   15     -        右夹爪开度（0~100 映射为 0.0~2.0）

  ──────────────────────────────────────────────────────────
  使用示例

  1. 最快使用（必填参数 + 默认值）

  python src/lerobot/scripts/lerobot_replay_tron2_with_init.
  py \
      --dataset_root="/home/cuizhixing/data/outputs/recordin
  gs/tron2_final" \
      --repo_id="deeptouch/tron2_tactile_test"

  2. 只调节初始运动时间（更慢更稳）

  python src/lerobot/scripts/lerobot_replay_tron2_with_init.
  py \
      --dataset_root="/home/cuizhixing/data/outputs/recordin
  gs/tron2_final" \
      --repo_id="deeptouch/tron2_tactile_test" \
      --side_time=5.0 \
      --start_time=5.0

  3. 调节回放帧率（跳帧但运动速度保持一致）

  python src/lerobot/scripts/lerobot_replay_tron2_with_init.
  py \
      --dataset_root="/home/cuizhixing/data/outputs/recordin
  gs/tron2_final" \
      --repo_id="deeptouch/tron2_tactile_test" \
      --fps=10.0

  4. 使用自定义位置

  python src/lerobot/scripts/lerobot_replay_tron2_with_init.
  py \
      --dataset_root="/home/cuizhixing/data/outputs/recordin
  gs/tron2_final" \
      --repo_id="deeptouch/tron2_tactile_test" \
      --side_pos="0.1,0.4,0.7,-1.1,0.4,-0.1,0.5,-0.1,-0.5,-0
  .8,-0.6,-0.5,-0.5,-0.4,2.0,2.0" \
      --start_pos="0.0,0.2,0.0,-1.6,0.2,0.0,0.0,0.0,-0.2,0.0
  ,-1.6,-0.2,0.0,0.0,2.0,2.0"

  5. 步进模式调试

  python src/lerobot/scripts/lerobot_replay_tron2_with_init.
  py \
      --dataset_root="/home/cuizhixing/data/outputs/recordin
  gs/tron2_final" \
      --repo_id="deeptouch/tron2_tactile_test" \
      --step_mode

  ──────────────────────────────────────────────────────────
  执行流程

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
          帧率: --fps FPS
          模式: 连续播放 或 步进模式

---

## 3. Model Training

Use the standard LeRobot training script. (Note: Ensure your policy configuration supports tactile input dimensions).

```bash
python src/lerobot/scripts/lerobot_train.py \
  --dataset.repo_id="deeptouch/tron2_tactile_test" \
  --dataset.root="outputs/recordings/tron2_test" \
  --policy.type=<YOUR_POLICY_NAME> \
  --output_dir="outputs/train/tron2_policy" \
  --device=cuda \
  --batch_size=32
```

---

## 4. Policy Inference (Evaluation)

To run the trained policy on the physical robot:

```bash
python src/lerobot/scripts/lerobot_eval.py \
  --policy.path="outputs/train/tron2_policy/checkpoints/last" \
  --robot.type=tron2 \
  --robot.robot_ip="10.192.1.2" \
  --robot.cameras='{
    "left_rgb": {"type": "ros2", "topic": "/camera/left/color/image_rect_raw"},
    "right_rgb": {"type": "ros2", "topic": "/camera/right/color/image_rect_raw"}
  }' \
  --robot.tactile_sensors='{
    "tac3d_sensor": {"type": "tac3d", "udp_port": 9988}
  }'
```

---

## Pre-requisites
1. **ROS2 Humble**: Must be sourced (`source /opt/ros/humble/setup.bash`).
2. **Tac3D Core**: The Tac3D Core binary must be running in the background for tactile data.
   ```bash
   # Example
   ./Tac3D -c config/DL1-GWM0053 -i 127.0.0.1 -p 9988
   ```
3. **Environment**: Use the conda environment with `limxsdk` and `pytac3d` installed.
m


📋 Tron2 关节定义清单

  16 个关节组成

  索引:  0   1   2   3   4   5   6  |  7   8   9  10  11  12  13 | 14  15
         ==========================|============================|========
         左  臂  (7 joints)        | 右  臂  (7 joints)          | 夹爪

   索引   名称                类型       单位   限位 (rad)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    0     left_arm_joint_0    根部旋转   rad    [-3.14, 2.60]
    1     left_arm_joint_1    大臂俯仰   rad    [-0.26, 2.97]
    2     left_arm_joint_2    大臂旋转   rad    [-3.67, 1.48]
    3     left_arm_joint_3    肘部俯仰   rad    [-2.62, 0.52]
    4     left_arm_joint_4    前臂旋转   rad    [-1.75, 1.40]
    5     left_arm_joint_5    腕部俯仰   rad    [-0.79, 0.79]
    6     left_arm_joint_6    腕部旋转   rad    [-1.57, 1.57]
    7     right_arm_joint_0   根部旋转   rad    [-3.14, 2.60]
    8     right_arm_joint_1   大臂俯仰   rad    [-0.26, 2.97]
    9     right_arm_joint_2   大臂旋转   rad    [-3.67, 1.48]
    10    right_arm_joint_3   肘部俯仰   rad    [-2.62, 0.52]
    11    right_arm_joint_4   前臂旋转   rad    [-1.75, 1.40]
    12    right_arm_joint_5   腕部俯仰   rad    [-0.79, 0.79]
    13    right_arm_joint_6   腕部旋转   rad    [-1.57, 1.57]
    14    left_gripper        左夹爪      %     [0, 100]
    15    right_gripper       右夹爪      %     [0, 100]

  ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
  📊 数据集标准

  Observation (48 维)

  observation.state = [
      # 左臂 (0-6): [pos, vel, tau] × 7
      joint_0_pos, joint_0_vel, joint_0_tau,  # [0,1,2]
      ...
      joint_6_pos, joint_6_vel, joint_6_tau,  # [18,19,20]

      # 右臂 (7-13): [pos, vel, tau] × 7
      joint_7_pos, joint_7_vel, joint_7_tau,   # [21,22,23]
      ...
      joint_13_pos, joint_13_vel, joint_13_tau, # [39,40,41]

      # 夹爪 (14-15): [pos, vel, tau] × 2
      joint_14_pos, joint_14_vel, joint_14_tau, # [42,43,44]
      joint_15_pos, joint_15_vel, joint_15_tau, # [45,46,47]
  ]

  Action (16 维)

  action = [
      # 仅目标位置
      joint_0_target, joint_1_target, ..., joint_15_target
  ]

  ────────────────────────────────────────────────────────────────