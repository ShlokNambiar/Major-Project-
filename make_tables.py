"""results/results_real.json (VeReMi Extension, run_real.py) -> paper/tables.tex and paper/fig_perattack.pdf.
Simulator results (results/results.json) are no longer used for the paper."""
import json, os, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = json.load(open("results/results_real.json"))
ATT = ["A3", "A5", "Overall"]
LAB = {"A3": "RandomPos", "A5": "ConstSpeed", "Overall": "Overall"}
def ms(runs, a, k):
    v = np.array([r[a][k] for r in runs]); return v.mean(), v.std()
def cell(runs, a, k="f1"):
    m, s = ms(runs, a, k); return f"{m:.3f}$\\pm${s:.3f}"
names = {"persender": "Per-sender", "nonbr": "Ours w/o spatial interaction", "full": "Ours (neighbourhood-aware)"}
n = len(R["full"])
L = ["\\begin{table}[t]\\centering\\caption{VeReMi Extension (RandomPos, ConstSpeed; 14:00--16:00 subsets). F1 / AUC (mean$\\pm$std over %d seeds). Train: first hour; test: later hour, receiver-disjoint split.}\\label{tab:main}\\small" % n,
     "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{l" + "cc" * len(ATT) + "}\\toprule",
     "Model & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{LAB[a]}}}" for a in ATT) + " \\\\",
     " & " + " & ".join("F1 & AUC" for _ in ATT) + " \\\\\\midrule"]
for k, nm in names.items():
    L.append(nm + " & " + " & ".join(cell(R[k], a) + " & " + cell(R[k], a, "auc") for a in ATT) + " \\\\")
L.append("\\bottomrule\\end{tabular}}\\end{table}")
os.makedirs("paper", exist_ok=True)
open("paper/tables.tex", "w").write("\n".join(L))
fig, ax = plt.subplots(figsize=(5, 2.6)); w = 0.27
for i, (k, nm) in enumerate(names.items()):
    ax.bar(np.arange(len(ATT)) + (i - 1) * w, [ms(R[k], a, "f1")[0] for a in ATT], w,
           yerr=[ms(R[k], a, "f1")[1] for a in ATT], label=nm)
ax.set_xticks(range(len(ATT))); ax.set_xticklabels([LAB[a] for a in ATT], fontsize=8)
ax.set_ylim(0.9, 1.0); ax.set_ylabel("F1"); ax.legend(fontsize=6); plt.tight_layout(); plt.savefig("paper/fig_perattack.pdf")
print("\n".join(L))
