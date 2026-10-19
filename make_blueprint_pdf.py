"""Builds docs/research_methodology_blueprint.pdf in the university's AI/ML Research Methodology Blueprint format."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

INK = colors.HexColor("#111111")
TITLE = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=15, alignment=1, spaceAfter=8, textColor=INK)
HDR = ParagraphStyle("Hd", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK)
SEC = ParagraphStyle("S", fontName="Helvetica-Bold", fontSize=11, spaceBefore=3, spaceAfter=1, textColor=INK)
LBL = ParagraphStyle("L", fontName="Helvetica-Bold", fontSize=8.6, leading=10.4, leftIndent=10, textColor=INK)
TXT = ParagraphStyle("X", fontName="Helvetica", fontSize=8.6, leading=10.4, leftIndent=20, spaceAfter=1.5, textColor=INK)
BUL = ParagraphStyle("B", parent=TXT, leftIndent=30, bulletIndent=21)

def item(label, text=None):
    out = [Paragraph(f"- {label}", LBL)]
    if text: out.append(Paragraph(text, TXT))
    return out
def bullets(items): return [Paragraph(i, BUL, bulletText="•") for i in items]

S = [Paragraph("AI/ML RESEARCH METHODOLOGY BLUEPRINT", TITLE)]
hdr = Table([[Paragraph("<b>Student Name / Roll No:</b> Shlok (UAI05BTA2317), Jiya (UAI05BTA2313), Caleb (UAI05BTA2319)", HDR)],
             [Paragraph("<b>Branch:</b> BTech AI ML", HDR)],
             [Paragraph("<b>Project Title / Topic:</b> Neighbourhood-aware misbehavior detection for V2X networks (VeReMi Extension benchmark)", HDR)]],
            colWidths=[16.4*cm])
hdr.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("TOPPADDING", (0,0), (-1,-1), 1), ("BOTTOMPADDING", (0,0), (-1,-1), 1)]))
S += [hdr]

S += [Paragraph("1. PROBLEM FORMULATION:", SEC)]
S += item("Specific ML/AI Problem or Failure Mode Addressed:",
  "Connected vehicles broadcast position, speed and heading; a misbehaving vehicle sends false data (spoofed position, frozen speed, copied trails) that misleads others. "
  "Most learned detectors judge each sender <b>in isolation</b>, so evidence from the surrounding vehicles goes unused, and it is untested how a neighbour-aware "
  "detector behaves when many neighbours are themselves malicious or when attackers collude and tell consistent lies. "
  "Failure mode: missed or slow detection of falsified data, and unknown robustness to malicious neighbours.")

S += [Paragraph("2. HYPOTHESIS FORMULATION:", SEC)]
S += item("Null Hypothesis (H0):",
  "Adding attention across nearby senders (neighbours) gives the same F1 as the same model without it on held-out traffic (F1 with neighbours = F1 without).")
S += item("Alternative Hypothesis (H1):",
  "Neighbour attention gives higher F1 (F1 with &gt; F1 without) with no increase in false positives. "
  "Secondary (H1b): the gain holds even when most of a sender's neighbours are attackers (H0b: the gain shrinks as malicious neighbours increase).")

S += [Paragraph("3. RESEARCH &amp; EXPERIMENTAL DESIGN:", SEC)]
S += item("Dataset to be used (e.g., ImageNet, Kaggle, Custom collected):",
  "VeReMi Extension (public simulated benchmark, Zenodo 20090854; F2MD/VEINS/SUMO, Luxembourg scenario). Main study: 14 of its 19 attack types "
  "(RandomSpeedOffset archive excluded as mislabeled); 109,823 train / 29,547 validation / 68,971 test windows. Extension: 18 attacks, adding the 4 Sybil attacks (88,695 test windows).")
S += item("Baseline Model vs. Proposed Architecture/Modification:",
  "<b>Baselines:</b> a speed-check rule; our first model (transformer on raw claims, no checks); the same model with neighbour attention switched off. "
  "<b>Proposed (v2):</b> small transformer (144k parameters) with temporal and cross-sender (neighbour) attention. Inputs: 9 claim values + 10 plausibility checks "
  "(kinematics, a road map learned from honest traffic, nearest other claim, exact self-repeat, copied trail, log movement). Training adds carefully injected lies "
  "(offset, fake stop); optional receiver-side memory.")
S += item("Evaluation Metrics (e.g., F1-Score, mAP, BLEU, AUC-ROC):")
S += bullets(["<b>Precision:</b> of the senders we flag as malicious, the share that really are (few false alarms).",
              "<b>Recall:</b> of all malicious senders, the share we catch (few missed attackers).",
              "<b>F1-score:</b> balance of precision and recall (their harmonic mean); one-number summary of detection quality.",
              "<b>Accuracy:</b> share of all windows (honest and malicious) classified correctly.",
              "<b>False-positive rate (FPR):</b> share of honest senders wrongly flagged as malicious.",
              "<b>Detection latency:</b> seconds from an attacker's first appearance at a receiver to the first alarm on it.",
              "<b>Colluder recall at matched 1% FPR:</b> how many colluding attackers are caught when false alarms are held at 1%."])

S += [Paragraph("4. PROPOSED VALIDATION STRATEGY:", SEC)]
S += item("(e.g., K-Fold Cross Validation, Statistical Significance Test):")
S += bullets(["Train on the first simulated hour; test on the second hour, whose receivers are split into separate validation (30%) and test (70%) blocks; thresholds and memory decay chosen on validation only; 2 seeds per model.",
              "Two label views: <b>message labels</b> (attacker counted only in windows where it sent a falsified message) and <b>vehicle labels</b> (every window of an attacker vehicle).",
              "Paired bootstrap over receivers (95% CI) with Holm correction across attacks; results by malicious-neighbour share; collusion stress test with consistent lies (offset, fake stop, spoofed convoy, on-road lies)."])

S += [Paragraph("5. EXPECTED AI / COMPUTATIONAL OUTCOME:", SEC)]
S += bullets(["<b>Results (14 attacks, 68,971 test windows, 2 seeds).</b> Message labels: v2 precision 98.65%, recall 97.12%, F1 97.88%, accuracy 98.69%, FPR 0.60%; with memory P 98.16%, R 97.78%, F1 97.97%, accuracy 98.74%. "
              "Vehicle labels: v2 F1 97.01% (recall 95.41%); with memory F1 97.12%. First model F1 94.9% (vehicle labels); speed-check rule F1 78.9%.",
              "<b>Neighbour attention:</b> +0.3 F1 points (95% CI about [0.2, 0.4]), significant on 8-10 of 14 attacks, FPR 0.90% to 0.60%, so H0 is rejected. "
              "H1b is not supported: the gain shrinks and turns slightly negative when attackers are the majority of neighbours.",
              "<b>Latency:</b> mean 0.9 s to first alarm (median 0); 96% of attacker-receiver pairs flagged. <b>Collusion:</b> v2 catches 50 m offsets (recall 0.83-0.86), fake stops (about 0.70) and unseen spoofed convoys (0.87-0.90), "
              "where the first model caught at most 0.04; lies that follow the road map stay hard (0.23-0.48).",
              "<b>Sybil extension (18 attacks, senders tracked by pseudonym, 3-model ensemble):</b> message labels P 96.30%, R 95.46%, F1 95.88%, accuracy 97.04%, FPR 2.07%; vehicle labels F1 95.38%. "
              "Neighbour attention adds about +1.3 F1 here. Main miss: GridSybil ghosts (recall 0.82), which pass every content check.",
              "Reference: a 2025 IEEE T-ITS survey lists 97.37% for VeReMi (original 5 attacks, no Sybil); on 14 attacks v2 + memory is above it on all four metrics with message labels, on 18 attacks all four are below it; not like-for-like. "
              "Open: original VeReMi/NextGen check, dense traffic, a 3rd seed; on-road lies and GridSybil ghosts need an independent signal (signal strength, sensors, RSUs)."])

SimpleDocTemplate("docs/research_methodology_blueprint.pdf", pagesize=A4, leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=0.9*cm, bottomMargin=0.8*cm,
                  title="AI/ML Research Methodology Blueprint").build(S)
