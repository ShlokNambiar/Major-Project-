"""18-attack extension (14 + 4 Sybil): final ensemble = mean score of full_0, full_1 (d=64) and the d=96/3-block model, threshold picked on
validation (message labels / vehicle labels separately). -> results/results_v18_final.json, paper/tables_v18.tex (overall rows only;
per-attack F1 is plotted by make_paper_figs.py). TABLES_ONLY=1 rewrites the table from the saved JSON without recomputing."""
import json, os, numpy as np
TABLES_ONLY = os.environ.get("TABLES_ONLY") == "1"
from nambd.evalutil import prf, attack_mask
P = "results/preds_v18"; FEAT = "data/cache_feat18b"
zv = np.load(f"{P}/val_meta.npz"); vy, vM = zv["y"], zv["M"]; zt = np.load(f"{P}/test_meta.npz"); y = zt["y"]; D = dict(y=y, grp=zt["grp"])
A = np.load(f"{P}/test_active.npz"); act, vact = A["active"], A["val_active"]
names = {int(k): v for k, v in json.load(open(f"{P}/attack_names.json")).items()}
if TABLES_ONLY:
    res = json.load(open("results/results_v18_final.json"))
else:
    import torch
    from nambd.model import Detector
    Xv = np.load(f"{FEAT}/val.npy", mmap_mode="r")
    sd = torch.load("results/models_v18big/full_0.pt", weights_only=True)
    m = Detector(fin=Xv.shape[-1], spatial=True, d=sd["inp.weight"].shape[0], layers=len({k.split(".")[1] for k in sd if k.startswith("blocks.")})); m.load_state_dict(sd); m.eval()
    dev = "cuda" if torch.cuda.is_available() else "cpu"; m.to(dev)
    with torch.no_grad():
        Svb = np.concatenate([torch.sigmoid(m(torch.tensor(Xv[i:i + 1024], dtype=torch.float32).to(dev), torch.tensor(vM[i:i + 1024]).to(dev))).cpu().numpy() for i in range(0, len(vy), 1024)])
    MEMBERS = {"full_0": (np.load(f"{P}/valscores_full_0.npy"), np.load(f"{P}/full_0.npz")["test"]), "full_1": (np.load(f"{P}/valscores_full_1.npy"), np.load(f"{P}/full_1.npz")["test"]),
               "big_0": (Svb, np.load("results/preds_v18big/full_0.npz")["test"])}
    NB = {"nonbr_0": (np.load(f"{P}/valscores_nonbr_0.npy"), np.load(f"{P}/nonbr_0.npz")["test"]), "nonbr_1": (np.load(f"{P}/valscores_nonbr_1.npy"), np.load(f"{P}/nonbr_1.npz")["test"])}
    def lab(yy, a): yy = yy.copy(); yy[(yy > 0) & ~a] = -1; return yy
    def best(S, yy):
        v = yy >= 0; ts = np.linspace(0.02, 0.98, 49); a = (yy > 0)[v]
        return float(ts[int(np.argmax([prf(((S > t)[v] & a).sum(), ((S > t)[v] & ~a).sum(), (~(S > t)[v] & a).sum())[2] for t in ts]))])
    def met(S, t, yy):
        v = yy >= 0; a = (yy > 0)[v]; f = (S > t)[v]; tp, fp, fn = (f & a).sum(), (f & ~a).sum(), (~f & a).sum(); p, r, f1 = prf(tp, fp, fn)
        out = dict(precision=float(p), recall=float(r), f1=float(f1), accuracy=float((f == a).mean()), fpr=float(fp / max((~a).sum(), 1)), threshold=t)
        for k in sorted(names):
            sm = attack_mask(dict(D, y=yy), k); fa = (S > t)[sm]; ya = yy[sm] == k
            if ya.sum(): out[names[k]] = dict(recall=float((fa & ya).sum() / ya.sum()), f1=float(prf((fa & ya).sum(), (fa & ~ya).sum(), (~fa & ya).sum())[2]), n=int(ya.sum()))
        return out
    res = {"members": list(MEMBERS), "note": __doc__}
    for name, grp in (("ensemble", MEMBERS), ("no_neighbour_ensemble", NB)):
        sv = np.mean([v[0] for v in grp.values()], 0); st = np.mean([v[1] for v in grp.values()], 0)
        res[name] = {sch: met(st, best(sv, yy_v), yy_t) for sch, yy_v, yy_t in (("message", lab(vy, vact), lab(y, act)), ("vehicle", vy, y))}
    json.dump(res, open("results/results_v18_final.json", "w"), indent=1)
e, n = res["ensemble"], res["no_neighbour_ensemble"]
for sch in ("message", "vehicle"): print(sch, {k: round(100 * e[sch][k], 2) for k in ("precision", "recall", "f1", "accuracy", "fpr")}, "| no-nbr F1", round(100 * n[sch]["f1"], 2))
BS = chr(92)                                                        # one backslash, written without escape sequences
T = lambda s: s.replace("@", BS)                                      # LaTeX templates below use @ for a backslash
L = [T("@begin{table}[t]@centering@caption{Extension to 18 of the 19 attack types (the 14 above plus four Sybil attacks), %s test windows. Ours: mean score of three models; no-neighbour rows: mean of two models (seeds 0, 1); thresholds picked on validation; per-attack F1 in Fig.~@ref{fig:attacks18}.}@label{tab:v18}@small") % f"{len(y):,}",
     T("@resizebox{@columnwidth}{!}{@begin{tabular}{lcccc}@toprule"), T("Overall & Precision & Recall & F1 & Accuracy @@@midrule")]
for sch in ("message", "vehicle"):
    L.append(f"Ours, {sch} labels & " + " & ".join("%.2f" % (100 * e[sch][k]) for k in ("precision", "recall", "f1", "accuracy")) + T(" @@"))
    L.append(T("No nbr.@ attention, ") + f"{sch} & " + " & ".join("%.2f" % (100 * n[sch][k]) for k in ("precision", "recall", "f1", "accuracy")) + T(" @@"))
L.append(T("@bottomrule@end{tabular}}@end{table}"))
open("paper/tables_v18.tex", "w").write("\n".join(L))
