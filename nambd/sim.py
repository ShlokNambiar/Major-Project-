"""VeReMi-style highway simulator with ground truth and five attack types.

Used when the real VeReMi logs are not available (see data.load_veremi for the
real-data loader). Produces per-step true and claimed (BSM) state for every vehicle.
"""
from dataclasses import dataclass
import numpy as np

ATTACKS = {0: "Benign", 1: "ConstPos", 2: "ConstPosOffset", 3: "RandomPos",
           4: "RandomPosOffset", 5: "EventualStop"}


@dataclass
class SimConfig:
    name: str = "highway"
    length: float = 3000.0       # loop length (m)
    lanes: int = 3               # lanes per direction
    lane_w: float = 3.5
    density: float = 20.0        # veh / km / lane
    v0_mean: float = 28.0
    v0_std: float = 3.0
    steps: int = 240             # 1 Hz BSM samples (downsampled from 10 Hz)
    comm_range: float = 300.0
    gps_noise: float = 1.0
    attacker_frac: float = 0.25
    off_min: float = 30.0
    off_max: float = 120.0


URBAN = SimConfig(name="dense", length=2000.0, lanes=2, lane_w=3.2, density=45.0,
                  v0_mean=14.0, v0_std=3.0, comm_range=250.0, gps_noise=1.5,
                  off_min=25.0, off_max=100.0)


def _idm(v, gap, dv, v0):
    s_star = 2.0 + v * 1.4 + v * dv / (2 * np.sqrt(1.5 * 2.0))
    a = 1.5 * (1 - (v / v0) ** 4 - (s_star / np.maximum(gap, 0.5)) ** 2)
    return np.clip(a, -6.0, 3.0)


def simulate(cfg: SimConfig, seed: int, id_offset: int = 0):
    rng = np.random.default_rng(seed)
    nl = cfg.lanes * 2
    per_lane = int(cfg.density * cfg.length / 1000)
    n = nl * per_lane
    lane = np.repeat(np.arange(nl), per_lane)
    s = np.concatenate([np.sort(rng.uniform(0, cfg.length, per_lane)) for _ in range(nl)])
    v0 = np.clip(rng.normal(cfg.v0_mean, cfg.v0_std, n), 5, None)
    v = v0 * 0.8
    dirn = np.where(lane < cfg.lanes, 1.0, -1.0)
    ly = np.where(lane < cfg.lanes, 1.0, -1.0) * (cfg.lane_w * (lane % cfg.lanes + 0.5) + 1.5)
    T = cfg.steps
    warm = 60
    P = np.zeros((T, n, 2)); V = np.zeros((T, n)); H = np.zeros((T, n))
    for step in range(T + warm):
        for l in range(nl):
            idx = np.where(lane == l)[0]
            order = idx[np.argsort(s[idx])]
            lead = np.roll(order, -1)
            gap = (s[lead] - s[order] - 4.5) % cfg.length
            dv = v[order] - v[lead]
            a = _idm(v[order], gap, dv, v0[order])
            v[order] = np.clip(v[order] + a * 0.1 * 10, 0, None)  # 1 s step, 10 substeps folded
        s = (s + v) % cfg.length
        if step >= warm:
            t = step - warm
            x = np.where(dirn > 0, s, cfg.length - s)
            y = ly + rng.normal(0, 0.15, n)
            P[t, :, 0] = x; P[t, :, 1] = y
            V[t] = v; H[t] = np.where(dirn > 0, 0.0, np.pi)
    # claimed state
    C = P + rng.normal(0, cfg.gps_noise, P.shape)
    CV = V + rng.normal(0, 0.1, V.shape)
    label = np.zeros(n, dtype=np.int64)
    att = rng.permutation(n)[: int(cfg.attacker_frac * n)]
    label[att] = rng.integers(1, 6, len(att))
    area = np.array([cfg.length, 2 * (cfg.lanes * cfg.lane_w + 3)])
    for i in att:
        k = label[i]
        if k == 1:      # constant position
            C[:, i] = np.array([rng.uniform(0, cfg.length), rng.uniform(-area[1] / 2, area[1] / 2)])
        elif k == 2:    # constant position offset
            mag = rng.uniform(cfg.off_min, cfg.off_max); ang = rng.uniform(0, 2 * np.pi)
            C[:, i] = P[:, i] + mag * np.array([np.cos(ang), np.sin(ang)]) + rng.normal(0, cfg.gps_noise, (T, 2))
        elif k == 3:    # random position every message
            C[:, i, 0] = P[:, i, 0] + rng.uniform(-300, 300, T)
            C[:, i, 1] = rng.uniform(-area[1] / 2, area[1] / 2, T)
        elif k == 4:    # random offset every message
            C[:, i] = P[:, i] + rng.uniform(-150, 150, (T, 2))
        elif k == 5:    # eventual stop
            ts = rng.integers(T // 4, T // 2)
            C[ts:, i] = C[ts, i]; CV[ts:, i] = 0.0
    ids = np.arange(n) + id_offset
    return dict(P=P, C=C, V=V, CV=CV, H=H, label=label, ids=ids, cfg=cfg)
