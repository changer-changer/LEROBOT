# GelFusion: 深度论文分析报告

**论文标题**: GelFusion: Enhancing Robotic Manipulation under Visual Constraints via Visuotactile Fusion  
**作者**: Shulong Jiang, Shiqi Zhao, Yuxuan Fan, Peng Yin  
**机构**: City University of Hong Kong, HKUST(Guangzhou)  
**arXiv**: 2505.07455v1  
**项目主页**: https://gelfusion.github.io/

---

## 1. 网络架构细节

### 1.1 整体架构

GelFusion采用**Diffusion Policy UNet**作为下游条件去噪模型的框架结构，使用UMI配置：
- **观测时间步**: 2 timesteps
- **动作序列长度**: 16 action steps（作为一个整体序列学习）
- **输出动作维度**: 10自由度（end-effector positions + 6D orientation + 1D gripper openness）

### 1.2 视觉编码器 (Vision Encoder)

| 参数 | 配置 |
|------|------|
| **模型** | CLIP-pretrained ViT-B/16 |
| **输入尺寸** | 224×224 pixels |
| **输入帧数** | 2帧序列 |
| **数据增强** | Random cropping, Color jittering |
| **特征维度** | 768 (CLS token) |
| **微调策略** | Fine-tuned for task adaptation |

**输出**: 视觉特征 $F_v$ (使用classification token作为视觉特征)

### 1.3 触觉编码器 (Tactile Encoder) - 双通道架构

触觉编码器独立处理左右夹爪的GelSight图像，采用**双通道架构**：

#### 通道1: 几何特征通道 (Geometric Feature Channel)

| 参数 | 配置 |
|------|------|
| **模型** | ResNet-18 (from scratch训练) |
| **输入** | 224×224 GelSight图像 |
| **特征图** | 512-channel, 7×7 |
| **池化方式** | Attention Pooling |
| **处理方式** | 所有观测帧特征向量拼接后线性投影 |
| **输出** | 左触觉特征 $F_l^T$, 右触觉特征 $F_r^T$ |

#### 通道2: 动态特征通道 (Dynamic Feature Channel)

| 参数 | 配置 |
|------|------|
| **输入** | 连续触觉帧的时空残差 |
| **二值化** | 使用阈值对差分图像进行二值化 |
| **统计特征** | 空间均值(Mean) + 方差(Variance) |
| **输出维度** | 2D特征向量 $F_{dyn}$ |

**动态特征的意义**:
- 均值(Mean): 反映变化区域的整体比例
- 方差(Variance): 反映变化的空间分布

### 1.4 模态融合模块 (Sensory Fusion)

采用**Cross-Attention机制**进行跨模态融合：

**注意力权重计算**:
```
注意力权重: [W_V, W_T^l, W_T^r]

Q = Linear(F_v)  # Visual Query
K = Concat[F_v, F_l^T, F_r^T]  # Keys from all modalities

注意力权重 = Softmax(Q × K^T / √d)
```

**Attended特征计算**:
$$F_{att} = W_V \cdot F_V + W_T^l \cdot F_l^T + W_T^r \cdot F_r^T$$

其中 $F_{att} \in \mathbb{R}^{B \times D}$

**最终融合特征**:
$$F_{fusion} = Concat[F_v, F_{att}]$$

**完整条件特征**:
$$F_{condition} = Concat[F_{fusion}, F_{dyn}, F_{proprioception}]$$

---

## 2. 损失函数与训练细节

### 2.1 训练配置

| 参数 | 配置 |
|------|------|
| **优化器** | AdamW |
| **Betas** | [0.95, 0.999] |
| **Epsilon** | 1.0e-8 |
| **Weight Decay** | 1.0e-6 |
| **初始学习率** | 3e-4 (ViT微调: 3e-5) |
| **Batch Size** | 64 |
| **训练Epochs** | ~50 |
| **GPU** | 2 × NVIDIA A800 |
| **精度** | BF16混合精度 |
| **EMA** | 使用Exponential Moving Average |

### 2.2 Diffusion Policy损失

使用标准的Diffusion Policy训练目标，即学习条件去噪模型：

$$L = \mathbb{E}_{t, x_0, \epsilon} \left[ \| \epsilon - \epsilon_\theta(x_t, t, F_{condition}) \|^2 \right]$$

其中:
- $x_t$: 时间步t的噪声动作
- $F_{condition}$: 融合后的多模态特征
- $\epsilon_\theta$: 去噪网络

### 2.3 数据增强

**视觉数据增强**:
- Random cropping
- Color jittering

---

## 3. 多模态融合机制详解

### 3.1 设计哲学

GelFusion采用**Vision-Dominated Cross-Attention Fusion**机制：

**核心思想**:
1. 视觉信息作为主要查询(Query)
2. 触觉信息作为键值(Key-Value)补充
3. 确保视觉特征在融合过程中不被破坏

**优势**:
- 避免触觉信息过度主导
- 保持视觉观测的完整性
- 触觉作为视觉的补充信息

### 3.2 融合流程

```
视觉特征 F_v (Query)
         ↓
    [Cross-Attention]
         ↓
    ┌──────────┐
    │ W_V·F_V  │ ← 视觉自注意力
    │ W_T^l·F_l^T │ ← 左触觉贡献
    │ W_T^r·F_r^T │ ← 右触觉贡献
    └──────────┘
         ↓
    F_att (加权融合特征)
         ↓
    Concat[F_v, F_att] = F_fusion
         ↓
    Concat[F_fusion, F_dyn, F_proprio] = Final Condition
```

### 3.3 与其他融合方法的对比

| 方法 | 机制 | GelFusion中的效果 |
|------|------|------------------|
| **Concatenation** | 简单拼接 | 定位精度差，出现"air wiping" |
| **Self-Attention** | 模态间相互注意 | 泛化能力差，过度依赖本体感知，过压 |
| **Cross-Attention** | 视觉主导 | **最优**，精确定位接触点，动态调整力 |

### 3.4 双通道触觉表示的优势

**为什么需要双通道？**

1. **高维空间特征 (ResNet)**:
   - 捕获表面纹理细节
   - 精确接触区域几何信息
   - 理解静态物体属性

2. **低维动态特征 (Difference)**:
   - 编码时间交互事件
   - 接触开始/结束检测
   - 压力变化感知
   - 对策略学习更一致

**设计洞察**: 动态交互特征可能在高维静态帧中被掩盖，显式分离有助于策略学习。

---

## 4. 实验设置与数据集

### 4.1 硬件配置

| 组件 | 规格 |
|------|------|
| **机械臂** | Fairino FR5 (100Hz) |
| **主相机** | UVC模块化摄像头 + 150°广角镜头 (30Hz) |
| **触觉传感器** | 自制GelSight传感器 (Logitech C270, 30Hz) |
| **推理频率** | 2Hz |
| **推理GPU** | Nvidia 4060 Ti |
| **OS** | Ubuntu 20.04 |

### 4.2 自制GelSight传感器细节

| 参数 | 规格 |
|------|------|
| **成本** | ~30 USD |
| **硅胶类型** | 高透明度自脱气双组分加成型硅胶 |
| **反射层** | 铝银粉 + 薄膜基底 |
| **固化温度** | 35°C |
| **制造周期** | ~5小时 |
| **传感区域** | 小于橡皮擦接触面 ( wiping task设计约束) |

### 4.3 任务与数据集

#### Task 1: 表面擦拭 (Surface Wiping)

| 参数 | 详情 |
|------|------|
| **演示数量** | 50 demonstrations |
| **训练区域** | 60cm × 42cm 白板 |
| **线型** | 直线(40cm) + 箭头 + "CORL 2025" |
| **分布** | Top/Middle/Bottom区域各10条直线 + 5条随机图案 |
| **测试场景** | 不同擦拭区域、线型、初始高度 |

**评估指标**:
- **Float (漂浮)**: 残余未擦除线条 > 10cm → 失败
- **Overpressed (过压)**: 硅胶损坏或橡皮擦边界滑出视野 → 失败

#### Task 2: 插销插入 (Peg Insertion)

| 参数 | 详情 |
|------|------|
| **演示数量** | 50 demonstrations |
| **销钉位置** | 25cm半径圆内随机采样 |
| **盒子旋转** | 0°, 90°, 180°, 270° + 随机角度 |
| **干扰项** | 正方形、三角形孔洞作为干扰 |
| **数据分布** | 67%视觉对齐 + 33%接触触发调整 |

**评估指标**:
- **连续碰撞 (Continuous Collision)**: 插入过程中碰撞 → 失败
- **过渡碰撞 (Transition Collision)**: 接近时碰撞 → 失败

#### Task 3: 薯片拾取 (Chips Pick)

| 参数 | 详情 |
|------|------|
| **演示数量** | 50 demonstrations |
| **物体** | 完整马鞍形薯片 |
| **抓取策略** | 夹取薯片两端 |
| **力控制** | 接近破碎阈值的力水平 |
| **力测量** | 二值残差图像的平均值表征相对力 |

**评估指标**:
- 成功抓取而不破碎
- 力水平与演示差异 < 20%
- 过于轻柔(不稳定)也算失败

---

## 5. 关于Tac3D的信息

### 5.1 Tac3D相关性分析

**论文中未直接提及Tac3D**，但相关工作和引用中涉及类似的高分辨率触觉传感器：

**引用的相关触觉传感器工作**:
1. **GelSight** [1, 3] - 高分辨率机器人触觉传感器
2. **GelSlim 3.0** [32] - 用于测量形状、力和滑动的紧凑型触觉传感手指
3. **IFem2.0** [6] - 基于视觉的触觉传感器的密集3D接触力场重建

### 5.2 GelFusion与Tac3D类传感器的关系

**技术对比**:

| 特性 | GelFusion (GelSight-based) | Tac3D类传感器 |
|------|---------------------------|--------------|
| **传感原理** | 内部相机+软膜变形 | 类似：相机+弹性体变形 |
| **信息提取** | 双通道(纹理几何+动态交互) | 通常为3D力/几何重建 |
| **特征表示** | CNN特征 + 时序差分统计 | 通常为3D点云/力场 |
| **融合方式** | Cross-attention with vision | 因系统而异 |

**GelFusion对Tac3D类传感器的启示**:

1. **双通道表示可扩展**: 动态交互特征通道的设计思想可应用于Tac3D传感器数据
2. **跨模态融合策略**: Vision-dominated fusion可保持视觉完整性
3. **低成本实现**: 自研低成本GelSight(~30美元)证明高分辨率触觉可以普及

### 5.3 相关传感器技术引用

论文引用的高分辨率触觉传感器相关文献：

```
[1] W. Yuan, S. Dong, E.H. Adelson. "GelSight: High-resolution robot tactile sensors 
     for estimating geometry and force." Sensors, 2017.

[32] I.H. Taylor, S. Dong, A. Rodriguez. "GelSlim 3.0: High-resolution measurement 
      of shape, force and slip in a compact tactile-sensing finger." ICRA 2022.

[6] C. Zhao, J. Liu, D. Ma. "IFem2.0: Dense 3D contact force field reconstruction 
    and assessment for vision-based tactile sensors." IEEE T-RO 2024.
```

---

## 6. 关键实验结果摘要

### 6.1 擦拭任务结果

| 方法 | 成功率 | 主要失败模式 |
|------|--------|-------------|
| **GelFusion (Full)** | **最高** | - |
| No Cross-Attention | 降低 | Air wiping (失去接触) |
| No Dynamic Features | 降低 | Overpressed (过压) |
| Vision-Only | 最低 | 无法建立有效接触 |
| Self-Attention | 低于Vision-Only | 泛化差，过压 |

### 6.2 插入任务结果

| 方法 | 成功率 | 观察 |
|------|--------|------|
| **GelFusion (Full)** | **高** | 处理视觉遮挡能力强 |
| Vision-Only | 中低 | 最终插入阶段经常失败 |
| No Dynamic Features | 中等 | 静态触觉有帮助但力控制不足 |
| ResNet18 (Default) | 最优 | 从scratch训练最佳 |
| ViT-B/16 (UMI-style) | 差 | CLS token压缩信息可能丢失关键触觉信息 |
| ResNet34 | 与ResNet18相当 | 容量足够，无需更深网络 |

### 6.3 薯片拾取结果

| 方法 | 力控制能力 |
|------|-----------|
| **触觉增强方法** | 力分布接近演示 |
| Vision-Only | 过于轻柔，力分布偏差大 |

---

## 7. 局限性与未来方向

### 7.1 当前局限

1. **数据规模有限**: 仅50次演示/任务
   - 限制泛化鲁棒性
   - 复杂融合方法(如Self-Attention)需要更多数据

2. **动态特征处理可改进**:
   - 当前仅使用差分图像的统计特征(均值、方差)
   - 可能丢失压力变化率、剪切力模式等丰富信息
   - 建议: RNNs, LSTMs, 或TCNs进行时间建模

### 7.2 未来方向

1. 扩大数据集规模和多样性
2. 探索更复杂的时间建模方法
3. 应用到更多接触丰富的任务
4. 与其他传感器(如音频)的多模态融合

---

## 8. 总结

GelFusion是一个创新的视触觉融合框架，主要贡献包括：

1. **双通道触觉表示**: 显式分离静态纹理几何特征和动态交互特征
2. **视觉主导的跨模态注意力融合**: 保持视觉信息完整性同时有效利用触觉
3. **低成本实现**: 自研GelSight传感器成本仅30美元
4. **广泛验证**: 在擦拭、插入、易碎物体拾取三个任务上验证有效性

该论文为视触觉融合在模仿学习中的应用提供了有价值的架构设计和实验见解。

---

**分析完成日期**: 2026-03-10  
**分析者**: AI研究助手
