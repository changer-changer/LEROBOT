# Tactile-Conditioned Diffusion Policy for Dexterous Manipulation_2510.13324

## 1. 研究背景

**核心**：
灵巧操作（Dexterous Manipulation）任务（如抓那个、插那个）不仅需要精确的位置控制，还需要精确的力控制（Force Control），特别是在接触物体时。现有的扩散策略（Diffusion Policy）大多只控制位置（Positional Control），忽略了对接触力的显式调节。
**前人研究**：

- **Vision-based IL**：如 UMI，利用视觉和手腕相机做模仿学习，但无法感知接触力。
- **Tactile-aware IL**：虽然引入了触觉图像作为输入，但动作输出仍然只包含位置，没有 Force Control，导致策略在接触时只能“盲目”地移动，无法主动调节抓取力。
  **痛点**：
- 缺乏一种既能利用高维触觉图像（感知接触分布），又能显式控制抓取力（Force-based Control）的模仿学习框架。

## 2. 研究问题

**核心**：
本文提出 **FARM (Force-Aware Robot Manipulation)** 框架。
具体问题：

- 如何将力控制（Grip Force Control）集成到扩散策略的动作空间中？
- 高维的触觉分布信息（Force Distribution）对操作成功率有多大贡献？

## 3. 核心创新工作

**核心**：
提出 **FARM**：

1.  **FEATS (Force Estimation)**：
    - 首先训练一个监督模型 FEATS，从 GelSight Mini 的触觉图像中估计出接触力的分布（Force Distribution Map）和总法向力（Total Normal Force）。
    - 这一步将原始的光学触觉图像转化为物理意义明确的力学特征。
2.  **Extended Action Space**：
    - 不仅预测 End-Effector Pose 和 Grip Width，还显式预测 **Target Grip Force**。
    - 设计了一个 **Dual-mode Controller**：在非接触阶段使用位置控制（Grip Width），在接触阶段切换到力控制（Force Control），实现闭环调节。
3.  **Tactile-Conditioned Diffusion**：
    - 将 FEATS 估计的力分布图作为观测输入，引导策略生成包含目标力的动作序列。

## 4. 关键实验设计

**核心**：

- **硬件**：Franka Research 3 + Actuated UMI Gripper + GelSight Mini。
- **任务**：
  1.  **Plant Insertion**：插花（需大力抓稳）。
  2.  **Grape Picking**：摘葡萄（需小力柔顺，防捏碎）。
  3.  **Screw Tightening**：拧螺丝（需动态力调节）。
- **对比基准**：
  - Vision-Only.
  - Tactile-Aware (Raw Image, no force control).
  - Force-Aware (Total Force only).
- **指标**：Success Rate.

## 5. 核心结果与关键Insight

**核心**：

1.  **力控至关重要**：在摘葡萄任务中，FARM 达到了 80% 的成功率，而 Vision-Only 只有 15%（经常捏碎葡萄）。
2.  **力分布信息**：相比于只使用总力（Total Force）的基线，使用完整力分布图（Force Map）的 FARM 在拧螺丝任务中成功率更高（65% vs 45%），因为分布图能反映接触的稳定性（如是否打滑）。
3.  **混合控制有效性**：Dual-mode Controller 成功实现了从自由空间运动到接触力控的平滑过渡。

## 6. 待解决问题与未来方向

**核心**：

1.  **不同传感器**：FEATS 模型是针对 GelSight Mini 训练的，对于其他非视触觉传感器（如电容式），力分布的估计可能更难。
2.  **动态力**：目前的力控主要是 Grip Force（抓握力），对于操作过程中的外部交互力（如插孔时的阻力）尚未显式建模。
