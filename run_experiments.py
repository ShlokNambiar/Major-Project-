"""Reproduces every number in the paper. Usage: python run_experiments.py [--quick]"""
import json, sys, time, numpy as np
from nambd.sim import SimConfig, URBAN
from nambd.data import build
from nambd.train import fit, scores, best_thr, evaluate

quick = "--quick" in sys.argv
EP = 3 if quick else 5
NS = 1 if quick else 3
nsim = (2, 1, 1) if quick else (4, 1, 2)
HW = SimConfig()
t0 = time.time()
log = lambda *a: print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)

# Disjoint simulation runs => held-out sender identities between train / val / test.
tr = build(HW, range(100, 100 + nsim[0]), id_base=0)
va = build(HW, range(200, 200 + nsim[1]), id_base=10**6)
te = build(HW, range(300, 300 + nsim[2]), id_base=2 * 10**6)
tgt_u = build(URBAN, range(400, 400 + nsim[0]), id_base=3 * 10**6)       # unlabeled target (training)
tgt_va = build(URBAN, range(500, 500 + nsim[1]), id_base=4 * 10**6)
tgt_te = build(URBAN, range(600, 600 + nsim[2]), id_base=5 * 10**6)
log("windows", {k: v["X"].shape for k, v in dict(train=tr, val=va, test=te, tgt=tgt_te).items()})

out = {"in_domain": {}, "transfer": {}, "meta": dict(epochs=EP, seeds=NS, n_train=len(tr["X"]), n_test=len(te["X"]),
                                                     n_tgt_test=len(tgt_te["X"]))}
for mode in ["persender", "nonbr", "full"]:
    runs = []
    for sd in range(NS):
        m = fit(mode, tr, epochs=EP, seed=sd, log=log)
        thr = best_thr(*scores(m, va, mode))
        runs.append(evaluate(*scores(m, te, mode), thr))
        if mode == "full":   # source-only transfer baseline: same model, evaluated on the target domain
            out["transfer"].setdefault("source_only", []).append(evaluate(*scores(m, tgt_te, mode), thr))
        log(mode, "seed", sd, "macro F1 %.3f" % runs[-1]["Macro"]["f1"], "ConstPosOffset F1 %.3f" % runs[-1]["ConstPosOffset"]["f1"])
    out["in_domain"][mode] = runs
    json.dump(out, open("results/results.json", "w"), indent=1)

# Domain-adversarial training (full model); threshold from SOURCE validation only (no target labels).
for lam in [0.05, 0.2]:
    runs = []
    for sd in range(min(NS, 2)):
        m = fit("full", tr, tgt=tgt_u, dann=lam, epochs=EP, seed=sd, log=log)
        thr = best_thr(*scores(m, va, "full"))
        runs.append(evaluate(*scores(m, tgt_te, "full"), thr))
        log("dann", lam, "seed", sd, "macro F1 %.3f" % runs[-1]["Macro"]["f1"])
    out["transfer"][f"dann_{lam}"] = runs
    json.dump(out, open("results/results.json", "w"), indent=1)
log("done")
