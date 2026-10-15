# Neighbourhood-Aware Misbehavior Detection in V2X Networks

> **Taking over this project? Read [`HANDOFF.md`](HANDOFF.md) first** (status, results, rules, open work, environment traps).

Transformer encoder whose attention runs across **co-located senders at the same instant** (spatial axis)
as well as across time, so a sender's claims are judged in the context of what surrounding vehicles claim.
(The collusion study below shows what this does and does not buy: it does not catch lies that are physically consistent.)

```
nambd/sim.py     VeReMi-style highway simulator (5 attacks) used when real logs are unavailable
nambd/data.py    receiver-centric windows (K nearest senders x T steps); load_veremi() for real VeReMi logs
nambd/model.py   factorised temporal/spatial transformer, spatial-off ablation, gradient reversal (DANN)
nambd/train.py   training, threshold selection, per-attack F1/AUC
nambd/collusion.py   collusion generator: rewrites m honest senders of a finished window into colluders
run_experiments.py   reproduces all results -> results/results.json
make_tables.py       results -> paper/tables.tex + figure
run_collusion.py     malicious-neighbour / collusion study -> results/results_collusion.json
make_collusion_fig.py  -> paper/tables_collusion.tex + paper/fig_collusion.pdf
tests/               python -m pytest tests -q (collusion generator; no data needed)
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

## Malicious neighbours and collusion (`results/results_collusion.json`)
`run_collusion.py` (PREDS=results/preds14, MODELS=results/models14; about 3 min on a laptop GPU) then `make_collusion_fig.py`.
Uses the same test windows and trained models as above; no retraining. The no-neighbour model cannot see other senders,
so it is the control: an effect that appears only in the neighbourhood-aware model comes from neighbour attention.

1. **Real VeReMi attackers, by share of attackers in the window** (0-20 / 20-40 / 40-60 / >60%): the neighbourhood-aware model's recall falls
   0.943 / 0.929 / 0.917 / 0.877 while the no-neighbour model stays flat (0.905 / 0.908 / 0.904 / 0.900). Computed within each attack type
   (so the attack mix cannot explain it), the recall gain from neighbour attention is +0.021 / +0.013 / **-0.023** in the 20-40 / 40-60 / >60% bins
   (14 attack types each). Neighbour context helps while most neighbours are honest and stops helping once attackers are the majority.
2. **Injected lies that are physically consistent are not detected by either model.** In 1,514 test windows with at least 9 honest senders,
   m = 1..8 honest senders were rewritten to (a) shift their claimed position by 50 m, (b) claim to stop (fake jam / crash scene), or
   (c) claim to be a convoy driving at the receiver; each coordinated (one shared story) and independent. With both models at the same 1% validation FPR,
   colluder recall is at most 0.04 in every setting, for both models. Larger offsets are caught more often (offset 100 / 200 / 400 m, 4 colluders:
   recall about 0.04 / 0.10 / 0.41), with no consistent difference between the two models.
   Why: real VeReMi attackers are mostly caught because their claims are physically implausible (positions beyond radio range, speed that does not match displacement),
   not because neighbours contradict them. The models learned plausibility, not cross-checking between senders.
3. **Framing.** A spoofed convoy makes the neighbourhood-aware model flag honest neighbours: honest-sender FPR rises from 0.90% to 2.98% with 8 coordinated colluders
   (2.56% independent). The no-neighbour model's FPR is unaffected. Coordinated 50 m offsets give a smaller rise (0.90% to 1.25%).
4. Coordination itself matters little: coordinated vs independent lies differ by at most about 0.4 FPR points and 0.01 recall.

Limits of this study: colluders are rewritten honest vehicles of the trace (not a separate attack simulation), the 16 senders of a window are not re-selected after the
claims change, and the models were never trained on these scenarios. It is a stress test, not a claim of robustness.

## Limitations
Simulated benchmark; 14 of 19 attack types (the four Sybil attacks are not run, and the RandomSpeedOffset archive is mislabeled and excluded);
2 seeds; physically consistent and colluding lies are not detected (see above); dense-traffic transfer on 2 attacks only; no VeReMi NextGen / original VeReMi / MixAll evaluation;
no comparison against published learned detectors. `results/preds*/` (large per-window predictions) are git-ignored; rerun `run_full.py` to regenerate.
