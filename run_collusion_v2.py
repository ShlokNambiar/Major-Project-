"""Collusion stress test for the v2 models (run_v2.py): the same three scenarios as run_collusion.py, injected into the raw claims of the
test windows, all features recomputed (road map, kinematics, nearest other claim). Training saw offset and stop lies only;
the spoofed-approach convoy is never seen in training. -> results/results_collusion_v2.json"""
import glob, json, os, pickle, time, numpy as np, torch
from nambd.model import Detector
from nambd.train import MODES
from nambd.features import featurize
from nambd.collusion import make_set_raw, SCENARIOS

P = os.environ.get("PREDS", "results/preds_v2"); MD = os.environ.get("MODELS", "results/models_v2")
NW = int(os.environ.get("NWIN", 4000)); MS = [1, 2, 4, 6, 8]; OUT = os.environ.get("OUT", "results/results_collusion_v2.json")
dev = "cuda" if torch.cuda.is_available() else "cpu"; t0 = time.time()
log = lambda *a: print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)
raw = pickle.load(open(f"{P}/test_raw.pkl", "rb")); rmap = pickle.load(open(f"{P}/roadmap.pkl", "rb"))
z = np.load(f"{P}/val_meta.npz"); va = dict(M=z["M"], y=z["y"], X=np.load(os.environ.get("FEAT", "data/cache_feat") + "/val.npy", mmap_mode="r"))
runs = sorted(os.path.basename(f)[:-4] for f in glob.glob(f"{P}/*_[0-9].npz") if "meta" not in f)
models = {}
for r in runs:
    zr = np.load(f"{P}/{r}.npz"); cols = zr["cols"]; mode = r.split("-")[0].rsplit("_", 1)[0]
    m = Detector(fin=len(cols), spatial=MODES[mode]["spatial"]); m.load_state_dict(torch.load(f"{MD}/{r}.pt", weights_only=True))
    models[r] = (m.to(dev).eval(), cols, float(zr["thr"]))


@torch.no_grad()
def score(r, X, M, bs=1024):
    m, cols, _ = models[r]
    return np.concatenate([torch.sigmoid(m(torch.tensor(X[i:i + bs][..., cols], dtype=torch.float32).to(dev), torch.tensor(M[i:i + bs]).to(dev))).cpu().numpy()
                           for i in range(0, len(X), bs)])


thr1 = {r: float(np.quantile(score(r, va["X"], va["M"])[va["y"] == 0], 0.99)) for r in runs}
log("runs", runs, "thr at 1% val FPR", {r: round(t, 4) for r, t in thr1.items()})


def rates(S, Y, r):
    g = lambda f, s: float(f[s].mean()) if s.any() else None
    f, f1 = S > models[r][2], S > thr1[r]
    return dict(colluder_recall=g(f, Y == -2), honest_fpr=g(f, Y == 0), real_attacker_recall=g(f, Y > 0),
                colluder_recall_fpr1=g(f1, Y == -2), honest_fpr_fpr1=g(f1, Y == 0))


res = {"thr_fpr1": thr1, "injected": {}, "magnitude": {}, "setup": dict(m=MS, scenarios=SCENARIOS, runs=runs, held_out_in_training=["approach"])}
for sc in SCENARIOS:
    for coord in (True, False):
        key = f"{sc}_{'coordinated' if coord else 'independent'}"; res["injected"][key] = {}
        for m in MS:
            S, win = make_set_raw(raw, m, sc, coord, np.random.default_rng(1000 + m), n_windows=NW, min_honest=max(MS) + 1)
            Xn = featurize(S, rmap); Xc = featurize(raw, rmap, idx=win)
            res["injected"][key][m] = {r: dict(injected=rates(score(r, Xn, S["M"]), S["y"], r), clean=rates(score(r, Xc, S["M"]), S["y"], r)) for r in runs}
            res["setup"]["windows_used"] = int(len(win))
            log(key, "m", m, {r: round(e["injected"]["colluder_recall_fpr1"], 3) for r, e in res["injected"][key][m].items()})
for sc, arg, vals in (("offset", "off_m", [10, 25, 50, 100, 200, 400]), ("stop", "stop_at", [8, 5, 2]), ("approach", "v", [5, 10, 15, 25])):
    key = f"{sc}_coordinated"; res["magnitude"][key] = {}
    for v in vals:
        S, win = make_set_raw(raw, 4, sc, True, np.random.default_rng(2000), n_windows=NW, min_honest=max(MS) + 1, **{arg: v})
        Xn = featurize(S, rmap); lab = 10 - v if sc == "stop" else v
        res["magnitude"][key][lab] = {r: rates(score(r, Xn, S["M"]), S["y"], r) for r in runs}
        log(key, arg, v, {r: round(e["colluder_recall_fpr1"], 3) for r, e in res["magnitude"][key][lab].items()})
json.dump(res, open(OUT, "w"), indent=1); log("saved", OUT)
