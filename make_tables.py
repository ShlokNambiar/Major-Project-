"""results/results_full.json (run_full.py + run_analysis.py) -> paper/tables.tex and paper/fig_perattack.pdf"""
import json, os, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
DEFAULT = "results/results_full14.json" if os.path.exists("results/results_full14.json") else "results/results_full.json"
J = json.load(open(os.environ.get("RESULTS", DEFAULT))); R = J["res"]; seeds = J["seeds"]
M = R["models"]; names = {"persender": "Per-sender (baseline)", "nonbr": "No neighbour attention", "full": "Neighbourhood-aware (ours)"}
modes = [m for m in ("persender", "nonbr", "full") if m in M]
ATT = [k for k in M[modes[0]]["runs"][0] if isinstance(M[modes[0]]["runs"][0][k], dict)]
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
L += ["\\begin{table}[t]\\centering\\caption{Per-attack F1 (mean over seeds), and F1 gain of the neighbourhood-aware model over the same model without neighbour attention, with 95\\% paired-bootstrap CI (receivers resampled) and Holm-corrected $p$.}\\label{tab:perattack}\\small",
      "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{l" + "c" * (len(modes) + 4) + "}\\toprule", "Attack & " + " & ".join(names[m] for m in modes) + " & Speed check & $\\Delta$F1 vs " + BASE + " & 95\\% CI & $p_{Holm}$ \\\\\\midrule"]
for a in ATT:
    d = [s[a] for s in sig] if sig else []
    dm = np.mean([x["delta_f1"] for x in d]) if d else float("nan"); lo = np.mean([x["ci95"][0] for x in d]) if d else float("nan"); hi = np.mean([x["ci95"][1] for x in d]) if d else float("nan"); ph = max([x["p_holm"] for x in d]) if d else float("nan")
    L.append(a + " & " + " & ".join("%.3f" % ms(M[m]["runs"], a, "f1")[0] for m in modes) + " & %.3f & %+.3f & [%.3f, %.3f] & %s \\\\" % (R["rule_based"]["SSC_speed_check"][a]["f1"], dm, lo, hi, "<0.001" if ph < 0.001 else "%.3f" % ph))
L.append("\\bottomrule\\end{tabular}}\\end{table}")
if all(R.get("dense", {}).get(m) for m in modes):      # dense metrics computed from the same run
    ex = R["dense"][modes[0]][0]; Dn = dict(names={i: k for i, k in enumerate(k for k in ex if isinstance(ex[k], dict))}, models=R["dense"], rule_based=None)
elif os.path.exists("results/results_dense.json"): Dn = json.load(open("results/results_dense.json"))
else: Dn = None
if Dn:
    an = list(Dn["names"].values())
    L += ["\\begin{table}[t]\\centering\\caption{Transfer to dense rush-hour traffic (07:00--09:00; %s only): models trained on 14:00--16:00 traffic, threshold from low-density validation; mean over %d seeds.}\\label{tab:dense}\\small" % (" and ".join(an), len(next(iter(Dn["models"].values())))),
          "\\begin{tabular}{lcccc}\\toprule", "Model & Precision & Recall & F1 & FPR \\\\\\midrule"]
    for m in modes:
        rr = Dn["models"][m]; L.append(names[m] + " & " + " & ".join("%.3f" % np.mean([r[k] for r in rr]) for k in ("precision", "recall", "f1", "fpr")) + " \\\\")
    if Dn["rule_based"]: L.append("\\midrule")
    for k, nm in (("ART_range_check", "Range check (VeReMi)"), ("SSC_speed_check", "Speed check (VeReMi)")) if Dn["rule_based"] else []:
        r = Dn["rule_based"][k]; L.append(nm + " & " + " & ".join("%.3f" % r[x] for x in ("precision", "recall", "f1", "fpr")) + " \\\\")
    L.append("\\bottomrule\\end{tabular}\\end{table}")
open("paper/tables.tex", "w").write("\n".join(L))
fig, ax = plt.subplots(figsize=(7, 3)); w = 0.26; x = np.arange(len(ATT))
series = [(names[m], [ms(M[m]["runs"], a, "f1")[0] for a in ATT], [ms(M[m]["runs"], a, "f1")[1] for a in ATT]) for m in modes] + [("Speed check (VeReMi)", [R["rule_based"]["SSC_speed_check"][a]["f1"] for a in ATT], None)]
w = 0.8 / len(series)
for i, (n, v, e) in enumerate(series): ax.bar(x + (i - (len(series) - 1) / 2) * w, v, w, yerr=e, label=n)
ax.set_xticks(x); ax.set_xticklabels(ATT, rotation=25, ha="right", fontsize=8); ax.set_ylabel("F1"); ax.set_ylim(0, 1); ax.legend(fontsize=6, ncol=2); plt.tight_layout(); plt.savefig("paper/fig_perattack.pdf")
print("\n".join(L))
