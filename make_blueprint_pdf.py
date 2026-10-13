"""Builds docs/research_methodology_blueprint.pdf in the university's AI/ML Research Methodology Blueprint format."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

INK = colors.HexColor("#111111")
TITLE = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=15, alignment=1, spaceAfter=8, textColor=INK)
HDR = ParagraphStyle("Hd", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK)
SEC = ParagraphStyle("S", fontName="Helvetica-Bold", fontSize=11, spaceBefore=7, spaceAfter=1, textColor=INK)
LBL = ParagraphStyle("L", fontName="Helvetica-Bold", fontSize=8.9, leading=11.4, leftIndent=10, textColor=INK)
TXT = ParagraphStyle("X", fontName="Helvetica", fontSize=8.9, leading=11.4, leftIndent=20, spaceAfter=1.5, textColor=INK)
BUL = ParagraphStyle("B", parent=TXT, leftIndent=30, bulletIndent=21)

def item(label, text=None):
    out = [Paragraph(f"- {label}", LBL)]
    if text: out.append(Paragraph(text, TXT))
    return out
def bullets(items): return [Paragraph(i, BUL, bulletText="•") for i in items]

S = [Paragraph("AI/ML RESEARCH METHODOLOGY BLUEPRINT", TITLE)]
hdr = Table([[Paragraph("<b>Student Name:</b> Shlok, Jiya, Caleb (team)", HDR), Paragraph("<b>Branch:</b> BTech AI ML", HDR)],
             [Paragraph("<b>Roll No:</b> Shlok - UAI05BTA2317, Jiya - UAI05BTA2313, Caleb - UAI05BTA2323", HDR), ""],
             [Paragraph("<b>Project Title / Topic:</b> Neighbourhood-aware misbehavior detection for V2X networks (VeReMi Extension benchmark)", HDR), ""]],
            colWidths=[11.4*cm, 5.0*cm])
hdr.setStyle(TableStyle([("SPAN", (0,1), (1,1)), ("SPAN", (0,2), (1,2)), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("TOPPADDING", (0,0), (-1,-1), 1), ("BOTTOMPADDING", (0,0), (-1,-1), 1)]))
S += [hdr]

S += [Paragraph("1. PROBLEM FORMULATION:", SEC)]
S += item("Specific ML/AI Problem or Failure Mode Addressed:",
  "Connected vehicles broadcast position, speed and heading. A misbehaving vehicle sends false data (random or spoofed position, frozen speed) that misleads others. "
  "Most learned detectors judge each sender <b>in isolation</b>, so evidence from the surrounding vehicles goes unused, and it is untested how a neighbour-aware "
  "detector behaves when many neighbours are themselves malicious (cooperative schemes often assume an honest majority). "
  "Failure mode: missed or slow detection of falsified data, and unknown robustness to malicious neighbours.")

S += [Paragraph("2. HYPOTHESIS FORMULATION:", SEC)]
S += item("Null Hypothesis (H0):",
  "A detector that also attends to the 16 nearest neighbours has the same F1 as the per-sender baseline on held-out traffic (F1 full = F1 per-sender).")
S += item("Alternative Hypothesis (H1):",
  "The neighbourhood-aware detector has higher F1 (F1 full &gt; F1 per-sender), with higher recall and shorter detection latency and no increase in false positives. "
  "Secondary (H1b): its recall stays within about 2 points of its clean value even when over half of a sender's neighbours are malicious (H0b: recall falls as malicious neighbours increase).")

S += [Paragraph("3. RESEARCH &amp; EXPERIMENTAL DESIGN:", SEC)]
S += item("Dataset to be used (e.g., ImageNet, Kaggle, Custom collected):",
  "VeReMi Extension (public benchmark, Zenodo; simulated traffic and attackers, F2MD/VEINS/SUMO, Luxembourg scenario, 30% attackers, 19 attack types). "
  "Done: RandomPos and ConstSpeed (14:00-16:00). Planned: other attacks, dense 07:00-09:00 subsets, MixAll_0024, VeReMi NextGen. "
  "Windows: 16 nearest senders x 10 s (61,708 train / 11,251 val / 26,255 test).")
S += item("Baseline Model vs. Proposed Architecture/Modification:",
  "<b>Baseline:</b> per-sender transformer (no neighbour information); also a no-spatial ablation. "
  "<b>Proposed:</b> factorised temporal + spatial transformer in which each sender attends over its own history and over the other senders in the window.")
S += item("Evaluation Metrics (e.g., F1-Score, mAP, BLEU, AUC-ROC):")
S += bullets(["<b>Precision:</b> of the senders we flag as malicious, the share that really are (few false alarms).",
              "<b>Recall:</b> of all malicious senders, the share we catch (few missed attackers).",
              "<b>F1-score:</b> balance of precision and recall (their harmonic mean); one-number summary of detection quality.",
              "<b>False-positive rate (FPR):</b> share of honest senders wrongly flagged as malicious.",
              "<b>AUC-ROC:</b> how well the model ranks malicious senders above honest ones over all thresholds (1.0 perfect, 0.5 random).",
              "<b>Detection latency:</b> seconds from a sender's first appearance to the first alarm raised on it.",
              "<b>Recall/FPR by malicious-neighbour share:</b> checks the detector still works when many of a sender's neighbours are attackers."])

S += [Paragraph("4. PROPOSED VALIDATION STRATEGY:", SEC)]
S += item("(e.g., K-Fold Cross Validation, Statistical Significance Test):")
S += bullets(["<b>Done:</b> train on the first hour, test on the later hour; receiver-disjoint validation/test blocks; threshold chosen on validation only; 3 seeds per model (mean and std). No formal significance test yet.",
              "<b>Planned:</b> grouped 5-fold cross-validation by receiver vehicle (5-10 seeds); paired bootstrap 95% CIs on the F1 difference; Wilcoxon signed-rank test across folds/seeds and McNemar's test on paired decisions; "
              "Holm-Bonferroni correction across attack types; colluding-attacker stress test; low-to-high density transfer."])

S += [Paragraph("5. EXPECTED AI / COMPUTATIONAL OUTCOME:", SEC)]
S += bullets(["The neighbour-aware model is expected to beat the per-sender baseline by about 1 F1 point, mainly through recall. Preliminary (2 attacks, 3 seeds): F1 0.982 vs 0.973, recall 0.975 vs 0.959, precision 0.989 vs 0.987, FPR about 0.5% for both.",
              "Faster alarms (preliminary mean latency 0.15 s vs 0.70 s) and recall near 0.97 even with over 50% malicious neighbours (0.971 vs 0.973 clean).",
              "Some attacks may not benefit: ConstSpeed was slightly worse with neighbours (0.948 vs 0.960), so H0 should be rejected overall, not necessarily for every attack.",
              "Small model (about 0.6 MB, about 10 min CPU training). Scope: simulated benchmark, independent attackers; no collusion or crash intent."])

SimpleDocTemplate("docs/research_methodology_blueprint.pdf", pagesize=A4, leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=1.1*cm, bottomMargin=1.0*cm,
                  title="AI/ML Research Methodology Blueprint").build(S)
