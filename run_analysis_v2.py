"""Analyse the v2 runs (run_v2.py) -> results/results_v2.json.
Two label schemes: `vehicle` (every slot of an attacker vehicle is positive; as in results_full14.json) and `message` (only attacker
slots that sent a falsified message in the window are positive; inactive attacker slots are left out; label_active.py).
For each scheme the alarm threshold is picked on the validation block (max F1, same scheme), never on test.
Also: receiver-side memory (nambd/memory.py, decay picked on validation) and the mean of the seeds' scores (2-model ensemble),
paired bootstrap / McNemar of full vs nonbr (and full vs full-noaug), per-attack F1/recall, latency."""
import glob, json, os, sys, numpy as np, torch
sys.path.insert(0, ".")
from nambd.model import Detector
from nambd.train import MODES
from nambd.memory import with_memory
from nambd.evalutil import prf, latency, counts_by_receiver, boot_diff, mcnemar, holm, attack_mask, rule_scores
from sklearn.metrics import roc_auc_score
from run_v2 import all_dirs, load_one

P = os.environ.get("PREDS", "results/preds_v2"); MD = os.environ.get("MODELS", "results/models_v2"); FEAT = os.environ.get("FEAT", "data/cache_feat")
B = int(os.environ.get("BOOT", 2000)); OUT = os.environ.get("OUT", "results/results_v2.json"); rng = np.random.default_rng(0)
names = {int(k): v for k, v in json.load(open(f"{P}/attack_names.json")).items()}
z = np.load(f"{P}/test_meta.npz"); te = {k: z[k] for k in z.files}
zv = np.load(f"{P}/val_meta.npz"); va = dict(y=zv["y"], M=zv["M"])
A = np.load(f"{P}/test_active.npz"); act, vact = A["active"], A["val_active"]
V = {k: [] for k in ("rid", "te", "sid", "grp")}                    # validation window identities (first 30% of each slice), for memory
for g, d in enumerate(all_dirs("54000_57600")):
    p = load_one(d)
    if p is None: continue
    c = int(0.3 * len(p["te"]))
    for k in ("rid", "te", "sid"): V[k].append(p[k][:c])
    V["grp"].append(np.full(c, g, np.int32))
va.update({k: np.concatenate(v) for k, v in V.items()})
runs = sorted(os.path.basename(f)[:-4] for f in glob.glob(f"{P}/*_[0-9].npz") if "meta" not in f)
dev = "cuda" if torch.cuda.is_available() else "cpu"


def val_scores(r):
    f = f"{P}/valscores_{r}.npy"
    if os.path.exists(f): return np.load(f)
    zr = np.load(f"{P}/{r}.npz"); cols = zr["cols"]; mode = r.split("-")[0].rsplit("_", 1)[0]
    sd = torch.load(f"{MD}/{r}.pt", weights_only=True)                 # width/depth read from the checkpoint
    m = Detector(fin=len(cols), spatial=MODES[mode]["spatial"], d=sd["inp.weight"].shape[0], layers=len({k.split(".")[1] for k in sd if k.startswith("blocks.")})); m.load_state_dict(sd); m = m.to(dev).eval()
    X = np.load(f"{FEAT}/val.npy", mmap_mode="r")
    with torch.no_grad():
        S = np.concatenate([torch.sigmoid(m(torch.tensor(X[i:i + 1024][..., cols], dtype=torch.float32).to(dev), torch.tensor(va["M"][i:i + 1024]).to(dev))).cpu().numpy()
                            for i in range(0, len(X), 1024)])
    S[va["y"] < 0] = np.nan; np.save(f, S); return S


_mem = {}
def mem(S, D, dec, key):
    if key not in _mem: _mem[key] = with_memory(S, D, dec)
    return _mem[key]


def labels(D, a, scheme):
    """y used for scoring: inactive attacker slots -> -1 under the message scheme."""
    y = D["y"].copy()
    if scheme == "message": y[(y > 0) & ~a] = -1
    return y


def pick_thr(S, y):
    v = y >= 0; ts = np.linspace(0.02, 0.98, 49); yy = (y > 0)[v]
    f1 = [prf(((S > t)[v] & yy).sum(), ((S > t)[v] & ~yy).sum(), (~(S > t)[v] & yy).sum())[2] for t in ts]
    return float(ts[int(np.argmax(f1))]), float(max(f1))


def metrics(S, thr, D, y):
    v = y >= 0; yy = (y > 0)[v]; f = (S > thr)[v]
    tp, fp, fn = (f & yy).sum(), (f & ~yy).sum(), (~f & yy).sum(); p, r, f1 = prf(tp, fp, fn)
    out = dict(precision=p, recall=r, f1=f1, accuracy=(f == yy).mean(), fpr=fp / max((~yy).sum(), 1), auc=roc_auc_score(yy, S[v]), n_pos=int(yy.sum()), n_neg=int((~yy).sum()))
    Dm = dict(D, y=y)
    for a in sorted(names):
        sm = attack_mask(Dm, a); fa = (S > thr)[sm]; ya = (y[sm] == a)
        if ya.sum() == 0: continue
        tpa, fpa, fna = (fa & ya).sum(), (fa & ~ya).sum(), (~fa & ya).sum()
        out[names[a]] = dict(f1=prf(tpa, fpa, fna)[2], recall=prf(tpa, fpa, fna)[1], n=int(ya.sum()))
    return {k: (float(x) if not isinstance(x, dict) else x) for k, x in out.items()}


res = {"setup": dict(runs=runs, schemes=["vehicle", "message"], test_windows=int(len(te["y"])), note=__doc__), "runs": {}, "ensemble": {}, "significance": {}, "rule_based": {}}
St = {r: np.load(f"{P}/{r}.npz")["test"] for r in runs}; Sv = {r: val_scores(r) for r in runs}
groups = sorted({r.rsplit("_", 1)[0] for r in runs})
for g in groups:                                                     # ensemble = mean over seeds
    rs = [r for r in runs if r.rsplit("_", 1)[0] == g]
    if len(rs) > 1: St[g + "_ens"] = np.mean([St[r] for r in rs], 0); Sv[g + "_ens"] = np.mean([Sv[r] for r in rs], 0)
for r in St:
    ent = {}
    for scheme in ("vehicle", "message"):
        yv, yt = labels(va, vact, scheme), labels(te, act, scheme)
        thr, vf1 = pick_thr(Sv[r], yv)
        e = dict(threshold=thr, val_f1=vf1, test=metrics(St[r], thr, te, yt))
        best = None                                                   # memory: decay and threshold both picked on validation
        for dec in (0.9, 0.95, 0.97, 0.99):
            Svm = mem(Sv[r], va, dec, ("v", r, dec)); t2, f2 = pick_thr(Svm, yv)
            if best is None or f2 > best[2]: best = (dec, t2, f2)
        dec, t2, f2 = best; Stm = mem(St[r], te, dec, ("t", r, dec))
        e["memory"] = dict(decay=dec, threshold=t2, val_f1=f2, test=metrics(Stm, t2, te, yt))
        if scheme == "vehicle": e["latency"] = latency(te, np.nan_to_num(St[r] > thr).astype(bool))
        ent[scheme] = e
    (res["ensemble"] if r.endswith("_ens") else res["runs"])[r] = ent
    m = ent["message"]["test"]; mm = ent["message"]["memory"]["test"]
    print(f"{r:18s} message: P {m['precision']:.4f} R {m['recall']:.4f} F1 {m['f1']:.4f} Acc {m['accuracy']:.4f} | +memory P {mm['precision']:.4f} R {mm['recall']:.4f} F1 {mm['f1']:.4f} Acc {mm['accuracy']:.4f}"
          f" | vehicle F1 {ent['vehicle']['test']['f1']:.4f}", flush=True)
# significance: full vs nonbr and full vs full-noaug, per seed, both schemes
for base in ("nonbr", "full-noaug"):
    out = {}
    for scheme in ("vehicle", "message"):
        per = []
        for s in sorted({int(r.rsplit("_", 1)[1]) for r in runs}):
            a, b = f"{base}_{s}", f"full_{s}"
            if a not in res["runs"] or b not in res["runs"]: continue
            yt = labels(te, act, scheme); D = dict(te, y=yt)
            fA = np.nan_to_num(St[a] > res["runs"][a][scheme]["threshold"]).astype(bool); fB = np.nan_to_num(St[b] > res["runs"][b][scheme]["threshold"]).astype(bool)
            ov = boot_diff(counts_by_receiver(fA, D), counts_by_receiver(fB, D), rng, B)
            ents = {"overall": dict(delta_f1=ov[0], ci95=ov[1], p_boot=ov[2], mcnemar=mcnemar(fA, fB, D))}
            ids = sorted(set(yt[yt > 0].tolist())); pv = []
            for at in ids:
                d = boot_diff(counts_by_receiver(fA, D, at), counts_by_receiver(fB, D, at), rng, B); ents[names[at]] = dict(delta_f1=d[0], ci95=d[1], p_boot=d[2]); pv.append(d[2])
            for at, pa in zip(ids, holm(np.array(pv))): ents[names[at]]["p_holm"] = float(pa)
            per.append(ents)
        out[scheme] = per
    res["significance"][f"full_vs_{base}"] = out
# rule baselines on the same windows (features 0-6 are the original ones), threshold picked on validation
Xv = np.load(f"{FEAT}/val.npy", mmap_mode="r"); Xt = np.load(f"{FEAT}/test.npy", mmap_mode="r")
rv = rule_scores(dict(X=np.asarray(Xv[..., :9], np.float32), M=va["M"])); rt = rule_scores(dict(X=np.asarray(Xt[..., :9], np.float32), M=te["M"]))
for k in rv:
    for scheme in ("vehicle", "message"):
        yv, yt = labels(va, vact, scheme), labels(te, act, scheme); v = yv >= 0
        ts = np.quantile(rv[k][v], np.linspace(0.05, 0.99, 60)); yy = (yv > 0)[v]
        f1 = [prf(((rv[k] > t)[v] & yy).sum(), ((rv[k] > t)[v] & ~yy).sum(), (~(rv[k] > t)[v] & yy).sum())[2] for t in ts]
        thr = float(ts[int(np.argmax(f1))]); res["rule_based"].setdefault(k, {})[scheme] = dict(threshold=thr, test=metrics(np.where(te["y"] >= 0, rt[k], np.nan), thr, te, yt))
json.dump(res, open(OUT, "w"), indent=1, default=float); print("saved", OUT)
