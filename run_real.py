"""Real-data experiment on VeReMi Extension (RandomPos_1416 + ConstSpeed_1416, Zenodo 20090854).
Train: 50400-54000 s slices of both attacks. Val/test: 54000-57600 s slices (later time window),
split into receiver-disjoint contiguous blocks (30% val / 70% test). Usage: python run_real.py [data_dir]"""
import glob, json, os, sys, time, numpy as np
from sklearn.metrics import f1_score, roc_auc_score
from nambd.data import load_veremi
from nambd.train import fit, scores, best_thr

root = sys.argv[1] if len(sys.argv) > 1 else "data"
def slices(tag):
    return sorted({os.path.dirname(p) for p in glob.glob(f"{root}/**/traceJSON-*.json", recursive=True) if tag in p})
def load(tag):
    parts = [load_veremi(d) for d in slices(tag)]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}, parts
tr, _ = load("50400_54000"); late, parts = load("54000_57600")
n = len(late["X"]); cut = int(0.3 * n)
va = {k: v[:cut] for k, v in late.items()}; te = {k: v[cut:] for k, v in late.items()}
print({k: v["X"].shape for k, v in dict(train=tr, val=va, test=te).items()}, flush=True)
out = {}
for mode in ["persender", "nonbr", "full"]:
    runs = []
    for sd in range(3):
        m = fit(mode, tr, epochs=5, seed=sd)
        thr = best_thr(*scores(m, va, mode)); s, y = scores(m, te, mode)
        r = dict(Overall=dict(f1=float(f1_score(y > 0, s > thr)), auc=float(roc_auc_score(y > 0, s))))
        for k in sorted(set(y.tolist()) - {0}):
            sel = (y == 0) | (y == k)
            r[f"A{k}"] = dict(f1=float(f1_score(y[sel] == k, s[sel] > thr)), auc=float(roc_auc_score(y[sel] == k, s[sel])))
        runs.append(r); print(mode, sd, json.dumps(r), flush=True)
    out[mode] = runs
os.makedirs("results", exist_ok=True); json.dump(out, open("results/results_real.json", "w"), indent=1)
