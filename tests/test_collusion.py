"""Checks for nambd/collusion.py on simulator windows (no VeReMi data needed). Run: python -m pytest tests -q"""
import numpy as np, pytest
from nambd.data import build, F
from nambd.sim import SimConfig
from nambd.collusion import inject, make_set, _raw, _rebuild


@pytest.fixture(scope="module")
def win():
    D = build(SimConfig(steps=40), seeds=[0], n_per_step=10)
    rate = np.random.default_rng(0).uniform(0, 1, D["X"].shape[:3]).astype(np.float32) * D["M"]
    D["X"] = np.concatenate([D["X"], rate[..., None]], -1)          # 9 features, as in the 14-attack run
    return D


def test_round_trip_is_exact(win):
    for i in range(50):
        x, m = win["X"][i], win["M"][i]
        assert np.allclose(_rebuild(*_raw(x, m)), x, atol=1e-5)


def full_senders(win):
    i = int(np.argmax(win["M"].all(-1).sum(1)))                     # window with the most fully observed senders
    return win["X"][i], win["M"][i], np.nonzero(win["M"][i].all(-1))[0][:3]


def test_coordinated_offset_is_shared_and_keeps_motion(win):
    x, m, idx = full_senders(win)
    xn = inject(x, m, idx, "offset", True, np.random.default_rng(0), off_m=50.0)
    shift = (xn[idx, :, 0:2] - x[idx, :, 0:2]) * 300.0
    assert np.allclose(shift, shift[0, 0], atol=1e-3) and np.isclose(np.linalg.norm(shift[0, 0]), 50.0, atol=1e-2)
    assert np.allclose(xn[idx, :, 2:], x[idx, :, 2:], atol=1e-5)    # speed, heading, displacement, valid, rate unchanged
    others = np.setdiff1d(np.arange(len(x)), idx); assert np.array_equal(xn[others], x[others])


def test_independent_offsets_differ(win):
    x, m, idx = full_senders(win)
    xn = inject(x, m, idx, "offset", False, np.random.default_rng(0))
    s = (xn[idx, -1, 0:2] - x[idx, -1, 0:2]); assert not np.allclose(s[0], s[1])


def test_stop_freezes_position_and_zeroes_speed(win):
    x, m, idx = full_senders(win)
    xn = inject(x, m, idx, "stop", True, np.random.default_rng(0), stop_at=5)
    assert np.allclose(xn[idx, 5:, 2], 0) and np.allclose(xn[idx, 6:, 5:7], 0)
    assert np.allclose(xn[idx, 5:, 0:2], xn[idx, 5:6, 0:2])
    assert np.allclose(xn[idx, :5], x[idx, :5], atol=1e-5)


def test_approach_is_a_consistent_convoy(win):
    x, m, idx = full_senders(win)
    xn = inject(x, m, idx, "approach", True, np.random.default_rng(0), v=15.0)
    d = np.linalg.norm(xn[idx, :, 0:2], axis=-1) * 300.0
    assert np.all(np.diff(d, axis=1) < 0)                             # closing in on the receiver
    assert np.allclose(d[:, -1], [15, 25, 35], atol=1e-3)               # 10 m spacing
    step = np.linalg.norm(xn[idx, 1:, 5:7], axis=-1) / 3.0 * 300.0     # displacement per second matches claimed speed
    assert np.allclose(step, 15.0, atol=1e-3) and np.allclose(xn[idx, :, 2] * 30.0, 15.0)


def test_make_set_labels_and_same_colluders_across_variants(win):
    a = make_set(win["X"], win["M"], win["y"], 2, "offset", True, np.random.default_rng(7), n_windows=20, min_honest=3)
    b = make_set(win["X"], win["M"], win["y"], 2, "offset", False, np.random.default_rng(7), n_windows=20, min_honest=3)
    assert ((a[2] == -2).sum(1) == 2).all() and np.array_equal(a[2], b[2]) and np.array_equal(a[3], b[3])
    assert ((a[2] == -2) <= (win["y"][a[3]] == 0)).all()              # colluders were honest senders
