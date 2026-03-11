import os
import pdfplumber

PDFS = [
    r"f:\论文收集\ForceVLA_2505.22159.pdf",
    r"f:\论文收集\TacDiffusion_2409.11047.pdf",
    r"f:\论文收集\ManiCM_Real-time_3D_Diffusion_Policy_via_Consistency_Model_2406.01586.pdf",
    r"f:\论文收集\FlowPolicy_2412.04987.pdf",
    r"f:\论文收集\PointFlowMatch_Learning_Robotic_Manipulation_Policies_from_Point_Clouds_with_Conditional_Flow_Matching_2409.07343.pdf",
    r"f:\论文收集\Scaling_Diffusion_Policy_in_Transformer_to_1_Billion_Parameters_2409.14411.pdf",
    r"f:\论文收集\SpatialVLA_Exploring_Spatial_Representations_for_Visual-Language-Action_Model_2501.15830.pdf",
    r"f:\论文收集\Spec-VLA_Speculative_Decoding_for_Vision-Language-Action_Models_2507.22424.pdf",
    r"f:\论文收集\ET-SEED_Efficient_Trajectory-Level_SE(3)_Equivariant_Diffusion_Policy_2411.03990.pdf",
    r"f:\论文收集\CordViP_2502.08449.pdf",
    r"f:\论文收集\ViViDex_Learning_Vision-based_Dexterous_Manipulation_from_Human_Videos_2404.15709.pdf",
    r"f:\论文收集\FACTR_2502.17432.pdf",
    r"f:\论文收集\Bi-LAT_2504.01301.pdf",
    r"f:\论文收集\GR00T_N1_Open_Foundation_Model_for_Generalist_Humanoid_Robots_2503.14734.pdf",
    r"f:\论文收集\Gemini_Robotics_Bringing_AI_into_the_Physical_World_2503.20020.pdf",
    r"f:\论文收集\PointVLA_2503.07511.pdf",
]

OUT_DIR = r"f:\论文收集\_extracted_full"

def extract_pdf(path):
    lines = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines.append(f"=== Page {i} ===")
            lines.append(text)
    return "\n".join(lines)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for pdf_path in PDFS:
        if not os.path.exists(pdf_path):
            continue
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        out_path = os.path.join(OUT_DIR, f"{base}.txt")
        if os.path.exists(out_path):
            continue
        text = extract_pdf(pdf_path)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)

if __name__ == "__main__":
    main()
