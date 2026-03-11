import os
import re

BASE_DIR = r"f:\论文收集"
TXT_DIR = os.path.join(BASE_DIR, "_extracted_full")

TARGETS = [
    "ManiCM_Real-time_3D_Diffusion_Policy_via_Consistency_Model_2406.01586",
    "FlowPolicy_2412.04987",
    "PointFlowMatch_Learning_Robotic_Manipulation_Policies_from_Point_Clouds_with_Conditional_Flow_Matching_2409.07343",
    "Scaling_Diffusion_Policy_in_Transformer_to_1_Billion_Parameters_2409.14411",
    "SpatialVLA_Exploring_Spatial_Representations_for_Visual-Language-Action_Model_2501.15830",
    "Spec-VLA_Speculative_Decoding_for_Vision-Language-Action_Models_2507.22424",
    "ET-SEED_Efficient_Trajectory-Level_SE(3)_Equivariant_Diffusion_Policy_2411.03990",
    "CordViP_2502.08449",
    "ViViDex_Learning_Vision-based_Dexterous_Manipulation_from_Human_Videos_2404.15709",
    "FACTR_2502.17432",
    "Bi-LAT_2504.01301",
    "GR00T_N1_Open_Foundation_Model_for_Generalist_Humanoid_Robots_2503.14734",
    "Gemini_Robotics_Bringing_AI_into_the_Physical_World_2503.20020",
    "PointVLA_2503.07511",
]

def load_text(name):
    path = os.path.join(TXT_DIR, f"{name}.txt")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def clean_lines(text):
    raw = [l.strip() for l in text.splitlines()]
    lines = []
    for l in raw:
        if not l or l.startswith("=== Page"):
            continue
        if re.fullmatch(r"[\d\.\-]+", l):
            continue
        letters = sum(ch.isalpha() for ch in l)
        if letters == 0:
            continue
        if letters / max(len(l), 1) < 0.3:
            continue
        if re.search(r"\[\d+\]", l):
            continue
        lines.append(l)
    return lines

def pick_lines(text, patterns, limit=25, max_len=220):
    lines = clean_lines(text)
    out = []
    seen = set()
    for line in lines:
        if any(re.search(p, line, flags=re.IGNORECASE) for p in patterns):
            if line not in seen:
                seen.add(line)
                out.append(line[:max_len])
        if len(out) >= limit:
            break
    return out

def build_md(name, text):
    figs = pick_lines(text, [r"^Fig\.", r"^Figure", r"^TABLE", r"^Table"], limit=80)
    intro = pick_lines(text, [r"Introduction", r"background", r"motivation", r"challenge"], limit=25)
    problem = pick_lines(text, [r"we propose", r"goal", r"aim", r"problem", r"challenge"], limit=20)
    method = pick_lines(text, [r"framework", r"method", r"pipeline", r"model", r"architecture", r"encoder", r"decoder", r"diffusion", r"training"], limit=30)
    exp = pick_lines(text, [r"experiment", r"setup", r"dataset", r"data collection", r"evaluation", r"task", r"metric", r"benchmark"], limit=30)
    results = pick_lines(text, [r"success rate", r"runtime", r"performance", r"improve", r"table", r"fig\."], limit=35)
    future = pick_lines(text, [r"conclusion", r"future", r"limitation"], limit=15)

    def block(lines):
        if not lines:
            return "（未在全文中找到明确段落，需人工补充）"
        return "\n".join([f"> {l}" for l in lines])

    md = []
    md.append(f"# {name}")
    md.append("")
    md.append("## 1. 研究背景")
    md.append("")
    md.append("**核心**：")
    md.append(block(intro))
    md.append("")
    md.append("## 2. 研究问题")
    md.append("")
    md.append("**核心**：")
    md.append(block(problem))
    md.append("")
    md.append("## 3. 核心创新工作")
    md.append("")
    md.append("**核心**：")
    md.append(block(method))
    md.append("")
    md.append("## 4. 关键实验设计")
    md.append("")
    md.append("**核心**：")
    md.append(block(exp))
    md.append("")
    md.append("## 5. 核心结果与关键Insight")
    md.append("")
    md.append("**核心**：")
    md.append(block(results))
    md.append("")
    md.append("## 6. 待解决问题与未来方向")
    md.append("")
    md.append("**核心**：")
    md.append(block(future))
    md.append("")
    md.append("## 7. 图表与实验细节摘录")
    md.append("")
    md.append("**核心**：")
    md.append(block(figs))
    md.append("")
    return "\n".join(md)

def main():
    for name in TARGETS:
        text = load_text(name)
        if not text:
            continue
        md = build_md(name, text)
        md_path = os.path.join(BASE_DIR, f"{name}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)

if __name__ == "__main__":
    main()
