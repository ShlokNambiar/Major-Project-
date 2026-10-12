"""Builds docs/research_plan.pdf (problem, hypotheses, design, validation, expected outcome)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

NAVY, TEAL = colors.HexColor("#0B1F33"), colors.HexColor("#1C7C7D")
ss = getSampleStyleSheet()
T = ParagraphStyle("T", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=19, textColor=NAVY, alignment=0, spaceAfter=2)
SUB = ParagraphStyle("S", parent=ss["Normal"], fontSize=10, textColor=colors.HexColor("#5B6B7A"), spaceAfter=10)
H = ParagraphStyle("H", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=TEAL, spaceBefore=12, spaceAfter=4)
L = ParagraphStyle("L", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=10.5, textColor=NAVY, spaceBefore=6, spaceAfter=1)
B = ParagraphStyle("B", parent=ss["Normal"], fontName="Helvetica", fontSize=10.5, leading=14.5, spaceAfter=3)
BL = ParagraphStyle("BL", parent=B, leftIndent=14, bulletIndent=2)
def bl(items): return [Paragraph(i, BL, bulletText="•") for i in items]

S = []
S += [Paragraph("Neighbourhood-aware misbehavior detection for V2X", T),
      Paragraph("Research plan: problem, hypotheses, experimental design and validation. Status: work in progress; results quoted are preliminary.", SUB)]

S += [Paragraph("1. Problem formulation", H), Paragraph("Specific ML/AI problem or failure mode addressed", L),
 Paragraph("Connected vehicles broadcast Basic Safety Messages (position, speed, heading). A misbehaving vehicle can send false data, "
  "for example a random or spoofed position or a frozen speed, which misleads other vehicles. Most learned detectors judge each sender "
  "<b>in isolation</b>, so a sender's lie is only visible against its own history. They ignore what the surrounding vehicles report, "
  "and the evidence from neighbours that could expose an inconsistency goes unused.", B),
 Paragraph("The failure mode we address has two parts:", B)]
S += bl(["<b>Missed or slow detection of falsified data</b> when a sender is judged alone (lower recall, longer time to first alarm).",
         "<b>Unknown behaviour when neighbours are themselves malicious.</b> Cooperative schemes often assume an honest majority and fail under collusion "
         "(2025 V2X intrusion-detection survey); it is untested whether a neighbour-aware learned detector degrades when many neighbours are attackers."])

S += [Paragraph("2. Hypothesis formulation", H),
 Paragraph("Primary hypothesis", L),
 Paragraph("<b>Null hypothesis (H0):</b> A detector that also attends to the 16 nearest neighbours has the same detection quality (F1) as the per-sender "
           "baseline on held-out traffic: F1<sub>full</sub> = F1<sub>per-sender</sub>.", B),
 Paragraph("<b>Alternative hypothesis (H1):</b> The neighbourhood-aware detector achieves higher F1 than the per-sender baseline: "
           "F1<sub>full</sub> &gt; F1<sub>per-sender</sub>, and it raises recall and shortens detection latency without raising the false-positive rate.", B),
 Paragraph("Secondary hypothesis (robustness to malicious neighbours)", L),
 Paragraph("<b>H0b:</b> Recall of the neighbour-aware detector falls as the share of malicious neighbours rises (it is poisoned by them).", B),
 Paragraph("<b>H1b:</b> Recall stays within a small margin (e.g. 2 points) of its value at 0 to 10% malicious neighbours, even above 50%.", B)]

rows = [["Item", "Choice"],
 ["Dataset", "VeReMi Extension (public benchmark, simulated traffic and attackers; F2MD / VEINS / SUMO, Luxembourg LuST scenario, 30% attackers). "
             "Done: RandomPos and ConstSpeed (14:00-16:00). Planned: the other 17 attack types, the 07:00-09:00 dense subsets, MixAll_0024 (full day, all attacks), "
             "then VeReMi NextGen / original VeReMi as external checks."],
 ["Input / windows", "Receiver-centric windows: K = 16 nearest senders x T = 10 one-second steps; 8 features per step (relative position, speed, heading, motion deltas, validity). "
             "Preliminary split: 61,708 train, 11,251 validation, 26,255 test windows."],
 ["Baseline", "<b>Per-sender</b> model: the same transformer without neighbour information. Also the <b>no-spatial</b> ablation (sees neighbours, no cross-sender attention). "
             "Planned: a rule-based reference (range / speed checks from the original VeReMi paper) for context."],
 ["Proposed", "<b>Full model:</b> factorised temporal then spatial transformer; each sender attends over its own history and over the other senders in the window."],
 ["Metrics", "Precision, recall, F1, false-positive rate (FPR), AUC-ROC (per attack and overall), <b>detection latency</b> (seconds from a sender's first appearance to the first alarm), "
             "and recall / FPR stratified by the share of malicious neighbours."]]
HW = ParagraphStyle("hw", parent=B, textColor=colors.white, fontName="Helvetica-Bold")
tbl = Table([[Paragraph(a, HW) for a in rows[0]]] + [[Paragraph(f"<b>{r[0]}</b>", B), Paragraph(r[1], B)] for r in rows[1:]], colWidths=[3.2*cm, 13.3*cm], repeatRows=1)
tbl.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                         ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#C9D3DA")), ("VALIGN", (0,0), (-1,-1), "TOP"),
                         ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F3F7F8")])]))
S += [Paragraph("3. Research and experimental design", H), tbl]

S += [Paragraph("4. Proposed validation strategy", H),
 Paragraph("Done so far", L)]
S += bl(["Train on the first hour of the simulation, test on the later hour; validation and test are separate blocks of receivers, and the alarm threshold is chosen on validation only.",
         "3 random seeds per model; mean and standard deviation reported (std 0.001 to 0.004 in F1). <b>No formal significance test has been run yet.</b>"])
S += [Paragraph("Planned", L)]
S += bl(["<b>Grouped K-fold cross-validation (K = 5)</b>, grouping by receiver vehicle and keeping time ordering, so no vehicle's log is in both train and test; 5 to 10 seeds per fold.",
         "<b>Statistical significance:</b> paired bootstrap 95% confidence intervals on the F1 difference (resampling receivers); Wilcoxon signed-rank test across folds and seeds "
         "for full vs per-sender; McNemar's test on paired alarm decisions.",
         "<b>Multiple comparisons:</b> Holm-Bonferroni correction across attack types.",
         "<b>Robustness:</b> recall and FPR by malicious-neighbour share; a colluding-attacker scenario (attackers coordinating false reports) as a stress test.",
         "<b>Generalisation:</b> train on low-density, test on rush-hour (dense) traffic; leave-one-attack-out; external check on VeReMi NextGen."])

S += [Paragraph("5. Expected AI / computational outcome", H)]
S += bl(["<b>Detection quality:</b> the neighbour-aware model is expected to beat the per-sender baseline by roughly 1 F1 point overall, mainly through higher recall. "
         "Preliminary result (2 attacks, 3 seeds): F1 0.982 vs 0.973, recall 0.975 vs 0.959, precision 0.989 vs 0.987, FPR about 0.5% for both.",
         "<b>Latency:</b> a faster first alarm; preliminary mean 0.15 s vs 0.70 s, 99% vs 96% of attacker-receiver pairs eventually flagged "
         "(counted from the first window containing the sender, so each window already holds about 10 s of history).",
         "<b>Robustness:</b> recall expected to stay near 0.97 even when most neighbours are malicious; preliminary: 0.971 at over 50% malicious neighbours vs 0.973 at 0 to 10%.",
         "<b>Honest expectation of limits:</b> some attacks may not benefit. ConstSpeed was slightly worse with neighbours in the preliminary run (0.948 vs 0.960), "
         "so H0 is expected to be rejected overall and for RandomPos, but not necessarily for every attack type.",
         "<b>Computational cost:</b> a small model (about 0.6 MB of weights) trained in roughly 10 minutes on CPU, suitable for on-board evaluation; to be measured as inference time per window."]) 
S += [Spacer(1, 6), Paragraph("<i>Scope: the benchmark is simulated, attackers act independently, and only 2 of 19 attack types have been run so far. Collusion and crash intent are not modelled.</i>", B)]

SimpleDocTemplate("docs/research_plan.pdf", pagesize=A4, leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=1.5*cm, bottomMargin=1.5*cm,
                  title="Research plan: neighbourhood-aware misbehavior detection for V2X").build(S)
