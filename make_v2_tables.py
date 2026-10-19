"""results/results_v2.json + results/results_collusion_v2.json (+ _onroad) -> paper/tables_v2.tex"""
import json, os, numpy as np
TAG = os.environ.get("TAG", "v2")                                   # v2: 14 attacks, v18: 18 attacks
R = json.load(open(f"results/results_{TAG}.json")); C = json.load(open(f"results/results_collusion_{TAG}.json"))
OF = f"results/results_collusion_{TAG}_onroad.json"; O = json.load(open(OF)) if os.path.exists(OF) else {}
NATT = len(json.load(open(f"results/preds_{TAG}/attack_names.json"))); NTW = R["setup"]["test_windows"]
nm = {"full": "Ours", "nonbr": "No nbr. attention", "full-noaug": "No lie augm."}
def ms(m, sch, k, mem=False):
    v = [(R["runs"][f"{m}_{s}"][sch]["memory"]["test"] if mem else R["runs"][f"{m}_{s}"][sch]["test"])[k] for s in (0, 1)]
    return "%.2f" % (100 * np.mean(v))
L = ["\\begin{table}[t]\\centering\\caption{VeReMi Extension, %d attack types, %s test windows, mean of 2 seeds (\\%). \\emph{Message} labels count an attacker as positive only in windows where it sent a falsified message (ground truth); \\emph{vehicle} labels count every window of an attacker vehicle. Thresholds and memory decay are picked on validation. Reference: 97.37\\% reported for VeReMi (original, 5 attacks) in the survey of Abdel Hakeem and Kim (2025).}\\label{tab:v2}\\small".replace("%d attack types, %s test", f"{NATT} attack types, {NTW:,} test"),
     "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{llccccc}\\toprule", "Labels & Model & Precision & Recall & F1 & Accuracy & FPR \\\\\\midrule"]
for sch in ("message", "vehicle"):
    for m in ("full", "nonbr", "full-noaug"):
        L.append(f"{sch} & {nm[m]} & " + " & ".join(ms(m, sch, k) for k in ("precision", "recall", "f1", "accuracy", "fpr")) + " \\\\")
    L.append(f"{sch} & Ours + memory & " + " & ".join(ms("full", sch, k, True) for k in ("precision", "recall", "f1", "accuracy")) + " & -- \\\\")
    for k, n in (("SSC_speed_check", "Speed check (rule)"),):
        t = R["rule_based"][k][sch]["test"]; L.append(f"{sch} & {n} & " + " & ".join("%.2f" % (100 * t[x]) for x in ("precision", "recall", "f1", "accuracy", "fpr")) + " \\\\")
    L.append("\\midrule")
L[-1] = "\\bottomrule\\end{tabular}}\\end{table}"
runs = C["setup"]["runs"]; avg = lambda key, m, mode: np.mean([C["injected"][key][str(m)][r]["injected"]["colluder_recall_fpr1"] for r in runs if r.rsplit("_", 1)[0] == mode])
L += ["\\begin{table}[t]\\centering\\caption{Injected consistent lies (careful: acceleration consistent, GPS-like jitter), $m$ colluders per window, coordinated; colluder recall at a matched 1\\% validation FPR, mean of 2 seeds. Training saw offset and stop lies only. Before the plausibility checks both models caught at most 4\\% at these sizes. In the two on-road rows the last two columns are single runs (seed 0).}\\label{tab:traj}\\small",
      "\\resizebox{\\columnwidth}{!}{\\begin{tabular}{lccc}\\toprule", "Scenario & " + " & ".join(nm[m] for m in ("full", "nonbr", "full-noaug")) + " \\\\\\midrule"]
for key, lab in (("offset_coordinated", "Offset 50 m"), ("stop_coordinated", "Fake stop"), ("approach_coordinated", "Convoy (unseen)")):
    for m in (1, 8):
        L.append(f"{lab}, $m={m}$ & " + " & ".join("%.2f" % avg(key, m, mode) for mode in ("full", "nonbr", "full-noaug")) + " \\\\")
for k, lab in (("offset_road_50.0_m4", "Offset 50 m along road, $m=4$"), ("approach_road_15.0_m4", "Convoy on own road, $m=4$")):
    if k in O: L.append(f"{lab} & %.2f & %.2f & %.2f \\\\" % (np.mean([O[k]['full_0'], O[k]['full_1']]), O[k]["nonbr_0"], O[k]["full-noaug_0"]))
L.append("\\bottomrule\\end{tabular}}\\end{table}")
open("paper/tables_v2.tex", "w").write("\n".join(L)); print("\n".join(L))
