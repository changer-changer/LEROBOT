# Scaling_Diffusion_Policy_in_Transformer_to_1_Billion_Parameters_2409.14411

## 1. 研究背景

**核心**：
扩散策略具备可扩展潜力，但 DP‑T 在规模扩大时出现训练不稳定与性能下降。  
**来源**：https://arxiv.org/abs/2409.14411

## 2. 研究问题

**核心**：
如何稳定训练 DP‑T 并实现从 10M 到 1B 参数的可扩展扩散 Transformer 策略。  
**来源**：https://arxiv.org/abs/2409.14411

## 3. 核心创新工作

**核心**：
1. **AdaLN 条件融合**：用多层仿射特征融合替代 cross‑attention，降低梯度不稳定。  
2. **非因果注意力**：移除 masked attention，使动作 token 能看到未来动作，提升长序列建模稳定性。  
3. **ScaleDP 规模化配置**：Ti/S/B/L/H 五种规模，从 10M 扩展到 1B。  
**来源**：https://arxiv.org/abs/2409.14411

## 4. 关键实验设计

**核心**：
1. **仿真**：MetaWorld 50 任务，20 demos×3 seeds。  
2. **真实机器人**：  
   - 单臂 Franka 4 任务（Close Laptop、Flip Mug、Stack Cube、Place Tennis）。  
   - 双臂 UR5 3 任务（Put Tennis Ball into Bag、Sweep Trash、Bimanual Stack Cube）。  
3. **对比基线**：DP‑T、DP‑Unet、ACT、MDT、Octo、Beso。  
**来源**：https://arxiv.org/abs/2409.14411

## 5. 核心结果与关键Insight

**核心**：
1. **MetaWorld**：ScaleDP 平均提升 21.6%。  
2. **真实机器人**：  
   - 单臂平均提升 36.25%（ScaleDP‑H 87.5% vs DP‑T 51.25%）。  
   - 双臂平均提升 75%（ScaleDP‑H 98.33% vs DP‑T 23.33%）。  
3. **非因果注意力消融**：双臂任务成功率提升显著。  
**来源**：https://arxiv.org/abs/2409.14411

## 6. 待解决问题与未来方向

**核心**：
规模化训练仍需探索更大数据规模下的稳定性与泛化规律。  
**来源**：https://arxiv.org/abs/2409.14411
