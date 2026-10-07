"""Extended real-data evaluation (professor's review): precision/recall/F1/FPR, detection latency, and behaviour
when neighbouring vehicles are themselves malicious. Same split as run_real.py. -> results/results_real_extra.json"""
import glob, json, os, sys, numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score
from nambd.data import load_veremi
from nambd.train import fit, scores, best_thr

root = sys.argv[1] if len(sys.argv) > 1 else "data"
def load(tag):
    ds = sorted({os.path.dirname(p) for p in glob.glob(f"{root}/**/traceJSON-*.json", recursive=True) if tag in p})
    parts = [load_veremi(d) for d in ds]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
tr = load("50400_54000"); late = load("54000_57600")
cut = int(0.3 * len(late["X"]))
va = {k: v[:cut] for k, v in late.items()}; te = {k: v[cut:] for k, v in late.items()}

def latency(D, flag):
    """Per (receiver, malicious sender) pair: seconds from first window containing the sender to first alarm."""
    first, alarm = {}, {}
    N, K = D["y"].shape
    for i in np.argsort(D["te"], kind="stable"):
        for j in range(K):
            if D["y"][i, j] > 0:
                key = (D["rid"][i], D["sid"][i, j])
                first.setdefault(key, D["te"][i])
                if flag[i, j] and key not in alarm: alarm[key] = D["te"][i]
    lat = np.array([alarm[k] - first[k] for k in alarm], float)
    return dict(pairs=len(first), detected_frac=len(alarm) / max(len(first), 1),
                mean_s=float(lat.mean()), median_s=float(np.median(lat)), p90_s=float(np.percentile(lat, 90)))

def full_scores(m, D, mode):
    s, y = scores(m, D, mode); S = np.full(D["y"].shape, np.nan); S[D["y"] >= 0] = s; return S

out = {}
for mode in ["persender", "full"]:
    runs = []
    for sd in range(3):
        m = fit(mode, tr, epochs=5, seed=sd, log=lambda *a: None)
        thr = best_thr(*scores(m, va, mode)); S = full_scores(m, te, mode); Y = te["y"]
        v = Y >= 0; flag = (S > thr) & v; yb = (Y > 0)[v]; pb = flag[v]
        r = dict(precision=float(precision_score(yb, pb)), recall=float(recall_score(yb, pb)), f1=float(f1_score(yb, pb)),
                 fpr=float(pb[~yb].mean()), latency=latency(te, flag))
        # neighbour-malicious stratification: share of OTHER malicious senders among the window's neighbours
        nv = v.sum(1, keepdims=True); nm = ((Y > 0) & v).sum(1, keepdims=True)
        share = (nm - (Y > 0)) / np.maximum(nv - 1, 1)
        strat = {}
        for lo, hi in [(0, .1), (.1, .3), (.3, .5), (.5, 1.01)]:
            sel = v & (share >= lo) & (share < hi)
            b, p = (Y > 0)[sel], flag[sel]
            strat[f"{lo:.1f}-{min(hi,1):.1f}"] = dict(n=int(sel.sum()), malicious_frac=float(b.mean()),
                recall=float(p[b].mean()) if b.any() else None, fpr=float(p[~b].mean()) if (~b).any() else None)
        r["by_malicious_neighbour_share"] = strat
        runs.append(r); print(mode, sd, json.dumps(r), flush=True)
    out[mode] = runs
    json.dump(out, open("results/results_real_extra.json", "w"), indent=1)
