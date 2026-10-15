"""Malicious-neighbour analysis (professor's point 2) on the saved 14-attack test windows and trained models.
Part A, natural: recall / FPR of every saved model binned by the share of attackers among the senders in the window.
Part B, injected collusion: m honest senders per window become colluders (nambd/collusion.py), coordinated or
independent; we report colluder recall, honest-sender FPR, and recall on the window's real attackers, against the
same windows without injection. nonbr is blind to other senders, so any change in `full` that nonbr does not show
comes from neighbour attention. Needs PREDS (from run_full.py) and MODELS. -> results/results_collusion.json"""
import glob, json, os, time, numpy as np, torch
from nambd.model import Detector
from nambd.train import MODES
from nambd.evalutil import rule_scores, prf
from nambd.collusion import make_set, SCENARIOS

P = os.environ.get("PREDS", "results/preds14"); MD = os.environ.get("MODELS", "results/models14")
NW = int(os.environ.get("NWIN", 4000)); MS = [int(m) for m in os.environ.get("MS", "1,2,4,6,8").split(",")]
OUT = os.environ.get("OUT", "results/results_collusion.json")
dev = "cuda" if torch.cuda.is_available() else "cpu"; t0 = time.time()
log = lambda *a: print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)
z = np.load(f"{P}/test_meta.npz"); te = {k: z[k] for k in z.files}
z = np.load(f"{P}/val_meta.npz"); va = {k: z[k] for k in z.files}
runs = sorted(os.path.basename(f)[:-4] for f in glob.glob(f"{P}/*_[0-9].npz"))
models = {}
for r in runs:
    mode = r.rsplit("_", 1)[0]
    m = Detector(fin=te["X"].shape[-1], spatial=MODES[mode]["spatial"]); m.load_state_dict(torch.load(f"{MD}/{r}.pt", weights_only=True))
    models[r] = (m.to(dev).eval(), mode, float(np.load(f"{P}/{r}.npz")["thr"]))
log("runs", runs, "device", dev)


@torch.no_grad()
def score(r, X, M, bs=1024):
    m, mode, _ = models[r]; out = []
    for i in range(0, len(X), bs):
        x = torch.tensor(X[i:i + bs], dtype=torch.float32); x[..., MODES[mode]["drop"]] = 0
        out.append(torch.sigmoid(m(x.to(dev), torch.tensor(M[i:i + bs]).to(dev))).cpu().numpy())
    return np.concatenate(out)


thr1 = {}                                    # threshold giving 1% FPR on honest validation senders: compares models at equal false alarms
for r in runs:
    Sv = score(r, va["X"], va["M"]); thr1[r] = float(np.quantile(Sv[va["y"] == 0], 0.99))
log("thr at 1% val FPR", {r: round(t, 4) for r, t in thr1.items()})

res = {"thr_fpr1": thr1, "natural": {}, "injected": {}, "rules": {}, "setup": dict(n_windows=NW, m=MS, scenarios=SCENARIOS, runs=runs)}

# ---------------- A. natural attacker share (real VeReMi attackers, saved test predictions)
y = te["y"]; share = (y > 0).sum(1) / np.maximum((y >= 0).sum(1), 1)
bins = [0, 0.2, 0.4, 0.6, 1.01]; b = np.digitize(share, bins) - 1
res["natural"]["bins"] = [f"{int(bins[i] * 100)}-{min(int(bins[i + 1] * 100), 100)}%" for i in range(len(bins) - 1)]
res["natural"]["n_windows"] = [int((b == i).sum()) for i in range(len(bins) - 1)]
for r in runs:
    S = np.load(f"{P}/{r}.npz")["test"]; f = S > models[r][2]; rows = []
    for i in range(len(bins) - 1):
        w = b == i; yy = y[w]; ff = f[w]
        rows.append(dict(recall=float(ff[yy > 0].mean()) if (yy > 0).any() else None, fpr=float(ff[yy == 0].mean()) if (yy == 0).any() else None))
    res["natural"][r] = rows
log("natural done", res["natural"]["n_windows"])

# ---------------- rule baselines: thresholds picked on validation as in run_analysis.py
rv = rule_scores(va); rthr = {}
for k in rv:
    v = va["y"] >= 0; ts = np.quantile(rv[k][v], np.linspace(0.05, 0.99, 60)); yv = (va["y"] > 0)[v]
    f1s = [prf(((rv[k] > t)[v] & yv).sum(), ((rv[k] > t)[v] & ~yv).sum(), (~(rv[k] > t)[v] & yv).sum())[2] for t in ts]
    rthr[k] = float(ts[int(np.argmax(f1s))])


def rates(flag, Y, flag1=None):
    g = lambda f, s: float(f[s].mean()) if s.any() else None
    out = dict(colluder_recall=g(flag, Y == -2), honest_fpr=g(flag, Y == 0), real_attacker_recall=g(flag, Y > 0))
    if flag1 is not None: out.update(colluder_recall_fpr1=g(flag1, Y == -2), honest_fpr_fpr1=g(flag1, Y == 0))
    return out


# ---------------- B. injected collusion: same windows for every m (enough honest senders for the largest m + 1)
for sc in SCENARIOS:
    for coord in (True, False):
        key = f"{sc}_{'coordinated' if coord else 'independent'}"; res["injected"][key] = {}; res["rules"][key] = {}
        for m in MS:
            Xn, Mn, Yn, win = make_set(te["X"], te["M"], te["y"], m, sc, coord, np.random.default_rng(1000 + m), n_windows=NW, min_honest=max(MS) + 1)
            Xc = te["X"][win].astype(np.float32)                                # same windows without injection (colluder slots still honest)
            ent = {}
            for r in runs:
                thr = models[r][2]; Sn, Sc = score(r, Xn, Mn), score(r, Xc, Mn)
                ent[r] = dict(injected=rates(Sn > thr, Yn, Sn > thr1[r]), clean=rates(Sc > thr, Yn, Sc > thr1[r]))
            res["injected"][key][m] = ent; res["setup"]["windows_used"] = int(len(win))
            rs = rule_scores(dict(X=Xn, M=Mn))
            res["rules"][key][m] = {k: rates(rs[k] > rthr[k], Yn) for k in rs}
            log(key, "m", m, "windows", len(win), {r: round(e["injected"]["colluder_recall"], 3) for r, e in ent.items()})
# ---------------- C. how large must a lie be before it is caught? offset size and stop duration, m = 4
res["magnitude"] = {}
for sc, arg, vals in (("offset", "off_m", [25, 50, 100, 200, 400]), ("stop", "stop_at", [8, 5, 2])):
    for coord in ((True, False) if sc == "offset" else (True,)):      # independent stops draw their own stop step
        key = f"{sc}_{'coordinated' if coord else 'independent'}"; res["magnitude"][key] = {}
        for v in vals:
            Xn, Mn, Yn, win = make_set(te["X"], te["M"], te["y"], 4, sc, coord, np.random.default_rng(2000), n_windows=NW, min_honest=max(MS) + 1, **{arg: v})
            lab = v if sc == "offset" else te["X"].shape[2] - v                  # stop: seconds spent stopped inside the 10 s window
            res["magnitude"][key][lab] = {r: (lambda S: rates(S > models[r][2], Yn, S > thr1[r]))(score(r, Xn, Mn)) for r in runs}
            log(key, arg, v, {r: round(e["colluder_recall"], 3) for r, e in res["magnitude"][key][lab].items()})

# ---------------- D. part A controlled for attack mix: per attack type, recall by attacker-share bin (bins with >= 200 attacker slots)
names = {int(k): v for k, v in json.load(open(f"{P}/attack_names.json")).items()}
res["natural_by_attack"] = {}
for a in sorted(set(y[y > 0].tolist())):
    ent = {}
    for r in runs:
        f = np.load(f"{P}/{r}.npz")["test"] > models[r][2]
        ent[r] = [float(f[(b == i)[:, None] & (y == a)].mean()) if ((b == i)[:, None] & (y == a)).sum() >= 200 else None for i in range(len(bins) - 1)]
    res["natural_by_attack"][names.get(a, f"A{a}")] = ent
json.dump(res, open(OUT, "w"), indent=1)
log("saved", OUT)
