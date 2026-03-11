# ForceVLA_2505.22159

## 1. 研究背景

**核心**：
VLA 依赖视觉与语言，但接触丰富任务在插入、装配、工具使用中高度依赖外力/力矩反馈。现有 VLA 在视觉遮挡、动力学不确定时缺少“接触相位感知”，导致动作无法随接触状态动态调整。论文从 VLA、接触操控与 MoE 三条路线回溯：VLA 在语义与空间规划上强，但缺乏力模态；力/触觉策略在接触稳定性上有效，但缺乏 VLA 的通用泛化；MoE 在多模态中具备稀疏路由与阶段化处理能力。  
**来源**：https://arxiv.org/abs/2505.22159

## 2. 研究问题

**核心**：
在 VLA 框架中把 6 轴外力/力矩作为一级模态，并让动作解码显式依赖“接触相位”的力信息，从而提升插入、擦拭、剥皮等接触任务的成功率与稳定性。  
**来源**：https://arxiv.org/abs/2505.22159

## 3. 核心创新工作

**核心**：
1. **任务形式化与观测定义**：  
   - 观测：O_t = {V^b_t, V^h_t, s_t, f_t}，包含基座与手部视觉、7 维本体状态 s_t（TCP 位姿+夹爪宽度）与 6 维外力/力矩 f_t。  
   - 动作：A_t = {a_t, …, a_{t+H-1}} 的动作块，动作由 TCP 位姿 (x,y,z, α,β,γ) + 夹爪宽度构成。  
2. **ForceVLA 总体结构**：  
   - 基于 π 框架的 flow matching 动作解码。  
   - SigLIP + PaLiGemma 形成 VLM 编码，输出视觉-语言 token。  
   - 力模态经线性映射形成 force token，并在解码阶段与 VLM token 融合。  
3. **FVLMoE 模块（关键结构细节）**：  
   - 输入序列 E_in = [E_VL; E_F]，E_VL 为 VLM token，E_F = ϕ_F(f_raw) 为单个 force token。  
   - 共享编码层：多头自注意力 + FFN 进行跨模态交互。  
   - MoE 层：E=4 个专家 MLP，top‑k=1 的动态路由，MoE 输出与输入残差相加得到 E_fused。  
   - 线性投影对齐动作专家维度。  
4. **动作注入机制**：  
   - 从 E_fused 取最后 H_action 个 token 形成 G_FVLMoE，  
   - 与由机器人状态 s_t 与噪声动作 a^τ_t 形成的 S_suffix 做逐元素相加，作为 flow 头条件，引导去噪。  
5. **ForceVLA‑Data 数据集**：  
   - 平台：Flexiv Rizon 7‑DoF + Dahuan 自适应夹爪；D435（1280×720@30FPS，第三视角）+ D415（640×480@30FPS，腕部）。  
   - 采集：Quest 3 VR 遥操作，5 名操作者，5 个任务（bottle pumping、plug insertion、USB insertion、whiteboard wiping、cucumber peeling）。  
   - 规模：244 轨迹、约 14 万同步步，图像统一到 480×640，动作表示为目标 TCP 位姿+夹爪宽度。  
**来源**：https://arxiv.org/abs/2505.22159

## 4. 关键实验设计

**核心**：
1. **任务定义与成功条件**：  
   - 插入类：完成插入为成功；  
   - Whiteboard wiping：Wipe‑1 为擦拭动作成功，Wipe‑2 为完全擦净；  
   - Cucumber peeling：平均剥离长度与最少剥离次数作为效率指标。  
2. **评测次数**：插入/泵压各 20 次，白板 10 次，黄瓜 15 次（每次 15 次剥离）。  
3. **基线对比**：  
   - π0‑base w/o F、π0‑base w/ F、π0‑fast w/o F、π0‑fast w/ F。  
   - 重点比较“直接拼接力输入”与“FVLMoE 融合”的差异。  
4. **泛化设置**（Table 2）：  
   - Object Gen.1（瓶型变化）、Object Gen.2（插头变化）、Height Gen.（高度变化）、Visual Occlusion（遮挡）、Unstable Socket（不稳插座）。  
5. **消融设计**（Table 3）：  
   - 线性/ MoE 早融合（before VLM），  
   - 视觉-语言后拼接（concatenate after VLM），  
   - FVLMoE（ForceVLA）。  
**来源**：https://arxiv.org/abs/2505.22159

## 5. 核心结果与关键Insight

**核心**：
1. **整体成功率**：ForceVLA 平均成功率 60.5%，比 π0‑base w/o F 的 37.3% 提升 23.2%。  
2. **剥黄瓜精细指标**：平均剥离长度 14.12 cm、最少剥离 7 次，优于 π0‑base w/F（13.17 cm, 10 次）与 w/o F（10.27 cm, 14 次）。  
3. **泛化表现（Table 2）**：ForceVLA 在 Object Gen.1/2/Height/Visual Occlusion/Unstable Socket 分别达到 80.00% / 40.00% / 88.89% / 90.00% / 20.00%，平均 63.78%，显著高于所有基线。  
4. **消融验证**：  
   - “MoE before VLM” 直接失败（0%），说明破坏预训练 VLM 表征。  
   - “concatenate after VLM” 提升到 60%，但仍低于 ForceVLA 的 80%。  
5. **关键 Insight**：  
   - 力信号仅作为输入并不够；需要在 VLM 之后进行“相位感知”的稀疏路由融合。  
   - FVLMoE 的后融合 + MoE 路由是提升接触鲁棒性的核心。  
**来源**：https://arxiv.org/abs/2505.22159

## 6. 待解决问题与未来方向

**核心**：
1. 外力/力矩为估计值，高精度接触任务仍受限于传感精度与标定质量。  
2. 实验依赖高成本力矩传感平台，需验证在低成本或外接传感器平台上的可迁移性。  
**来源**：https://arxiv.org/abs/2505.22159
