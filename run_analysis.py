"""Analyse results/preds/*.npz: per-attack metrics, latency, significance (paired bootstrap over receivers, McNemar),
rule-based baselines (VeReMi range / speed checks), dense-traffic transfer. -> results/results_full.json"""
import glob, json, os, numpy as np
from scipy.stats import binomtest
from sklearn.metrics import roc_auc_score
P = os.environ.get("PREDS", "results/preds"); B = int(os.environ.get("BOOT", 2000)); rng = np.random.default_rng(0)
names = {int(k): v for k, v in json.load(open(f"{P}/attack_names.json")).items()}
def meta(k):
    z = np.load(f"{P}/{k}_meta.npz"); return {a: z[a] for a in z.files}
te, va = meta("test"), meta("val"); dense = meta("dense") if os.path.exists(f"{P}/dense_meta.npz") else None

def prf(tp, fp, fn):
    p = tp / max(tp + fp, 1); r = tp / max(tp + fn, 1); return p, r, 2 * p * r / max(p + r, 1e-12)
def metrics(S, thr, D):
    v = D["y"] >= 0; y = (D["y"] > 0)[v]; f = (S > thr)[v]; s = S[v]
    tp, fp, fn = (f & y).sum(), (f & ~y).sum(), (~f & y).sum()
    p, r, f1 = prf(tp, fp, fn)
    out = dict(precision=p, recall=r, f1=f1, fpr=(f & ~y).sum() / max((~y).sum(), 1), auc=roc_auc_score(y, s))
    for a in sorted(set(D["y"][v].tolist()) - {0}):
        sel = (D["y"][v] == 0) | (D["y"][v] == a); ya = D["y"][v][sel] == a; fa = f[sel]
        tpa, fpa, fna = (fa & ya).sum(), (fa & ~ya).sum(), (~fa & ya).sum()
        out[names.get(a, f"A{a}")] = dict(f1=prf(tpa, fpa, fna)[2], recall=prf(tpa, fpa, fna)[1], auc=roc_auc_score(ya, s[sel]))
    return {k: (float(x) if not isinstance(x, dict) else {kk: float(vv) for kk, vv in x.items()}) for k, x in out.items()}
def latency(D, flag):
    first, alarm = {}, {}
    for i in np.argsort(D["te"], kind="stable"):
        for j in np.nonzero(D["y"][i] > 0)[0]:
            key = (D["grp"][i], D["rid"][i], D["sid"][i, j]); first.setdefault(key, D["te"][i])
            if flag[i, j] and key not in alarm: alarm[key] = D["te"][i]
    l = np.array([alarm[k] - first[k] for k in alarm], float)
    return dict(detected=len(alarm) / max(len(first), 1), mean_s=float(l.mean()), median_s=float(np.median(l)), p90_s=float(np.percentile(l, 90)))
def counts_by_receiver(flagA, D, pos_label=None):
    """per-receiver TP/FP/FN (binary or one attack vs benign)."""
    y = D["y"]; v = y >= 0
    sel = v if pos_label is None else v & ((y == 0) | (y == pos_label))
    pos = (y > 0) if pos_label is None else (y == pos_label)
    key = D["grp"].astype(np.int64)[:, None] * 10**7 + D["rid"].astype(np.int64)[:, None] + np.zeros_like(y, np.int64)
    k = key[sel]; uk, inv = np.unique(k, return_inverse=True)
    c = np.zeros((len(uk), 3))
    f = flagA[sel]; p = pos[sel]
    np.add.at(c[:, 0], inv, f & p); np.add.at(c[:, 1], inv, f & ~p); np.add.at(c[:, 2], inv, ~f & p)
    return c
def boot_diff(cA, cB):
    """paired bootstrap over receivers of F1(B) - F1(A); returns mean diff, 95% CI, one-sided p (diff <= 0)."""
    n = len(cA); idx = rng.integers(0, n, (B, n))
    def f1(c): s = c[idx].sum(1); p = s[:, 0] / np.maximum(s[:, 0] + s[:, 1], 1); r = s[:, 0] / np.maximum(s[:, 0] + s[:, 2], 1); return 2 * p * r / np.maximum(p + r, 1e-12)
    d = f1(cB) - f1(cA); return float(d.mean()), [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], float((d <= 0).mean())
def mcnemar(fA, fB, D):
    v = D["y"] >= 0; y = (D["y"] > 0)[v]; a = fA[v] == y; b = fB[v] == y     # correct decisions
    n01, n10 = int((~a & b).sum()), int((a & ~b).sum())
    return dict(a_wrong_b_right=n01, a_right_b_wrong=n10, p=float(binomtest(n01, n01 + n10, 0.5).pvalue) if n01 + n10 else 1.0)
def holm(ps):
    o = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0
    for r, i in enumerate(o): run = max(run, (m - r) * ps[i]); adj[i] = min(run, 1.0)
    return adj

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
# significance: baseline persender vs each other model, per seed, overall and per attack (Holm across attacks)
if "persender" in modes:
    for m in modes:
        if m == "persender": continue
        per_seed = []
        for s in seeds:
            if ("persender", s) not in loaded or (m, s) not in loaded: continue
            zA, zB = loaded[("persender", s)], loaded[(m, s)]; fA, fB = zA["test"] > float(zA["thr"]), zB["test"] > float(zB["thr"])
            fA, fB = np.nan_to_num(fA), np.nan_to_num(fB); fA, fB = fA.astype(bool), fB.astype(bool)
            ov = boot_diff(counts_by_receiver(fA, te), counts_by_receiver(fB, te)); ents = {"overall": dict(delta_f1=ov[0], ci95=ov[1], p_boot=ov[2], mcnemar=mcnemar(fA, fB, te))}
            ids = sorted(set(te["y"][te["y"] > 0].tolist())); pv = []
            for a in ids:
                d = boot_diff(counts_by_receiver(fA, te, a), counts_by_receiver(fB, te, a)); ents[names.get(a, f"A{a}")] = dict(delta_f1=d[0], ci95=d[1], p_boot=d[2]); pv.append(d[2])
            for a, pa in zip(ids, holm(np.array(pv))): ents[names.get(a, f"A{a}")]["p_holm"] = float(pa)
            per_seed.append(ents)
        res["significance"][m + "_vs_persender"] = per_seed
# rule-based baselines from the original VeReMi paper, on the same windows
def rule_scores(D):
    X = D["X"].astype(np.float32); M = D["M"]
    art = np.linalg.norm(X[:, :, -1, 0:2], axis=-1) * 300.0
    spd = X[:, :, :, 2] * 30.0; disp = np.linalg.norm(X[:, :, :, 5:7], axis=-1) / 3.0 * 300.0
    ok = M[:, :, 1:] & M[:, :, :-1]; dev = np.abs(spd[:, :, 1:] - disp[:, :, 1:]) * ok
    ssc = dev.sum(-1) / np.maximum(ok.sum(-1), 1); return dict(ART_range_check=art, SSC_speed_check=ssc)
rv, rt = rule_scores(va), rule_scores(te)
for k in rv:
    v = va["y"] >= 0; ts = np.quantile(rv[k][v], np.linspace(0.05, 0.99, 60))
    f1s = []
    for t in ts:
        f = (rv[k] > t)[v]; y = (va["y"] > 0)[v]; f1s.append(prf((f & y).sum(), (f & ~y).sum(), (~f & y).sum())[2])
    thr = float(ts[int(np.argmax(f1s))]); res["rule_based"][k] = dict(threshold=thr, **metrics(np.where(te["y"] >= 0, rt[k], np.nan), thr, te))
json.dump(dict(res=res, seeds=seeds, modes=modes, n_test_windows=int(len(te["y"]))), open(os.environ.get("OUT", "results/results_full.json"), "w"), indent=1, default=float)
print("saved", os.environ.get("OUT", "results/results_full.json"), "modes", modes, "seeds", seeds)
