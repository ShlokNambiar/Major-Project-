"""results/results_full.json (run_full.py + run_analysis.py) -> paper/tables.tex and paper/fig_perattack.pdf"""
import json, os, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
J = json.load(open(os.environ.get("RESULTS", "results/results_full.json"))); R = J["res"]; seeds = J["seeds"]
M = R["models"]; names = {"persender": "Per-sender (baseline)", "nonbr": "No spatial interaction", "full": "Neighbourhood-aware (ours)"}
modes = [m for m in ("persender", "nonbr", "full") if m in M]
ATT = [k for k in M["persender"]["runs"][0] if isinstance(M["persender"]["runs"][0][k], dict)]
def ms(runs, a, k=None):
    v = np.array([(r[a][k] if k else r[a]) for r in runs]); return v.mean(), v.std()
def cell(runs, a, k=None, f="{:.3f}"): m, s = ms(runs, a, k); return (f + "$\\pm$" + f).format(m, s)
os.makedirs("paper", exist_ok=True)
L = ["\\begin{table}[t]\\centering\\caption{Overall detection quality on %d VeReMi Extension attack types (mean$\\pm$std over %d seeds); latency = seconds from a sender's first appearance to the first alarm.}\\label{tab:overall}\\small" % (len(ATT), len(seeds)),
     "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{lccccccc}\\toprule", "Model & Prec. & Recall & F1 & FPR & AUC & Latency (s) & Detected \\\\\\midrule"]
for m in modes:
    runs = M[m]["runs"]; lat = M[m]["latency"]
    L.append(names[m] + " & " + " & ".join(cell(runs, k) for k in ("precision", "recall", "f1", "fpr", "auc")) + " & " + cell(lat, "mean_s", None, "{:.2f}") + " & " + cell(lat, "detected", None, "{:.2f}") + " \\\\")
L.append("\\midrule")
for k, nm in (("ART_range_check", "Range check (VeReMi)"), ("SSC_speed_check", "Speed check (VeReMi)")):
    r = R["rule_based"][k]; L.append(nm + " & " + " & ".join("%.3f" % r[x] for x in ("precision", "recall", "f1", "fpr", "auc")) + " & -- & -- \\\\")
L.append("\\bottomrule\\end{tabular}}\\end{table}")
BASE = "nonbr" if "nonbr" in modes else "persender"; sig = R["significance"].get(f"full_vs_{BASE}", [])
L += ["\\begin{table}[t]\\centering\\caption{Per-attack F1 (mean over seeds), and F1 gain of the neighbourhood-aware model over the per-sender baseline with 95\\% paired-bootstrap CI (receivers resampled) and Holm-corrected $p$.}\\label{tab:perattack}\\small",
      "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{l" + "c" * (len(modes) + 4) + "}\\toprule", "Attack & " + " & ".join(names[m] for m in modes) + " & Speed check & $\\Delta$F1 vs " + BASE + " & 95\\% CI & $p_{Holm}$ \\\\\\midrule"]
for a in ATT:
    d = [s[a] for s in sig] if sig else []
    dm = np.mean([x["delta_f1"] for x in d]) if d else float("nan"); lo = np.mean([x["ci95"][0] for x in d]) if d else float("nan"); hi = np.mean([x["ci95"][1] for x in d]) if d else float("nan"); ph = max([x["p_holm"] for x in d]) if d else float("nan")
    L.append(a + " & " + " & ".join("%.3f" % ms(M[m]["runs"], a, "f1")[0] for m in modes) + " & %.3f & %+.3f & [%.3f, %.3f] & %s \\\\" % (R["rule_based"]["SSC_speed_check"][a]["f1"], dm, lo, hi, "<0.001" if ph < 0.001 else "%.3f" % ph))
L.append("\\bottomrule\\end{tabular}}\\end{table}")
if R.get("dense") and any(R["dense"].values()): pass
open("paper/tables.tex", "w").write("\n".join(L))
fig, ax = plt.subplots(figsize=(7, 3)); w = 0.26; x = np.arange(len(ATT))
series = [(names[m], [ms(M[m]["runs"], a, "f1")[0] for a in ATT], [ms(M[m]["runs"], a, "f1")[1] for a in ATT]) for m in modes] + [("Speed check (VeReMi)", [R["rule_based"]["SSC_speed_check"][a]["f1"] for a in ATT], None)]
w = 0.8 / len(series)
for i, (n, v, e) in enumerate(series): ax.bar(x + (i - (len(series) - 1) / 2) * w, v, w, yerr=e, label=n)
ax.set_xticks(x); ax.set_xticklabels(ATT, rotation=25, ha="right", fontsize=8); ax.set_ylabel("F1"); ax.set_ylim(0, 1); ax.legend(fontsize=6, ncol=2); plt.tight_layout(); plt.savefig("paper/fig_perattack.pdf")
print("\n".join(L))
