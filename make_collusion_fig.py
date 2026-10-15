"""results/results_collusion.json (run_collusion.py) -> paper/tables_collusion.tex and paper/fig_collusion.pdf"""
import json, os, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
J = json.load(open(os.environ.get("RESULTS", "results/results_collusion.json")))
runs = J["setup"]["runs"]; MS = J["setup"]["m"]; SC = J["setup"]["scenarios"]
modes = [m for m in ("nonbr", "full") if any(r.startswith(m + "_") for r in runs)]
names = {"nonbr": "No neighbour attention", "full": "Neighbourhood-aware (ours)"}
color = {"full": "#2a78d6", "nonbr": "#eb6834"}
title = {"offset": "Position offset (50 m)", "stop": "Fake stop / jam", "approach": "Spoofed approach convoy"}
def avg(mode, f):
    v = [f(r) for r in runs if r.startswith(mode + "_")]; v = [x for x in v if x is not None]; return float(np.mean(v)) if v else float("nan")
def inj(sc, coord, m, mode, k, which="injected"): return avg(mode, lambda r: J["injected"][f"{sc}_{coord}"][str(m)][r][which][k])
nat = J["natural"]; nb = len(nat["bins"]); NA = J["natural_by_attack"]
def gain_by_bin():          # per attack type: full - nonbr recall, mean over the attacks present in every bin from 20% up
    g = np.array([[np.nan if NA[a]["full_0"][i] is None else avg("full", lambda r: NA[a][r][i]) - avg("nonbr", lambda r: NA[a][r][i]) for i in range(nb)] for a in NA])
    return np.nanmean(g, 0), (~np.isnan(g)).sum(0)
gain, n_att = gain_by_bin()

os.makedirs("paper", exist_ok=True)
fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6))
x = np.arange(nb)
for mode in modes:                                               # (a) real attackers, by attacker share
    ax[0].plot(x, [avg(mode, lambda r: nat[r][i]["recall"]) for i in range(nb)], "-o", ms=4, lw=1.6, color=color[mode], label=names[mode])
ax[0].set_xticks(x); ax[0].set_xticklabels(nat["bins"], fontsize=6.5); ax[0].set_xlabel("attackers among senders", fontsize=8)
ax[0].set_ylabel("recall (real attackers)", fontsize=8); ax[0].set_title("(a) VeReMi attackers", fontsize=8.5)
mag = J["magnitude"]; sizes = list(mag["offset_coordinated"])
for mode in modes:                                               # (b) offset size, recall at matched 1% FPR
    for coord, ls, mk in (("coordinated", "-", "o"), ("independent", "--", "s")):
        ax[1].plot([int(s) for s in sizes], [avg(mode, lambda r: mag[f"offset_{coord}"][s][r]["colluder_recall_fpr1"]) for s in sizes], ls, marker=mk, ms=4, lw=1.6, color=color[mode])
ax[1].set_xscale("log"); ax[1].set_xticks([int(s) for s in sizes]); ax[1].set_xticklabels(sizes, fontsize=7); ax[1].set_ylim(0, 1)
ax[1].set_xlabel("position offset (m), 4 colluders", fontsize=8); ax[1].set_ylabel("colluder recall at 1% FPR", fontsize=8); ax[1].set_title("(b) Consistent lies", fontsize=8.5)
for mode in modes:                                               # (c) framing: honest FPR as the convoy grows
    for coord, ls, mk in (("coordinated", "-", "o"), ("independent", "--", "s")):
        ax[2].plot(MS, [100 * inj("approach", coord, m, mode, "honest_fpr") for m in MS], ls, marker=mk, ms=4, lw=1.6, color=color[mode])
    ax[2].plot(MS, [100 * inj("approach", "coordinated", m, mode, "honest_fpr", "clean") for m in MS], ":", lw=1, color=color[mode])
ax[2].set_ylim(bottom=0); ax[2].set_xticks(MS); ax[2].set_xlabel("colluders per window (m)", fontsize=8); ax[2].set_ylabel("honest-sender FPR (%)", fontsize=8); ax[2].set_title("(c) Spoofed convoy: framing", fontsize=8.5)
for a in ax: a.grid(alpha=0.25, lw=0.5); a.tick_params(labelsize=7)
h = [plt.Line2D([], [], color=color[m], lw=1.6) for m in modes] + [plt.Line2D([], [], color="0.4", ls=s, marker=k, ms=4) for s, k in (("-", "o"), ("--", "s"))] + [plt.Line2D([], [], color="0.4", ls=":")]
l = [names[m] for m in modes] + ["coordinated", "independent", "no injection"]
fig.legend(h, l, loc="lower center", ncol=5, fontsize=6.5, frameon=False); plt.tight_layout(rect=(0, 0.08, 1, 1)); plt.savefig(os.environ.get("FIG", "paper/fig_collusion.pdf"), dpi=150)

L = ["\\begin{table}[t]\\centering\\caption{Real VeReMi Extension attackers: test windows grouped by the share of attackers among the senders in the window (mean over seeds, each model at its own validation threshold). Last row: recall gain of neighbour attention computed within each attack type, averaged over the attack types present in the bin.}\\label{tab:share}\\small",
     "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{l" + "c" * nb + "}\\toprule", "Attacker share & " + " & ".join(b.replace("%", "\\%") for b in nat["bins"]) + " \\\\", "Windows & " + " & ".join(str(n) for n in nat["n_windows"]) + " \\\\\\midrule"]
for mode in modes:
    for k, nm in (("recall", "recall"), ("fpr", "FPR (\\%)")):
        L.append(f"{names[mode]} {nm} & " + " & ".join("--" if np.isnan(v := avg(mode, lambda r: nat[r][i][k])) else ("%.2f" % (100 * v) if k == "fpr" else "%.3f" % v) for i in range(nb)) + " \\\\")
L.append("\\midrule Within-attack recall gain (attack types) & " + " & ".join("%+.3f (%d)" % (g, n) for g, n in zip(gain, n_att)) + " \\\\")
L.append("\\bottomrule\\end{tabular}}\\end{table}")
L += ["\\begin{table}[t]\\centering\\caption{Injected collusion: $m$ honest senders per test window falsify their messages, coordinated (one shared story) or independently; %d windows with at least %d honest senders, mean over seeds. Colluder recall with both models at the same 1\\%% validation FPR, and honest-sender FPR (\\%%) at each model's own threshold, without injection in brackets.}\\label{tab:collusion}\\small" % (J["setup"].get("windows_used", J["setup"]["n_windows"]), max(MS) + 1),
      "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{ll" + "c" * len(MS) + "}\\toprule", "Scenario & Model & " + " & ".join(f"$m={m}$" for m in MS) + " \\\\\\midrule"]
for sc in SC:
    for coord in ("coordinated", "independent"):
        for mode in modes:
            L.append(f"{title.get(sc, sc)}, {coord} & {names[mode]} & " + " & ".join("%.3f / %.2f (%.2f)" % (inj(sc, coord, m, mode, "colluder_recall_fpr1"), 100 * inj(sc, coord, m, mode, "honest_fpr"), 100 * inj(sc, coord, m, mode, "honest_fpr", "clean")) for m in MS) + " \\\\")
    L.append("\\midrule")
L[-1] = "\\bottomrule\\end{tabular}}\\end{table}"
open("paper/tables_collusion.tex", "w").write("\n".join(L)); print("\n".join(L))
