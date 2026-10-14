"""Low-density -> dense-traffic transfer. Loads models saved by run_full.py (results/models) and evaluates them, with the
low-density validation threshold, on 07:00-09:00 subsets (25200-28800 s) found under data/. -> results/results_dense.json"""
import glob, json, os, re, numpy as np, torch
from nambd.data import load_veremi
from nambd.model import Detector
from nambd.train import MODES, scores
from nambd.evalutil import metrics, rule_scores, prf, counts_by_receiver, boot_diff, latency

MAXR = int(os.environ.get("MAXR", 300)); rng = np.random.default_rng(1)
dirs = sorted({os.path.dirname(p) for p in glob.glob("data/**/traceJSON-*.json", recursive=True) if "25200_28800" in os.path.dirname(p)})
parts, names = [], {}
for g, d in enumerate(dirs):
    p = load_veremi(d, max_receivers=MAXR)
    if len(p["te"]) == 0 or not (25200 <= p["te"].min() <= 25500): print("SKIP", d); continue
    p["grp"] = np.full(len(p["X"]), g, np.int32); nm = re.search(r"([A-Za-z]+)_0709", d).group(1)
    for a in np.unique(p["y"][p["y"] > 0]): names[int(a)] = nm
    parts.append(p)
D = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
print("dense windows", D["X"].shape, "attacks", names, "attacker share", float((D["y"] > 0).sum() / (D["y"] >= 0).sum()))
vz = np.load("results/preds/val_meta.npz"); V = {k: vz[k] for k in vz.files}
res = {"names": names, "n_windows": int(len(D["y"])), "models": {}, "rule_based": {}}
def full_scores(m, mode):
    s, _ = scores(m, D, mode); S = np.full(D["y"].shape, np.nan, np.float32); S[D["y"] >= 0] = s; return S
flags = {}
for f in sorted(glob.glob("results/models/*.pt")):
    mode, sd = os.path.basename(f)[:-3].rsplit("_", 1)
    m = Detector(spatial=MODES[mode]["spatial"]); m.load_state_dict(torch.load(f)); m.eval()
    thr = float(np.load(f"results/preds/{mode}_{sd}.npz")["thr"]); S = full_scores(m, mode)
    r = metrics(S, thr, D, names); r["latency"] = latency(D, S > thr); res["models"].setdefault(mode, []).append(r); flags[(mode, int(sd))] = np.nan_to_num(S > thr).astype(bool)
    print(mode, sd, "dense F1 %.3f recall %.3f fpr %.4f" % (r["f1"], r["recall"], r["fpr"]), flush=True)
for (mode, sd), fl in flags.items():
    if mode != "persender" and ("persender", sd) in flags:
        d = boot_diff(counts_by_receiver(flags[("persender", sd)], D), counts_by_receiver(fl, D), rng)
        res.setdefault("delta_f1_vs_persender", {}).setdefault(mode, []).append(dict(delta_f1=d[0], ci95=d[1], p_boot=d[2]))
rv, rt = rule_scores(V), rule_scores(D)
for k in rv:
    v = V["y"] >= 0; ts = np.quantile(rv[k][v], np.linspace(0.05, 0.99, 60)); f1s = []
    for t in ts:
        f = (rv[k] > t)[v]; y = (V["y"] > 0)[v]; f1s.append(prf((f & y).sum(), (f & ~y).sum(), (~f & y).sum())[2])
    thr = float(ts[int(np.argmax(f1s))]); res["rule_based"][k] = dict(threshold=thr, **metrics(np.where(D["y"] >= 0, rt[k], np.nan), thr, D, names))
json.dump(res, open("results/results_dense.json", "w"), indent=1, default=float); print("saved results/results_dense.json")
