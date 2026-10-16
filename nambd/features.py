"""Features from raw claims (data.load_veremi_raw): the original 9 inputs plus plausibility checks.

Original (as load_veremi with rate=True): 0-1 claimed position relative to the receiver / 300 m, 2 speed / 30, 3-4 cos/sin heading,
5-6 position change between steps x3, 7 valid, 8 log(1 + messages that second) / 3.
Added:
  9  claimed acceleration along the heading / 5
  10 kinematics: (speed change between steps - claimed acceleration) / 5
  11 kinematics: (distance moved - claimed speed) / 10, per step
  12 heading vs direction of movement: 1 - cos(angle between them), only when the sender moved > 1 m
  13 road map: log(1 + honest vehicle-seconds observed in the 5 m cell of the claimed position) / log(1 + max)   (0 = off-road)
  14 road map: alignment of the claimed heading with the cell's dominant driving direction (|cos|, axial; 0 when no road)
  15 between senders: distance from the claimed position to the nearest other sender's claimed position at that step / 50 m (clipped 1)
  16 repeat: the claimed position equals (< 1 cm) one of the sender's own earlier claims in the window (real GPS fixes always jitter)
  17 copied trail: the claimed position equals (< 1 cm) a position another sender claimed at this or an earlier step
  18 log10(distance moved since the previous step + 1 mm) / 3, so centimetre-level movement is visible
The road map is built only from receivers' own states in the training hour (a stand-in for the map every vehicle carries).
"""
import numpy as np

FEAT_NAMES = ["relx", "rely", "spd", "cos", "sin", "dx", "dy", "valid", "rate", "acl", "dv_vs_acl", "disp_vs_spd",
              "hed_vs_motion", "road", "road_dir", "nearest_other", "self_repeat", "other_trail", "log_disp"]
GROUPS = {"base": list(range(9)), "kin": [9, 10, 11, 12], "map": [13, 14], "pair": [15], "repeat": [16, 17, 18]}


class RoadMap:
    def __init__(self, own, cell=5.0, blur=1):
        """own: (n,4) x, y, heading, speed of receivers' own states. Only moving states (> 1 m/s) give a direction."""
        x, y, h, v = own.T
        self.cell = cell; self.x0 = x.min() - 1000; self.y0 = y.min() - 1000
        self.nx = int((x.max() + 1000 - self.x0) / cell) + 1; self.ny = int((y.max() + 1000 - self.y0) / cell) + 1
        ix, iy = self._idx(x, y)
        cnt = np.zeros((self.nx, self.ny), np.float32); np.add.at(cnt, (ix, iy), 1)
        mv = v > 1.0                                    # axial direction: average of (cos 2h, sin 2h)
        c2 = np.zeros_like(cnt); s2 = np.zeros_like(cnt)
        np.add.at(c2, (ix[mv], iy[mv]), np.cos(2 * h[mv])); np.add.at(s2, (ix[mv], iy[mv]), np.sin(2 * h[mv]))
        for a in range(blur):                           # 1-cell dilation per pass: tolerates GPS noise (about 3 m)
            cnt, c2, s2 = (self._box(z) for z in (cnt, c2, s2))
        self.road = np.log1p(cnt) / np.log1p(cnt.max())
        self.dir = 0.5 * np.arctan2(s2, c2); self.has_dir = (np.hypot(c2, s2) > 0)

    @staticmethod
    def _box(z):
        p = np.pad(z, 1); return sum(p[1 + i:p.shape[0] - 1 + i, 1 + j:p.shape[1] - 1 + j] for i in (-1, 0, 1) for j in (-1, 0, 1))

    def _idx(self, x, y):
        return (np.clip(((x - self.x0) / self.cell).astype(np.int64), 0, self.nx - 1),
                np.clip(((y - self.y0) / self.cell).astype(np.int64), 0, self.ny - 1))

    def lookup(self, pos, hed):
        ix, iy = self._idx(pos[..., 0], pos[..., 1])
        road = self.road[ix, iy]; align = np.abs(np.cos(hed - self.dir[ix, iy])) * self.has_dir[ix, iy] * (road > 0)
        return road.astype(np.float32), align.astype(np.float32)


def featurize(D, rmap, idx=None, comm_range=300.0, chunk=4000):
    """D: raw dict from load_veremi_raw (or a collusion-modified copy). Returns X (N,K,T,16) float32. idx: optional window subset."""
    idx = np.arange(len(D["M"])) if idx is None else np.asarray(idx)
    return np.concatenate([_featurize(D, rmap, idx[i:i + chunk], comm_range) for i in range(0, len(idx), chunk)])


def _featurize(D, rmap, idx, comm_range):
    g = lambda k: D[k][idx]
    pos, spd, hed, acl, cnt, M, ctr = g("pos"), g("spd"), g("hed"), g("acl"), g("cnt"), g("M"), g("ctr")
    Mf = M.astype(np.float64)
    rel = (pos - ctr[:, None, None, :]) / comm_range * Mf[..., None]
    ok = M.copy(); ok[..., 1:] &= M[..., :-1]; ok[..., 0] = False; okf = ok.astype(np.float64)
    d = np.zeros_like(rel); d[..., 1:, :] = rel[..., 1:, :] - rel[..., :-1, :]; d *= okf[..., None]
    sp = spd * Mf; hd = hed * Mf; ac = acl * Mf
    dv = np.zeros_like(sp); dv[..., 1:] = (sp[..., 1:] - sp[..., :-1]) - ac[..., 1:]; dv *= okf
    disp = np.linalg.norm(d, axis=-1) * comm_range
    dsp = (disp - sp) * okf
    mov = ok & (disp > 1.0)
    ang = np.arctan2(d[..., 1], d[..., 0]); hm = (1 - np.cos(ang - hd)) * mov
    road, align = rmap.lookup(pos, hed); road = road * M; align = align * M
    P = np.where(M[..., None], pos, np.nan)                                       # nearest other claimed position at the same step
    dd = np.linalg.norm(P[:, :, None] - P[:, None, :], axis=-1)                   # (N,K,K,T)
    K = P.shape[1]; dd[:, np.arange(K), np.arange(K)] = np.inf
    near = np.nan_to_num(np.nanmin(np.where(np.isnan(dd), np.inf, dd), axis=2), posinf=50.0)
    near = np.minimum(near / 50.0, 1.0) * M
    rep, trail = _repeats(pos, M)
    ldisp = (np.log10(disp + 1e-3) + 3) / 3 * okf
    ex = M.any(-1, keepdims=True)                                                  # empty sender slots stay all-zero, as in load_veremi
    X = np.stack([rel[..., 0], rel[..., 1], sp / 30.0, np.cos(hd) * ex, np.sin(hd), d[..., 0] * 3, d[..., 1] * 3, Mf,
                  np.log1p(cnt) / 3.0 * Mf, ac / 5.0, dv / 5.0, np.clip(dsp / 10.0, -5, 5), hm, road, align, near, rep, trail, ldisp], -1)
    return X.astype(np.float32)


def _repeats(pos, M, tol=0.01, sub=500):
    """self repeat (N,K,T) and copied trail (N,K,T) indicators; computed in sub-chunks (the trail test is (K*T)^2 per window)."""
    N, K, T, _ = pos.shape; rep = np.zeros((N, K, T)); trail = np.zeros((N, K, T))
    tri = np.tril(np.ones((T, T), bool), -1)                       # s < t
    tle = np.tril(np.ones((T, T), bool))                            # s <= t
    offk = ~np.eye(K, dtype=bool)
    for i in range(0, N, sub):
        p = pos[i:i + sub].astype(np.float64); m = M[i:i + sub]
        d_self = np.linalg.norm(p[:, :, :, None] - p[:, :, None, :], axis=-1)                       # (n,K,T,T)
        ok = m[:, :, :, None] & m[:, :, None, :] & tri
        rep[i:i + sub] = ((d_self < tol) & ok).any(-1)
        d = np.linalg.norm(p[:, :, None, :, None, :] - p[:, None, :, None, :, :], axis=-1)         # (n,K,K,T,T): j at t vs k at s
        ok = m[:, :, None, :, None] & m[:, None, :, None, :] & tle & offk[:, :, None, None]
        trail[i:i + sub] = ((d < tol) & ok).any((2, 4))
    return rep * M, trail * M


def featurize_to_file(D, rmap, path, n_feat=19, start=0, out=None, chunk=4000):
    """Write features of all windows of D into a float16 .npy memmap at rows [start, start + N) (created if `out` is None)."""
    N = len(D["M"]); K, T = D["M"].shape[1:]
    if out is None: out = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(N, K, T, n_feat))
    for i in range(0, N, chunk):
        out[start + i:start + min(i + chunk, N)] = _featurize(D, rmap, np.arange(i, min(i + chunk, N)), 300.0).astype(np.float16)
    out.flush(); return out
