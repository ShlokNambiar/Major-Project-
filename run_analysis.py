"""Analyse results/preds/*.npz: per-attack metrics, latency, significance (paired bootstrap over receivers, McNemar),
rule-based baselines (VeReMi range / speed checks), dense-traffic transfer. -> results/results_full.json"""
import glob, json, os, numpy as np
P = os.environ.get("PREDS", "results/preds"); B = int(os.environ.get("BOOT", 2000)); rng = np.random.default_rng(0)
names = {int(k): v for k, v in json.load(open(f"{P}/attack_names.json")).items()}
def meta(k):
    z = np.load(f"{P}/{k}_meta.npz"); return {a: z[a] for a in z.files}
te, va = meta("test"), meta("val"); dense = meta("dense") if os.path.exists(f"{P}/dense_meta.npz") else None

from nambd.evalutil import prf, metrics as _metrics, latency, counts_by_receiver, boot_diff as _boot_diff, mcnemar, holm, rule_scores
metrics = lambda S, thr, D: _metrics(S, thr, D, names)
boot_diff = lambda cA, cB: _boot_diff(cA, cB, rng, B)

res = {"models": {}, "significance": {}, "rule_based": {}, "dense": {}}
modes = sorted({os.path.basename(f).rsplit("_", 1)[0] for f in glob.glob(f"{P}/*_[0-9].npz") if "meta" not in f})
seeds = sorted({int(f[-5]) for f in glob.glob(f"{P}/*_[0-9].npz") if "meta" not in f})
loaded = {(m, s): np.load(f"{P}/{m}_{s}.npz") for m in modes for s in seeds if os.path.exists(f"{P}/{m}_{s}.npz")}
for m in modes:
    runs, lats, dr = [], [], []
    for s in seeds:
        if (m, s) not in loaded: continue
        z = loaded[(m, s)]; thr = float(z["thr"]); runs.append(metrics(z["test"], thr, te)); lats.append(latency(te, z["test"] > thr))
        if "dense" in z.files and dense is not None: dr.append(metrics(z["dense"], thr, dense))
    res["models"][m] = dict(runs=runs, latency=lats); res["dense"][m] = dr
# significance: every ordered pair persender < nonbr < full, per seed, overall and per attack (Holm across attacks)
ORDER = [m for m in ("persender", "nonbr", "full") if m in modes]
def sig_pair(base, m):
    per_seed = []
    for s in seeds:
        if (base, s) not in loaded or (m, s) not in loaded: continue
        zA, zB = loaded[(base, s)], loaded[(m, s)]
        fA = np.nan_to_num(zA["test"] > float(zA["thr"])).astype(bool); fB = np.nan_to_num(zB["test"] > float(zB["thr"])).astype(bool)
        ov = boot_diff(counts_by_receiver(fA, te), counts_by_receiver(fB, te)); ents = {"overall": dict(delta_f1=ov[0], ci95=ov[1], p_boot=ov[2], mcnemar=mcnemar(fA, fB, te))}
        ids = sorted(set(te["y"][te["y"] > 0].tolist())); pv = []
        for a in ids:
            d = boot_diff(counts_by_receiver(fA, te, a), counts_by_receiver(fB, te, a)); ents[names.get(a, f"A{a}")] = dict(delta_f1=d[0], ci95=d[1], p_boot=d[2]); pv.append(d[2])
        for a, pa in zip(ids, holm(np.array(pv))): ents[names.get(a, f"A{a}")]["p_holm"] = float(pa)
        per_seed.append(ents)
    return per_seed
for i, base in enumerate(ORDER):
    for m in ORDER[i + 1:]: res["significance"][f"{m}_vs_{base}"] = sig_pair(base, m)
# rule-based baselines from the original VeReMi paper, on the same windows
rv, rt = rule_scores(va), rule_scores(te)
for k in rv:
    v = va["y"] >= 0; ts = np.quantile(rv[k][v], np.linspace(0.05, 0.99, 60))
    f1s = []
    for t in ts:
        f = (rv[k] > t)[v]; y = (va["y"] > 0)[v]; f1s.append(prf((f & y).sum(), (f & ~y).sum(), (~f & y).sum())[2])
    thr = float(ts[int(np.argmax(f1s))]); res["rule_based"][k] = dict(threshold=thr, **metrics(np.where(te["y"] >= 0, rt[k], np.nan), thr, te))
json.dump(dict(res=res, seeds=seeds, modes=modes, n_test_windows=int(len(te["y"]))), open(os.environ.get("OUT", "results/results_full.json"), "w"), indent=1, default=float)
print("saved", os.environ.get("OUT", "results/results_full.json"), "modes", modes, "seeds", seeds)
