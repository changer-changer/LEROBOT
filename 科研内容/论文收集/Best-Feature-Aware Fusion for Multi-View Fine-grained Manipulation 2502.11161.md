# Best-Feature-Aware Fusion for Multi-View Fine-grained Manipulation

**arXiv ID**: 2502.11161
**简称**: BFA (Best-Feature-Aware)

## 1. 研究背景

**领域现状**: 在精细操纵任务（Fine-grained Manipulation）中，通常使用多个相机（如顶视图、手腕视图等）来解决自遮挡问题。现有的模仿学习方法（如ACT, RDT）通常简单地将多视角特征进行拼接或平均，**平等地对待所有视角的图像**。
**前人研究**:

- **多视角融合**: 之前的工作通常假设所有视角的输入都同等重要，或者依赖复杂的注意力机制隐式学习权重。
- **局限性**: 在任务的不同阶段，关键视角是动态变化的（例如抓取时手腕相机重要，移动时全局相机重要）。简单的融合方式引入了大量冗余信息（Redundancy），甚至干扰了策略的学习，导致计算负担重且精度不足。
  **应用痛点**: 如何在精细操作中动态地筛选出“最佳视角（Best Feature）”，减少冗余信息干扰，同时降低计算量。

## 2. 研究问题

**拟解决难题**:

1. **视角冗余**: 多视角输入中包含大量无关背景或被遮挡的无效信息，如何去除这些噪声？
2. **动态关注**: 不同的操作阶段（如接近、抓取、操作）需要依赖不同的视角，如何让网络自动感知并切换关注点？
3. **数据标注**: 如何低成本地获取“在当前时刻哪个视角最重要”的监督信号？

## 3. 核心创新工作

**系统/算法**: 提出 **BFA (Best-Feature-Aware)** 融合策略，作为一个即插即用（Plug-and-Play）的模块，可集成到ACT、RDT等现有策略中。

1. **Score Network (评分网络)**: 一个轻量级的MLP网络，输入多视角的全局特征，输出每个视角的“重要性得分（Importance Score）”。
   - **加权融合**: 利用预测的得分对各视角特征进行加权求和，生成融合特征输入到策略网络中。
2. **VLM自动标注系统 (VLM Scoring System)**: 利用GPT-4o等强大的视觉语言模型，根据图像内容和当前任务阶段（Holding, Approaching, Operating, Returning），自动为训练数据标注“哪个视角最重要”。
   - **规则指导**: 根据预定义的规则（如Approaching阶段关注目标物体所在视角），指导VLM生成Ground-Truth Score，用于监督训练Score Network。

## 4. 关键实验设计

**实验平台**:

- **硬件**: ALOHA双臂机器人平台，配备4个机械臂（AgileX）和4个Realsense/Orbbec相机（1个顶视，4个手腕）。
- **任务**: 5个精细操作任务，部分涉及双臂协同。
  - Unzip Bag（拉拉链）、Open Box（开盒）、Fold Towel（叠毛巾）、Play Chess（下棋）、Slide Bag。

**数据集**:

- 每个任务采集50-500条示教数据。
- 对比基准: ACT (Action Chunking with Transformers), RDT (Robotic Diffusion Transformer)。

**评价指标**:

- **任务成功率**: 分阶段记录成功率。
- **计算效率**: 推理时间、参数量。

## 5. 核心结果与关键Insight

**核心数据**:

- **性能提升**: 相比原始ACT和RDT，集成BFA后，所有任务的成功率均有显著提升（提升幅度**22%-46%**）。
- **抗干扰能力**: 在物体位置变化或抓取点随机变化的情况下，BFA能准确关注有效视角，修正了基线方法中常见的抓取位置偏差（偏差主要源于冗余视角的干扰）。
- **计算效率**: BFA结构轻量，且由于动态筛选了特征，理论上可减少后续网络的输入维度（尽管文中主要强调性能提升，但也提到了减少计算负担的潜力）。

**关键Insight**:

- **少即是多 (Less is More)**: 在多视角融合中，保留所有信息并不总是好事。主动抑制无关视角的噪声，反而能让策略网络更专注于关键几何特征，从而提高精细操作的精度。
- **VLM作为监督者**: 利用VLM的常识推理能力来生成“注意力标签”，是一种低成本引入人类先验知识（Human Prior）的有效途径，避免了昂贵的人工标注。

## 6. 待解决问题与未来方向

**局限性**:

- **VLM标注成本**: 尽管只需在训练阶段使用，但对视频数据进行逐帧或抽帧标注仍需要调用大量API资源。
- **规则依赖**: VLM的评分规则仍需根据任务阶段预定义（如表I所示），可能不够完全自动化。

**未来方向**:

- **扩展到VLA**: 将BFA策略应用于视觉-语言-动作（Vision-Language-Action）大模型中。由于VLA主要处理图像Token，减少无效Token数量将显著降低推理算力消耗，提升实时性。
  基于你提供的BFA论文，以下是完整可复现的架构细节，精确到每一层的数据维度和数学操作。

---

1. 整体系统架构与数据流

输入层：系统接收4路RGB图像流，记为 I_1, I_2, I_3, I_4，分别对应3个全局相机和1个腕部相机。每帧图像的尺寸为 640 \times 480 \times 3（宽×高×通道），批次维度记为 B。

第一级：视觉编码器（Vision Encoder）

采用标准的ResNet-18架构，但移除了最后的全局平均池化层（GAP）和全连接层（FC），保留前4个残差块（Layer0-Layer4）。这4路图像共享同一套权重（Shared Weights），分别通过该编码器。

对于单视图 I_i，编码器输出特征图 f_i \in \mathbb{R}^{B \times 512 \times 20 \times 15}。这里的空间维度 20 \times 15 是由输入 640 \times 480 经过4次下采样（每次 stride=2）得到的（640/32=20，480/32=15），通道维度512是ResNet-18最后一层的标准输出。

将4个视图的特征在批次维度上堆叠，得到多视图特征张量 \mathcal{F} = \{f_1, f_2, f_3, f_4\} \in \mathbb{R}^{B \times 4 \times 512 \times 20 \times 15}。

第二级：全局平均池化（GAP）

对每一视图的特征图独立执行全局平均池化（Adaptive Average Pooling），将空间维度 20 \times 15 压缩为 1 \times 1，保留通道维度。操作定义为：
f_i^{\text{gap}} = \frac{1}{H \times W} \sum{h=1}^{H} \sum{w=1}^{W} f_i(b, c, h, w)

输出为4个特征向量，每个 f_i^{\text{gap}} \in \mathbb{R}^{B \times 512}，堆叠后形成 \mathcal{F}{\text{gap}} \in \mathbb{R}^{B \times 4 \times 512}。这里的"low-dimensional"指的是空间维度被压缩，而非通道维度减少。

第三级：评分网络（Score Network）

这是一个三层全连接网络（3-Layer MLP），输入维度512，隐藏层维度分别为256和128，输出维度1。

具体结构如下：

- 第一层：线性变换 W_1 \in \mathbb{R}^{512 \times 256}，后接ReLU激活函数
- 第二层：线性变换 W_2 \in \mathbb{R}^{256 \times 128}，后接ReLU激活函数
- 第三层：线性变换 W_3 \in \mathbb{R}^{128 \times 1}，后接Sigmoid激活函数 \sigma(\cdot)

对于每个视图的特征向量 f_i^{\text{gap}}，评分网络输出一个标量重要性分数 s_i \in [0, 1]：
s_i = \sigma(W_3 \cdot \text{ReLU}(W_2 \cdot \text{ReLU}(W_1 \cdot f_i^{\text{gap}} + b_1) + b_2) + b_3)

对4个视图分别计算，得到分数向量 \mathbf{s} = [s_1, s_2, s_3, s_4] \in \mathbb{R}^{B \times 4}。

第四级：重加权融合（Reweight Fusion）

这是BFA的核心创新。不同于简单的拼接（Concatenation）或硬选择（Hard Selection），这里采用元素级加权求和（Element-wise Weighted Addition）。

具体操作为：将每个视图的原始特征向量 f_i^{\text{gap}}（注意：这里使用的是GAP后的特征，而非原始特征图）与其对应的重要性分数 s_i 进行逐元素相乘（Hadamard积），然后对所有视图的结果求和：
\hat{f} = \sum{i=1}^{4} f_i^{\text{gap}} \odot (s_i \cdot \mathbf{1}{512})

其中 \mathbf{1}{512} 是512维的全1向量，s_i 被广播到512维。最终输出融合特征 \hat{f} \in \mathbb{R}^{B \times 512}，与单视图特征同维度，但包含了4个视图的加权信息。

第五级：策略网络（Policy Network）

融合特征 \hat{f} 与本体感觉信息（Proprioceptive State，如机械臂关节角度）拼接后，输入到下游的策略网络（如ACT的Transformer或Diffusion Policy的UNet），输出动作序列。

---

2. 双头损失函数与梯度传播机制

BFA采用双任务联合训练范式，包含两个损失函数：

Policy Loss (L_p)：

衡量策略网络预测动作与专家演示动作的差异，对于Diffusion Policy通常是去噪损失（MSE），对于ACT是动作预测损失。该损失的梯度反向传播路径为：

1. 从Policy输出反向经过Policy Network
2. 到达融合特征 \hat{f} 后，分流至两条路径：
   - Path A（Fused Feature → Vision Encoder）：梯度继续回传至ResNet-18，更新视觉编码器权重
   - Path B（Fused Feature → Score Network）：在此被阻断（Gradient Detach），评分网络的参数不接收Policy Loss的梯度

这是通过在前向传播时，将Score Network的输出视为常数（stop_gradient）实现的，确保评分网络只学习视图重要性，而不被Policy的动作预测目标干扰。

Score Loss (L_s)：

采用二元交叉熵损失（Binary Cross-Entropy, BCE），比较预测的分数 \mathbf{s} 与VLM（Vision-Language Model）生成的伪标签 \hat{\mathbf{s}}：
L_s = \text{BCE}(\mathbf{s}, \hat{\mathbf{s}}) = -\frac{1}{4} \sum{i=1}^{4} [\hat{s}i \log(s_i) + (1-\hat{s}i)\log(1-s_i)]

该损失的梯度完整传播至Score Network的所有层，同时也传播至Vision Encoder（因为 f_i^{\text{gap}} 依赖于编码器）。这使得视觉编码器不仅学习好的特征表示，还学习有利于判断视图重要性的特征。

总损失函数：
L{\text{total}} = \lambda_1 L_s + \lambda_2 L_p
其中 \lambda_1 和 \lambda_2 是平衡系数，通常初始设为1.0，可根据训练情况调整。

---

3. 针对你4相机配置的适配细节

视图分配策略：

- 视图1-3（Global Cameras）：安装在场景上方或侧面的全局相机，覆盖整个工作空间。在接近阶段（Approaching），这些相机的分数应接近0.8-0.9。
- 视图4（Wrist Camera）：安装在执行器末端的腕部相机，提供局部特写。在插孔阶段（Insertion/Peg-in-Hole），当末端接近目标时，该视图的分数应自动上升至0.9左右，而全局相机因被手臂遮挡分数下降至0.2-0.3。

维度处理注意事项：
当你的输入图像经过ResNet-18后，假设原始输入是 640 \times 480，经过32倍下采样后特征图尺寸为 20 \times 15。此时GAP操作对每个通道的300个像素（20 \times 15）取平均，得到512维向量。

如果你的输入分辨率不同（如 480 \times 640 或 512 \times 512），GAP层会自动适应（Adaptive Pooling），始终输出 B \times 512，因此无需调整网络结构，仅需确保所有4个相机的输入分辨率一致。

与触觉模态的接口：
BFA原论文仅处理视觉。在你的视触觉融合系统中，建议将BFA的输出 \hat{f} \in \mathbb{R}^{B \times 512} 作为视觉分支的最终表征，与触觉分支（经过你的Gating机制后）输出的特征（如 \mathbb{R}^{B \times 256}）在通道维度拼接，形成 \mathbb{R}^{B \times 768} 的联合表征，再送入策略网络。

---

4. 关键实现细节与常见陷阱

Score Network的初始化：

由于使用Sigmoid输出，初始时评分可能偏向0.5。建议在训练初期对Score Loss使用较大的 \lambda_1（如2.0或5.0），迫使网络快速学习区分视图重要性，待分数分布稳定后再降低至1.0。

VLM标签的替代方案：

若10天内无法构建VLM自动标注管道，可采用规则生成伪标签：

- 根据末端执行器与目标的距离（可从 proprioception 计算）判定阶段：当距离 > 阈值时，全局相机标签设为1，腕部为0；当距离 < 阈值时，腕部设为1，全局为0.3（不完全为0，保留部分全局上下文）。这些标签需归一化使每帧的 \sum \hat{s}i = 1 或独立为0-1标签（取决于BCE的实现）。

维度一致性检查点：

- GAP前：[B, 4, 512, H, W]（空间维度任意，但通常 H, W \geq 7）
- GAP后：[B, 4, 512]（空间维度压缩为1）
- Score Network输入：[B \times 4, 512]（展平为2D张量）
- Score Network输出：[B \times 4, 1]，恢复为 [B, 4]
- 加权融合：[B, 4, 512] \times [B, 4, 1] \rightarrow [B, 4, 512]（广播乘法）\rightarrow [B, 512]（求和）

梯度阻断的实现：

在计算Policy Loss时，确保使用 `stop_gradient` 操作（在PyTorch中为 `.detach()`）阻断Score Network的参数。具体而言，在融合公式中：
\hat{f} = \sum{i} f_i^{\text{gap}} \cdot \text{stop_gradient}(s_i)
这使得 s_i 在Policy backward中视为常数，其梯度仅来自 L_s。

这个思路非常符合直觉，这也是当前主流 Transformer 策略（如 ACT, RDT）的标准做法。在你的设想中：

1. **输入**：多视角图像 -> 编码器 -> 特征向量。
2. **融合层**：用 Cross Attention（Query 可以是任务 Token 或动作 Token，Key/Value 是多视角特征）让模型自己学权重。
3. **输出**：融合后的特征 -> Diffusion Policy。

**但在该论文的语境下，作者认为（并试图证明）这种“让模型自己学融合（Self-learned Fusion）”的方法在“精细操作”任务上是不够的。**

以下是论文针对你这个方案的“反驳”逻辑和实验证据，解释为什么他们坚持要加一个“外部监督（VLM/规则）”的 BFA 模块，而不是让 Cross Attention 自己学：

### 1. 核心痛点：梯度信号太弱 (Gradient Starvation)

作者在 **IV-D (Mechanism Analysis)** 章节明确指出了这一点。

- **你的方案依赖什么更新权重？** Cross Attention 的权重更新完全依赖于最后的 **Policy Loss**（动作预测误差）反向传播回来。
- **论文的发现：** 作者指出，“the backpropagated gradient of the action loss is not strong enough” 。

- 对于简单的任务（如把物体从 A 拿到 B），动作 Loss 足够让 Attention 学会“看物体”。
- 对于**精细任务**（如拉开只有 2.5cm 的拉链 ），动作极其细微。如果仅靠动作误差回传，梯度在经过 Diffusion Policy 和 Vision Encoder 的层层传递后，已经变得非常微弱和模糊。模型很难精确地学到：“在第 45 帧，我必须**完全无视**顶视图，**只看**左手手腕”。

### 2. 实验证据：无监督 vs 有监督 (Ablation Study)

论文中的 **"w/o Score Loss"** 实验 就是你这个方案的“替身”。

- **实验设置：** 保留了加权融合的结构，但**去掉了 VLM 的监督**，完全让网络通过 Policy Loss 自己去学那个 （权重）。这在数学本质上和你用 Attention 学权重是一样的（都是 End-to-End 自适应权重）。
- 实验结果 (Table III) ：

- **Unzip Bag:** 成功率 **50%** (相比之下，有强监督的 BFA 是 **90%**)。
- **Open Box:** 成功率 **80%** (相比之下，有强监督的 BFA 是 **90%**)。

- **发生了什么？** 作者观察到，如果没有强监督，学出来的权重 是**僵化**的（Static）。
- 例如：在拉拉链任务中，无监督模型学出的权重一直是 `[0.4, 0.2, 0.4]` 。

- **后果：** 它变成了一个“平均加权”，并没有实现真正的“动态切换”。而在精细操作的关键时刻（比如对准拉链头），只要引入了一点点无关视角的噪声（比如顶视图看到的杂乱背景），操作就会失败。

### 3. Cross Attention 的特性 vs 任务需求

- **Cross Attention 倾向于“软注意”（Soft Attention）：** 它通常给出的权重是像 `0.3, 0.5, 0.2` 这样的分布。这意味着它总会保留所有视角的一部分信息（也就是保留了一部分噪声）。
- **BFA 追求的是“硬门控”（Hard Gating）：** 论文通过 VLM 生成的标签往往是非常极端的，例如 `[0, 1, 0]` 。

- **作用：** 这相当于在特征进入 Policy 之前，**物理上切断**了干扰视角的信号。对于 Diffusion Policy 这种对噪声敏感的生成模型来说，输入的特征越纯净（信噪比越高），生成的动作轨迹越稳定。

### 总结

你可以用 Cross Attention，这在学术界和工业界绝对是**正确且主流**的做法。

但是，**如果你面对的是数据量很少（比如只有 50 条演示）且精度要求极高（毫米级）的任务**，这篇论文给你的启示是：

> Cross Attention 可能学得不够快、不够准。它可能还没学会“该看哪里”，模型就已经过拟合或者陷入局部最优了。

这时候，**手动引入先验知识（Prior Knowledge）**——也就是通过 BFA 这种模块，强制告诉模型“这时候别看全局，就看手腕”——能极大地提升数据效率和最终成功率。这是一种用“人工规则/VLM 知识”换取“训练效果”的策略。
