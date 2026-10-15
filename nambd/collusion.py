"""Collusion stress test: turn m honest senders of a test window into colluders that falsify their BSMs.

Works on finished windows (X: (N,K,T,F), M: (N,K,T)), so the trained models are scored on exactly the windows
of the main experiment with only the colluders' claims changed. Raw claims are recovered from the features
(relative position, speed, heading, valid, rate), rewritten, and the features are rebuilt with data._features.

Scenarios (each in a coordinated and an independent variant):
  offset   colluders shift their claimed positions by an offset of `off_m` metres.
           coordinated: one shared offset (the group stays mutually consistent); independent: one offset each.
  stop     colluders claim to stop (speed 0, position frozen) from step `stop_at` on: a fake jam / crash scene.
           coordinated: all stop at the same step; independent: each at a random step.
  approach colluders claim to be a convoy driving at the receiver at `v` m/s and ending 15-45 m away (spoofed approach).
           coordinated: one shared direction, spaced 10 m apart; independent: a random direction each.
Limits: the K senders in a window are not re-selected after the claims change (the receiver's real selection
uses claimed distance), and colluders are honest vehicles of the trace, not a separate attack simulation.
"""
import numpy as np
from .data import _features, F

SCENARIOS = ("offset", "stop", "approach")


def _raw(x, m):
    """(K,T,F') features -> claimed rel position (K,T,2) in units of 300 m, speed m/s, heading rad, valid, rate (or None)."""
    rel = x[..., 0:2].astype(np.float64); spd = x[..., 2] * 30.0; hed = np.arctan2(x[..., 4], x[..., 3])
    rate = x[..., F] if x.shape[-1] > F else None
    return rel, spd, hed, m.copy(), rate


def _rebuild(rel, spd, hed, valid, rate):
    x = _features(rel, spd, hed, valid)
    if rate is not None: x = np.concatenate([x, rate[..., None].astype(np.float32)], -1)
    return x.astype(np.float32)


def inject(x, m, idx, scenario, coordinated, rng, off_m=50.0, stop_at=5, v=15.0, scale=300.0):
    """Return a copy of one window's features with senders `idx` rewritten as colluders. Rate (message count) is untouched."""
    rel, spd, hed, valid, rate = _raw(x, m)
    T = rel.shape[1]; tt = np.arange(T)
    if scenario == "offset":
        ang = rng.uniform(0, 2 * np.pi, 1 if coordinated else len(idx))
        o = np.stack([np.cos(ang), np.sin(ang)], -1) * off_m / scale
        o = np.broadcast_to(o, (len(idx), 2))
        for o_i, j in zip(o, idx): rel[j] += o_i
    elif scenario == "stop":
        for j in idx:
            t0 = stop_at if coordinated else int(rng.integers(1, T - 1))
            vt = np.nonzero(valid[j, :t0 + 1])[0]
            if len(vt) == 0: continue
            p0 = rel[j, vt[-1]].copy(); h0 = hed[j, vt[-1]]
            rel[j, t0:] = p0; spd[j, t0:] = 0.0; hed[j, t0:] = h0
    elif scenario == "approach":
        ang = rng.uniform(0, 2 * np.pi, 1 if coordinated else len(idx))
        for i, j in enumerate(idx):
            a = ang[0] if coordinated else ang[i]; u = np.array([np.cos(a), np.sin(a)])      # direction of travel
            d_end = 15.0 + 10.0 * i if coordinated else rng.uniform(15.0, 45.0)              # convoy spacing 10 m
            pos = -u[None] * (d_end + v * (T - 1 - tt))[:, None]                             # moving along +u toward the receiver at 0
            rel[j] = pos / scale; spd[j] = v; hed[j] = a
    else:
        raise ValueError(scenario)
    inv = ~valid; rel[inv] = 0; spd[inv] = 0; hed[inv] = 0           # loader convention: unobserved steps are zero
    xn = x.copy()
    xn[idx] = _rebuild(rel[idx], spd[idx], hed[idx], valid[idx], None if rate is None else rate[idx])
    return xn


def make_set(X, M, Y, m, scenario, coordinated, rng, n_windows=4000, min_honest=None, **kw):
    """Pick windows with at least `min_honest` honest senders (default m + 1, so honest senders remain to measure FPR),
    choose m of them at random as colluders. Returns X', M, y' (colluders get label -2), the window indices."""
    min_honest = m + 1 if min_honest is None else min_honest
    ok = np.nonzero((Y == 0).sum(1) >= min_honest)[0]
    win = np.sort(rng.choice(ok, min(n_windows, len(ok)), replace=False))
    Xn, Yn = X[win].astype(np.float32).copy(), Y[win].copy()
    picks = [rng.choice(np.nonzero(Yn[w] == 0)[0], m, replace=False) for w in range(len(win))]   # drawn first: same seed -> same colluders in both variants
    for w, idx in enumerate(picks):
        Xn[w] = inject(Xn[w], M[win[w]], idx, scenario, coordinated, rng, **kw)
        Yn[w, idx] = -2
    return Xn, M[win], Yn, win
