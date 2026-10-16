"""Receiver-side memory (reputation): a receiver keeps a decaying suspicion of each sender it has heard,
s'_t = max(s_t, decay * s'_{t-1}) over that receiver's windows of the same sender in time order. Post-processing only; no retraining."""
import numpy as np


def with_memory(S, D, decay):
    """S (N,K) window scores; D has grp, rid, te, sid (N,K). Returns smoothed scores (same shape)."""
    out = S.copy(); last = {}
    for i in np.lexsort((D["te"], D["rid"], D["grp"])):
        for j in np.nonzero(D["sid"][i] >= 0)[0]:
            k = (D["grp"][i], D["rid"][i], D["sid"][i, j]); s = S[i, j]
            if np.isnan(s): continue
            prev = last.get(k)
            if prev is not None and D["te"][i] - prev[1] <= 30: s = max(s, decay * prev[0])   # forget after 30 s without hearing the sender
            out[i, j] = s; last[k] = (s, D["te"][i])
    return out
