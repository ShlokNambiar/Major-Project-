"""Receiver-centric window construction: every sample is (receiver, end-time) with the
K nearest (by claimed distance) senders heard at the end step and T steps of history."""
import json, glob, os
import numpy as np
from .sim import simulate, SimConfig

F = 8  # relx, rely, speed, cos h, sin h, dx, dy, valid


def _features(rel, spd, hed, valid):
    """rel: (K,T,2) claimed pos relative to receiver / range-scale; returns (K,T,F)."""
    K, T, _ = rel.shape
    d = np.zeros_like(rel)
    d[:, 1:] = rel[:, 1:] - rel[:, :-1]
    ok = valid.copy(); ok[:, 1:] &= valid[:, :-1]; ok[:, 0] = False
    d = d * ok[..., None]
    return np.concatenate([rel, spd[..., None] / 30.0, np.cos(hed)[..., None],
                           np.sin(hed)[..., None], d * 3.0, valid[..., None]], -1).astype(np.float32)


def windows_from_sim(sim, n_per_step=40, T=10, K=16, stride=3, seed=0, scale=None):
    rng = np.random.default_rng(seed)
    P, C, CV, H, label = sim["P"], sim["C"], sim["CV"], sim["H"], sim["label"]
    R = sim["cfg"].comm_range
    scale = scale or R
    steps, n = len(P), P.shape[1]
    X, M, Y, SID = [], [], [], []
    for te in range(T - 1, steps, stride):
        for r in rng.choice(n, n_per_step, replace=False):
            ts = slice(te - T + 1, te + 1)
            D = np.linalg.norm(P[ts] - P[ts, r][:, None], axis=-1)       # (T,n) true distances
            valid = D <= R; valid[:, r] = False
            cand = np.where(valid[-1])[0]
            if len(cand) == 0:
                continue
            cd = np.linalg.norm(C[te, cand] - P[te, r], axis=-1)
            sel = cand[np.argsort(cd)[:K]]
            k = len(sel)
            rel = (C[ts][:, sel] - P[te, r]).transpose(1, 0, 2) / scale
            xs = np.zeros((K, T, F), np.float32); ms = np.zeros((K, T), bool); ys = -np.ones(K, np.int64)
            v = valid[:, sel].T
            xs[:k] = _features(rel, CV[ts][:, sel].T, H[ts][:, sel].T, v)
            ms[:k] = v; ys[:k] = label[sel]
            X.append(xs); M.append(ms); Y.append(ys)
            sid = -np.ones(K, np.int64); sid[:k] = sim["ids"][sel]; SID.append(sid)
    return dict(X=np.stack(X), M=np.stack(M), y=np.stack(Y), sid=np.stack(SID))


def build(cfg: SimConfig, seeds, id_base=0, **kw):
    parts = []
    for i, s in enumerate(seeds):
        sim = simulate(cfg, s, id_offset=id_base + i * 10000)
        parts.append(windows_from_sim(sim, seed=s, **kw))
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


# ---------------------------------------------------------------- real VeReMi logs
def load_veremi(trace_dir, gt_file=None, T=10, K=16, comm_range=300.0, stride=3, max_receivers=None):
    """Load a VeReMi Extension simulation folder (validated against the real Zenodo archives).

    trace_dir: folder with traceJSON-<vehId>-<pseudo>-A<attackType>-<start>-<run>.json, one log per
        vehicle; each line is type 2 (receiver's own state) or type 3 (received BSM with `sender`,
        `rcvTime`, pos, spd, hed). The attack type of vehicle <vehId> is encoded in its filename
        (A0 = benign); sender ids in BSMs are vehicle ids, so labels are looked up from filenames.
        Messages are binned to 1 s. gt_file is unused (kept for API compatibility).
    """
    gt = {}
    for fp in glob.glob(os.path.join(trace_dir, "traceJSON-*.json")):
        p = os.path.basename(fp).split("-")
        gt[int(p[1])] = int(p[3][1:])
    X, M, Y, SID, TE, RID = [], [], [], [], [], []
    files = sorted(glob.glob(os.path.join(trace_dir, "traceJSON-*.json")))[:max_receivers]
    for fp in files:
        rid = int(os.path.basename(fp).split('-')[1])
        own, bsm = {}, {}
        with open(fp) as f:
            for line in f:
                r = json.loads(line)
                t = int(r["rcvTime"])
                if r["type"] == 2:
                    own[t] = np.array(r["pos"][:2])
                else:
                    bsm.setdefault(t, {})[r["sender"]] = (np.array(r["pos"][:2]), float(np.linalg.norm(r["spd"][:2])),
                                                           float(np.arctan2(r["hed"][1], r["hed"][0])))
        for te in range(min(own) + T - 1, max(own) + 1, stride):
            if te not in bsm or any(t not in own for t in range(te - T + 1, te + 1)):
                continue
            ctr = own[te]
            senders = sorted(bsm[te], key=lambda s: np.linalg.norm(bsm[te][s][0] - ctr))[:K]
            xs = np.zeros((K, T, F), np.float32); ms = np.zeros((K, T), bool); ys = -np.ones(K, np.int64)
            sid = -np.ones(K, np.int64)
            for j, s in enumerate(senders):
                rel = np.zeros((T, 2)); sp = np.zeros(T); hd = np.zeros(T); v = np.zeros(T, bool)
                for a, t in enumerate(range(te - T + 1, te + 1)):
                    if t in bsm and s in bsm[t]:
                        p, spd, hed = bsm[t][s]; rel[a] = (p - ctr) / comm_range; sp[a] = spd; hd[a] = hed; v[a] = True
                xs[j] = _features(rel[None], sp[None], hd[None], v[None])[0]; ms[j] = v
                ys[j] = gt.get(s, 0); sid[j] = s
            X.append(xs); M.append(ms); Y.append(ys); SID.append(sid); TE.append(te); RID.append(rid)
    return dict(X=np.stack(X), M=np.stack(M), y=np.stack(Y), sid=np.stack(SID),
                te=np.array(TE), rid=np.array(RID))
