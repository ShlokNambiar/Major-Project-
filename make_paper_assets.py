"""Paper assets for the v2 models: per-attack table and the attacker-share analysis (professor's point 2) on v2 predictions.
-> results/results_v2_share.json, paper/tables_paper.tex, paper/fig_share_v2.pdf"""
import json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
P = "results/preds_v2"; R = json.load(open("results/results_v2.json"))
z = np.load(f"{P}/test_meta.npz"); y = z["y"].copy(); act = np.load(f"{P}/test_active.npz")["active"]
y[(y > 0) & ~act] = -1                                                      # message labels
names = {int(k): v for k, v in json.load(open(f"{P}/attack_names.json")).items()}
share = (z["y"] > 0).sum(1) / np.maximum((z["y"] >= 0).sum(1), 1)          # share of attacker vehicles among the window's senders
bins = [0, 0.2, 0.4, 0.6, 1.01]; b = np.digitize(share, bins) - 1; BN = ["0--20", "20--40", "40--60", "60--100"]
out = {"bins": BN, "n_windows": [int((b == i).sum()) for i in range(4)], "overall": {}, "within_attack_gain": {}}
flags = {}
for m in ("full", "nonbr"):
    for s in (0, 1):
        r = f"{m}_{s}"; flags[r] = R["runs"][r]["message"]["threshold"]
        S = np.load(f"{P}/{r}.npz")["test"]; f = S > flags[r]; flags[r] = f
        out["overall"][r] = [dict(recall=float(f[(b == i)[:, None] & (y > 0)].mean()), fpr=float(f[(b == i)[:, None] & (y == 0)].mean())) for i in range(4)]
for a in sorted(names):                                                     # within each attack type: removes attack-mix effects
    g = []
    for i in range(4):
        sel = (b == i)[:, None] & (y == a)
        g.append(None if sel.sum() < 200 else float(np.mean([flags[f"full_{s}"][sel].mean() - flags[f"nonbr_{s}"][sel].mean() for s in (0, 1)])))
    out["within_attack_gain"][names[a]] = g
G = np.array([[np.nan if v is None else v for v in g] for g in out["within_attack_gain"].values()])
out["mean_within_attack_gain"] = [float(x) for x in np.nanmean(G, 0)]; out["n_attacks_in_bin"] = [int(x) for x in (~np.isnan(G)).sum(0)]
json.dump(out, open("results/results_v2_share.json", "w"), indent=1)
avg = lambda m, i, k: np.mean([out["overall"][f"{m}_{s}"][i][k] for s in (0, 1)])
print("share bins", out["n_windows"]); print("full recall", [round(avg("full", i, "recall"), 4) for i in range(4)]); print("nonbr recall", [round(avg("nonbr", i, "recall"), 4) for i in range(4)])
print("within-attack gain", [round(x, 4) for x in out["mean_within_attack_gain"]], out["n_attacks_in_bin"])

# per-attack table (message labels, mean of 2 seeds)
def pa(m, a, k): return np.mean([R["runs"][f"{m}_{s}"]["message"]["test"][a][k] for s in (0, 1)])
L = ["\\begin{table}[t]\\centering\\caption{Per-attack results on message labels (mean of 2 seeds). F1 scores each attack against the honest senders of its own simulation run. $\\Delta$: F1 gain of neighbour attention.}\\label{tab:perattack}\\small",
     "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{lccccc}\\toprule", "Attack & Speed check & No nbr.\\ F1 & Ours F1 & Ours recall & $\\Delta$F1 \\\\\\midrule"]
for a in [names[k] for k in sorted(names)]:
    sc = R["rule_based"]["SSC_speed_check"]["message"]["test"][a]["f1"]
    L.append(f"{a} & {sc:.3f} & {pa('nonbr', a, 'f1'):.3f} & {pa('full', a, 'f1'):.3f} & {pa('full', a, 'recall'):.3f} & {pa('full', a, 'f1') - pa('nonbr', a, 'f1'):+.3f} \\\\")
L.append("\\bottomrule\\end{tabular}}\\end{table}")
L += ["\\begin{table}[t]\\centering\\caption{Recall on real attackers by the share of attacker vehicles among the senders in the window (message labels, mean of 2 seeds). Last row: recall gain of neighbour attention computed within each attack type (number of attack types with at least 200 attacker slots in the bin).}\\label{tab:share}\\small",
      "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{lcccc}\\toprule", "Attacker share (\\%) & " + " & ".join(BN) + " \\\\", "Windows & " + " & ".join(f"{n:,}" for n in out["n_windows"]) + " \\\\\\midrule"]
for m, n in (("nonbr", "No neighbour attention"), ("full", "Ours")):
    L.append(f"{n} recall & " + " & ".join("%.3f" % avg(m, i, "recall") for i in range(4)) + " \\\\")
    L.append(f"{n} FPR (\\%) & " + " & ".join("%.2f" % (100 * avg(m, i, "fpr")) for i in range(4)) + " \\\\")
L.append("\\midrule Within-attack gain & " + " & ".join("%+.3f (%d)" % (g, n) for g, n in zip(out["mean_within_attack_gain"], out["n_attacks_in_bin"])) + " \\\\")
L.append("\\bottomrule\\end{tabular}}\\end{table}")
open("paper/tables_paper.tex", "w").write("\n".join(L))

# figure: colluder recall vs offset size, first model (no checks) vs v2, matched 1% FPR, 4 coordinated colluders
C1 = json.load(open("results/results_collusion.json")); C2 = json.load(open("results/results_collusion_v2.json"))
def curve(C, mode):
    d = C["magnitude"]["offset_coordinated"]; xs = sorted(d, key=float)
    return [float(x) for x in xs], [np.mean([d[x][r]["colluder_recall_fpr1"] for r in d[x] if r.rsplit("_", 1)[0] == mode]) for x in xs]
fig, ax = plt.subplots(figsize=(3.4, 2.3))
for C, mode, lab, col, ls in ((C2, "full", "With checks (ours)", "#2a78d6", "-"), (C2, "nonbr", "With checks, no nbr. attention", "#2a78d6", "--"),
                              (C1, "full", "First model (no checks)", "#eb6834", "-"), (C1, "nonbr", "First model, no nbr. attention", "#eb6834", "--")):
    x, v = curve(C, mode); ax.plot(x, v, ls, marker="o", ms=3.5, lw=1.5, color=col, label=lab)
ax.set_xscale("log"); ax.set_xticks([10, 25, 50, 100, 200, 400]); ax.set_xticklabels(["10", "25", "50", "100", "200", "400"])
ax.set_ylim(0, 1); ax.set_xlabel("claimed position offset (m)", fontsize=8); ax.set_ylabel("colluder recall at 1% FPR", fontsize=8)
ax.tick_params(labelsize=7); ax.grid(alpha=0.25, lw=0.5); ax.legend(fontsize=6, frameon=False, loc="upper left")
plt.tight_layout(); plt.savefig("paper/fig_offset.pdf")
print("per-attack n:", {a: R["runs"]["full_0"]["message"]["test"][a]["n"] for a in [names[k] for k in sorted(names)]})
