# ImplicitRDP: Force-Reactive Policy for Contact-Rich Manipulation_2512.10946

## 1. 研究背景

**核心**：
接触丰富的操作任务（Contact-rich Manipulation），如翻转盒子、拨动开关，需要高频的力反馈调节。单纯的视觉策略（Vision-only）容易因估计误差导致用力过猛（损坏物体）或接触不良。
**前人研究**：

- **Rapid Motor Adaptation (RMA)**、**RDP (Reactive Diffusion Policy)**：采用分层架构（Hierarchical），上层视觉策略输出 Latent，下层力控策略快速反应。
- **缺点**：分层架构中的 Latent Space 压缩可能导致信息丢失，且上下层策略解耦训练难以达到最优配合。现有的 End-to-End 方法又往往难以平衡视觉的全局规划和力的局部反应。
  **痛点**：
- 如何设计一个端到端（End-to-End）的策略，既能利用视觉进行规划，又能利用原始力信号（Raw Force）进行高频闭环控制？

## 2. 研究问题

**核心**：
本文致力于提出一种端到端的力觉反应式策略 **ImplicitRDP**。
具体问题：

- 如何将力觉信号有效地融合到 Diffusion Policy 中，使其不仅仅是作为一个观测输入，而是能直接驱动“反应性”动作（Reactive Behaviors）？
- 如何在模仿学习中解决力觉信号的协变量偏移（Covariate Shift）问题？

## 3. 核心创新工作

**核心**：
提出 **ImplicitRDP**：

1.  **端到端闭环（End-to-End Closed-Loop）**：
    - 不同于 RDP 的分层结构，ImplicitRDP 是一个单一模型，直接接受 Visual, Proprioception, Force 输入，输出 Action。
    - 为了解决不同模态的频率差异，采用了 **Structural Slow-Fast Learning (SSL)**：视觉 Token 处理慢，力觉 Token 处理快（在 Attention 机制中设计）。
2.  **隐式力控（Implicit Force Control）**：
    - 不显式预测力（Force Prediction），而是通过 **Virtual-Target-based Representation Regularization (VRR)**，迫使模型学习到的动作表征隐含了力控意图。
3.  **硬件设计**：
    - 设计了 **Custom Compliant Fingertip**（柔性指尖），相比刚性指尖，能产生更清晰、更易学习的力觉信号变化。

## 4. 关键实验设计

**核心**：

- **硬件**：Flexiv Rizon 4s 自适应力控机器人。
- **任务**：
  1.  **Box Flipping**（翻转薄盒）：不能用力过猛（<14N），否则压扁盒子。
  2.  **Switch Toggling**（拨动开关）：需要克服开关的阻力阈值。
- **对比基准**：
  - DP (Vision-only)：纯视觉。
  - RDP (Hierarchical)：分层架构 SOTA。
- **指标**：Success Rate, Peak Force.

## 5. 核心结果与关键Insight

**核心**：

1.  **端到端优于分层**：ImplicitRDP 在 Box Flipping (20/20) 和 Switch Toggling (19/20) 任务上均达到了近乎完美的成功率，显著优于分层结构的 RDP（16/20 和 15/20）。
2.  **力控的必要性**：纯视觉 DP 在翻盒子时经常把盒子捏扁（Fail），因为它无法感知接触力的大小。ImplicitRDP 能根据力反馈实时调整动作。
3.  **VRR 的作用**：Ablation 研究表明，使用 VRR 正则化比显式的 Force Prediction 辅助任务效果更好，因为显式预测力可能让模型过分关注力的数值拟合，而忽略了力对动作的指导意义。

## 6. 待解决问题与未来方向

**核心**：

1.  **泛化性**：目前的实验任务较少，且都在同一台机器人上进行，跨机器人（Cross-robot）的力觉策略迁移是主要难点（因为力传感器的特性差异大）。
2.  **刚性物体**：对于完全刚性的物体，力信号变化极快（硬碰硬），即使是 50Hz 的控制频率也可能不够，需要更高频的控制或软硬件协同设计。
