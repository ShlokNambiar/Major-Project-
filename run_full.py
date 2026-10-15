"""Full real-data experiment on many VeReMi Extension attack types.
Train: 50400-54000 s slices of all 14:00-16:00 attack subsets found under data/. Val/test: 54000-57600 s slices
(30% / 70% contiguous receiver blocks per subset). Dense transfer test: 07:00-09:00 (25200-28800 s) subsets, if present.
Saves per-window scores for every (model, seed) to results/preds/ for run_analysis.py. Resumable."""
import glob, json, os, re, sys, time, numpy as np
from nambd.data import load_veremi
from nambd.train import fit, scores, best_thr, MODES as MODE_CFG
from nambd.model import Detector

RATE = os.environ.get("RATE", "0") == "1"; ROOT = "data"; MAXR = int(os.environ.get("MAXR", 250)); SEEDS = int(os.environ.get("SEEDS", 3))
MODES = os.environ.get("MODES", "persender,full").split(","); EPOCHS = int(os.environ.get("EPOCHS", 5))
PREDS = os.environ.get("PREDS", "results/preds"); os.makedirs(PREDS, exist_ok=True)
t0 = time.time()
log = lambda *a: print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)

def cat(parts): return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
EXCLUDE = os.environ.get("EXCLUDE", "RandomSpeedOffset").split(",")   # RandomSpeedOffset_1416: both archives hold the same later-hour data
all_dirs = lambda tag: sorted({os.path.dirname(p) for p in glob.glob(f"{ROOT}/**/traceJSON-*.json", recursive=True)
                               if tag in os.path.dirname(p) and not any(x and x in p for x in EXCLUDE)})
def load_checked(d, lo, hi):          # skip slices that do not START inside [lo, hi] (catches duplicated / mislabeled archives)
    p = load_veremi(d, max_receivers=MAXR, rate=RATE)
    if len(p["te"]) == 0 or not (lo <= p["te"].min() <= hi):
        log("SKIP mislabeled/empty slice", d); return None
    return p
tr_dirs = [d for d in all_dirs("50400_54000")]
late_dirs = [d for d in all_dirs("54000_57600")]
dense_dirs = [d for d in all_dirs("25200_28800")]
log("train subsets", len(tr_dirs), "late", len(late_dirs), "dense", len(dense_dirs))
tr = cat([p for p in (load_checked(d, 50400, 50700) for d in tr_dirs) if p is not None]); log("train", tr["X"].shape, "attack ids", sorted(set(np.unique(tr["y"])) - {-1}))
names = {}
def tag(p, g, d):
    p["grp"] = np.full(len(p["X"]), g, np.int32)
    m = re.search(r"([A-Za-z]+)_(1416|0709)", d); nm = (m.group(1) if m else d) + "_" + (m.group(2) if m else "")
    for a in np.unique(p["y"][p["y"] > 0]): names[int(a)] = nm.rsplit("_", 1)[0]
    return p
va_p, te_p = [], []
for g, d in enumerate(late_dirs):
    p = load_checked(d, 54000, 54300)
    if p is None: continue
    p = tag(p, g, d); c = int(0.3 * len(p["X"]))
    va_p.append({k: v[:c] for k, v in p.items()}); te_p.append({k: v[c:] for k, v in p.items()})
va, te = cat(va_p), cat(te_p); log("val", va["X"].shape, "test", te["X"].shape)
dense = cat([tag(p, g, d) for g, d in enumerate(dense_dirs) for p in [load_checked(d, 25200, 25500)] if p is not None]) if dense_dirs else None
if dense is not None: log("dense", dense["X"].shape, sorted(set(np.unique(dense["y"])) - {-1}))
json.dump(names, open(f"{PREDS}/attack_names.json", "w"))
for k, v in dict(val=va, test=te, dense=dense).items():
    if v is not None: np.savez_compressed(f"{PREDS}/{k}_meta.npz", y=v["y"], rid=v["rid"], te=v["te"], sid=v["sid"], grp=v["grp"], X=v["X"].astype(np.float16), M=v["M"])

def full_scores(m, D, mode):
    s, _ = scores(m, D, mode); S = np.full(D["y"].shape, np.nan, np.float32); S[D["y"] >= 0] = s; return S

for sd in range(SEEDS):
    for mode in MODES:
        f = f"{PREDS}/{mode}_{sd}.npz"
        if os.path.exists(f): continue
        import torch; MD = os.environ.get("MODELS", "results/models"); os.makedirs(MD, exist_ok=True); mp = f"{MD}/{mode}_{sd}.pt"
        if os.path.exists(mp) and os.environ.get("REUSE", "1") == "1":   # rebuild predictions from a committed model instead of retraining
            m = Detector(fin=tr["X"].shape[-1], spatial=MODE_CFG[mode]["spatial"]); m.load_state_dict(torch.load(mp, weights_only=True)); log("loaded", mp)
        else:
            m = fit(mode, tr, epochs=EPOCHS, seed=sd, log=log); torch.save(m.state_dict(), mp)
        thr = float(best_thr(*scores(m, va, mode)))
        out = dict(thr=thr, test=full_scores(m, te, mode))
        if dense is not None: out["dense"] = full_scores(m, dense, mode)
        np.savez_compressed(f, **out); log("saved", f, "thr", thr)
log("done")
