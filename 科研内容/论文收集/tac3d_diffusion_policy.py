"""
Tac3D Diffusion Policy - 完整代码框架
基于GelFusion + DP3 + FARM的融合架构

核心创新:
1. TacPointEncoder: 专为Tac3D 6D点云设计的编码器
2. VisuoTactileFusion: Vision-Dominated Cross-Attention融合
3. ForceAwareDiffusionPolicy: 扩展动作空间支持力控制
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
import numpy as np


# =============================================================================
# 模块1: TacPointEncoder - Tac3D专用点云编码器
# =============================================================================

class TacPointEncoder(nn.Module):
    """
    Tac3D点云专用编码器
    
    输入: Tac3D点云 [B, 400, 6] (x,y,z, Fx,Fy,Fz)
    输出: 触觉特征 [B, 512]
    
    设计要点:
    - 几何和力分别编码（不同物理量）
    - 使用LayerNorm而非BatchNorm（参考DP3）
    - MaxPooling提供置换不变性
    """
    def __init__(
        self,
        input_dim: int = 6,          # 3D位移 + 3D力
        output_dim: int = 512,       # 输出特征维度
        hidden_dims: list = [64, 128, 256],
        use_layernorm: bool = True   # DP3发现LayerNorm更稳定
    ):
        super().__init__()
        
        # 几何分支 (前3维: x,y,z)
        geo_layers = []
        prev_dim = 3
        for hidden_dim in hidden_dims:
            geo_layers.append(nn.Linear(prev_dim, hidden_dim))
            geo_layers.append(nn.ReLU())
            if use_layernorm:
                geo_layers.append(nn.LayerNorm(hidden_dim))
            prev_dim = hidden_dim
        self.geo_encoder = nn.Sequential(*geo_layers)
        
        # 力分支 (后3维: Fx,Fy,Fz)
        force_layers = []
        prev_dim = 3
        for hidden_dim in hidden_dims:
            force_layers.append(nn.Linear(prev_dim, hidden_dim))
            force_layers.append(nn.ReLU())
            if use_layernorm:
                force_layers.append(nn.LayerNorm(hidden_dim))
            prev_dim = hidden_dim
        self.force_encoder = nn.Sequential(*force_layers)
        
        # MaxPooling (置换不变操作)
        self.pool = nn.AdaptiveMaxPool1d(1)
        
        # 融合MLP
        self.fusion_mlp = nn.Sequential(
            nn.Linear(hidden_dims[-1] * 2, output_dim),
            nn.ReLU(),
            nn.Linear(output_dim, output_dim)
        )
        
    def forward(self, tac3d: torch.Tensor) -> torch.Tensor:
        """
        Args:
            tac3d: [B, N, 6] - Tac3D点云 (N=400)
        Returns:
            feat: [B, 512] - 触觉特征
        """
        B, N, _ = tac3d.shape
        
        # 分别编码几何和力
        geo_feat = self.geo_encoder(tac3d[:, :, :3])      # [B, N, 256]
        force_feat = self.force_encoder(tac3d[:, :, 3:])  # [B, N, 256]
        
        # MaxPooling (沿点维度)
        geo_feat = self.pool(geo_feat.transpose(1, 2)).squeeze(-1)      # [B, 256]
        force_feat = self.pool(force_feat.transpose(1, 2)).squeeze(-1)  # [B, 256]
        
        # 早期融合
        fused = torch.cat([geo_feat, force_feat], dim=-1)  # [B, 512]
        return self.fusion_mlp(fused)  # [B, 512]


# =============================================================================
# 模块2: VisuoTactileFusion - Vision-Dominated Cross-Attention融合
# =============================================================================

class VisuoTactileFusion(nn.Module):
    """
    Vision-Dominated Cross-Attention融合模块
    
    设计要点:
    - 视觉作为Query，防止触觉信息淹没视觉
    - 触觉作为Key/Value，补充接触信息
    - 参考GelFusion的融合策略
    """
    def __init__(
        self,
        rgb_dim: int = 768,      # ViT-B/16输出
        tactile_dim: int = 512,  # TacPointEncoder输出
        output_dim: int = 512,
        num_heads: int = 8
    ):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = output_dim // num_heads
        self.scale = self.head_dim ** -0.5
        
        # 投影层
        self.q_proj = nn.Linear(rgb_dim, output_dim)
        self.k_proj = nn.Linear(tactile_dim, output_dim)
        self.v_proj = nn.Linear(tactile_dim, output_dim)
        self.out_proj = nn.Linear(output_dim, output_dim)
        
    def forward(
        self,
        rgb_feat: torch.Tensor,           # [B, 768] - ViT CLS token
        tactile_left: torch.Tensor,       # [B, 512] - 左触觉
        tactile_right: torch.Tensor       # [B, 512] - 右触觉
    ) -> torch.Tensor:
        """
        Returns:
            fused: [B, 512] - 融合特征
        """
        B = rgb_feat.shape[0]
        
        # Query来自视觉
        Q = self.q_proj(rgb_feat).view(B, self.num_heads, self.head_dim)  # [B, H, D]
        
        # K/V来自所有模态 (视觉+双触觉)
        # 注意: 这里可以让视觉也作为K/V的一部分，实现自注意力
        all_features = torch.stack([
            self.k_proj(rgb_feat),        # 视觉
            self.k_proj(tactile_left),    # 左触觉
            self.k_proj(tactile_right)    # 右触觉
        ], dim=1)  # [B, 3, output_dim]
        
        all_values = torch.stack([
            self.v_proj(rgb_feat),
            self.v_proj(tactile_left),
            self.v_proj(tactile_right)
        ], dim=1)  # [B, 3, output_dim]
        
        #  reshape for multi-head attention
        K = all_features.view(B, 3, self.num_heads, self.head_dim).transpose(1, 2)  # [B, H, 3, D]
        V = all_values.view(B, 3, self.num_heads, self.head_dim).transpose(1, 2)    # [B, H, 3, D]
        
        # Cross-Attention
        attn = torch.matmul(Q.unsqueeze(2), K.transpose(-2, -1)) * self.scale  # [B, H, 1, 3]
        attn = F.softmax(attn, dim=-1)
        
        # 输出
        out = torch.matmul(attn, V).squeeze(2)  # [B, H, D]
        out = out.view(B, -1)
        return self.out_proj(out)  # [B, 512]


class ContactAwareGating(nn.Module):
    """
    接触感知门控 - 接触时增加触觉权重
    
    参考TacDiffusion的接触检测机制
    """
    def __init__(self, force_threshold: float = 0.5):
        super().__init__()
        self.force_threshold = force_threshold
        
    def forward(
        self,
        tac3d_force_norm: torch.Tensor,  # [B, N] - 每个点的力大小
        fusion_weight: torch.Tensor        # 当前融合权重
    ) -> torch.Tensor:
        """
        检测接触并调整权重
        """
        # 检测是否发生接触 (任意点力超过阈值)
        contact_detected = (tac3d_force_norm > self.force_threshold).any(dim=1)  # [B]
        
        # 接触时增加触觉权重
        weight = torch.where(
            contact_detected.unsqueeze(-1),
            torch.tensor(0.6, device=tac3d_force_norm.device),  # 接触时触觉60%
            torch.tensor(0.3, device=tac3d_force_norm.device)   # 非接触时触觉30%
        )
        return weight


# =============================================================================
# 模块3: ForceAwareDiffusionPolicy - 力感知扩散策略
# =============================================================================

class ForceAwareDiffusionPolicy(nn.Module):
    """
    力感知扩散策略
    
    扩展标准DP动作空间:
    - 标准: [dx, dy, dz, droll, dpitch, dyaw, gripper_width] (7D)
    - 扩展: [dx, dy, dz, droll, dpitch, dyaw, gripper_width, grip_force] (8D)
    
    参考FARM的双模式控制设计
    """
    def __init__(
        self,
        observation_dim: int,      # 观察维度 (视觉+触觉+本体状态)
        action_dim: int = 8,       # 动作维度 (7+1力)
        horizon: int = 16,         # 预测horizon
        n_diffusion_steps: int = 100,
        n_layers: int = 4,
        hidden_dim: int = 256
    ):
        super().__init__()
        self.action_dim = action_dim
        self.horizon = horizon
        self.n_diffusion_steps = n_diffusion_steps
        
        # 噪声预测网络 (1D CNN)
        self.noise_pred_net = self._build_noise_pred_net(
            observation_dim, action_dim, horizon, n_layers, hidden_dim
        )
        
        # 扩散调度器参数 (DDPM)
        self.register_buffer('betas', self._get_beta_schedule(n_diffusion_steps))
        alphas = 1.0 - self.betas
        self.register_buffer('alphas', alphas)
        self.register_buffer('alphas_cumprod', torch.cumprod(alphas, dim=0))
        
    def _build_noise_pred_net(
        self, obs_dim, act_dim, horizon, n_layers, hidden_dim
    ) -> nn.Module:
        """构建噪声预测网络 (简化版UNet)"""
        layers = []
        in_dim = act_dim + obs_dim  # 动作 + 条件
        
        for i in range(n_layers):
            out_dim = hidden_dim if i < n_layers - 1 else act_dim
            layers.append(nn.Conv1d(in_dim, out_dim, kernel_size=3, padding=1))
            if i < n_layers - 1:
                layers.append(nn.ReLU())
            in_dim = out_dim
            
        return nn.Sequential(*layers)
    
    def _get_beta_schedule(self, n_steps: int) -> torch.Tensor:
        """线性beta调度"""
        return torch.linspace(1e-4, 0.02, n_steps)
    
    def forward(
        self,
        noisy_action: torch.Tensor,    # [B, act_dim, horizon]
        timestep: torch.Tensor,        # [B]
        cond: torch.Tensor             # [B, obs_dim] - 条件（观察编码）
    ) -> torch.Tensor:
        """
        预测噪声
        """
        B = noisy_action.shape[0]
        
        # 时间步嵌入 (简化)
        t_emb = timestep.float() / self.n_diffusion_steps  # [B]
        t_emb = t_emb.view(B, 1, 1).expand(-1, -1, self.horizon)  # [B, 1, horizon]
        
        # 拼接输入
        cond_expanded = cond.unsqueeze(-1).expand(-1, -1, self.horizon)  # [B, obs_dim, horizon]
        x = torch.cat([noisy_action, cond_expanded], dim=1)  # [B, act_dim+obs_dim, horizon]
        
        # 预测噪声
        noise_pred = self.noise_pred_net(x)  # [B, act_dim, horizon]
        return noise_pred
    
    def sample(
        self,
        cond: torch.Tensor,
        num_samples: int = 1
    ) -> torch.Tensor:
        """
        DDIM采样生成动作
        
        Args:
            cond: [B, obs_dim] - 观察条件
        Returns:
            action: [B, act_dim, horizon] - 生成的动作序列
        """
        B = cond.shape[0]
        device = cond.device
        
        # 从噪声开始
        x = torch.randn(B, self.action_dim, self.horizon, device=device)
        
        # DDIM采样 (10步加速)
        timesteps = torch.linspace(self.n_diffusion_steps - 1, 0, 10, dtype=torch.long)
        
        for t in timesteps:
            t_batch = torch.full((B,), t, device=device, dtype=torch.long)
            
            # 预测噪声
            noise_pred = self.forward(x, t_batch, cond)
            
            # DDIM更新
            alpha_t = self.alphas_cumprod[t]
            alpha_prev = self.alphas_cumprod[t-1] if t > 0 else torch.tensor(1.0)
            
            pred_x0 = (x - torch.sqrt(1 - alpha_t) * noise_pred) / torch.sqrt(alpha_t)
            x = torch.sqrt(alpha_prev) * pred_x0 + torch.sqrt(1 - alpha_prev) * noise_pred
            
        return x


# =============================================================================
# 模块4: 完整观察编码器 (整合所有模态)
# =============================================================================

class ObservationEncoder(nn.Module):
    """
    完整观察编码器
    
    整合:
    - RGB图像 (ViT-B/16)
    - Tac3D点云 (左右触觉)
    - 机器人本体状态
    """
    def __init__(
        self,
        use_pretrained_vit: bool = True,
        tactile_output_dim: int = 512,
        fusion_output_dim: int = 512
    ):
        super().__init__()
        
        # 视觉编码器 (ViT-B/16)
        if use_pretrained_vit:
            from transformers import ViTModel
            self.rgb_encoder = ViTModel.from_pretrained('google/vit-base-patch16-224')
            # 冻结部分层或微调
            rgb_dim = 768  # ViT-B/16 CLS token维度
        else:
            # 简化版ResNet
            import torchvision.models as models
            resnet = models.resnet18(pretrained=True)
            self.rgb_encoder = nn.Sequential(*list(resnet.children())[:-1])
            rgb_dim = 512
            
        # 触觉编码器
        self.tactile_encoder = TacPointEncoder(output_dim=tactile_output_dim)
        
        # 融合模块
        self.fusion = VisuoTactileFusion(
            rgb_dim=rgb_dim,
            tactile_dim=tactile_output_dim,
            output_dim=fusion_output_dim
        )
        
        # 接触感知门控
        self.contact_gating = ContactAwareGating()
        
    def forward(
        self,
        rgb: torch.Tensor,                    # [B, 3, 224, 224]
        tac3d_left: torch.Tensor,             # [B, 400, 6]
        tac3d_right: torch.Tensor,            # [B, 400, 6]
        proprio: Optional[torch.Tensor] = None  # [B, 10] - 本体状态
    ) -> torch.Tensor:
        """
        Returns:
            obs_feat: [B, fusion_output_dim + proprio_dim] - 完整观察特征
        """
        # 编码各模态
        rgb_feat = self.rgb_encoder(rgb).last_hidden_state[:, 0]  # [B, 768] (CLS token)
        tactile_left = self.tactile_encoder(tac3d_left)           # [B, 512]
        tactile_right = self.tactile_encoder(tac3d_right)         # [B, 512]
        
        # 融合
        fused = self.fusion(rgb_feat, tactile_left, tactile_right)  # [B, 512]
        
        # 拼接本体状态
        if proprio is not None:
            obs_feat = torch.cat([fused, proprio], dim=-1)  # [B, 512+10]
        else:
            obs_feat = fused
            
        return obs_feat


# =============================================================================
# 模块5: 双模式控制器 (位置控制 + 力控制)
# =============================================================================

class HybridController:
    """
    双模式控制器
    
    参考FARM设计:
    - 非接触阶段: 位置控制
    - 接触阶段: 力控制
    """
    def __init__(
        self,
        force_threshold: float = 0.5,  # 接触检测阈值
        kp_force: float = 0.1,         # 力控制P增益
        max_force: float = 5.0         # 最大允许力
    ):
        self.force_threshold = force_threshold
        self.kp_force = kp_force
        self.max_force = max_force
        self.in_contact = False
        
    def control(
        self,
        action: np.ndarray,           # [8] - [dx,dy,dz,dr,dp,dy,grip_width,grip_force]
        current_force: float,         # 当前测量的夹爪力
        current_width: float          # 当前夹爪宽度
    ) -> Dict[str, np.ndarray]:
        """
        生成控制命令
        
        Returns:
            cmd: {
                'position': [6] - 末端执行器位姿命令
                'gripper': scalar - 夹爪命令
                'mode': str - 当前模式
            }
        """
        pos_action = action[:6]       # 位置控制
        target_width = action[6]      # 目标宽度
        target_force = action[7]      # 目标力
        
        # 检测接触
        if abs(current_force) > self.force_threshold:
            self.in_contact = True
            
        # 模式选择
        if self.in_contact and abs(target_force) > 0.1:
            # 力控制模式
            force_error = target_force - current_force
            grip_cmd = current_width + self.kp_force * force_error
            grip_cmd = np.clip(grip_cmd, 0, 0.08)  # 夹爪范围限制
            mode = 'force_control'
        else:
            # 位置控制模式
            grip_cmd = target_width
            mode = 'position_control'
            
        return {
            'position': pos_action,
            'gripper': grip_cmd,
            'mode': mode
        }
    
    def reset(self):
        """重置接触状态"""
        self.in_contact = False


# =============================================================================
# 模块6: 训练脚本框架
# =============================================================================

class Tac3DDiffusionPolicyTrainer:
    """
    训练框架
    """
    def __init__(
        self,
        obs_encoder: ObservationEncoder,
        policy: ForceAwareDiffusionPolicy,
        device: str = 'cuda'
    ):
        self.obs_encoder = obs_encoder.to(device)
        self.policy = policy.to(device)
        self.device = device
        
        # 优化器
        self.optimizer = torch.optim.AdamW(
            list(obs_encoder.parameters()) + list(policy.parameters()),
            lr=3e-4,
            weight_decay=1e-6,
            betas=(0.95, 0.999)
        )
        
        # EMA
        self.ema_decay = 0.995
        
    def train_step(
        self,
        batch: Dict[str, torch.Tensor]
    ) -> Dict[str, float]:
        """
        单步训练
        
        Args:
            batch: {
                'rgb': [B, 3, 224, 224],
                'tac3d_left': [B, 400, 6],
                'tac3d_right': [B, 400, 6],
                'proprio': [B, 10],
                'action': [B, 8, 16]  # 动作序列
            }
        """
        # 编码观察
        obs_feat = self.obs_encoder(
            batch['rgb'],
            batch['tac3d_left'],
            batch['tac3d_right'],
            batch['proprio']
        )  # [B, obs_dim]
        
        # 扩散训练
        B = obs_feat.shape[0]
        
        # 随机采样时间步
        t = torch.randint(0, self.policy.n_diffusion_steps, (B,), device=self.device)
        
        # 添加噪声
        noise = torch.randn_like(batch['action'])
        alpha_t = self.policy.alphas_cumprod[t].view(B, 1, 1)
        noisy_action = torch.sqrt(alpha_t) * batch['action'] + \
                       torch.sqrt(1 - alpha_t) * noise
        
        # 预测噪声
        noise_pred = self.policy(noisy_action, t, obs_feat)
        
        # 损失
        loss = F.mse_loss(noise_pred, noise)
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return {'loss': loss.item()}


# =============================================================================
# 使用示例
# =============================================================================

def demo():
    """使用示例"""
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # 创建模型
    obs_encoder = ObservationEncoder()
    
    # 计算观察维度
    dummy_rgb = torch.randn(1, 3, 224, 224)
    dummy_tac3d = torch.randn(1, 400, 6)
    dummy_proprio = torch.randn(1, 10)
    
    with torch.no_grad():
        dummy_obs = obs_encoder(dummy_rgb, dummy_tac3d, dummy_tac3d, dummy_proprio)
    obs_dim = dummy_obs.shape[1]
    
    policy = ForceAwareDiffusionPolicy(
        observation_dim=obs_dim,
        action_dim=8,  # 7D位置+1D力
        horizon=16
    )
    
    # 创建训练器
    trainer = Tac3DDiffusionPolicyTrainer(obs_encoder, policy, device)
    
    # 模拟训练数据
    batch = {
        'rgb': torch.randn(4, 3, 224, 224).to(device),
        'tac3d_left': torch.randn(4, 400, 6).to(device),
        'tac3d_right': torch.randn(4, 400, 6).to(device),
        'proprio': torch.randn(4, 10).to(device),
        'action': torch.randn(4, 8, 16).to(device)
    }
    
    # 训练一步
    loss_dict = trainer.train_step(batch)
    print(f"Loss: {loss_dict['loss']:.4f}")
    
    # 采样动作
    obs_encoder.eval()
    policy.eval()
    with torch.no_grad():
        obs_feat = obs_encoder(
            batch['rgb'][:1],
            batch['tac3d_left'][:1],
            batch['tac3d_right'][:1],
            batch['proprio'][:1]
        )
        action = policy.sample(obs_feat)  # [1, 8, 16]
    print(f"Sampled action shape: {action.shape}")


if __name__ == '__main__':
    demo()
