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
def load_veremi(trace_dir, gt_file=None, T=10, K=16, comm_range=300.0, stride=3, max_receivers=None, rate=False):
    """Load a VeReMi Extension simulation folder (validated against the real Zenodo archives).

    trace_dir: folder with traceJSON-<vehId>-<pseudo>-A<attackType>-<start>-<run>.json, one log per
        vehicle; each line is type 2 (receiver's own state) or type 3 (received BSM with `sender`,
        `rcvTime`, pos, spd, hed). The attack type of vehicle <vehId> is encoded in its filename
        (A0 = benign); sender ids in BSMs are vehicle ids, so labels are looked up from filenames.
        Messages are binned to 1 s. gt_file is unused (kept for API compatibility).
        rate=True appends a 9th feature, log(1 + messages heard from the sender in that second) / 3, so that
        flooding (DoS) attacks are visible; default False keeps the original 8 features.
    """
    gt = {}
    for fp in glob.glob(os.path.join(trace_dir, "traceJSON-*.json")):
        p = os.path.basename(fp).split("-")
        gt[int(p[1])] = int(p[3][1:])
    X, M, Y, SID, TE, RID = [], [], [], [], [], []
    files = sorted(glob.glob(os.path.join(trace_dir, "traceJSON-*.json")))
    if max_receivers and len(files) > max_receivers:      # evenly spaced subsample over receivers
        files = [files[i] for i in np.linspace(0, len(files) - 1, max_receivers).astype(int)]
    for fp in files:
        rid = int(os.path.basename(fp).split('-')[1])
        own, bsm, cnt = {}, {}, {}
        with open(fp) as f:
            for line in f:
                r = json.loads(line)
                t = int(r["rcvTime"])
                if r["type"] == 2:
                    own[t] = np.array(r["pos"][:2])
                else:
                    cnt[(t, r["sender"])] = cnt.get((t, r["sender"]), 0) + 1
                    bsm.setdefault(t, {})[r["sender"]] = (np.array(r["pos"][:2]), float(np.linalg.norm(r["spd"][:2])),
                                                           float(np.arctan2(r["hed"][1], r["hed"][0])))
        for te in range(min(own) + T - 1, max(own) + 1, stride):
            if te not in bsm or any(t not in own for t in range(te - T + 1, te + 1)):
                continue
            ctr = own[te]
            senders = sorted(bsm[te], key=lambda s: np.linalg.norm(bsm[te][s][0] - ctr))[:K]
            xs = np.zeros((K, T, F + int(rate)), np.float32); ms = np.zeros((K, T), bool); ys = -np.ones(K, np.int64)
            sid = -np.ones(K, np.int64)
            for j, s in enumerate(senders):
                rel = np.zeros((T, 2)); sp = np.zeros(T); hd = np.zeros(T); v = np.zeros(T, bool); rt = np.zeros(T)
                for a, t in enumerate(range(te - T + 1, te + 1)):
                    if t in bsm and s in bsm[t]:
                        p, spd, hed = bsm[t][s]; rel[a] = (p - ctr) / comm_range; sp[a] = spd; hd[a] = hed; v[a] = True; rt[a] = np.log1p(cnt[(t, s)]) / 3.0
                xs[j, :, :F] = _features(rel[None], sp[None], hd[None], v[None])[0]; ms[j] = v
                if rate: xs[j, :, F] = rt
                ys[j] = gt.get(s, 0); sid[j] = s
            X.append(xs); M.append(ms); Y.append(ys); SID.append(sid); TE.append(te); RID.append(rid)
    return dict(X=np.stack(X), M=np.stack(M), y=np.stack(Y), sid=np.stack(SID),
                te=np.array(TE), rid=np.array(RID))


def load_veremi_raw(trace_dir, T=10, K=16, stride=3, max_receivers=None, with_own=False):
    """Same windows as load_veremi (same receivers, end times, sender selection), but returns the raw claims so that
    features can be recomputed after changing them (nambd/features.py, nambd/collusion.py):
      pos (N,K,T,2) absolute claimed position (m), spd (N,K,T) m/s, hed (N,K,T) rad, acl (N,K,T) claimed acceleration along
      the claimed heading (m/s^2), cnt (N,K,T) messages heard from the sender in that second, M valid, ctr (N,2) receiver
      position at the window end, own (list of (x, y, heading) receiver states, used only to build the road map)."""
    gt = {}
    for fp in glob.glob(os.path.join(trace_dir, "traceJSON-*.json")):
        p = os.path.basename(fp).split("-"); gt[int(p[1])] = int(p[3][1:])
    files = sorted(glob.glob(os.path.join(trace_dir, "traceJSON-*.json")))
    own_all = []
    own_files = files                                     # every vehicle's own states feed the road map (with_own=True)
    if max_receivers and len(files) > max_receivers:
        files = [files[i] for i in np.linspace(0, len(files) - 1, max_receivers).astype(int)]
    keep = set(files)
    if not with_own: own_files = files
    out = {k: [] for k in ("pos", "spd", "hed", "acl", "cnt", "M", "y", "sid", "te", "rid", "ctr")}
    for fp in own_files:
        rid = int(os.path.basename(fp).split('-')[1])
        own, bsm, cnt = {}, {}, {}
        with open(fp) as f:
            for line in f:
                if fp not in keep and not line.startswith('{"type":2'): continue
                r = json.loads(line); t = int(r["rcvTime"])
                if r["type"] == 2:
                    own[t] = np.array(r["pos"][:2])
                    if with_own: own_all.append((r["pos"][0], r["pos"][1], np.arctan2(r["hed"][1], r["hed"][0]), np.hypot(*r["spd"][:2])))
                elif fp in keep:
                    cnt[(t, r["sender"])] = cnt.get((t, r["sender"]), 0) + 1
                    h = np.array(r["hed"][:2]); h = h / max(np.linalg.norm(h), 1e-9)
                    bsm.setdefault(t, {})[r["sender"]] = (np.array(r["pos"][:2]), float(np.linalg.norm(r["spd"][:2])),
                                                           float(np.arctan2(h[1], h[0])), float(np.dot(r["acl"][:2], h)))
        if fp not in keep or not own:
            continue
        for te in range(min(own) + T - 1, max(own) + 1, stride):
            if te not in bsm or any(t not in own for t in range(te - T + 1, te + 1)):
                continue
            ctr = own[te]
            senders = sorted(bsm[te], key=lambda s: np.linalg.norm(bsm[te][s][0] - ctr))[:K]
            pos = np.zeros((K, T, 2)); sp = np.zeros((K, T)); hd = np.zeros((K, T)); ac = np.zeros((K, T)); cn = np.zeros((K, T))
            ms = np.zeros((K, T), bool); ys = -np.ones(K, np.int64); sid = -np.ones(K, np.int64)
            for j, s in enumerate(senders):
                for a, t in enumerate(range(te - T + 1, te + 1)):
                    if t in bsm and s in bsm[t]:
                        p, v, h, c = bsm[t][s]; pos[j, a] = p; sp[j, a] = v; hd[j, a] = h; ac[j, a] = c; cn[j, a] = cnt[(t, s)]; ms[j, a] = True
                ys[j] = gt.get(s, 0); sid[j] = s
            for k, v in zip(out, (pos, sp, hd, ac, cn, ms, ys, sid, te, rid, ctr)): out[k].append(v)
    D = {k: np.stack(v) if k not in ("te", "rid") else np.array(v) for k, v in out.items()}
    D["pos"] = D["pos"].astype(np.float64); D["own"] = np.array(own_all, np.float64)
    return D
