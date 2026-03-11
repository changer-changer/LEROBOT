# 3D Diffusion Policy: Generalizable Visuomotor Policy Learning via Simple 3D Representations_2403.03954

## 1. 研究背景

**核心**：
机器人操作通常在 3D 空间中进行，但目前的模仿学习方法（如 Diffusion Policy）大多基于 2D 会图像作为观测输入。2D 图像虽然获取容易，但对视角变化非常敏感，且难以精确推理空间几何关系（Depth Ambiguity）。
**前人研究**：

- **Point Cloud Policies**：早期将点云用于 RL 或 IL，但通常网络复杂（PointNet++等），难以实时推理。
- **2D Diffusion Policy**：SOTA 模仿学习方法，但在视角变换（Viewpoint Change）或场景扰动下泛化性差。
  **痛点**：
- 如何将 3D 表征（点云）引入到 Diffusion Policy 中，并在保持高推理速度的同时，获得比 2D 策略更好的泛化性？

## 2. 研究问题

**核心**：
本文致力于提出 **DP3 (3D Diffusion Policy)**。
具体问题：

- 3D 点云表征是否比 2D 图像更适合 Diffusion Policy？
- 如何通过简单的 3D 表征（无需复杂的预训练模型）实现高效且鲁棒的策略学习？

## 3. 核心创新工作

**核心**：
提出 **DP3**：

1.  **3D Visuomotor Policy**：
    - 将观测空间从 2D RGB 改为 3D Point Cloud。
    - 利用 Diffusion Model 生成动作序列（Action Sequence）。
2.  **DP3 Encoder**：
    - 并未采用复杂的 PointNet++ 或 Transformer，而是设计了一个基于 MLP 的轻量级点云编码器（类似于简化版 PointNet，去掉了 T-Net 等冗余）。
    - 这种设计极大地提高了训练和推理速度（Inference Speed），与 2D 策略相当。
3.  **Visual Augmentation**：
    - 虽然是 3D 点云，但也引入了针对点云的数据增强，进一步提升鲁棒性。

## 4. 关键实验设计

**核心**：

- **环境**：包含 72 个仿真任务（Adroit, MetaWorld, DexArt 等）和 4 个真机任务（Roll-up, Dumpling, Drill, Pour）。
- **变量**：演示数量（10 demos vs more），视角变化。
- **对比基准**：
  - Diffusion Policy (2D): 强基线。
  - Simple 3D baselines (Voxel, Depth).
- **指标**：Success Rate.

## 5. 核心结果与关键Insight

**核心**：

1.  **泛化性碾压**：DP3 在绝大多数任务（72个中的大部分）上优于 2D Diffusion Policy，特别是在视角变化（View Change）和光照变化下，DP3 表现出天然的稳定性。
2.  **意外的高效**：尽管处理的是 3D 数据，DP3 的收敛速度（Convergence）比 2D 策略更快（约 500 epochs vs 更慢），且推理速度并未显著下降。
3.  **简单即有效**：复杂的点云编码器（如 PointNeXt, Point Transformer）反而不如简单的 MLP Encoder 效果好。这可能是因为模仿学习的数据量较小，复杂模型容易过拟合。

## 6. 待解决问题与未来方向

**核心**：

1.  **点云质量**：真实世界的深度相机噪声（Real-world Noise）会影响点云质量，尤其是对透明物体。
2.  **计算资源**：随着点数增加（Scaling up points），MLP 编码器的显存占用线性增加，可能限制了对超精细物体的感知。
3.  **颜色信息**：目前的 DP3 主要依赖几何信息（XYZ），对于仅仅纹理不同（颜色区分）的物体可能无法区分。
