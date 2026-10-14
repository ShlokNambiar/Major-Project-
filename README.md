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

## Results (VeReMi Extension, 8 attack types, 14:00-16:00; 2 seeds)
Trained on the first hour (`run_full.py`), tested on the later hour with receiver-disjoint validation/test blocks; analysis in `run_analysis.py`,
dense-traffic transfer in `run_dense.py`; tables/figure from `make_tables.py`. Raw outputs: `results/results_full.json`, `results/results_dense.json`.

| Model | Precision | Recall | F1 | FPR |
|---|---|---|---|---|
| Per-sender, no position features | 0.931 | 0.695 | 0.795 | 2.3% |
| No neighbour attention, all features (`nonbr`) | 0.970 | 0.853 | 0.908 | 1.2% |
| Neighbourhood-aware (full) | 0.977 | 0.874 | 0.923 | 0.9% |
| VeReMi speed check (rule) / range check (rule) | 1.000 / 0.649 | 0.560 / 0.474 | 0.718 / 0.548 | 0.0% / 11.5% |

- Most of the gain over the per-sender model comes from the receiver-relative position features (+0.113 F1, 95% CI [0.10, 0.13]).
- Neighbour attention adds a smaller gain on top (+0.015 overall F1, CI [0.011, 0.018]). Per attack (each attack scored against the benign senders of its own simulation run), the gain is significant after Holm correction for ConstPosOffset (+0.041), RandomPos, RandomPosOffset, EventualStop (+0.067) and DelayedMessages, but not for ConstPos, ConstSpeed or DataReplay.
- The simple speed-consistency rule beats the learned models on RandomPos, RandomPosOffset, ConstSpeed and DataReplay, but scores 0 on ConstPosOffset and EventualStop.
- Dense 07:00-09:00 traffic (RandomPos, ConstSpeed only): full 0.963 F1 vs no-neighbour 0.956 vs per-sender 0.922 (speed-check rule 0.954).
- Earlier two-attack results (`results/results_real*.json`) are superseded; there, neighbour attention added nothing.

## Limitations
Simulated benchmark; 8 of 19 attack types (Sybil attacks and RandomSpeed/ConstSpeedOffset/DoS variants not run; the RandomSpeedOffset archive is mislabeled and was excluded);
2 seeds; independent (non-colluding) attackers; dense-traffic transfer on 2 attacks only; no comparison against published learned detectors.
`results/preds/` (large per-window predictions) is git-ignored; rerun `run_full.py` to regenerate.
