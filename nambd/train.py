import os
import numpy as np, torch, torch.nn.functional as Fn
from sklearn.metrics import f1_score, roc_auc_score
from .model import Detector
from .sim import ATTACKS

MODES = {"full": dict(spatial=True, drop=[]),            # neighbourhood-aware (ours)
         "nonbr": dict(spatial=False, drop=[]),          # same model, neighbourhood removed
         "persender": dict(spatial=False, drop=[0, 1])}  # classic per-sender view (no claimed position vs receiver)


def tens(D, mode):
    X = torch.from_numpy(np.ascontiguousarray(D["X"]))           # no copy unless features must be zeroed
    if MODES[mode]["drop"]: X = X.clone(); X[..., MODES[mode]["drop"]] = 0
    return X, torch.tensor(D["M"]), torch.tensor(D["y"])


def batches(n, bs, shuffle, rng):
    idx = rng.permutation(n) if shuffle else np.arange(n)
    for i in range(0, n, bs): yield idx[i:i + bs]


def fit(mode, src, tgt=None, epochs=8, bs=128, lr=2e-3, seed=0, dann=0.0, log=print, device="cpu"):
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    import os
    m = Detector(fin=src["X"].shape[-1], spatial=MODES[mode]["spatial"], d=int(os.environ.get("MODEL_D", 64)),
                 layers=int(os.environ.get("MODEL_L", 2))).to(device)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-2)
    X, M, Y = tens(src, mode)
    if device != "cpu" and tgt is None:                  # keep the whole set on the GPU (half precision), cast per batch
        X, M, Y = X.to(device, torch.float16), M.to(device), Y.to(device)
    if tgt is not None and dann > 0: Xt, Mt, _ = tens(tgt, mode)
    steps = epochs * ((len(X) + bs - 1) // bs); sched = torch.optim.lr_scheduler.OneCycleLR(opt, lr, total_steps=steps)
    it = 0; start = 0
    ck = os.environ.get("EPOCH_CKPT")                          # optional per-epoch checkpoint: a stopped run resumes at the next epoch
    if ck and os.path.exists(ck):
        st = torch.load(ck, weights_only=False)
        m.load_state_dict(st["model"]); opt.load_state_dict(st["opt"]); sched.load_state_dict(st["sched"])
        rng.bit_generator.state = st["rng"]; torch.set_rng_state(st["torch_rng"]); start, it = st["epoch"], st["it"]
        log(f"  [{mode}] resumed at epoch {start + 1}/{epochs}")
    for ep in range(start, epochs):
        m.train(); tot = 0
        for b in batches(len(X), bs, True, rng):
            if device != "cpu": b = torch.as_tensor(b, device=device)
            valid = Y[b] >= 0
            lam = None
            if dann > 0 and tgt is not None:
                p = it / steps; lam = dann * (2 / (1 + np.exp(-10 * p)) - 1)
                tb = rng.choice(len(Xt), len(b))
                xb = torch.cat([X[b], Xt[tb]]); mb = torch.cat([M[b], Mt[tb]])
                out, dom = m(xb, mb, lam)
                n = len(b); lab = (Y[b] > 0).float()
                loss = Fn.binary_cross_entropy_with_logits(out[:n][valid], lab[valid], pos_weight=torch.tensor(2.0))
                vm = torch.cat([valid, mb[n:, :, -1]])
                dl = torch.cat([torch.zeros(n, X.shape[1]), torch.ones(len(tb), X.shape[1])])
                loss = loss + Fn.binary_cross_entropy_with_logits(dom[vm], dl[vm])
            else:
                out = m(X[b].to(device).float(), M[b].to(device)); lab = (Y[b] > 0).float().to(device); valid = valid.to(device)
                loss = Fn.binary_cross_entropy_with_logits(out[valid], lab[valid], pos_weight=torch.tensor(2.0, device=device))
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step(); sched.step()
            tot += loss.item() * len(b); it += 1
        log(f"  [{mode}] epoch {ep + 1}/{epochs} loss {tot / len(X):.4f}")
        if ck: torch.save(dict(model=m.state_dict(), opt=opt.state_dict(), sched=sched.state_dict(), rng=rng.bit_generator.state,
                               torch_rng=torch.get_rng_state(), epoch=ep + 1, it=it), ck)
    return m.cpu() if device == "cpu" else m


@torch.no_grad()
def scores(m, D, mode, bs=512):
    m.eval(); X, M, Y = tens(D, mode); dev = next(m.parameters()).device
    s = torch.cat([torch.sigmoid(m(X[i:i + bs].to(dev).float(), M[i:i + bs].to(dev))).cpu() for i in range(0, len(X), bs)])
    v = Y >= 0
    return s[v].numpy(), Y[v].numpy()


def best_thr(s, y, fine=False):
    ts = np.linspace(0.02, 0.98, 49) if fine else np.linspace(0.05, 0.95, 19)
    return ts[int(np.argmax([f1_score(y > 0, s > t) for t in ts]))]


def evaluate(s, y, thr):
    """Per-attack F1: that attack's senders as positives vs. all benign senders."""
    res = {}
    for k, name in ATTACKS.items():
        if k == 0: continue
        sel = (y == 0) | (y == k)
        yk = (y[sel] == k); res[name] = dict(f1=f1_score(yk, s[sel] > thr), auc=roc_auc_score(yk, s[sel]))
    res["Overall"] = dict(f1=f1_score(y > 0, s > thr), auc=roc_auc_score(y > 0, s))
    res["Macro"] = dict(f1=float(np.mean([res[a]["f1"] for a in list(ATTACKS.values())[1:]])),
                        auc=float(np.mean([res[a]["auc"] for a in list(ATTACKS.values())[1:]])))
    return res
