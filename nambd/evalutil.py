"""Evaluation helpers shared by run_analysis.py and run_dense.py."""
import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import roc_auc_score

def attack_mask(D, a):
    """valid slots in windows from the simulation subset that contains attack `a` (benign senders of the same run + attackers of type a)."""
    y = D["y"]; g = np.bincount(D["grp"][(y == a).any(1)]).argmax() if "grp" in D else None
    inrun = (D["grp"] == g)[:, None] if g is not None else np.ones((len(y), 1), bool)
    return (y >= 0) & inrun & ((y == 0) | (y == a))


def prf(tp, fp, fn):
    p = tp / max(tp + fp, 1); r = tp / max(tp + fn, 1); return p, r, 2 * p * r / max(p + r, 1e-12)
def metrics(S, thr, D, names):
    v = D["y"] >= 0; y = (D["y"] > 0)[v]; f = (S > thr)[v]; s = S[v]
    tp, fp, fn = (f & y).sum(), (f & ~y).sum(), (~f & y).sum()
    p, r, f1 = prf(tp, fp, fn)
    out = dict(precision=p, recall=r, f1=f1, accuracy=(f == y).mean(), fpr=(f & ~y).sum() / max((~y).sum(), 1), auc=roc_auc_score(y, s))
    for a in sorted(set(D["y"][v].tolist()) - {0}):
        sm = attack_mask(D, a); fa = (S > thr)[sm]; ya = (D["y"][sm] == a); sa = S[sm]
        tpa, fpa, fna = (fa & ya).sum(), (fa & ~ya).sum(), (~fa & ya).sum()
        out[names.get(a, f"A{a}")] = dict(f1=prf(tpa, fpa, fna)[2], recall=prf(tpa, fpa, fna)[1], auc=roc_auc_score(ya, sa))
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
    sel = v if pos_label is None else attack_mask(D, pos_label)
    pos = (y > 0) if pos_label is None else (y == pos_label)
    key = D["grp"].astype(np.int64)[:, None] * 10**7 + D["rid"].astype(np.int64)[:, None] + np.zeros_like(y, np.int64)
    k = key[sel]; uk, inv = np.unique(k, return_inverse=True)
    c = np.zeros((len(uk), 3))
    f = flagA[sel]; p = pos[sel]
    np.add.at(c[:, 0], inv, f & p); np.add.at(c[:, 1], inv, f & ~p); np.add.at(c[:, 2], inv, ~f & p)
    return c
def boot_diff(cA, cB, rng, B=2000):
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


def rule_scores(D):
    X = D["X"].astype(np.float32); M = D["M"]
    art = np.linalg.norm(X[:, :, -1, 0:2], axis=-1) * 300.0
    spd = X[:, :, :, 2] * 30.0; disp = np.linalg.norm(X[:, :, :, 5:7], axis=-1) / 3.0 * 300.0
    ok = M[:, :, 1:] & M[:, :, :-1]; dev = np.abs(spd[:, :, 1:] - disp[:, :, 1:]) * ok
    ssc = dev.sum(-1) / np.maximum(ok.sum(-1), 1); return dict(ART_range_check=art, SSC_speed_check=ssc)
