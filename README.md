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

## Results (VeReMi Extension, 14 attack types, 14:00-16:00; 2 seeds)
Pipeline: `run_full.py` (RATE=1: 9th feature = message rate, so DoS floods are visible; MODES=nonbr,full; outputs to `results/preds14`, `results/models14`),
`run_analysis.py` (PREDS=results/preds14 -> `results/results_full14.json`), `make_tables.py` (-> `paper/tables.tex`, `paper/fig_perattack.pdf`).
Trained on the first hour of each attack subset, tested on the later hour (receiver-disjoint val/test blocks, 68,971 test windows).
Per-attack F1 scores each attack against the benign senders of its own simulation run.

| Model | Precision | Recall | F1 | FPR | AUC |
|---|---|---|---|---|---|
| VeReMi range check (rule) | 0.416 | 0.674 | 0.514 | 43.7% | 0.690 |
| VeReMi speed check (rule) | 0.956 | 0.672 | 0.789 | 1.4% | 0.778 |
| No neighbour attention (all features) | 0.968 | 0.905 | 0.935 | 1.4% | 0.979 |
| Neighbourhood-aware (full) | 0.984 | 0.916 | 0.949 | 0.7% | 0.990 |

- Neighbour attention adds +0.014 overall F1 (paired bootstrap 95% CI [0.012, 0.016] in both seeds), halves the false-positive rate, and is significant after Holm correction
  on 12 of 14 attacks (not ConstPos, p = 0.22, nor ConstSpeedOffset, p = 0.085). Largest gains: EventualStop (+0.072) and ConstPosOffset (+0.042).
- Hardest attacks remain EventualStop (F1 0.74) and ConstPosOffset (0.79); all others are above 0.93.
- The speed-check rule fails on ConstPosOffset, EventualStop, DelayedMessages and DoS (F1 below 0.1) but is competitive on the content-falsification attacks.
- Dense 07:00-09:00 traffic (RandomPos, ConstSpeed only): F1 0.972 (full) vs 0.968 (no neighbour attention).
- Mean time to first alarm about 1.4 s (median 0; counted from the first window containing the sender); 93% of attacker-receiver pairs eventually flagged.
- Earlier 8-attack run (`results/results_full.json`, with a per-sender model that also lacks position features): position features were worth +0.113 F1, neighbour attention a further +0.015.
  The two-attack results in `results/results_real*.json` are superseded.

## Limitations
Simulated benchmark; 14 of 19 attack types (the four Sybil attacks are not run, and the RandomSpeedOffset archive is mislabeled and excluded);
2 seeds; independent (non-colluding) attackers; dense-traffic transfer on 2 attacks only; no VeReMi NextGen / original VeReMi / MixAll evaluation;
no comparison against published learned detectors. `results/preds*/` (large per-window predictions) are git-ignored; rerun `run_full.py` to regenerate.
