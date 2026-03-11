# Reactive Diffusion Policy_2503.02881

## 1. 研究背景

**核心**：
扩散策略（Diffusion Policy）在机器人操作中表现出色，但计算开销大，推理速度较慢（通常几Hz）。对于需要高频力控的接触任务（如插拔、打磨），这种低频控制会导致不稳定或失败。
**前人研究**：

- **Action Chunking**：一次预测一段动作序列，提高了动作的连贯性，但牺牲了实时反应能力（Open-loop execution during the chunk）。
- **Temporal Ensembling**：平滑多个预测，但增加了延迟。
  **痛点**：
- **Frequency Mismatch**：Diffusion Model 的慢推理与接触任务所需的快响应之间的矛盾。

## 2. 研究问题

**核心**：
本文提出 **Reactive Diffusion Policy (RDP)**，一种快慢双流（Slow-Fast）架构。
具体问题：

- 如何在保持 Diffusion Policy 长时序规划能力的同时，赋予其高频（>100Hz）的反应能力？
- 慢速的规划层和快速的控制层如何交互？

## 3. 核心创新工作

**核心**：
提出 **Slow-Fast Policy Learning Framework**：

1.  **Slow Policy (LDP)**：
    - Latent Diffusion Policy，运行在低频（如 5Hz）。
    - 负责全局规划，预测未来的 **Latent Action Chunk**（潜在动作块），而不是直接输出动作。
2.  **Fast Policy (Asymmetric Tokenizer)**：
    - 运行在高频（如 100Hz+）。
    - 是一个轻量级的解码器（Decoder），接收 Slow Policy 输出的 Latent Chunk 和当前的 **高频触觉/力反馈（High-freq Tactile/Force）**。
    - 根据实时反馈对 Latent Chunk 进行微调（Refining），生成当前的实际动作。
3.  **Asymmetric Design**：
    - Fast Policy 的设计是不对称的：编码器（Encoder）用于离线训练时的压缩，解码器（Decoder）用于在线推理时的解压和调节。

## 4. 关键实验设计

**核心**：

- **任务**：
  1.  **Pushing with Obstacles**：避障推箱子。
  2.  **Peg Insertion**：高精度插孔。
- **对比基准**：
  - Standard Diffusion Policy.
  - RMA (Rapid Motor Adaptation).
- **指标**：Success Rate, Force Profile (接触力的平稳性).

## 5. 核心结果与关键Insight

**核心**：

1.  **快慢结合的优势**：RDP 在插孔任务中表现出更高的成功率和更小的过度接触力（Excessive Force）。Slow Policy 保证了轨迹的大方向正确，Fast Policy 保证了接触瞬间的柔顺性。
2.  **实时性**：Fast Policy 的推理时间 < 1ms，足以支持 500Hz 以上的控制频率，彻底解决了 Diffusion Policy 响应慢的问题。
3.  **Latent Space 的鲁棒性**：在 Latent Space 进行规划比在原始动作空间更鲁棒，因为它过滤掉了高频噪声，专注于意图层面。

## 6. 待解决问题与未来方向

**核心**：

1.  **复杂力控**：目前的 Fast Policy 主要是基于简单的用于修正轨迹的力反馈，对于需要复杂力-位混合控制（Hybrid Force-Motion Control）的任务可能还需要进一步设计动作空间。
2.  **训练复杂性**：需要分阶段训练（先训练 Tokenizer，再训练 Diffusion），比端到端训练略显繁琐。
