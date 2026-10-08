"""Train the full neighbourhood-aware model on VeReMi Extension (same setup as run_real.py, seed 0) and save
weights + decision threshold to models/. Usage: python save_model.py [data_dir]"""
import glob, json, os, sys, numpy as np, torch
from nambd.data import load_veremi
from nambd.train import fit, scores, best_thr

root = sys.argv[1] if len(sys.argv) > 1 else "data"
def load(tag):
    ds = sorted({os.path.dirname(p) for p in glob.glob(f"{root}/**/traceJSON-*.json", recursive=True) if tag in p})
    parts = [load_veremi(d) for d in ds]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
tr = load("50400_54000"); late = load("54000_57600")
va = {k: v[:int(0.3 * len(late["X"]))] for k, v in late.items()}
m = fit("full", tr, epochs=5, seed=0)
thr = float(best_thr(*scores(m, va, "full")))
os.makedirs("models", exist_ok=True)
torch.save(m.state_dict(), "models/full_seed0.pt")
json.dump(dict(mode="full", seed=0, epochs=5, threshold=thr, T=10, K=16, comm_range=300.0,
               data="VeReMi Extension RandomPos_1416 + ConstSpeed_1416, train slice 50400-54000 s"),
          open("models/full_seed0.json", "w"), indent=1)
print("saved, threshold", thr)
