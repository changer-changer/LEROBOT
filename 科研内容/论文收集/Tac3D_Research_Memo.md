# Tac3D + Diffusion Policy 研究备忘录

> **生成时间**: 2026-03-10  
> **研究目标**: 发表顶会论文 (ICRA/IROS/CoRL) - Tac3D点云与RGB视觉融合的Diffusion Policy  
> **核心Gap**: 无现有工作直接处理Tac3D的400×6点云格式（3D位移+3D力）

---

## 一、领域SOTA分析（基于14篇核心论文）

### 1.1 研究脉络时间线

| 时间 | 论文 | 核心贡献 | 与你的关系 |
|------|------|---------|-----------|
| 2024.03 | **DP3** (3D Diffusion Policy) | 点云输入+轻量MLP编码器，样本效率10-40次演示 | **核心Baseline**，点云处理框架 |
| 2024.09 | **PointFlowMatch** | CFM流匹配替代扩散，RLBench 67.8%成功率 | 快速推理替代方案 |
| 2024.09 | **TacDiffusion** | 力域扩散直接生成6D wrench | 力控制参考 |
| 2024.10 | **3D-ViTac** | 3D点云+触觉图像融合，Tactile Points投影 | **最接近相关工作** |
| 2024.10 | **FARM** (Tactile-Conditioned DP) | 触觉图像+力控制，摘葡萄80%成功率 | 力控动作空间参考 |
| 2025.02 | **AnyTouch** | 跨传感器通用触觉表征 | 触觉编码参考 |
| 2025.03 | **Reactive DP** | 快慢双流500Hz+ | 实时性参考 |
| 2025.05 | **GelFusion** ⭐ | 双通道触觉编码+Cross-Attention融合 | **主要Baseline** |
| 2025.05 | **ForceVLA** | FVLMoE力感知路由 | MoE融合参考 |

### 1.2 核心研究Gap

| 现有工作 | 局限 | **你的创新空间** |
|---------|------|-----------------|
| **GelFusion** | GelSight **RGB图像** (视觉触觉) | Tac3D **6D点云** (400×6: 位移+力) |
| **3D-ViTac** | 点云+**触觉图像**融合 | 点云+**Tac3D点云**融合 (双点云) |
| **FARM** | 触觉图像估计力分布 | 直接处理**原始力/位移点云** |
| **DP3/PointFlowMatch** | 纯几何点云，**无力信息** | 融合**触觉力信息**的6D点云 |
| **ForceVLA** | **外力/力矩估计值** | **Tac3D高分辨率力分布** |

**🔥 核心Gap**：**没有任何现有工作直接处理Tac3D的400×6点云格式（3D位移+3D力）并与RGB视觉融合用于Diffusion Policy**

---

## 二、Baseline选择（详细技术对比）

### 2.1 主Baseline: GelFusion (2505.07455)

**选择理由**:
- ✅ 最新SOTA（2025年5月）
- ✅ 开源可用（https://gelfusion.github.io/）
- ✅ Cross-Attention融合机制可直接迁移
- ✅ 处理视觉受限场景（与你场景匹配）

**GelFusion技术细节**:
```python
# 网络架构
观测时间步: 2 timesteps
动作序列长度: 16 action steps
输出动作维度: 10DOF (pos + 6D orientation + gripper)

# 视觉编码器
模型: CLIP-pretrained ViT-B/16
输入: 224×224, 2帧序列
特征维度: 768 (CLS token)

# 触觉编码器 - 双通道架构
通道1 (几何): ResNet-18, 512-channel, Attention Pooling
通道2 (动态): 时空残差, 二值化, Mean+Variance统计特征

# 融合模块
Cross-Attention: Q=视觉, K/V=[视觉, 左触觉, 右触觉]
注意力权重: [W_V, W_T^l, W_T^r]
F_att = W_V·F_V + W_T^l·F_l^T + W_T^r·F_r^T
F_fusion = Concat[F_v, F_att]
F_condition = Concat[F_fusion, F_dyn, F_proprio]

# 训练配置
优化器: AdamW (lr=3e-4, ViT=3e-5)
Batch Size: 64
训练Epochs: ~50
GPU: 2×A800, BF16混合精度
损失: 标准DP去噪损失
```

**你需要修改**:
```python
# GelFusion原代码 (处理触觉图像)
tactile_feat = ResNet18(gelsight_image)  # [B, 512]

# 你的修改 (处理Tac3D点云)
tactile_feat = TacPointEncoder(tac3d_pointcloud)  # [B, 400, 6] -> [B, 512]
```

### 2.2 消融Baseline（必须对比）

| Baseline | 描述 | 目的 | 预期成功率 |
|---------|------|------|-----------|
| **RGB-only DP** | 纯视觉Diffusion Policy | 证明触觉必要性 | ~40% |
| **Early Concat** | RGB特征+Tac3D特征简单拼接 | 证明Cross-Attention价值 | ~55% |
| **No Force分支** | 只使用Tac3D的几何部分(前3维) | 证明力信息价值 | ~60% |
| **GelFusion-Adapt** | PointNet代替ResNet处理Tac3D | 对比你的TacPointEncoder | ~65% |
| **Ours (Full)** | 完整方法 | 目标 | **>75%** |

### 2.3 辅助Baseline: 3D Diffusion Policy (2403.03954)

**技术细节**:
```python
# 点云处理流程
单视角深度图(84×84) → 点云转换 → 空间裁剪 → FPS降采样(512/1024点)

# DP3编码器
3层MLP + MaxPooling + 投影头 → 64维紧凑表征
结构:
  Linear(3, 64) + ReLU + LayerNorm(64)
  Linear(64, 128) + ReLU + LayerNorm(128)
  Linear(128, 256) + ReLU + LayerNorm(256)
  MaxPooling1D()
  Linear(256, 64)  # 投影头

# 关键发现
- BatchNorm对策略学习有害，LayerNorm更稳定
- 轻量级MLP优于PointNet/PointNeXt等复杂编码器
- 点云表征显著优于RGB-D/Depth/Voxel (78.3% vs 32-40%)
- 样本效率: 仅需10-40次演示
- 安全性: 真实环境违规率0% (DP为32.5%)

# 扩散配置
噪声调度器: DDIM
训练步数: 100步
推理步数: 10步
预测目标: Sample Prediction (优于Epsilon Prediction)
训练轮数: 1000-3000 epochs
```

---

## 三、创新点提案（3个具体贡献）

### 创新点1: TacPoint Encoder - Tac3D专用点云编码器

**问题**: 现有PointNet/PointNet++处理不了6D输入（位移+力混合）

**架构设计**:
```python
class TacPointEncoder(nn.Module):
    """
    输入: Tac3D点云 [B, 400, 6] (x,y,z, Fx,Fy,Fz)
    输出: 触觉特征 [B, 512]
    """
    def __init__(self):
        super().__init__()
        # 双分支设计 - 几何和力分别编码
        self.geo_encoder = nn.Sequential(
            nn.Linear(3, 64), nn.ReLU(), nn.LayerNorm(64),
            nn.Linear(64, 128), nn.ReLU(), nn.LayerNorm(128),
            nn.Linear(128, 256), nn.ReLU(), nn.LayerNorm(256),
        )
        self.force_encoder = nn.Sequential(
            nn.Linear(3, 64), nn.ReLU(), nn.LayerNorm(64),
            nn.Linear(64, 128), nn.ReLU(), nn.LayerNorm(128),
            nn.Linear(128, 256), nn.ReLU(), nn.LayerNorm(256),
        )
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.fusion_mlp = nn.Sequential(
            nn.Linear(256*2, 512),
            nn.ReLU(),
            nn.Linear(512, 512)
        )
        
    def forward(self, tac3d):
        # tac3d: [B, 400, 6]
        B = tac3d.shape[0]
        
        # 分别编码
        geo_feat = self.geo_encoder(tac3d[:, :, :3])      # [B, 400, 256]
        force_feat = self.force_encoder(tac3d[:, :, 3:])  # [B, 400, 256]
        
        # MaxPooling (置换不变)
        geo_feat = self.pool(geo_feat.transpose(1, 2)).squeeze(-1)      # [B, 256]
        force_feat = self.pool(force_feat.transpose(1, 2)).squeeze(-1)  # [B, 256]
        
        # 早期融合
        fused = torch.cat([geo_feat, force_feat], dim=-1)  # [B, 512]
        return self.fusion_mlp(fused)  # [B, 512]
```

**关键设计决策**:
- 几何和力**分别编码**（不同物理量，不能混）
- 早期融合（early fusion）比晚期更好
- 使用LayerNorm而非BatchNorm（参考DP3发现）
- MaxPooling提供置换不变性

---

### 创新点2: Cross-Attention Force Fusion - 防模态崩塌机制

**问题**: RGB信息太强，触觉信息被淹没（视觉权重过大）

**解决方案**（改进自GelFusion）:
```python
class VisuoTactileFusion(nn.Module):
    """
    Vision-Dominated Cross-Attention Fusion
    防止视觉主导，让触觉在接触时"发声"
    """
    def __init__(self, dim=512, num_heads=8):
        super().__init__()
        self.num_heads = num_heads
        self.scale = (dim // num_heads) ** -0.5
        
        # Q来自视觉，K/V来自所有模态
        self.q_proj = nn.Linear(768, dim)  # ViT输出768维
        self.k_proj = nn.Linear(512, dim)
        self.v_proj = nn.Linear(512, dim)
        self.out_proj = nn.Linear(dim, dim)
        
    def forward(self, rgb_feat, tactile_left, tactile_right):
        # rgb_feat: [B, 768] (ViT CLS token)
        # tactile_left/right: [B, 512] (TacPoint Encoder输出)
        
        B = rgb_feat.shape[0]
        
        # Query来自视觉
        Q = self.q_proj(rgb_feat).view(B, self.num_heads, -1)  # [B, H, D]
        
        # K/V来自所有模态
        K = torch.stack([self.k_proj(rgb_feat), 
                         self.k_proj(tactile_left), 
                         self.k_proj(tactile_right)], dim=1)  # [B, 3, D]
        V = torch.stack([self.v_proj(rgb_feat),
                         self.v_proj(tactile_left),
                         self.v_proj(tactile_right)], dim=1)  # [B, 3, D]
        
        K = K.view(B, 3, self.num_heads, -1).transpose(1, 2)  # [B, H, 3, D]
        V = V.view(B, 3, self.num_heads, -1).transpose(1, 2)  # [B, H, 3, D]
        
        # Cross-Attention
        attn = torch.matmul(Q.unsqueeze(2), K.transpose(-2, -1)) * self.scale  # [B, H, 1, 3]
        attn = F.softmax(attn, dim=-1)
        
        # 输出
        out = torch.matmul(attn, V).squeeze(2)  # [B, H, D]
        out = out.view(B, -1)
        return self.out_proj(out)  # [B, 512]
```

**额外技巧 - 接触感知门控**（来自TacDiffusion启发）:
```python
class ContactGating(nn.Module):
    """接触时增加触觉权重"""
    def forward(self, tac3d_force_norm, fusion_weight):
        # tac3d_force_norm: [B, 400] 每个点的力大小
        # 检测是否发生接触
        contact_detected = (tac3d_force_norm > threshold).any(dim=1)  # [B]
        
        # 接触时增加触觉权重
        weight = torch.where(
            contact_detected.unsqueeze(-1),
            torch.tensor(0.6),  # 接触时触觉权重60%
            torch.tensor(0.3)   # 非接触时触觉权重30%
        )
        return weight
```

---

### 创新点3: Force-Aware Action Space - 力控制动作空间

**问题**: 标准DP只预测位置，精密装配需要力控制

**扩展动作空间**（参考FARM+TacDiffusion）:
```python
# 标准DP动作空间 (7D)
action_standard = [dx, dy, dz, droll, dpitch, dyaw, gripper_width]

# 你的动作空间（扩展力控制）(8D)
action_ours = [dx, dy, dz, droll, dpitch, dyaw, gripper_width, F_grip]
# 其中 F_grip 是目标夹爪力

# 6D旋转表示（参考PointFlowMatch）
# 使用旋转矩阵的前两列flatten为6D，比四元数更稳定
rotation_6d = [r11, r12, r21, r22, r31, r32]  # 第一列和第二列
```

**控制器设计**:
```python
class HybridController:
    """双模态控制器：位置控制 + 力控制"""
    def __init__(self, force_threshold=0.5):
        self.force_threshold = force_threshold
        self.in_contact = False
        
    def control(self, action, current_force):
        pos_action = action[:6]      # 位置控制 [dx, dy, dz, dr, dp, dy]
        width = action[6]            # 夹爪宽度
        target_force = action[7]     # 目标力
        
        # 检测接触
        if current_force > self.force_threshold:
            self.in_contact = True
        
        if self.in_contact:
            # 接触时：力控制模式
            force_error = target_force - current_force
            grip_cmd = self.force_controller(force_error)
            return {
                'position': pos_action,
                'gripper_width': grip_cmd,  # 力控制决定
                'mode': 'force_control'
            }
        else:
            # 非接触时：位置控制模式
            return {
                'position': pos_action,
                'gripper_width': width,     # 位置控制决定
                'mode': 'position_control'
            }
    
    def force_controller(self, error, kp=0.1):
        """简单的P控制力控制器"""
        return kp * error
```

---

## 四、30天冲刺计划（详细版）

### Week 1: 基础设施 (Day 1-7)

| 天数 | 任务 | 输出 |
|------|------|------|
| Day 1 | 确认Tac3D SDK接口，获取数据格式样本 | 数据格式文档 |
| Day 2-3 | 在LeRobot中集成Tac3D数据读取 | 数据读取模块 |
| Day 4-5 | 实现TacPoint Encoder | 编码器代码 |
| Day 6-7 | 实现Tac3D点云可视化，确认数据质量 | 可视化工具 |

### Week 2: 核心模型 (Day 8-14)

| 天数 | 任务 | 输出 |
|------|------|------|
| Day 8-9 | 实现Cross-Attention融合模块 | 融合模块代码 |
| Day 10-11 | 实现力控制动作空间和Hybrid Controller | 控制器代码 |
| Day 12-13 | 集成到Diffusion Policy框架 | 完整模型 |
| Day 14 | 小规模测试（Overfit 1 batch） | 可运行代码 |

### Week 3: 训练与调试 (Day 15-21)

| 天数 | 任务 | 输出 |
|------|------|------|
| Day 15-17 | 收集/整理精密装配任务数据 | 训练数据集（50条/任务） |
| Day 18-19 | 训练主模型+4个消融Baseline | 5个训练好的模型 |
| Day 20-21 | 调试训练稳定性 | 训练日志+收敛曲线 |

### Week 4: 实验与写作 (Day 22-30)

| 天数 | 任务 | 输出 |
|------|------|------|
| Day 22-24 | 运行对比实验，收集成功率数据 | 实验结果表格 |
| Day 25-26 | 绘制BFA权重变化图等可视化 | 论文图表 |
| Day 27-28 | 撰写论文（Method+Results） | 论文初稿 |
| Day 29-30 | 完善Related Work+Introduction，投稿准备 | 投稿版本 |

---

## 五、关键技术细节汇总

### 5.1 Tac3D数据处理

```python
# Tac3D输出格式
tac3d_data = {
    'points': [400, 3],      # 相对位移 (dx, dy, dz)
    'forces': [400, 3],      # 力向量 (Fx, Fy, Fz)
    'timestamp': float       # 时间戳
}

# 预处理
tac3d_input = np.concatenate([
    tac3d_data['points'], 
    tac3d_data['forces']
], axis=-1)  # [400, 6]

# 归一化（重要！）
geo_mean = [0.0, 0.0, 0.0]      # 位移中心
geo_std = [0.01, 0.01, 0.01]    # 位移范围约±1cm
force_mean = [0.0, 0.0, 0.0]    # 力中心
force_std = [2.0, 2.0, 2.0]     # 力范围约±2N
tac3d_normalized = np.concatenate([
    (tac3d_data['points'] - geo_mean) / geo_std,
    (tac3d_data['forces'] - force_mean) / force_std
], axis=-1)
```

### 5.2 网络架构总览

```
输入:
├── RGB图像 (224×224×3) ──> ViT-B/16 ──> [B, 768] ──┐
│                                                    │
└── Tac3D点云 (400×6) ──> TacPointEncoder ──> [B, 512] ┘
                                                        │
                                              Cross-Attention Fusion
                                                        │
                                              [B, 512] 融合特征
                                                        │
                                              + 机器人状态(10D)
                                                        │
                                              Diffusion Policy
                                                        │
                                              输出: [dx, dy, dz, dr, dp, dy, grip, force]
```

### 5.3 扩散策略配置

```python
# 基于DP3和GelFusion的配置
observation_horizon = 2    # 观测历史帧数
action_horizon = 16        # 预测动作序列长度
prediction_horizon = 16    # 预测未来步数

# 扩散配置
num_diffusion_iters = 100  # 训练步数
num_inference_iters = 10   # 推理步数
beta_schedule = 'scaled_linear'
beta_start = 0.0001
beta_end = 0.02

# 优化器
optimizer = AdamW(lr=3e-4, weight_decay=1e-6)
scheduler = CosineAnnealingLR(optimizer, T_max=3000)

# 训练
batch_size = 64
num_epochs = 2000
ema_decay = 0.995
```

---

## 六、实验设计建议

### 6.1 任务选择（3个接触丰富任务）

| 任务 | 难度 | 触觉需求 | 成功标准 |
|------|------|---------|---------|
| **精密插孔** (Peg Insertion) | 高 | 高 | 无碰撞完成插入 |
| **易碎品抓取** (Fragile Pick) | 中 | 高 | 不破碎稳定抓取 |
| **表面擦拭** (Surface Wiping) | 中 | 中 | 完全擦除污渍 |

### 6.2 评估指标

```python
# 主要指标
success_rate = 成功次数 / 总尝试次数

# 辅助指标
completion_time = 完成时间
force_profile_smoothness = 力曲线平滑度
position_accuracy = 位置精度

# 消融指标
contact_detection_accuracy = 接触检测准确率
tactile_weight_distribution = 触觉权重分布
```

### 6.3 对比实验设计

| 对比维度 | Baseline | 你的方法 | 预期提升 |
|---------|---------|---------|---------|
| 模态必要性 | RGB-only | Ours | +30% |
| 融合机制 | Early Concat | Cross-Attention | +15% |
| 力信息 | No Force | With Force | +10% |
| 编码器 | PointNet | TacPoint | +5% |

---

## 七、论文故事线（建议结构）

### 标题候选
1. "Tac3D Diffusion Policy: Visuotactile Fusion with 6D Point Cloud for Precision Assembly"
2. "Force-Aware Visuotactile Diffusion Policy via Tactile Point Cloud Encoding"
3. "TacPoint: Tactile Point Cloud Encoding for Contact-Rich Manipulation"

### 核心故事
> 现有方法要么只用视觉（遮挡时失效），要么用视觉触觉图像（GelSight），但**Tac3D点云包含更丰富几何+力信息**。我们首次将Tac3D的400×6点云（3D位移+3D力）与Diffusion Policy结合，解决精密装配中的力控制问题。

### 贡献总结（3点）
1. **TacPoint Encoder**: 首个专为Tac3D 6D点云设计的编码器，分离几何和力分支
2. **Cross-Attention Fusion**: 防模态崩塌的视触觉融合机制
3. **Force-Aware Action Space**: 扩展DP动作空间支持力控制

---

## 八、参考文献

### 核心引用
1. **GelFusion** (2505.07455) - 主要Baseline
2. **3D Diffusion Policy** (2403.03954) - 点云处理框架
3. **3D-ViTac** (2410.24091) - 最接近相关工作
4. **PointFlowMatch** (2409.07343) - 流匹配替代方案
5. **FARM/Tactile-Conditioned DP** (2510.13324) - 力控制参考

### 补充引用
6. **TacDiffusion** (2409.11047) - 力域扩散
7. **Reactive DP** (2503.02881) - 快慢双流
8. **ForceVLA** (2505.22159) - MoE融合
9. **AnyTouch** (2502.12191) - 触觉表征
10. **DP** (Chi et al., 2023) - 基础扩散策略

---

## 九、下一步行动清单

- [ ] 确认Tac3D数据格式：400×6是否正确？采样频率？与RGB时间同步？
- [ ] 获取GelFusion代码：https://gelfusion.github.io/ 开始复现
- [ ] 准备数据集：收集至少50条Tac3D+RGB的演示轨迹
- [ ] 搭建LeRobot开发环境
- [ ] 实现TacPoint Encoder（Week 1）
- [ ] 实现Cross-Attention融合（Week 2）
- [ ] 开始训练（Week 3）
- [ ] 撰写论文（Week 4）

---

*备忘录生成时间: 2026-03-10*  
*基于14篇核心论文深度阅读*  
*作者: AI研究助手*
