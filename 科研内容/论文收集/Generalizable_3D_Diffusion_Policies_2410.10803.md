# iDP3: Generalizable 3D Diffusion Policies_2410.10803

## 1. 研究背景

**核心**：
模仿学习（Imitation Learning）在机器人操作中取得了巨大成功，但大多数方法基于 2D 会图像（2D Images），容易受到视角变化（Viewpoint Shift）、光照干扰和背景杂波的影响。虽然 3D 表征（如 Point Cloud）包含丰富的几何信息，但在各种研究中，3D 策略的训练往往比 2D 策略更慢，且难以处理高分辨率数据。
**前人研究**：

- **DP3 (3D Diffusion Policy)**：证明了 3D 点云表征在泛化性上优于 2D，但使用的是简单的 MLP 编码器，处理大规模点云效率低。
- **2D Diffusion Policy**：基于 CNN/ViT，推理速度快但缺乏 3D 几何感知。
  **痛点**：
- 如何设计一种既高效又通用的 3D 视觉运动策略（Visuomotor Policy），使其能在单张显卡上实时运行，并能从单视角（Egocentric View）数据中学习出具备视角不变性（View Invariance）的技能。
- 3D 骨干网络（Backbone）的设计如何平衡计算效率和特征提取能力。

## 2. 研究问题

**核心**：
本文旨在提出 **iDP3 (Improved 3D Diffusion Policy)**，解决 3D 策略学习中的效率和泛化问题。
具体问题：

- Egocentric（第一人称）视角下的 3D 点云是否足以支持鲁棒的操作？
- 与 DP3 相比，如何改进网络架构以处理更多点云（Scaling up points）而不显著增加推理延迟？

## 3. 核心创新工作

**核心**：
提出 **iDP3**：

1.  **Egocentric 3D Representation**：
    - 主要依赖安装在机器人头部的单视角深度相机（Egocentric Camera）。
    - 即使只用单视角，3D 点云天然具备尺度一致性（Scale Consistency），通过坐标变换可以获得一定的视角不变性。
2.  **Conv + Pyramid Architecture**：
    - 不同于 DP3 使用的 MLP，iDP3 引入了 **3D 卷积（Sparse Conv / Conv3D）** 和 **金字塔特征提取（Pyramid Pooling）**。
    - 这种架构能更有效地捕捉局部几何特征，支持处理更多点（Scale up to 8192 points），同时保持较低的计算开销。
3.  **Humanoid Robot Deployment**：
    - 系统被部署在全尺寸人形机器人（Humanoid Robot）上，展示了从 Apple Vision Pro 遥操作数据中学习复杂全身技能的能力。

## 4. 关键实验设计

**核心**：

- **任务**：
  - **Simulation**: ManiSkill2, RLBench.
  - **Real World**: Pick&Place, Pour Water, Wipe Table (使用人形机器人）。
- **对比基准**：
  - DP (2D Diffusion Policy)：图像基线。
  - DP3 (Original MLP-based)：原始 3D 基线。
- **泛化性测试**：
  - **New View**：大幅改变相机视角。
  - **New Object**：测试未见的物体（不同形状的杯子）。
  - **New Scene**：在完全不同的场景（Lab -> Kitchen）中测试。

## 5. 核心结果与关键Insight

**核心**：

1.  **极强的泛化能力**：iDP3 在新视角（New View）和新场景（New Scene）测试中表现出了惊人的鲁棒性（9/10 成功率），而 2D Diffusion Policy 几乎全部失败（0/10 - 2/10）。这证实了 3D 表征天然适合处理空间变化。
2.  **效率提升**：相比于 DP3 的 MLP 编码器，iDP3 的卷积金字塔结构在处理大规模点云时更高效，且参数量更少。
3.  **单视角足以应付大多数任务**：实验表明，Egocentric 3D 视觉足以支持精确操作（如倒水），不需要复杂的外部多相机阵列校准。

## 6. 待解决问题与未来方向

**核心**：

1.  **深度传感器噪声**：深度相机（特别是消费级）的噪声仍然较大，影响了点云的质量，尤其是在透明或反光物体上。
2.  **数据采集瓶颈**：尽管 Vision Pro 遥操作方便，但在人形机器人上进行全身遥操作仍然令人疲惫，限制了数据采集的规模。
3.  **全身控制（Whole-body Control）**：目前的实验主要集中在上半身操作，如何在保持平衡的同时进行下半身移动和操作仍是挑战。
