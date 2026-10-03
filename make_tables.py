"""results/results.json -> paper/tables.tex (mean ± std over seeds) and paper/fig_perattack.pdf"""
import json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = json.load(open("results/results.json"))
ATT = ["ConstPos", "ConstPosOffset", "RandomPos", "RandomPosOffset", "EventualStop", "Macro"]
def ms(runs, a, k):
    v = np.array([r[a][k] for r in runs]); return v.mean(), v.std()
def cell(runs, a, k="f1"):
    m, s = ms(runs, a, k); return f"{m:.2f}$\\pm${s:.2f}"
names = {"persender": "Per-sender", "nonbr": "Ours w/o neighbourhood", "full": "Ours (neighbourhood-aware)"}
L = ["\\begin{table}[t]\\centering\\caption{Per-attack F1 (mean$\\pm$std over %d seeds), held-out senders.}\\label{tab:main}\\small" % len(R["in_domain"]["full"]),
     "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{l" + "c" * len(ATT) + "}\\toprule",
     "Model & ConstPos & ConstPosOff. & RandPos & RandPosOff. & EvStop & Macro \\\\\\midrule"]
for k, n in names.items():
    L.append(n + " & " + " & ".join(cell(R["in_domain"][k], a) for a in ATT) + " \\\\")
L.append("\\bottomrule\\end{tabular}}\\end{table}")
L += ["\\begin{table}[t]\\centering\\caption{Highway$\\to$dense transfer (target labels never used). Threshold fixed on source validation.}\\label{tab:dann}\\small",
      "\\begin{tabular}{lcccc}\\toprule Training & Macro F1 & Macro AUC & ConstPosOff. F1 & ConstPosOff. AUC\\\\\\midrule"]
tn = {"source_only": "Source only"}
for k, runs in R["transfer"].items():
    n = tn.get(k, "DANN $\\lambda$=" + k.split("_")[1])
    L.append(f"{n} & {cell(runs,'Macro')} & {cell(runs,'Macro','auc')} & {cell(runs,'ConstPosOffset')} & {cell(runs,'ConstPosOffset','auc')} \\\\")
L.append("\\bottomrule\\end{tabular}\\end{table}")
open("paper/tables.tex", "w").write("\n".join(L))
fig, ax = plt.subplots(figsize=(5, 2.6)); w = 0.27
for i, (k, n) in enumerate(names.items()):
    ax.bar(np.arange(len(ATT)) + (i - 1) * w, [ms(R["in_domain"][k], a, "f1")[0] for a in ATT], w,
           yerr=[ms(R["in_domain"][k], a, "f1")[1] for a in ATT], label=n)
ax.set_xticks(range(len(ATT))); ax.set_xticklabels(["ConstPos", "ConstPos\nOffset", "RandPos", "RandPos\nOffset", "Eventual\nStop", "Macro"], fontsize=7)
ax.set_ylabel("F1"); ax.legend(fontsize=6); plt.tight_layout(); plt.savefig("paper/fig_perattack.pdf")
print("\n".join(L))
