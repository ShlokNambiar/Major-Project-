"""v2 detector: original inputs + plausibility checks (nambd/features.py: kinematics, road map, nearest other claim) and training with
injected careful lies (nambd/collusion.augment; offset and stop only, the spoofed-approach convoy is held out for testing).
Same data, receivers, windows and val/test split as run_full.py. Raw windows are cached in data/cache_raw/ (git-ignored).
Saves per-window test scores + thresholds to PREDS (default results/preds_v2) and models to MODELS (default results/models_v2).
Variants (env VARIANTS, comma list): name = <mode>[-noaug][-<feature groups>], e.g. full, nonbr, full-noaug, full-base (all with aug unless -noaug)."""
import glob, json, os, re, time, pickle, numpy as np
from concurrent.futures import ProcessPoolExecutor

ROOT = "data"; MAXR = int(os.environ.get("MAXR", 250)); SEEDS = int(os.environ.get("SEEDS", 2)); EPOCHS = int(os.environ.get("EPOCHS", 8))
VARIANTS = os.environ.get("VARIANTS", "full,nonbr,full-noaug").split(","); AUGF = float(os.environ.get("AUGF", 0.5))
PREDS = os.environ.get("PREDS", "results/preds_v2"); MD = os.environ.get("MODELS", "results/models_v2"); CACHE = "data/cache_raw"
EXCLUDE = os.environ.get("EXCLUDE", "RandomSpeedOffset").split(",")
t0 = time.time()
log = lambda *a: print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)


def all_dirs(tag):
    return sorted({os.path.dirname(p) for p in glob.glob(f"{ROOT}/**/traceJSON-*.json", recursive=True)
                   if tag in os.path.dirname(p) and not any(x and x in p for x in EXCLUDE)})


def cache_path(d): return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9_]+", "_", d) + f"_{MAXR}.pkl")


def build_cache(args):
    """worker: parse one slice into its cache file; returns nothing (sending arrays back between processes exhausts memory on Windows)"""
    d, lo, hi, with_own = args
    if os.path.exists(cache_path(d)): return
    from nambd.data import load_veremi_raw
    p = load_veremi_raw(d, max_receivers=MAXR, with_own=with_own)
    if len(p["te"]) == 0 or not (lo <= p["te"].min() <= hi): p = None            # mislabeled / empty slice (see HANDOFF section 7)
    pickle.dump(p, open(cache_path(d), "wb"), protocol=4)


def load_one(d): return pickle.load(open(cache_path(d), "rb"))


def cat(parts):
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0] if k != "own"}


def sub(D, sl): return {k: v[sl] for k, v in D.items()}


FEAT = "data/cache_feat"


def build_features(log):
    """Phase 1 (once): raw windows -> float16 feature files in FEAT, freeing raw arrays as soon as they are used, so peak RAM stays low."""
    from nambd.features import RoadMap, featurize_to_file, FEAT_NAMES
    from nambd.collusion import augment
    nf = len(FEAT_NAMES)
    tr_dirs, late_dirs = all_dirs("50400_54000"), all_dirs("54000_57600")
    log("train subsets", len(tr_dirs), "late", len(late_dirs))
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count())) as ex:
        list(ex.map(build_cache, [(d, 50400, 50700, True) for d in tr_dirs] + [(d, 54000, 54300, False) for d in late_dirs]))
    trp = [p for p in (load_one(d) for d in tr_dirs) if p is not None]
    rmap = RoadMap(np.concatenate([p.pop("own") for p in trp])); log("road map", rmap.nx, "x", rmap.ny, "cells")
    pickle.dump(rmap, open(f"{PREDS}/roadmap.pkl", "wb"), protocol=4)
    tr = cat(trp); del trp
    ntr = len(tr["y"])
    for sd in range(SEEDS):                                         # train rows followed by this seed's augmented rows, one file per seed
        aug = augment(tr, np.random.default_rng(100 + sd), frac=AUGF)
        n = ntr + len(aug["y"]); out = np.lib.format.open_memmap(f"{FEAT}/train_{sd}.npy", mode="w+", dtype=np.float16, shape=(n,) + tr["M"].shape[1:] + (nf,))
        featurize_to_file(tr, rmap, None, nf, 0, out); featurize_to_file(aug, rmap, None, nf, ntr, out); del out
        np.savez(f"{FEAT}/train_{sd}_meta.npz", M=np.concatenate([tr["M"], aug["M"]]), y=np.concatenate([tr["y"], aug["y"]]), ntr=ntr)
        log("seed", sd, "train", ntr, "augmented", len(aug["y"]), "liars", int((aug["y"] == 99).sum())); del aug
    del tr
    names, va_p, te_p = {}, [], []
    for g, d in enumerate(late_dirs):
        p = load_one(d)
        if p is None: log("SKIP", d); continue
        p.pop("own", None); p["grp"] = np.full(len(p["te"]), g, np.int32)
        nm = re.search(r"([A-Za-z]+)_1416", d).group(1)
        for a in np.unique(p["y"][p["y"] > 0]): names[int(a)] = nm
        c = int(0.3 * len(p["te"])); va_p.append(sub(p, slice(None, c))); te_p.append(sub(p, slice(c, None)))
    va = cat(va_p); del va_p
    featurize_to_file(va, rmap, f"{FEAT}/val.npy", nf); np.savez(f"{PREDS}/val_meta.npz", y=va["y"], M=va["M"]); del va
    te = cat(te_p); del te_p
    featurize_to_file(te, rmap, f"{FEAT}/test.npy", nf)
    np.savez(f"{PREDS}/test_meta.npz", y=te["y"], rid=te["rid"], te=te["te"], sid=te["sid"], grp=te["grp"], M=te["M"])
    pickle.dump({k: te[k] for k in ("pos", "spd", "hed", "acl", "cnt", "M", "y", "ctr")}, open(f"{PREDS}/test_raw.pkl", "wb"), protocol=4)
    json.dump(names, open(f"{PREDS}/attack_names.json", "w")); log("features written", FEAT)


if __name__ == "__main__":
    import torch
    from nambd.features import GROUPS
    from nambd.train import fit, scores, best_thr
    for d in (CACHE, PREDS, MD, FEAT): os.makedirs(d, exist_ok=True)
    if not all(os.path.exists(f) for f in [f"{FEAT}/val.npy", f"{FEAT}/test.npy"] + [f"{FEAT}/train_{s}.npy" for s in range(SEEDS)]):
        build_features(log)
    mm = lambda f: np.load(f, mmap_mode="c")                      # copy-on-write memmap: torch can wrap it without loading it into RAM
    Xva, Xte = mm(f"{FEAT}/val.npy"), mm(f"{FEAT}/test.npy")
    zv = np.load(f"{PREDS}/val_meta.npz"); va = dict(M=zv["M"], y=zv["y"]); zt = np.load(f"{PREDS}/test_meta.npz"); te = dict(M=zt["M"], y=zt["y"])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    for sd in range(SEEDS):
        Xtr = mm(f"{FEAT}/train_{sd}.npy"); zm = np.load(f"{FEAT}/train_{sd}_meta.npz"); ntr = int(zm["ntr"]); Mtr, ytr = zm["M"], zm["y"]
        for v in VARIANTS:
            f = f"{PREDS}/{v}_{sd}.npz"
            if os.path.exists(f): continue
            parts = v.split("-"); mode = parts[0]; noaug = "noaug" in parts
            groups = [g for g in parts[1:] if g in GROUPS] or list(GROUPS)
            cols = sorted(set(sum((GROUPS[g] for g in groups), [])) | set(GROUPS["base"]))
            allc = len(cols) == Xtr.shape[-1]; pick = (lambda X: X) if allc else (lambda X: X[..., cols])
            n = ntr if noaug else len(ytr)
            m = fit(mode, dict(X=pick(Xtr[:n]), M=Mtr[:n], y=ytr[:n]), epochs=EPOCHS, seed=sd, log=log, device=dev)
            sv, yv = scores(m, dict(X=pick(Xva), M=va["M"], y=va["y"]), mode); thr = float(best_thr(sv, yv, fine=True))
            st, _ = scores(m, dict(X=pick(Xte), M=te["M"], y=te["y"]), mode)
            Sfull = np.full(te["y"].shape, np.nan, np.float32); Sfull[te["y"] >= 0] = st
            np.savez_compressed(f, thr=thr, test=Sfull, cols=np.array(cols)); torch.save(m.state_dict(), f"{MD}/{v}_{sd}.pt")
            yy = te["y"][te["y"] >= 0] > 0; ff = st > thr; tp = (ff & yy).sum(); fp = (ff & ~yy).sum(); fn = (~ff & yy).sum()
            log(f"saved {v}_{sd} thr {thr:.2f}  P {tp / (tp + fp):.4f} R {tp / (tp + fn):.4f} F1 {2 * tp / (2 * tp + fp + fn):.4f} Acc {(ff == yy).mean():.4f}")
            del m; torch.cuda.empty_cache()
    log("done")
