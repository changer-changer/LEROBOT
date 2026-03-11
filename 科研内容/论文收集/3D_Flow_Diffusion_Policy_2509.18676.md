# 3D Flow Diffusion Policy_2509.18676

## 1. 研究背景

**核心**：
模仿学习（IL）通常学习的是一种直接从观测到动作的映射。然而，现有的视觉策略（Visual Policies）大多隐式地学习物理动态，缺乏对场景中物体运动规律（Dynamics）的显式建模。
**前人研究**：

- **DP3 (3D Diffusion Policy)**：证明了 3D 点云的有效性，但本质上仍是直接回归动作。
- **Scene Flow**：在 CV 领域，场景流（3D Scene Flow）被用来描述点云在时间上的运动，但以前主要用于感知任务，较少直接用于驱动机器人策略。
  **痛点**：
- 在涉及复杂接触和物体交互（Interaction-rich）的任务中，简单的动作回归可能忽略了“我的动作会如何影响环境”这一因果关系。

## 2. 研究问题

**核心**：
本文旨在提出 **3D FDP (3D Flow Diffusion Policy)**，将场景流（Scene Flow）作为策略学习的**中间表征（Intermediate Representation）**。
具体问题：

- 显式预测场景流（即预测未来点云的运动）能否提升策略的操作精度和泛化性？
- 如何将流预测任务（Flow Prediction）与动作生成任务（Action Generation）结合？

## 3. 核心创新工作

**核心**：
提出 **3D FDP**：

1.  **Interaction-aware Representation**：
    - 策略网络不仅预测机器人的动作（Action），还同时预测场景中关键点（Query Points）的 **3D Flow**（即这些点在未来时刻的位移）。
    - 这种设计迫使网络理解物体是如何随时间运动的，从而增强了对动态物理过程的感知。
2.  **Dense Flow Tracking**：
    - 通过跟踪场景中的密集点流，模型能够捕捉到细微的物体运动（如被推动的物体、被挤压的形变）。
3.  **Joint Optimization**：
    - 流预测作为辅助任务（Auxiliary Task）或联合任务与动作扩散过程一起训练。

## 4. 关键实验设计

**核心**：

- **任务**：
  - **MetaWorld**: 仿真基准。
  - **Real World**: 8个任务，包括 Shelf Placing (书架放书), Non-prehensile Manipulation (推箱子旋转) 等高难度任务。
- **对比基准**：
  - DP3: SOTA 3D 策略。
  - MBA (Model-Based approach).
- **指标**：Success Rate.

## 5. 核心结果与关键Insight

**核心**：

1.  **动态感知能力**：在推箱子旋转（Non-prehensile）任务中，3D FDP 成功率为 35%，而 DP3 为 0%。因为 DP3 无法预测推力产生的旋转效应，而 3D FDP 显式预测了物体的流场。
2.  **抗遮挡与复杂交互**：在 Shelve（插书）任务中，物体被严重遮挡且接触复杂，3D FDP 仍能保持一定成功率，显著优于 DP3。
3.  **流预测的增益**：Ablation 显示，预测全场景的流（Global Scene Flow）比只预测物体流更有效，因为环境流提供了背景参考。

## 6. 待解决问题与未来方向

**核心**：

1.  **计算开销**：预测密集流场增加了额外的计算负担，可能影响推理实时性。
2.  **流的真值**：在真实世界中获取场景流的 Ground Truth 很困难（通常不需要 GT，而是作为自监督或辅助预测量？文中似乎是在 Sim 中有 GT，Real 中可能依赖伪标签或直接预测）。_注：文中 Real实验似乎只需预测流作为中间量，不需要GT监督，或者是通过自监督方式学习？需确认真实世界训练细节。_
