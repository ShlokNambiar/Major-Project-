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
      Paragraph("Research plan: problem, hypotheses, experimental design and validation. Status: final. 14 of 19 attack types run, collusion study done, v2 detector done, paper drafted (paper/main.tex). Results quoted are final (mean of 2 seeds).", SUB)]

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
 Paragraph("<b>Null hypothesis (H0):</b> A detector that also attends to the 16 nearest neighbours has the same detection quality (F1) as the same model "
           "without neighbour attention on held-out traffic: F1<sub>full</sub> = F1<sub>no-nbr</sub>.", B),
 Paragraph("<b>Alternative hypothesis (H1):</b> The neighbourhood-aware detector achieves higher F1 than the same model without neighbour attention: "
           "F1<sub>full</sub> &gt; F1<sub>no-nbr</sub>, without raising the false-positive rate.", B),
 Paragraph("Secondary hypothesis (robustness to malicious neighbours)", L),
 Paragraph("<b>H0b:</b> Recall of the neighbour-aware detector falls as the share of malicious neighbours rises (it is poisoned by them).", B),
 Paragraph("<b>H1b:</b> Recall stays within a small margin (e.g. 2 points) of its value at 0 to 10% malicious neighbours, even above 50%.", B)]

rows = [["Item", "Choice"],
 ["Dataset", "VeReMi Extension (public benchmark, simulated traffic and attackers; F2MD / VEINS / SUMO, Luxembourg LuST scenario, 30% attackers). "
             "Zenodo record 20090854. Done: 14 of 19 attack types (14:00-16:00); Sybil attacks not run; the RandomSpeedOffset archive was excluded as mislabeled. "
             "Not done: Sybil, dense (07:00-09:00) traffic for v2, original VeReMi / VeReMi NextGen as external checks."],
 ["Input / windows", "Receiver-centric windows: K = 16 nearest senders x T = 10 one-second steps. v2 inputs per sender and step: 9 claim values + 10 plausibility checks "
             "(kinematics, road map learned from honest traffic, nearest other claim, exact self-repeat, copied trail, log movement). "
             "Split: 109,823 train, 29,547 validation, 68,971 test windows."],
 ["Baseline", "<b>Per-sender</b> model: the same transformer without neighbour information. Also the <b>no-spatial</b> ablation (sees neighbours, no cross-sender attention). "
             "Rule-based reference: range and speed-consistency checks from the original VeReMi paper. Also the first model (same design, no checks)."],
 ["Proposed", "<b>Final model (v2):</b> small factorised transformer (144k parameters) with temporal and cross-sender (neighbour) attention over the 19 inputs; "
             "training adds careful injected lies (offset, fake stop); a receiver-side memory carries evidence across windows."],
 ["Metrics", "Precision, recall, F1, false-positive rate (FPR), AUC-ROC (per attack and overall), <b>detection latency</b> (seconds from a sender's first appearance to the first alarm), "
             "recall / FPR stratified by the share of malicious neighbours, and colluder recall at matched 1% FPR. Scored with message labels "
             "(attacker counted only in windows where it sent a falsified message) and vehicle labels (every window of an attacker vehicle)."]]
HW = ParagraphStyle("hw", parent=B, textColor=colors.white, fontName="Helvetica-Bold")
tbl = Table([[Paragraph(a, HW) for a in rows[0]]] + [[Paragraph(f"<b>{r[0]}</b>", B), Paragraph(r[1], B)] for r in rows[1:]], colWidths=[3.2*cm, 13.3*cm], repeatRows=1)
tbl.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                         ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#C9D3DA")), ("VALIGN", (0,0), (-1,-1), "TOP"),
                         ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F3F7F8")])]))
S += [Paragraph("3. Research and experimental design", H), tbl]

S += [Paragraph("4. Proposed validation strategy", H),
 Paragraph("Done so far", L)]
S += bl(["Train on the first hour of the simulation, test on the second hour; validation and test are separate blocks of receivers, and thresholds and memory decay are chosen on validation only.",
         "2 random seeds per model; results are the mean of the two.",
         "<b>Statistical significance:</b> paired bootstrap over receivers (2,000 resamples) with Holm correction across attacks.",
         "<b>Robustness:</b> results by malicious-neighbour share; a collusion stress test (coordinated consistent lies, colluder recall at matched 1% FPR)."])
S += [Paragraph("Remaining / next steps", L)]
S += bl(["<b>Sybil attacks</b> (not yet run).",
         "<b>External check</b> on original VeReMi and VeReMi NextGen.",
         "<b>Dense (rush-hour) traffic</b> for the v2 detector.",
         "<b>A 3rd seed</b> for every model.",
         "<b>On-road consistent lies</b> need an independent signal (signal strength, on-board sensors or roadside units); the claims alone are not enough."])

S += [Paragraph("5. Outcome (final results)", H)]
S += bl(["<b>Detection quality (v2, message labels):</b> precision 98.65, recall 97.12, F1 97.88, accuracy 98.69, FPR 0.60%. With receiver memory: "
         "precision 98.16, recall 97.78, F1 97.97, accuracy 98.74.",
         "<b>Vehicle labels:</b> v2 precision 98.65, recall 95.41, F1 97.01, accuracy 98.14; with memory recall 96.09, F1 97.12, accuracy 98.20. "
         "First model (no checks): precision 98.4, recall 91.6, F1 94.9, accuracy 96.9, FPR 0.7%. Speed-check rule: F1 78.9 (vehicle) / 80.0 (message).",
         "<b>Neighbour attention (H1):</b> +0.3 F1 (95% CI about [0.2, 0.4]), significant on 8-10 of 14 attacks; FPR 0.90% -> 0.60%. H0 is rejected overall, but the gain is small.",
         "<b>Malicious neighbours (H1b):</b> the benefit shrinks and turns negative when attackers are the majority of neighbours "
         "(v2: -0.004 within-attack; first model: +0.071 -> -0.023). So H1b is not supported.",
         "<b>Latency:</b> mean 0.9 s to first alarm, median 0; 96% of attacker-receiver pairs flagged.",
         "<b>Collusion:</b> the first model caught almost none of the consistent lies (colluder recall at most 0.04). v2: 50 m offset 0.83-0.86, fake stop about 0.70, "
         "spoofed convoy never seen in training 0.87-0.90. Map-aware on-road lies are still hard: offset along the road 0.23-0.25, convoy on its own road 0.36-0.48. "
         "Coordinated convoys raised the first model's honest FPR from 0.9% to 3.0%.",
         "<b>Reference paper</b> (Abdel Hakeem &amp; Kim, IEEE T-ITS 2025 survey, Table XIII: 97.37% on the original 5-attack VeReMi): v2 + memory is above 97.37 on all four "
         "metrics under message labels; under vehicle labels recall and F1 are not. This is not a like-for-like comparison.",
         "<b>Paper:</b> drafted as paper/main.tex -> paper/main.pdf (IEEE conference format, 6 pages, 18 references)."])
S += [Spacer(1, 6), Paragraph("<i>Scope: the benchmark is simulated (VeReMi Extension), not real-world data. 14 of 19 attack types have been run (no Sybil); "
      "collusion is covered only by the stress test, and crash intent is not modelled.</i>", B)]

SimpleDocTemplate("docs/research_plan.pdf", pagesize=A4, leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=1.5*cm, bottomMargin=1.5*cm,
                  title="Research plan: neighbourhood-aware misbehavior detection for V2X").build(S)
