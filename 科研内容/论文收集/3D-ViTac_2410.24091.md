# 3D-ViTac: Learning Multi-Modal Manipulation Policies from 3D Point Clouds and Tactile Images_2410.24091

## 1. 研究背景

**核心**：
为了实现通用的灵巧操作，机器人需要融合视觉（Vision）和触觉（Tactile）感知。然而，大多数现有方法使用 RGB 图像作为视觉输入，容易受光照变化和视角遮挡的影响。3D 点云（3D Point Cloud）具有更好的几何一致性和鲁棒性。
**前人研究**：

- **Vision-Tactile Fusion**：大多数工作（如 TACT）使用 2D 图像 + 触觉。
- **Point Cloud Policies**：DP3 等证明了 3D 策略的优势，但未融合触觉。
  **痛点**：
- 如何有效地融合 3D 点云（稀疏、无序）和触觉图像（密集、局部）？
- 如何在严重遮挡（Occlusion）的情况下，利用触觉弥补视觉缺失？

## 2. 研究问题

**核心**：
本文致力于提出 **3D-ViTac**，一种基于 3D 点云和触觉图像的多模态扩散策略。
具体问题：

- 触觉反馈能否弥补视觉点云在遮挡下的不足？
- 如何设计融合架构，使不同模态的特征在时空上对齐？

## 3. 核心创新工作

**核心**：
提出 **3D-ViTac**：

1.  **多模态融合架构**：
    - **Vision Branch**: 使用 PointNet++ 提取点云特征（Point Cloud Features）。
    - **Tactile Branch**: 使用 CNN (ResNet-like) 提取触觉图像特征。
    - **Tactile Points**: 创新性地将触觉特征投影到 3D 空间，形成“触觉点云”（Tactile Points）。这一步通过已知的传感器安装位置（FK）实现，使触觉信息在几何上与视觉点云对齐。
2.  **Cross-attention Fusion**：
    - 利用 Cross-attention 机制，让视觉特征和触觉特征相互查询，增强特征的交互。
3.  **Visual Occlusion Robustness**：
    - 验证了在视觉严重受限（如单相机、遮挡）情况下，引入触觉对成功率的显著提升。

## 4. 关键实验设计

**核心**：

- **任务**：四个长视距、接触丰富的任务：
  1.  **Egg Steaming**（蒸蛋）：极易碎。
  2.  **Fruit Preparation**（抓葡萄）：易损。
  3.  **Hex Key Collection**（六角扳手）：需要手中调整（In-hand Adjustment）。
  4.  **Sandwich Serving**（三明治）：倒煎蛋。
- **对比基准**：
  - RGB Only / PC Only: 纯视觉。
  - RGB w/ Tactile Image: 2D 视觉+触觉。
  - PC w/ Tactile Image: 3D 视觉+触觉（无 3D 对齐）。
- **Ablation**：测试不同程度的视觉遮挡（减少相机数量）。

## 5. 核心结果与关键Insight

**核心**：

1.  **3D + Tactile 最强**：3D-ViTac 在所有任务中均取得了最高成功率（如 Egg Steaming 达到 1.00），优于 RGB 基线（0.95）和 2D-ViTac（0.95）。
2.  **抗遮挡能力**：在减少相机数量（Single Cam）导致点云不完整时，3D-ViTac 依然能保持 0.95 的成功率，而纯点云策略从 1.00 掉到 0.90，证明触觉有效补充了缺失的几何信息。
3.  **触觉点云（Tactile Points）的价值**：单纯拼接触觉特征（PC w/ Tactile Image）不如将其投影为 Tactile Points（Ours），说明几何对齐（Geometric Alignment）对于 3D 策略至关重要。

## 6. 待解决问题与未来方向

**核心**：

1.  **触觉分辨率**：实验中发现，更高分辨率的触觉信号（16x16 vs 4x4）能显著提升精细操作能力。未来需要更高精度的传感器。
2.  **Sim-to-Real**：目前主要依赖真机遥操作数据（Teleoperation），采集成本高。
3.  **适用范围**：对于非刚体物体或产生形变的情况，触觉点的几何投影可能不再准确（因为接触面变了），需要更复杂的接触模型。
