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
paper/main.tex       conference paper (IEEEtran)
```

Run: `pip install -r requirements.txt && python run_experiments.py && python make_tables.py`
(`--quick` for a smoke test).

## Important status note
The sandbox this was built in could not reach Zenodo/GitHub, so **the reported numbers come from the
included simulator, not from the real VeReMi / VeReMi Extension / NextGen data**. `data.load_veremi` implements
the published log format but has not been run against the real archives. Before submission, download the
datasets, run `load_veremi`, and replace the simulated results (Section "Threats to validity" in the paper
says this explicitly).
