"""Message-level ground truth for the test windows of run_v2.py.
A received BSM is falsified if its claimed position differs by > 1 m, or its speed by > 0.5 m/s, from the sender's true state
(traceGroundTruthJSON, last true send at or before reception). Honest messages match exactly (error 0.00 m), so the tolerance only
absorbs float noise. An attacker slot of a window is *active* if it sent at least one falsified message within the window's T steps;
DoS-family attackers (13 DoS, 14 DoSRandom, 15 DoSDisruptive) misbehave by flooding and count as active throughout.
Output: PREDS/test_active.npz with active (N,K) bool, true only for attacker slots that are active (honest slots: False).
Inactive attacker slots (e.g. EventualStop before the fake stop starts) are excluded from message-level scoring."""
import bisect, glob, json, os, re, sys, numpy as np
from concurrent.futures import ProcessPoolExecutor

P = os.environ.get("PREDS", "results/preds_v2"); T = 10; FLOOD = {13, 14, 15} | {int(x) for x in os.environ.get("FLOOD_EXTRA", "").split(",") if x}


def falsified_slice(args):
    """-> set of (rid, second, sender) with at least one falsified message, for the given receivers of one slice."""
    d, rids = args
    traj = {}
    for line in open(glob.glob(os.path.join(d, "traceGroundTruthJSON-*.json"))[0]):
        r = json.loads(line); traj.setdefault(r["sender"], []).append((r["sendTime"], r["pos"][0], r["pos"][1], (r["spd"][0] ** 2 + r["spd"][1] ** 2) ** 0.5))
    for s in traj: traj[s].sort()
    times = {s: [x[0] for x in v] for s, v in traj.items()}
    bad = set()
    for f in glob.glob(os.path.join(d, "traceJSON-*.json")):
        rid = int(os.path.basename(f).split("-")[1])
        if rid not in rids: continue
        for line in open(f):
            if not line.startswith('{"type":3'): continue
            r = json.loads(line); s = r["sender"]; tr = traj.get(s)
            if not tr: continue
            i = bisect.bisect_right(times[s], r["rcvTime"]) - 1
            if i < 0: continue
            _, x, y, v = tr[i]
            if ((r["pos"][0] - x) ** 2 + (r["pos"][1] - y) ** 2) ** 0.5 > 1.0 or abs((r["spd"][0] ** 2 + r["spd"][1] ** 2) ** 0.5 - v) > 0.5:
                bad.add((rid, int(r["rcvTime"]), s))
    return bad


def label(y, rid, te, sid, grp, bads):
    active = np.zeros(y.shape, bool)
    for i in range(len(y)):
        b = bads[grp[i]]
        for j in np.nonzero(y[i] > 0)[0]:
            active[i, j] = int(y[i, j]) in FLOOD or any((int(rid[i]), t, int(sid[i, j])) in b for t in range(te[i] - T + 1, te[i] + 1))
    return active


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from run_v2 import all_dirs, load_one
    late = all_dirs("54000_57600")
    z = np.load(f"{P}/test_meta.npz"); y, rid, te, grp = z["y"], z["rid"], z["te"], z["grp"]
    sid = z["veh"] if "veh" in z.files else z["sid"]          # ground truth is keyed by vehicle id, not pseudonym
    V = {k: [] for k in ("y", "rid", "te", "sid", "grp")}                       # validation windows: first 30% of each slice (as run_v2.py)
    for g, d in enumerate(late):
        p = load_one(d)
        if p is None: continue
        c = int(0.3 * len(p["te"]))
        for k in ("y", "rid", "te"): V[k].append(p[k][:c])
        V["sid"].append(p.get("veh", p["sid"])[:c])
        V["grp"].append(np.full(c, g, np.int32))
    V = {k: np.concatenate(v) for k, v in V.items()}
    jobs = [(d, set(rid[grp == g].tolist()) | set(V["rid"][V["grp"] == g].tolist())) for g, d in enumerate(late)]
    with ProcessPoolExecutor(max_workers=4) as ex: bads = list(ex.map(falsified_slice, jobs))
    active = label(y, rid, te, sid, grp, bads)
    vy = np.load(f"{P}/val_meta.npz")["y"]; assert np.array_equal(vy, V["y"]), "validation windows do not match val_meta"
    np.savez_compressed(f"{P}/test_active.npz", active=active, val_active=label(V["y"], V["rid"], V["te"], V["sid"], V["grp"], bads))
    names = {int(k): v for k, v in json.load(open(f"{P}/attack_names.json")).items()}
    for a in sorted(names): print(f"{names[a]:16s} active share of attacker slots {active[y == a].mean():.3f}")
