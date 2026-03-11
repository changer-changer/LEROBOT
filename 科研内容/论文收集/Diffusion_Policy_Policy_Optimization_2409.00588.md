# Diffusion Policy Policy Optimization_2409.00588

## 1. 研究背景

**核心**：
Diffusion Policy 在模仿学习（Imitation Learning）中表现出色，能够从演示中学习复杂的多模态分布。然而，单纯的模仿学习受限于演示数据的质量，无法超越专家，且在面对新的环境变化时缺乏适应能力。
**前人研究**：

- 前人尝试将 RL 与 Diffusion Models 结合（如 IDQL, RL-Diffusion），但通常面临训练不稳定、采样效率低（推理慢）或难以在机器人连续控制任务中有效微调的问题。
- 只有少量工作（如 RLDS）探索了直接微调 Diffusion Policy，但缺乏系统性的算法设计来保证单调提升（Monotonic Improvement）和稳定性。
  **痛点**：
- 如何有效地利用强化学习（RL）来微调预训练的 Diffusion Policy，使其在保持原有分布特性的同时最大化奖励。
- 传统 PPO 算法难以直接应用于扩散模型的去噪过程。

## 2. 研究问题

**核心**：
本文旨在提出一种专门针对 Diffusion Policy 的策略优化算法（DPPO），以解决微调过程中的稳定性和效率问题。
具体问题：

- 如何将 Policy Gradient 方法（如 PPO）适配到多步去噪的扩散过程中？
- 如何平衡“利用演示信息”和“探索新动作”之间的关系？

## 3. 核心创新工作

**核心**：
提出 **DPPO (Diffusion Policy Policy Optimization)** 算法：

1.  **MDP 建模**：将去噪过程本身建模为一个 MDP，使得每一步去噪都可以被视为在一个“去噪动作空间”中的决策，从而可以直接应用 RL。
2.  **两阶段微调**：
    - **Pre-training**：先用 BC 预训练 Diffusion Policy。
    - **Fine-tuning**：冻结前几步去噪（作为特征提取/先验），只微调最后 K' 步的去噪网络，使用 PPO 进行策略更新。
3.  **重参数化技巧**：为了计算梯度，使用了重参数化技巧（Reparameterization Trick）来反向传播梯度到去噪网络。
4.  **高效采样**：微调时使用 DDIM 采样（减少步数），提高 RL 训练时的交互效率。

## 4. 关键实验设计

**核心**：

- **实验平台**：
  - **OpenAI Gym**: Locomotion benchmarks (Hopper, Walker2D, HalfCheetah).
  - **Franka Kitchen**: D4RL benchmarks.
  - **Robomimic**: Lift, Can, Square, Transport (High-dim, sparse reward).
  - **Furniture-Bench**: 长视距家具组装任务 (One-leg, Lamp, Round-table).
  - **实机实验**: 单臂组装家具腿。
- **基准对比**：对比了 IDQL, DQL, QSM, PPO, SAC 等 RL 算法以及其他 Demo-augmented RL 方法。
- **指标**：Success Rate, Cumulative Reward, Wall-clock training time.

## 5. 核心结果与关键Insight

**核心**：

1.  **SOTA 性能**：DPPO 在 Robomimic 和 Furniture-Bench 等复杂操作任务上显著优于 IDQL 和其他 Diffusion RL 方法，尤其是在稀疏奖励的长视距任务中。
2.  **稳定性**：相比于 Off-policy RL（易发散），DPPO 作为 On-policy 方法，在微调过程中表现出极高的稳定性。
3.  **微调策略**：并不是微调所有去噪步数最好，只微调最后几步（Last few steps）既能保留预训练的先验，又能快速适应新奖励，且计算开销更小。
4.  **实机验证**：展示了 Sim-to-Real 的潜力，在仿真中微调后的策略能直接部署到真机上完成组装任务。

## 6. 待解决问题与未来方向

**核心**：

1.  **采样速度**：尽管使用了 DDIM，扩散模型的推理速度仍然比 MLP 策略慢，影响 RL 的训练吞吐量（Wall-clock time）。
2.  **探索难题**：在极度稀疏奖励的任务中，单纯靠 PPO 的局部探索可能不够，仍需结合更强的探索机制。
3.  **超参数敏感**：RL 微调对 Reward Scale 和 Entropy Coefficient 比较敏感，需要仔细调参。
