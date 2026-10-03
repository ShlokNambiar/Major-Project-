import numpy as np, torch, torch.nn.functional as Fn
from sklearn.metrics import f1_score, roc_auc_score
from .model import Detector
from .sim import ATTACKS

MODES = {"full": dict(spatial=True, drop=[]),            # neighbourhood-aware (ours)
         "nonbr": dict(spatial=False, drop=[]),          # same model, neighbourhood removed
         "persender": dict(spatial=False, drop=[0, 1])}  # classic per-sender view (no claimed position vs receiver)


def tens(D, mode):
    X = torch.tensor(D["X"]).clone(); X[..., MODES[mode]["drop"]] = 0
    return X, torch.tensor(D["M"]), torch.tensor(D["y"])


def batches(n, bs, shuffle, rng):
    idx = rng.permutation(n) if shuffle else np.arange(n)
    for i in range(0, n, bs): yield idx[i:i + bs]


def fit(mode, src, tgt=None, epochs=8, bs=128, lr=2e-3, seed=0, dann=0.0, log=print):
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    m = Detector(spatial=MODES[mode]["spatial"])
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-2)
    X, M, Y = tens(src, mode)
    if tgt is not None and dann > 0: Xt, Mt, _ = tens(tgt, mode)
    steps = epochs * ((len(X) + bs - 1) // bs); sched = torch.optim.lr_scheduler.OneCycleLR(opt, lr, total_steps=steps)
    it = 0
    for ep in range(epochs):
        m.train(); tot = 0
        for b in batches(len(X), bs, True, rng):
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
                out = m(X[b], M[b]); lab = (Y[b] > 0).float()
                loss = Fn.binary_cross_entropy_with_logits(out[valid], lab[valid], pos_weight=torch.tensor(2.0))
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step(); sched.step()
            tot += loss.item() * len(b); it += 1
        log(f"  [{mode}] epoch {ep + 1}/{epochs} loss {tot / len(X):.4f}")
    return m


@torch.no_grad()
def scores(m, D, mode, bs=512):
    m.eval(); X, M, Y = tens(D, mode)
    s = torch.cat([torch.sigmoid(m(X[i:i + bs], M[i:i + bs])) for i in range(0, len(X), bs)])
    v = Y >= 0
    return s[v].numpy(), Y[v].numpy()


def best_thr(s, y):
    ts = np.linspace(0.05, 0.95, 19)
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
