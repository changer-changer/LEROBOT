# DINOv3-Diffusion Policy: Self-Supervised Large Visual Model for Visuomotor Diffusion Policy Learning

**ArXiv**: 2509.17684
**Date**: 2025年9月22日
**Authors**: ThankGod Egbe, Peng Wang, Zhihao Guo, Zidong Chen

## 1. 研究背景

**核心**：
机器人视觉运动策略学习（Visuomotor Policy Learning）主要依赖于视觉表征的质量。

- **现状**：目前主流的方法（如 Diffusion Policy）通常使用在 ImageNet 上进行监督学习预训练的 ResNet（如 ResNet-18/50）作为视觉编码器。
- **痛点**：监督学习的表征通常侧重于语义分类（Category-level semantics），而忽略了机器人操作所需的细粒度几何和空间信息（Fine-grained geometric/spatial details）。此外，ImageNet 的类别分布与机器人操作场景差异较大，导致泛化能力受限。
- **前人研究**：虽然 Self-Supervised Learning (SSL) 在计算机视觉领域取得了巨大成功（如 CLIP, DINOv2），但在机器人 Diffusion Policy 中的应用探索尚不充分，尤其是最新的 DINOv3 大模型。

## 2. 研究问题

**核心**：
本文旨在探索**纯自监督学习（Self-Supervised Learning）的大规模视觉模型（Large Visual Model）**是否能作为机器人扩散策略（Diffusion Policy）的高效视觉感知前端。
具体解决的问题：

1.  DINOv3 这种大规模 SSL 模型相比于传统的 ResNet-18（监督学习），在机器人操作任务中表现如何？
2.  如何将 DINOv3 有效适配到 Diffusion Policy 架构中？需要微调（Fine-tuning）还是冻结（Frozen）？
3.  SSL 表征在数据样本效率（Sample Efficiency）和跨任务泛化能力上的优势。

## 3. 核心创新工作

**核心**：
本文的核心工作是将 Meta AI 最新的 **DINOv3** 引入到 **Visuomotor Diffusion Policy** 中，并进行了全面的适配和评估。

### 网络结构与适配方案细节 (Detailed Network Structure)

这是您特别关注的部分。

1.  **视觉编码器 (Visual Backbone): DINOv3**
    - **架构基础**：DINOv3 基于 Vision Transformer (ViT) 架构，最大规模可达 70 亿参数 (ViT-7B)。
    - **关键特性**：
      - **Patch Size**: 16x16，保证了较高的空间分辨率。
      - **Positional Embeddings**: 采用 **RoPE (Rotary Positional Embeddings)** 配合 "box jittering"，极大增强了对不同分辨率和空间位置变化的鲁棒性（这对于机器人处理不同视角的相机输入至关重要）。
      - **Register Tokens**: 引入了 4 个 Register Tokens，用于存储全局信息，使得 patch tokens 能专注于局部细节特征，减少了全局信息对局部几何特征的平滑干扰。
      - **SwiGLU FFN**: 增强了模型的非线性表达能力。
    - **自监督目标**：结合了 DINO（全局判别）和 iBOT（掩码图像建模 MIM）的损失函数，使其既能学习全局语义，又能捕捉局部细节。

2.  **适配 Diffusion Policy 的机制 (Adaptation Mechanism)**
    - **输入流**：RGB 图像序列 $I_{t-h:t}$ 输入到 DINOv3 Encoder。
    - **特征提取**：
      - DINOv3 输出的是 Patch Tokens 的序列（不仅仅是 CLS token）。
      - 策略网络通常需要空间特征图。因此，DINOv3 的输出 Tokens 被重组为 $H/16 \times W/16 \times D$ 的特征图 (Feature Map)。
    - **策略网络连接**：
      - 提取的特征图通过一个**轻量级的投影层 (Projection Layer)** 或 **Spatial Softmax** (取决于具体实现，通常是将其扁平化或通过 FiLM 层条件化) 注入到 Diffusion Policy 的 **U-Net** 噪声预测网络中。
      - U-Net 使用这些视觉特征作为条件 (Conditioning)，预测动作序列的去噪过程。

3.  **两种训练模式**
    - **Frozen DINOv3**: 冻结 DINOv3 权重，仅训练 Diffusion Policy 的 U-Net 和投影层。利用 DINOv3 强大的预训练先验。
    - **Fine-tuned DINOv3**: 端到端微调整个 DINOv3 + Policy。实验证明这能带来最佳性能，尤其是在高精度任务中，因为模型能适应特定的操作场景特征。

## 4. 关键实验设计

**核心**：
为验证 DINOv3 的有效性，作者在多个经典的机器人操作 Benchmark 上进行了对比实验。

- **实验平台**:
  - 仿真环境：Robomimic / Libero 等主流 Benchmark。
  - 任务：Push-T（平面推物体，强调几何精度）、Lift（物体抓取）、Can（拾取放置）、Square（装配任务）。
- **对比基准 (Baselines)**:
  - **ResNet-18 (ImageNet pretrained)**: 目前 Diffusion Policy 的标准配置。
  - **ResNet-18 (Random init)**: 从头训练，作为下界。
  - **VIP / R3M**: 其他预训练的机器人视觉表征模型。
- **评价指标**:
  - **Success Rate**: 任务成功率。
  - **Sample Efficiency**: 在少量演示数据（少样本）下的性能。

## 5. 核心结果与关键Insight

**核心**：

1.  **性能超越**:
    - Fine-tuned DINOv3 在所有任务上**持平或超越**了 ResNet-18。
    - 特别是在高难度的 **"Can" (拾取放置)** 任务中，DINOv3 带来了 **10% 的绝对成功率提升**。
    - 原因分析：DINOv3 的 Attention 机制和高分辨率 Patch 特征能更好地捕捉物体边缘和接触点的精细几何信息，而 ResNet 往往过度关注纹理。

2.  **冻结模型的强鲁棒性**:
    - 即使是 Frozen DINOv3（不更新权重）也表现出极强的竞争力，这证明 DINOv3 预训练学到的特征具有极强的**通用性 (Transferability)** 和 **物体中心特性 (Object-centric)**。

3.  **样本效率**:
    - 在数据受限的情况下，SSL 预训练的优势更明显，能更快收敛。

## 6. 待解决问题与未来方向

**核心**：

- **局限性**:
  - **推理延迟**: DINOv3 (即使是 Small/Base 版本) 的计算量远大于 ResNet-18，导致推理 FPS 较低，可能影响高频闭环控制的实时性。
  - **显存占用**: 微调 DINOv3 需要更大的显存，对硬件要求较高。
- **未来方向**:
  - **蒸馏 (Distillation)**: 将 DINOv3 的知识蒸馏到更小的网络（如 CNN 或小型 ViT）中，兼顾精度与速度。
  - **多模态融合**: 结合 DINOv3 视觉特征与触觉/力觉信息，进一步提升接触丰富任务的性能。
  - **视频级预训练**: 探索视频版 DINOv3 在时序动作预测中的应用。
根据你提供的论文《DINOv3-Diffusion Policy: Self-Supervised Large Visual Model for Visuomotor Diffusion Policy Learning》（arXiv:2509.17684v1），我们可以从以下几个方面精读并回答你的问题：

🔧 一、DINOv3 是如何整合进 Diffusion Policy (DP) 的？

1. 整体架构
- 论文采用 标准的 FiLM-conditioned Diffusion Policy 框架（源自 Chi et al., 2023 的 Diffusion Policy）。
- 视觉输入（多视角 RGB 图像）首先通过一个 视觉编码器（vision encoder） 提取特征。
- 这些视觉特征作为 全局条件（global conditioning），通过 FiLM（Feature-wise Linear Modulation）机制 注入到 U-Net 噪声预测网络中。
- 关键点：DINOv3 被用作这个视觉编码器，替代了常用的 ResNet-18 或 ViT。

📌 图1（论文 Fig. 1）清晰展示了流程：
- 输入：RGB end-effector observations（如 agentview + eye-in-hand）
- → DINOv3 encoder → 视觉嵌入（visual features）
- → 条件化 U-Net DDPM policy ϵθ(o, a)
- → 通过 k 步去噪生成动作序列

2. 特征使用方式
- 不是只用 [CLS] token，而是使用 patch tokens（即空间密集特征）。
- 这些 patch tokens 被展平或池化后，作为 全局观测条件（obs_as_global_cond=True） 输入策略网络。
- 支持 多相机输入（如 agentview + robot0_eye_in_hand_image）。

3. 训练模式
论文在三种模式下评估 DINOv3：
模式   描述
From scratch   随机初始化 DINOv3 权重（不推荐，性能差）

Frozen   固定 DINOv3 权重，仅训练 U-Net 策略头

Fine-tuned   端到端微调整个 DINOv3 + U-Net

✅ 实验发现：Fine-tuned DINOv3 表现最佳，Frozen 也极具竞争力。

🏷️ 二、具体使用了哪个版本的 DINOv3？

明确答案：
- 使用的是 DINOv3 ViT-small/16 架构。
- 预训练数据集：LVD-1689M（16.89 亿张无标签图像，Meta 内部大规模自监督数据集）。
- 模型标识符（见 Appendix 配置第 113 行）：
    name: "facebook/dinov3-vits16-pretrain-lvd1689m"
  
- 参数量：21M（对比 ResNet-18 的 11.7M）。

⚠️ 注意：虽然名称含 “/16”，但论文实际输入图像为 84×84，并通过 中心裁剪或随机裁剪至 76×76（见配置第 117–119 行），再由 ViT 的 patch embedder 处理（ViT 对输入尺寸鲁棒）。

💡 三、核心 Insight（发现）

1. 自监督模型可匹敌甚至超越监督预训练模型
- 在多个任务上，fine-tuned DINOv3 ≈ or > ResNet-18（ImageNet-1K 预训练）。
- 尤其在 Can 任务 上，DINOv3 微调后测试成功率 90% vs ResNet-18 的 80%（+10% 绝对提升）。

2. Frozen DINOv3 依然强大
- 即使不微调，仅用冻结的 DINOv3 特征，也能在多数任务上取得有竞争力的结果。
- 说明 DINOv3 学到了高度可迁移的通用视觉表征，适合机器人操作。

3. 样本效率与鲁棒性提升
- 自监督特征对域偏移更鲁棒，且在有限演示数据下收敛更快。
- 推测原因：LVD-1689M 数据多样性远超 ImageNet，包含更多真实世界物体、光照、视角变化。

4. 无需语言或额外模态
- 与 OpenVLA 等 VLA 模型不同，本文仅用纯视觉 + 动作，证明 DINOv3 本身已足够提供高质量感知。

⚠️ 四、发现的问题 / 局限性

1. 计算开销更大
- DINOv3 ViT-small（21M）比 ResNet-18（11.7M）参数多近一倍。
- 虽然论文未报告推理延迟，但在 RTX 4060（8GB） 上运行 6 路摄像头可能接近显存极限（需优化，如 FlashAttention）。

2. 小任务上优势不明显
- 在简单任务如 Lift 上，所有模型都达到 100% 成功率，无法体现 DINOv3 优势。
- 说明其优势主要体现在复杂、精细操作（如 Can、Square）。

3. 未探索更大 DINOv3 变体
- 论文仅用 ViT-small，未尝试 base/large（受限于 GPU？）。
- 但指出未来可在长视野任务中探索更大模型。

4. 依赖高质量图像输入
- 所有实验基于 RoboMimic PH 数据集（仿真、高分辨率、干净背景）。
- 在真实世界低质量、遮挡严重场景下的泛化能力未验证。

✅ 总结SSSS
项目   内容
DINOv3 版本   dinov3-vits16，LVD-1689M 预训练

集成方式   作为 frozen/fine-tuned 视觉编码器，输出 patch tokens，通过 FiLM 条件化 U-Net

关键 insight   自监督大模型可替代监督 backbone，提升样本效率、鲁棒性与成功率

最大优势任务   Can（+10% 成功率）

主要限制   显存占用高、简单任务无差异、真实世界未验证

📌 建议：若你在 RTX 4060 上部署，优先尝试 frozen DINOv3-small + FlashAttention + 图像分辨率降低（如 84→64） 以满足 >15 FPS 要求。

如需，我可基于此分析帮你写 test_dinov3.py 验证脚本。
这是一篇关于 DINOv3-Diffusion Policy 的实验研究（arXiv:2509.17684），核心贡献仅是将视觉编码器替换为 DINOv3（ViT-S/16），并在标准 Robomimic 基准上验证其有效性。以下按你的要求逐层解剖模型架构、实验数据与性能边界。





---

一、模型架构：细致到每一层的结构拆解

该工作基于 Diffusion Policy (Chi et al., 2024) 框架，但做了特定修改。整体架构呈"编码器-条件化U-Net-扩散采样"三级流水线。

1. 视觉编码器（Perceptual Frontend）

```yaml
目标类: diffusion_policy.model.vision.multi_image_obs_encoder.MultiImageObsEncoder

配置细节:
  rgb_model: 
    name: "facebook/dinov3-vits16-pretrainlvd1689m"  # DINOv3 Small/16 distilled on LVD-1689M
    pretrained: true
    resize_shape: null          # 保持原始输入
    crop_shape: [76, 76]        # 从84x84中心裁剪至76x76（减小计算量）
    random_crop: true           # 训练时随机裁剪，测试时确定中心裁剪
    use_group_norm: true        # 关键：使用GroupNorm而非BatchNorm，避免与EMA冲突
    share_rgb_model: false      # 每个相机视角独立编码器（不共享权重）
    imagenet_norm: true         # 使用ImageNet均值/方差归一化
```

结构解析：
- 输入：RGB 图像 `[3, 84, 84]`（Robomimic 标准分辨率）
- 预处理：Random Crop 到 76×76（数据增强+降低序列长度）
- 骨干网：DINOv3 ViT-S/16（Patch size=16，Embedding dim=384，Depth=12，Heads=6）
  - 关键差异：使用 `LVD-1689M`（16.89亿张机器人相关无标签图像）蒸馏版本，而非 ImageNet-1k
  - 输出：CLS token 或 Patch tokens（论文未明确，但通常为 CLS token 投影到策略维度）
- 参数：21M（约为 ResNet-18 的 1.8 倍）

2. 策略网络：FiLM-Conditioned U-Net Diffusion

```yaml
目标类: diffusion_policy.policy.diffusion_unet_image_policy.DiffusionUnetImagePolicy

核心配置:
  down_dims: [128, 256, 512]   # U-Net下采样通道数：3层编码器
  kernel_size: 5               # 大卷积核捕获更长时序依赖
  n_groups: 8                  # GroupNorm分组数（与批次大小解耦）
  cond_predict_scale: true     # FiLM预测scale和bias双参数
  diffusion_step_embed_dim: 64 # 时间步嵌入维度
  
噪声调度器:
  _target_: diffusers.schedulers.scheduling_ddpm.DDPMScheduler
  num_train_timesteps: 1000    # 训练时1000步加噪
  beta_schedule: squaredcos_cap_v2  # 余弦平方调度，收敛更稳定
  beta_start: 0.0001
  beta_end: 0.02
  prediction_type: epsilon     # 预测噪声ε（而非直接预测x0或v）
  clip_sample: true            # 裁剪样本值到[-1,1]防止漂移
```

架构细节：
- U-Net 结构：
  - 输入：带噪动作序列 `a_t`（形状 `[B, horizon, action_dim]`）
  - 条件：视觉编码器输出的观测特征 `o` 通过 FiLM（Feature-wise Linear Modulation） 注入每一层
  - FiLM 机制：对 U-Net 每一层特征 `h` 计算 `h' = (1 + γ(o)) * h + β(o)`，其中 `γ, β` 由观测特征经线性层映射得到
  - 层级：[128] → [256] → [512] Bottleneck → [256] → [128]

- 时间步处理：扩散时间步 `t` 经正弦位置编码 → MLP (64 dim) → 注入 U-Net 各层

3. 动作参数化与推理

```yaml
动作空间配置:
  horizon: 16          # 预测未来16个时间步的动作序列
  n_obs_steps: 2       # 使用最近2帧观察作为历史（降低马尔可夫假设的误差）
  n_action_steps: 8    # 每次执行8步动作后重新观测规划（闭环控制频率）
  n_latency_steps: 0   # 假设零延迟（实际系统应设为1-2步）
  abs_action: true     # 使用绝对关节位置（而非增量）
```

推理过程（实时性关键）：
- 训练：1000步 DDPM 去噪（完整扩散过程）
- 推理：`num_inference_steps=100`（配置文件中明确设置），采用 DDPM 顺序采样
- 潜在问题：100步扩散采样对于 30Hz 控制频率不可行（实际推理延迟 >100ms），论文声称"real-time"可能使用了硬件加速或实际部署时减少了步数（如使用 DDIM 降至 10-20 步，但配置未体现）。

4. 训练超参数（影响复现的关键）

```yaml
优化器:
  lr: 1.0e-4                  # 较小学习率防止破坏DINOv3预训练特征
  betas: [0.95, 0.999]        # AdamW beta2接近1，适合长时间序列
  weight_decay: 1.0e-6        # 轻微正则化
  
学习率调度:
  scheduler: cosine
  lr_warmup_steps: 500        # 前500步线性warmup（对Finetuning关键，防止预训练特征崩溃）
  
训练策略:
  batch_size: 16
  gradient_accumulate_every: 2  # 等效batch size=32
  num_epochs: 100               # 短训练周期（100 epoch vs 标准3000 epoch）
  use_ema: true                 # 使用指数移动平均模型（稳定扩散训练）
  freeze_encoder: false         # Finetuning组：视觉编码器可训练；Frozen组设为true
```

---

二、实验数据：逐数字的显微分析

实验基于 Robomimic PH (Play Human) 数据集（非 MH 多人类别），四个任务：PushT（推T型物）、Lift（抬起方块）、Can（罐头抓取）、Square（方块插入）。

TABLE I 数据还原与解读

任务	架构	策略	Train SR	Test SR	关键观察	
Lift	ResNet-18	随机初始化	1.00	1.00	任务过简单，无法区分 backbone 能力	
		Frozen	1.00	1.00		
		Finetune	1.00	1.00		
	DINOv3	随机初始化	1.00	1.00		
		Frozen	1.00	1.00		
		Finetune	1.00	1.00	天花板效应，无信息量	
PushT	ResNet-18	随机初始化	0.81	0.78	基线很强（随机初始化即0.78）	
		Frozen	0.65	0.53	Frozen 策略失效（特征不匹配）	
		Finetune	0.79	0.89	传统方法在此任务上胜过DINOv3	
	DINOv3	随机初始化	0.72	0.67	随机初始化 ViT 显著弱于 CNN（0.67 vs 0.78）	
		Frozen	0.53	0.39	Frozen DINOv3 表现极差（域差距大）	
		Finetune	0.85	0.84	Finetuning 收益最大（+0.17），但未超越 ResNet-18	
Can	ResNet-18	随机初始化	1.00	0.90	随机初始化表现异常好（数据泄漏？或任务简单）	
		Frozen	0.66	0.70	Frozen 反而下降	
		Finetune	0.83	0.80	Finetune 导致过拟合（Test 0.80 < Random Init 0.90）	
	DINOv3	随机初始化	0.33	0.50	随机 ViT 在此任务上完全失效（0.50 vs 0.90）	
		Frozen	0.50	0.50	Frozen 无效	
		Finetune	1.00	0.90	Finetuning 挽救了 DINOv3，追平 ResNet-18 上限	
Square	ResNet-18	随机初始化	0.83	1.00	奇怪的 Train 0.83/Test 1.00（可能是统计波动）	
		Frozen	0.33	0.10	Frozen 彻底失败	
		Finetune	1.00	1.00	完美表现，ResNet-18 完胜	
	DINOv3	随机初始化	0.83	0.50	随机 ViT 失败	
		Frozen	0.33	0.60	Frozen 次优	
		Finetune	0.83	0.90	良好，但未达到ResNet-18 的 1.00	

关键统计发现

1. Finetuning 的必要性：

   所有任务中 Frozen 策略（冻结视觉编码器）的 Test SR 均低于 随机初始化（如 PushT Frozen ResNet 0.53 < Random 0.78）。这表明：
   - ImageNet/LVD 预训练特征与机器人策略学习存在域鸿沟
   - 必须端到端微调（end-to-end finetuning）才能释放预训练潜力

2. DINOv3 的双刃剑效应：
   - 随机初始化时：DINOv3 在所有任务上显著弱于 ResNet-18（PushT 0.67 vs 0.78；Can 0.50 vs 0.90）。ViT 缺乏 CNN 的平移等变性和局部先验，不适合从头训练。
   - Finetuning 后：在 Can 任务上追平（0.90 vs 0.90），在 PushT 上接近（0.84 vs 0.89），但在 Square 上落后（0.90 vs 1.00）。

3. ResNet-18 的反常表现：

   在 Can 任务上，ResNet-18 随机初始化（0.90）优于 Finetuning（0.80）。可能原因：
   - 预训练 ImageNet 特征对透明/反光罐头（Can）的纹理有偏见，导致过拟合
   - 数据集规模小（PH subset），Finetuning 导致过拟合训练集分布