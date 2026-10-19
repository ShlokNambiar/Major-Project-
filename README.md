# Neighbourhood-Aware Misbehavior Detection in V2X Networks

> **Taking over this project? Read [`HANDOFF.md`](HANDOFF.md) first** (status, results, rules, open work, environment traps).

Transformer encoder whose attention runs across **co-located senders at the same instant** (spatial axis)
as well as across time, so a sender's claims are judged in the context of what surrounding vehicles claim.
(The collusion study below shows what this does and does not buy: it does not catch lies that are physically consistent.)

```
nambd/sim.py     VeReMi-style highway simulator (5 attacks) used when real logs are unavailable
nambd/data.py    receiver-centric windows (K nearest senders x T steps); load_veremi() for the VeReMi Extension logs
nambd/model.py   factorised temporal/spatial transformer, spatial-off ablation, gradient reversal (DANN)
nambd/train.py   training, threshold selection, per-attack F1/AUC
nambd/collusion.py   collusion generator: rewrites m honest senders of a finished window into colluders
run_experiments.py   reproduces all results -> results/results.json
make_tables.py       results -> paper/tables.tex + figure
run_collusion.py     malicious-neighbour / collusion study -> results/results_collusion.json
make_collusion_fig.py  -> paper/tables_collusion.tex + paper/fig_collusion.pdf
tests/               python -m pytest tests -q (collusion generator; no data needed)
paper/            tables.tex + fig_perattack.pdf generated from the real-data results (main.tex -> main.pdf: the paper; build with `tectonic -X compile main.tex`)
```

Run: `pip install -r requirements.txt && python run_experiments.py && python make_tables.py`
(`--quick` for a smoke test).

## First model results (superseded by the v2 section below; VeReMi Extension, 14 attack types, 14:00-16:00; 2 seeds)
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

1. **VeReMi attackers (not injected), by share of attackers in the window** (0-20 / 20-40 / 40-60 / >60%): the neighbourhood-aware model's recall falls
   0.943 / 0.929 / 0.917 / 0.877 while the no-neighbour model stays flat (0.905 / 0.908 / 0.904 / 0.900). Computed within each attack type
   (so the attack mix cannot explain it), the recall gain from neighbour attention is +0.021 / +0.013 / **-0.023** in the 20-40 / 40-60 / >60% bins
   (14 attack types each). Neighbour context helps while most neighbours are honest and stops helping once attackers are the majority.
2. **Injected lies that are physically consistent are not detected by either model.** In 1,514 test windows with at least 9 honest senders,
   m = 1..8 honest senders were rewritten to (a) shift their claimed position by 50 m, (b) claim to stop (fake jam / crash scene), or
   (c) claim to be a convoy driving at the receiver; each coordinated (one shared story) and independent. With both models at the same 1% validation FPR,
   colluder recall is at most 0.04 in every setting, for both models. Larger offsets are caught more often (offset 100 / 200 / 400 m, 4 colluders:
   recall about 0.04 / 0.10 / 0.41), with no consistent difference between the two models.
   Why: the dataset's own attackers are mostly caught because their claims are physically implausible (positions beyond radio range, speed that does not match displacement),
   not because neighbours contradict them. The models learned plausibility, not cross-checking between senders.
3. **Framing.** A spoofed convoy makes the neighbourhood-aware model flag honest neighbours: honest-sender FPR rises from 0.90% to 2.98% with 8 coordinated colluders
   (2.56% independent). The no-neighbour model's FPR is unaffected. Coordinated 50 m offsets give a smaller rise (0.90% to 1.25%).
4. Coordination itself matters little: coordinated vs independent lies differ by at most about 0.4 FPR points and 0.01 recall.

Limits of this study: colluders are rewritten honest vehicles of the trace (not a separate attack simulation), the 16 senders of a window are not re-selected after the
claims change, and the models were never trained on these scenarios. It is a stress test, not a claim of robustness.

## v2: plausibility checks + training on careful lies (`results/results_v2.json`, `results/results_collusion_v2.json`)
Pipeline: `run_v2.py` (raw claims -> `nambd/features.py`, lie augmentation `nambd/collusion.augment`, GPU; features cached in `data/cache_feat`),
`label_active.py` (message-level ground truth), `run_analysis_v2.py`, `run_collusion_v2.py`, `make_v2_tables.py` (-> `paper/tables_v2.tex`).
Same receivers, windows and val/test split as the 14-attack run. New inputs per sender and step (19 in total): claimed acceleration and two
kinematic consistency checks, heading vs direction of movement, a **road map** learned from receivers' own positions in the training hour
(on-road density and road direction at the claimed position), distance to the nearest other claim, **exact repeat** of the sender's own earlier
position, **copied trail** (exact match with another sender's earlier claim), and log-scaled movement. Training adds copies of windows where
1-4 honest senders tell careful offset or stop lies (the spoofed-approach convoy is held out).

Labels: *vehicle* = every window of an attacker vehicle is positive (as above); *message* = an attacker counts only in windows where it sent at least
one falsified message (claim differs from `traceGroundTruthJSON` by > 1 m or > 0.5 m/s; honest claims match it exactly; DoS attackers always count).
The difference is almost entirely EventualStop before its fake stop (26% of its windows contain only true messages and are excluded).
Thresholds (and the memory decay) are always chosen on the validation block.

| Model (mean of 2 seeds) | Labels | Precision | Recall | F1 | Accuracy | FPR |
|---|---|---|---|---|---|---|
| v2 full | message | 98.65 | 97.12 | 97.88 | 98.69 | 0.60% |
| v2 full + receiver memory | message | **98.16** | **97.78** | **97.97** | **98.74** | |
| v2 no neighbour attention | message | 97.99 | 97.11 | 97.54 | 98.48 | 0.90% |
| v2 no lie augmentation | message | 98.75 | 97.39 | 98.07 | 98.80 | 0.56% |
| v2 full | vehicle | 98.65 | 95.41 | 97.01 | 98.14 | 0.60% |
| v2 full + receiver memory | vehicle | 98.16 | 96.09 | 97.12 | 98.20 | |
| previous model (14-attack run above) | vehicle | 98.4 | 91.6 | 94.9 | 96.9 | 0.7% |

- Reference: the survey of Abdel Hakeem and Kim (IEEE T-ITS 2025, Table XIII) lists 97.37% for VeReMi (accuracy/precision/recall/F1 lumped; original
  VeReMi, 5 attacks; source not cited). With message labels and receiver memory, all four of our numbers are above it in both seeds.
  With vehicle labels, precision and accuracy are above it, recall (96.1%) and F1 (97.1%) are not. Different dataset (VeReMi Extension, 14 attacks): not a like-for-like comparison.
- Neighbour attention still helps: +0.003 F1 over the no-neighbour model (95% CI about [0.002, 0.004] in both seeds and both label schemes),
  significant on 8-10 of 14 attacks, never significantly worse; FPR 0.60% vs 0.90-0.96%.
- Lie augmentation costs 0.002 F1 on the real attacks but is what makes fake stops detectable (below).
- ConstPosOffset recall 0.66 -> 0.97 (road map). Remaining weak spots: DelayedMessages (recall 0.87), DataReplay (0.93).
- Latency: mean 0.9 s to first alarm (median 0), 96% of attacker-receiver pairs flagged.

**Trajectory lies after v2** (colluder recall at a matched 1% FPR; before v2 at most 0.04): 50 m position offset 0.83-0.86; fake stop 0.69-0.72
(0.01 without augmentation); spoofed convoy, never seen in training, 0.87-0.90. Offset size: 10 / 25 / 100 / 400 m -> 0.15 / 0.63 / 0.92 / 0.98.
**Map-aware liars stay hard:** shifting 50 m *along the road* is caught 0.23-0.25, a convoy *along the receiver's road* 0.36-0.48. A lie that is on the road
and kinematically consistent cannot be told apart from the message content alone; that needs an independent signal (signal strength, sensors, RSUs).
Neighbour attention adds little here (+0.01-0.02); the checks do the work.

## v18: Sybil extension (18 of 19 attacks) (`results/results_v18_final.json`, `paper/tables_v18.tex`)
Adds the four Sybil attacks: GridSybil (attack id 16), DataReplaySybil (17), DoSRandomSybil (18), DoSDisruptiveSybil (19). Together with the 14 above
that is 18 of the 19 VeReMi Extension attack types (RandomSpeedOffset stays out: its archive is mislabeled). 88,695 test windows; training uses
141,260 windows plus 51,033 augmented ones. VeReMi Extension is a simulated benchmark.

Pipeline:
```bash
FEAT=data/cache_feat18b PREDS=results/preds_v18 MODELS=results/models_v18 python run_v2.py    # features, then 2 seeds x (full, nonbr)
PREDS=results/preds_v18 FLOOD_EXTRA=18,19 python label_active.py                              # message labels; DoS*Sybil count as always active
FEAT=data/cache_feat18b PREDS=results/preds_v18 MODELS=results/models_v18 OUT=results/results_v18.json python run_analysis_v2.py
# capacity model (d=96, 3 blocks, 16 epochs); needs val_meta.npz / test_meta.npz (and the other preds_v18 meta files) copied into results/preds_v18big
MODEL_D=96 MODEL_L=3 EPOCHS=16 SEEDS=1 VARIANTS=full FEAT=data/cache_feat18b PREDS=results/preds_v18big MODELS=results/models_v18big \
  EPOCH_CKPT=results/models_v18big/full_0.epoch.ckpt python run_v2.py
python make_v18_assets.py      # 3-model ensemble -> results/results_v18_final.json + paper/tables_v18.tex
```
`run_v2.py` saves each model before scoring it (a stopped run reloads it instead of retraining; set `MODEL_D`/`MODEL_L` again when it reloads the
big model), and `EPOCH_CKPT` makes training resume at the next epoch after a stop.

What changed for Sybil:
- **Senders are tracked by pseudonym** (`senderPseudo`), which is all a receiver sees, so a Sybil attacker's fake identities are separate senders.
  Labels still come from the true vehicle (`sender` field). Outside the Sybil runs each vehicle uses one pseudonym, so the 14-attack windows are identical.
- Ghost messages differ from the true position in 74-100% of cases; honest messages never do. Message labels: DoS*Sybil attackers always count as
  active; for GridSybil 96% of attacker slots are active.
- Three new inputs (22 in total): **identity age** (following pseudonym changes), **handover distance** (how far a new pseudonym starts from one that just went silent),
  and **lockstep** (how rigid the offset is to the sender that moves most closely with it).
- Final system = mean score of 3 models: two 144k-parameter models (seeds 0 and 1) and one wider/deeper model (d=96, 3 blocks, 16 epochs); threshold picked on validation.

| 18 attacks, 3-model ensemble | Labels | Precision | Recall | F1 | Accuracy | FPR |
|---|---|---|---|---|---|---|
| Neighbourhood-aware | message | 96.30 | 95.46 | 95.88 | 97.04 | 2.07% |
| No neighbour attention (2-model ensemble) | message | 96.28 | 92.69 | 94.45 | 96.07 | 2.02% |
| Neighbourhood-aware | vehicle | 96.33 | 94.44 | 95.38 | 96.66 | 2.07% |
| No neighbour attention (2-model ensemble) | vehicle | 96.31 | 91.69 | 93.94 | 95.68 | 2.02% |

- **Neighbour attention matters more with Sybil**: +1.4 F1 (message labels; +1.4 vehicle) vs +0.3 on the 14 attacks.
- Per-attack recall (message labels, final ensemble): GridSybil 0.823 (the largest attack: 20,598 message-label test slots, 21,484 vehicle-label),
  DataReplaySybil 0.914, DoSDisruptiveSybil 0.969, DoSRandomSybil 0.997. The 14 original attacks are mostly at or above 0.96 (DelayedMessages 0.912, DataReplay 0.958).
  Single models are lower on Sybil (GridSybil about 0.79-0.80, DataReplaySybil about 0.89, DoSDisruptiveSybil about 0.95; `results/results_v18.json`).
- On the 14 original attack runs, the 18-attack model scores message F1 about 97.3 with FPR 1.6% (vs 0.6% for the 14-attack model): it lowers its
  threshold to catch ghosts, which costs false alarms.
- Tried and did not help: a bigger model alone (message F1 95.19 vs 95.76 for the 2-seed small ensemble); receiver memory (ghosts change pseudonyms, so
  per-sender memory has little to hold on to).
- **Content limit**: the GridSybil ghosts that are missed look honest on every content check (on the road, consistent motion), and no timing or formation
  cue separated them. Catching them needs an independent signal (signal strength, sensors, RSUs), as for the on-road lies in v2.
- **Against the 97.37% survey reference** (original VeReMi, 5 attacks, no Sybil): the 14-attack system is above it (message labels + memory: P 98.16 R 97.78
  F1 97.97 Acc 98.74). On 18 attacks with Sybil all four numbers are below it (P 96.3, R 95.5, F1 95.9, Acc 97.0). Neither is a like-for-like comparison.
- The 14-attack results in the v2 section are unchanged (`results/results_v2.json`).

## Limitations
Simulated benchmark; 18 of 19 attack types (the RandomSpeedOffset archive is mislabeled and excluded; the four Sybil attacks are covered only in the v18 section,
where GridSybil recall is 0.82 and all four headline numbers are below the 97.37% reference);
2 seeds (the 18-attack system is one 3-model ensemble); on-road, kinematically consistent lies are still mostly missed (v2 section); the 97.37% reference is from a different dataset; dense-traffic transfer on 2 attacks only; no VeReMi NextGen / original VeReMi / MixAll evaluation;
no comparison against published learned detectors. `results/preds*/` (large per-window predictions) are git-ignored; rerun `run_full.py` (14-attack) or `run_v2.py` (v2, v18) to regenerate.
