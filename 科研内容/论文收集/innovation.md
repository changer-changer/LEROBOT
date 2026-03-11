# IROS 2026 投稿：高效能视触觉融合装配任务创新点实施方案

> [!IMPORTANT]
> **核心约束**: 仅软件改进，10天倒计时。
> **目标**: 在插孔（Peg-in-Hole）任务上展示 "SOTA级的精细几何感知" 和 "生物启发的抗噪能力"。

---

## 创新点一：基于最佳特征感知 (BFA) 的动态视觉融合 (Best-Feature-Aware Fusion)

**针对问题**: 简单的多视角拼接（Concat）引入了大量被遮挡或无关背景的噪声，尤其是在精细操作阶段。
**核心思想**: 让网络自己学会“现在该看哪个相机”。

### 具体实施细节

1.  **特征提取 (Feature Extraction)**
    - **模块**: `SharedResNet18` (针对所有RGB相机共享权重) 或 `Frozen DINOv3` (如算力允许)。
    - **输入**: $N$ 个视角的图像张量 $[B, T, N, C, H, W]$。
    - **输出**: 提取后的特征向量 $F = [f_1, f_2, ..., f_N]$，每个 $f_i$ 的维度为 $(B, T, D_{embed})$。

2.  **BFA 评分网络 (Score Network)**
    - 这是一个轻量级的 MLP，用于给每个视角打分。
    - **结构定义**:
      ```python
      class BFAScoreNetwork(nn.Module):
          def __init__(self, input_dim):
              super().__init__()
              self.net = nn.Sequential(
                  nn.Linear(input_dim, 128),
                  nn.ReLU(),
                  nn.Linear(128, 1)  # 输出标量分数
              )
      ```
    - **前向传播**:
      - 对每个视角的特征 $f_i$ 输入网络，得到原始分数 $s_i = \text{Net}(f_i)$。
      - **Softmax 归一化**: $w_i = \frac{e^{s_i}}{\sum_j e^{s_j}}$，得到权重 $w_i \in [0, 1]$。

3.  **加权融合 (Weighted Fusion)**
    - 最终的视觉特征是各视角的加权和：
      $$ F*{fused} = \sum*{i=1}^{N} w_i \cdot f_i $$
    - **实施Tips**: 在训练初期，网络可能不知道该看哪，容易坍缩。建议在 Loss 中加入一个正则项，或者前几轮先用 Mean Fusion 热身。

### IROS 卖点 (Story)

- "无需昂贵的人工标注，通过端到端学习实现注意力的自动切换。"
- 展示权重曲线图：Approaching 阶段 Global 权重高，Insertion 阶段 Wrist 权重高。

---

## 创新点二：双流时空触觉网络 (Dual-Stream Spatiotemporal Tactile Network)

**针对问题**: 现在的 Policy 多为单帧输入，无法判断“由于接触导致的微小滑动”。GelSight 图像如果不处理时序，就只是普通的 RGB 图像。
**核心思想**: 结合 **空间特征 (CNN)** 和 **时序动态 (ConvRNN)**。

### 具体实施细节

1.  **数据预处理 (Input Pipeline)**
    - **输入**: GelSight 视频流 $(B, T, C, H, W)$。
    - **差分计算 (Motion Stream)**: 计算帧间差分 $D_t = |I_t - I_{t-1}|$，这代表了“形变的变化率”。

2.  **混合编码器架构 (Hybrid Encoder)**
    - **空间流 (Spatial Stream)**:
      - 使用 `ResNet18` 提取当前帧 $I_t$ 的特征 -> $h_{spatial}$。
    - **时序流 (Temporal Stream - 核心创新)**:
      - 使用 **IntersectionRNN** (来自 Task-Optimized ConvRNN 论文)。
      - **简化版实现 (可行性更高)**:
        ```python
        class TactileRNN(nn.Module):
            def __init__(self, input_dim, hidden_dim):
                super().__init__()
                # 使用标准 GRU 代替复杂的 IntersectionRNN 以确保 10 天能跑通
                # 效果足够发 IROS，且更稳定
                self.rnn = nn.GRU(input_dim, hidden_dim, batch_first=True)

            def forward(self, x_sequence):
                # x_sequence: (B, T, FeatureDim) from ResNet
                out, h_n = self.rnn(x_sequence)
                return h_n[-1]  # 取最后一个时间步的隐状态
        ```
      - **逻辑**: 先用 CNN 提取每帧特征，再扔进 RNN 聚合时序信息。

3.  **融合**:
    - 触觉最终特征 $F_{tactile} = \text{Concat}(h_{spatial}, h_{temporal})$。

### IROS 卖点 (Story)

- "We introduce a biologically plausible spatiotemporal encoder that captures both static deformation geometry and high-frequency contact dynamics."

---

## 创新点三：仿生事件驱动门控 (Bio-Inspired Event Gating)

**针对问题**: GelSight 在未接触物体时（In-Air）会有大量光照噪声，导致 Policy 动作抖动。
**核心思想**: "没碰别乱动"。模拟生物神经元的 Event 触发机制。

### 具体实施细节

1.  **背景建模 (Background Modeling)**
    - 在每一条轨迹开始的第一帧 $I_0$ (此时且必定在空中)，将其存为 $I_{bg}$。

2.  **门控逻辑 (Gating Logic)**
    - 计算当前帧与背景的 L2 距离：$E = ||I_t - I_{bg}||_2$。
    - **硬阈值 (Hard Threshold)**: 设定阈值 $\tau$ (需简单测试测定)。
    - **Mask 生成**:
      $$ M = \begin{cases} 1, & \text{if } E > \tau \\ 0, & \text{if } E \leq \tau \end{cases} $$
    - **特征抑制**: $F_{final} = F_{tactile} \times M$。

3.  **代码实现**:
    ```python
    # 在 Policy 的 forward 函数中
    diff = (curr_image - bg_image).abs().mean(dim=[1, 2, 3]) # (B,)
    mask = (diff > threshold).float().unsqueeze(-1) # (B, 1)
    tactile_embedding = tactile_encoder(curr_image) * mask
    ```

### IROS 卖点 (Story)

- "Explicit Noise Suppression": 显式地消除传感器空闲时的幻觉（Hallucination），极大提升了 Sim-to-Real 的稳定性。

---

## 10天冲刺计划 (Execution Roadmap)

- **Day 1: 环境与基础代码**
  - 搭建 LeRobot 开发环境。
  - **任务**: 跑通一个最简单的 Baseline (ResNet18 + MLP)，确保数据能流转，机器人能动。
- **Day 2: BFA 模块实现**
  - 编写 `innovation_modules/bfa.py`。
  - **验证**: 放入假数据，检查权重输出形状是否为 $(B, N, 1)$。
- **Day 3: 触觉模块实现**
  - 编写 `innovation_modules/tactile.py` (ResNet + GRU)。
  - **验证**: 检查时序输入 $(B, T, ...)$ 能否正确输出 $(B, D)$。
- **Day 4: Gating 模块与全系统集成**
  - 实现 Gating 逻辑。
  - 将三个模块集成到 `DiffusionPolicy` 类中。
- **Day 5: 仿真/真机 调试 (Debug)**
  - **关键**: 用小数据量（Overfit 1个 Batch）测试 Loss 是否下降。如果 Loss 不降，检查梯度链。
- **Day 6-8: 全量训练与实验**
  - 开始正式训练。
  - **Ablation 实验 (必须做)**:
    1.  Ours (Full)
    2.  No BFA (Average Scaling)
    3.  No Temporal (Single Frame Tactile)
- **Day 9: 数据分析与绘图**
  - 导出 WandB 曲线。
  - 绘制 BFA 权重变化图，截取 Gating 生效前后的对比图。
- **Day 10: 论文撰写与投稿**
  - 填补 Result 和 Method 章节。

---

## 最后的叮嘱

1.  **不要造轮子**: 尽量继承 LeRobot 现有的类，只重写 `forward` 方法。
2.  **先跑通再优化**: 代码能跑起来比架构完美更重要。
3.  **数据是王道**: 如果效果不好，大概率是数据预处理（归一化、裁剪）没做好，而不是模型不够复杂。
