# Neighbourhood-Aware Misbehavior Detection in V2X Networks

Transformer encoder whose attention runs across **co-located senders at the same instant** (spatial axis)
as well as across time, so a claimed position is judged against what surrounding vehicles claim.
Targets the constant-position-offset attack that per-sender detectors cannot see.

```
nambd/sim.py     VeReMi-style highway simulator (5 attacks) used when real logs are unavailable
nambd/data.py    receiver-centric windows (K nearest senders x T steps); load_veremi() for real VeReMi logs
nambd/model.py   factorised temporal/spatial transformer, spatial-off ablation, gradient reversal (DANN)
nambd/train.py   training, threshold selection, per-attack F1/AUC
run_experiments.py   reproduces all results -> results/results.json
make_tables.py       results -> paper/tables.tex + figure
paper/            tables.tex + fig_perattack.pdf generated from the real-data results (main.tex not in this repo)
```

Run: `pip install -r requirements.txt && python run_experiments.py && python make_tables.py`
(`--quick` for a smoke test).

## Status note
`nambd/sim.py` results (results/results.json) come from the included simulator. `data.load_veremi` has now been
validated on the public **VeReMi Extension** benchmark archives (simulated traffic, not field recordings) (Zenodo 20090854; RandomPos_1416 and ConstSpeed_1416 only).
`run_real.py` trains on the 50400-54000 s slices and tests on the later 54000-57600 s slices
(receiver-disjoint val/test blocks), 3 seeds; output in results/results_real.json and results/real_log.txt.
Original VeReMi, NextGen and the other Extension attacks have not been run yet.
