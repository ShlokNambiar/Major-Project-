"""Builds docs/research_methodology_worksheet.pdf (B.Tech Research Methodology & Project Blueprint Worksheet)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle

INK = colors.HexColor("#111111")
TITLE = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=13.5, alignment=1, spaceAfter=6, textColor=INK)
HDR = ParagraphStyle("Hd", fontName="Helvetica", fontSize=10, leading=13.5, textColor=INK)
PART = ParagraphStyle("P", fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=7, spaceAfter=1, textColor=INK)
Q = ParagraphStyle("Q", fontName="Helvetica-Bold", fontSize=9, leading=11.5, leftIndent=8, textColor=INK)
A = ParagraphStyle("A", fontName="Helvetica", fontSize=8.7, leading=10.6, leftIndent=18, spaceAfter=1.5, textColor=INK)
AB = ParagraphStyle("AB", parent=A, leftIndent=28, bulletIndent=19)
def q(label, *paras):
    out = [Paragraph(label, Q)]
    out += [Paragraph(p, A) for p in paras]
    return out
def qb(label, items, lead=None):
    out = [Paragraph(label, Q)]
    if lead: out.append(Paragraph(lead, A))
    out += [Paragraph(i, AB, bulletText="•") for i in items]
    return out

S = [Paragraph("B.TECH RESEARCH METHODOLOGY &amp; PROJECT BLUEPRINT WORKSHEET", TITLE)]
hdr = Table([[Paragraph("<b>Student Name / Roll No:</b> Shlok (UAI05BTA2317), Jiya (UAI05BTA2313), Caleb (UAI05BTA2319)", HDR)],
             [Paragraph("<b>Branch:</b> BTech AI ML", HDR)],
             [Paragraph("<b>Title:</b> Neighbourhood-aware misbehavior detection for V2X networks (VeReMi Extension benchmark)", HDR)]], colWidths=[16.6*cm])
hdr.setStyle(TableStyle([("LEFTPADDING", (0,0), (-1,-1), 0), ("TOPPADDING", (0,0), (-1,-1), 1), ("BOTTOMPADDING", (0,0), (-1,-1), 1)]))
S += [hdr]

S += [Paragraph("PART 1: PROBLEM CONCEPTION &amp; MOTIVATION", PART)]
S += q("1. Relevance (What practical, industrial, or social pain point does this address?):",
  "Connected cars broadcast their position, speed and heading several times a second, and nearby cars act on it (collision warnings, platooning). "
  "If a vehicle sends false data, for example a spoofed position or a frozen speed, others can be misled, and an approaching car can be hidden. "
  "Cryptographic signatures prove who sent a message, not that its content is true, so vehicle makers and road authorities need on-board misbehavior detection as a second line of defence. "
  "Social impact: road safety.")
S += q("2. Interest (Why are you personally invested or curious about solving this specific problem?):",
  "<b><i>[Draft - replace with your own words]</i></b> "
  "Road safety is a concrete place where a machine-learning error has real consequences, which makes it a good test of whether a model can be trusted. "
  "We were curious whether a car can catch a lying vehicle the way a person would, by noticing that it disagrees with what everyone around it reports, "
  "and whether that still works when some of those neighbours are lying too.")

S += [Paragraph("PART 2: DATA STRATEGY", PART)]
S += q("3. Data Availability (Where will you source your data? Provide repository or collection method):",
  "Public benchmark <b>VeReMi Extension</b>, downloaded from Zenodo (record 20090854, CC-BY 4.0). It is a <b>simulated</b> benchmark (F2MD / VEINS / SUMO, Luxembourg traffic scenario, 19 attack types), "
  "so no data collection is needed. Used: 14 of the 19 attack types at 14:00-16:00 (no Sybil attacks; the RandomSpeedOffset archive is excluded because it is mislabeled). "
  "Windows: 109,823 train, 29,547 validation, 68,971 test. Code, logs and weights: our GitHub repository.")
S += q("4. Choice of Data (What specific features/attributes will you include, and what will you filter out?):",
  "<b>Included</b> (19 per sender per second): 9 claim values (position relative to the receiver, speed, heading, movement, acceleration) and 10 plausibility checks: "
  "kinematic consistency, a road map learned from honest traffic, distance to the nearest other claim, exact self-repeat, copied trail, log movement. "
  "Each sample is a receiver's view: the 16 nearest senders over 10 seconds. Labels (dataset ground truth): "
  "<i>message</i> (attacker counted only where it sent a falsified message) and <i>vehicle</i> (every window of an attacker).",
  "<b>Filtered out:</b> sender identity (so the model cannot memorise vehicles), the simulated sensor-noise fields, windows where the receiver's own state is missing, and senders beyond the 16 nearest.")

S += [Paragraph("PART 3: METHODOLOGY &amp; ANALYSIS", PART)]
S += qb("5. Analysis of Data (Outline your ML pipeline: preprocessing, missing value handling, model selection):",
 ["<b>Preprocessing:</b> parse the JSON logs, bin messages to 1-second steps, build windows every 3 seconds, compute the 19 inputs (road map from the training hour only).",
  "<b>Missing values:</b> a sender not heard in a step is zero-filled and marked by a presence flag; the model masks those steps.",
  "<b>Model selection:</b> rule baseline (speed check); first model = transformer without checks; final model (v2) = small transformer (144k parameters) with temporal and cross-sender (neighbour) attention, "
  "plus checks; ablation = same model without neighbour attention. Training adds careful injected lies (position offset, fake stop). Optional receiver-side memory. "
  "Weighted binary cross-entropy (AdamW); alarm threshold chosen on validation data; 2 seeds."])

S += [Paragraph("PART 4: VALIDATION, GENERALIZATION, &amp; INTERPRETATION", PART)]
S += qb("6. Generalization (How will you test if your model works beyond your specific training dataset?):",
 ["<b>Done:</b> train on the first hour, test on the later hour (unseen time), receiver-disjoint validation and test blocks; collusion stress test with injected consistent lies (incl. a convoy never seen in training).",
  "<b>Open:</b> Sybil attacks; external check on original VeReMi / VeReMi NextGen; dense traffic for v2; a 3rd seed."])
S += [Paragraph("7. Analysis Validity Testing:", Q)]
S += [Paragraph("<b>Null Hypothesis (H0):</b> the neighbour-aware detector has the same F1 as the same model without neighbour attention. Alternative (H1): it is higher.", A)]
S += [Paragraph("<b>Evaluation Metrics:</b> precision, recall, F1, accuracy, false-positive rate, detection latency (seconds to first alarm), and colluder recall at a matched 1% false-positive rate.", A)]
S += [Paragraph("<b>Statistical Test:</b> paired bootstrap 95% confidence interval on the F1 difference (over receivers), McNemar's test on paired decisions, "
                "Holm correction across the 14 attacks; 2 seeds. Result: +0.3 F1 points, CI about [0.2, 0.4], significant on 8-10 of 14 attacks, so H0 is rejected.", A)]
S += qb("8. Interpretation (What actionable engineering or real-world insight will your final results yield?):",
 ["Final model (v2 + memory), message labels: precision 98.16, recall 97.78, F1 97.97, accuracy 98.74 (v2 alone: F1 97.88, FPR 0.60%). "
  "Vehicle labels: v2 + memory recall 96.09, F1 97.12. First model F1 94.9; speed-check rule F1 78.9. Mean 0.9 s to first alarm; 96% of attacker-receiver pairs flagged.",
  "Reference survey (Abdel Hakeem &amp; Kim, T-ITS 2025): 97.37% on the original VeReMi (5 attacks). We are above it on all four metrics with message labels, not on recall/F1 with vehicle labels; not like-for-like.",
  "Neighbour attention cuts false alarms (FPR 0.90% to 0.60%), but its gain turns slightly negative when attackers are most of the neighbours. "
  "Plausibility checks plus lie training raise recall on careful colluding lies from at most 0.04 to 0.70-0.90; lies that stay on the road remain hard (0.23-0.48). "
  "Insight: deploy behind message signatures; on-road lies need an independent signal (signal strength, sensors, RSUs). Limit: simulated data."])

SimpleDocTemplate("docs/research_methodology_worksheet.pdf", pagesize=A4, leftMargin=2.1*cm, rightMargin=2.1*cm, topMargin=0.8*cm, bottomMargin=0.7*cm,
                  title="B.Tech Research Methodology & Project Blueprint Worksheet").build(S)
