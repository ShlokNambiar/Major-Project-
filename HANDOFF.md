# HANDOFF: context packet for the next agent

Read this file first, then `README.md`. It states what the project is, what is done, what is open, the rules the
human has set, and the traps that already cost time. Everything here was verified against the repo and result files on 2026-10-15.
If anything here conflicts with a result file, **the result file wins**; fix this document.

- Repo: `shloknambiar/major-project-`, working branch **`claude/ecstatic-pasteur-0piqiz`** (all work is on this branch; no PR has been opened; do not open one unless asked).
- Team: Shlok (UAI05BTA2317), Jiya (UAI05BTA2313), Caleb (UAI05BTA2319); BTech AI ML, Universal AI University (UAI). The human talking to you is one of them; they are a student, time-pressed, and presenting to a professor.

---------------------------------------------------------------------------------------------------

## 1. The project in one paragraph

**Neighbourhood-aware misbehavior detection for V2X.** Connected vehicles broadcast Basic Safety Messages (position, speed, heading).
A misbehaving vehicle sends false data. Most learned detectors judge each sender alone. We build a receiver-centric transformer:
for each receiving car and time step, take the **16 nearest senders x 10 one-second steps**, and classify each sender as attacker or honest.
The proposed model adds **spatial attention across senders** (neighbour context). We test on the public **VeReMi Extension** benchmark
(simulated traffic and attackers; it is not real-world data, never call it that). The professor asked for (1) precision, recall, F1, FPR and detection latency, not just F1,
and (2) analysis of behaviour when neighbouring vehicles are themselves malicious.

## 2. Status at a glance

| Area | Status |
|---|---|
| Data loader for real VeReMi Extension logs | Done, validated (`nambd/data.py`) |
| 14-attack experiment, 2 models x 2 seeds, significance tests, rule baselines, latency | **Done**, final (`results/results_full14.json`) |
| Earlier 8-attack run incl. restricted per-sender model, dense-traffic transfer | Done (`results/results_full.json`, `results/results_dense.json`) |
| Paper tables + figure from results | Done (`paper/tables.tex`, `paper/fig_perattack.pdf`, via `make_tables.py`) |
| Paper (`paper/main.tex` -> `paper/main.pdf`, IEEE conference, 6 pages, 18 verified references) | **First full draft 2026-10-16**; compile with `tectonic -X compile main.tex` in `paper/`; tables from `make_v2_tables.py` + `make_paper_assets.py`; author full names/supervisor still TODO |
| Literature table (20 sources + ours) | Done, but mostly abstract-level reading (`docs/literature_review.docx`) |
| Blueprint PDF, worksheet PDF, research-plan PDF | Done but **numbers are outdated** (see section 9) |
| Progress deck (`presentation/progress_update.pptx`) | Done but **numbers are outdated**; human said "don't update the deck yet" |
| Attacks covered | 14 of 19 |
| Other datasets (original VeReMi, NextGen, MixAll_0024) | **Not run** |
| Malicious-neighbour / collusion / crash-intent study (injected, on saved test windows) | **Done** (`results/results_collusion.json`, section 3b) |
| Sybil attacks | **Not run** |
| **v2 detector** (plausibility checks + road map + lie augmentation; message-level labels; receiver memory) | **Done** (`results/results_v2.json`, section 3c) |

## 3. Final results (14 attacks; use these numbers)

Source: `results/results_full14.json` (`PREDS=results/preds14`). Train on first-hour slices, test on later-hour slices,
receiver-disjoint 30/70 val/test blocks per subset, 68,971 test windows, **2 seeds** (std about 0.001-0.004).

| Model | Precision | Recall | F1 | FPR | AUC |
|---|---|---|---|---|---|
| VeReMi range check (rule) | 0.416 | 0.674 | 0.514 | 43.7% | 0.690 |
| VeReMi speed check (rule) | 0.956 | 0.672 | 0.789 | 1.4% | 0.778 |
| No neighbour attention (`nonbr`, all features) | 0.968 | 0.905 | 0.935 | 1.4% | 0.979 |
| **Neighbourhood-aware (`full`)** | **0.984** | **0.916** | **0.949** | **0.7%** | **0.990** |

- `full` vs `nonbr`: **+0.014 F1**, paired-bootstrap 95% CI [0.012, 0.016] in both seeds; FPR halves. Significant after Holm correction on **12 of 14** attacks
  (not ConstPos p=0.22, not ConstSpeedOffset p=0.085). Biggest gains: EventualStop +0.072, ConstPosOffset +0.042.
- Hardest attacks: EventualStop (F1 0.74) and ConstPosOffset (0.79). All others above 0.93.
- Speed-check rule fails (F1 < 0.1) on ConstPosOffset, EventualStop, DelayedMessages, DoS; it is competitive on content-falsification attacks.
- Latency: mean 1.4 s to first alarm (median 0, p90 3 s), 93% of attacker-receiver pairs eventually flagged. Counted from the first window containing the sender; each window already holds about 10 s of history.
- Dense 07:00-09:00 traffic (RandomPos, ConstSpeed only, 2 attacks): F1 0.972 (`full`) vs 0.968 (`nonbr`).
- Earlier 8-attack run (8 features, no rate feature): restricted per-sender model F1 0.795; `nonbr` 0.908; `full` 0.923. The restricted per-sender model **also drops the receiver-relative position features**
  (`MODES["persender"]` drops features 0,1), so "persender -> nonbr" (+0.113) measures position information, and "nonbr -> full" (+0.015) measures neighbour attention.
  Never present persender -> full as "the effect of neighbours".
- Superseded: `results/results_real.json`, `results_real_extra.json` (2-attack runs; there neighbour attention added nothing) and `results/results.json` (our own highway simulator; not used for claims).

## 3b. Malicious neighbours and collusion (professor's point 2; added 2026-10-15)

Source: `results/results_collusion.json` (`run_collusion.py`, `nambd/collusion.py`, figure/tables via `make_collusion_fig.py`). Uses the saved 14-attack
test windows and the committed models (`results/models14`); no retraining. `nonbr` cannot see other senders, so it is the control.
- **Real attackers by attacker share in window** (0-20/20-40/40-60/>60%): `full` recall 0.943/0.929/0.917/0.877, `nonbr` flat ~0.90. Within-attack gain of
  neighbour attention +0.021/+0.013/**-0.023** (14 attack types per bin; 0-20% bin has only 5). The neighbour benefit disappears once attackers are the majority.
- **Injected physically consistent lies** (50 m offset, fake stop, spoofed approach convoy; m=1..8 colluders, coordinated or independent; 1,514 windows with >=9 honest senders):
  recall <= 0.04 for **both** models at a matched 1% validation FPR. Offset size sweep (m=4): 100/200/400 m -> recall ~0.04/0.10/0.41, models equal.
  Explanation (checked on feature statistics): real VeReMi attackers are caught through implausibility (claimed positions beyond radio range, speed vs displacement mismatch),
  not through cross-checking neighbours. **Do not claim the model cross-validates neighbours or resists collusion.**
- **Framing**: a coordinated spoofed convoy (m=8) raises `full`'s honest-sender FPR 0.90% -> 2.98% (independent 2.56%); `nonbr` unaffected.
- Coordinated vs independent differs little (<=0.4 FPR points, <=0.01 recall).
- At each model's own threshold `full` shows lower colluder recall than `nonbr`; that is only its stricter threshold (0.75-0.85 vs 0.55-0.65). Quote the matched-FPR numbers.
- Limits: colluders are rewritten honest vehicles; window senders are not re-selected after the lie; models never trained on these scenarios. Stress test only.
- The README line "Targets the constant-position-offset attack that per-sender detectors cannot see" was removed: a consistent 50 m offset is not detected.

## 3c. v2 detector (added 2026-10-16) — current best, use these numbers

The human's target: beat the **97.37%** that the survey `Advancing Intrusion Detection in V2X Networks` (Abdel Hakeem & Kim, IEEE T-ITS 26(8), 2025; PDF in the
human's Downloads) lists for VeReMi in Table XIII (accuracy/precision/recall/F1 lumped together, original VeReMi, no source cited), and solve the trajectory issue.
- Code: `nambd/data.py:load_veremi_raw`, `nambd/features.py` (19 features; RoadMap), `nambd/collusion.py` (inject_raw, augment, on-road scenarios), `nambd/memory.py`,
  `run_v2.py` (two phases: features to `data/cache_feat/*.npy`, then GPU training from memmaps), `label_active.py`, `run_analysis_v2.py`, `run_collusion_v2.py`, `make_v2_tables.py`.
- Models `results/models_v2/{full,nonbr,full-noaug}_{0,1}.pt`; preds in `results/preds_v2/` (git-ignored, includes `test_raw.pkl`, `roadmap.pkl`).
- Results (mean of 2 seeds), message labels: full P 98.65 R 97.12 F1 97.88 Acc 98.69; **full + receiver memory P 98.16 R 97.78 F1 97.97 Acc 98.74** (all above 97.37 in each seed).
  Vehicle labels: full P 98.65 R 95.41 F1 97.01 Acc 98.14 (+memory R 96.09 F1 97.12): recall/F1 below 97.37 there. Say which labels every time.
- Message labels exclude attacker windows without any falsified message (mostly EventualStop before its stop, 26% of its windows); ground truth from `traceGroundTruthJSON`
  (honest claims match it exactly). Defensible, but it is a choice: state it.
- The comparison is not like-for-like (different dataset, 14 vs 5 attacks, metric definitions unclear in the survey). Do not write "beats the state of the art".
- Neighbour attention: +0.003 F1, significant (CIs exclude 0, both seeds/schemes), 8-10/14 attacks; FPR 0.60% vs 0.90%.
- Trajectory: careful injected lies now caught (offset 50 m 0.84, fake stop 0.70, unseen convoy 0.88 at 1% FPR; before: <= 0.04). On-road map-aware lies remain hard
  (along-road offset 0.25, on-road convoy 0.42; `results/results_collusion_v2_onroad.json`). Do not claim the trajectory problem is fully solved.
- Memory: this laptop has 15.7 GB RAM with ~2-3 GB free; Claude Code kills background jobs under memory pressure. `run_v2.py` is written to stay low (memmaps); run analysis jobs one at a time.

## 4. How the system works (so you can modify it)

**Data layout** (VeReMi Extension, Zenodo record **20090854**, CC-BY 4.0): one zip per attack and time slot (`<Attack>_1416.zip` = 14:00-16:00, low traffic;
`<Attack>_0709.zip` = 07:00-09:00, dense; `MixAll_0024.zip` = full day). Each holds nested one-hour zips (`VeReMi_50400_54000_*` and `VeReMi_54000_57600_*`).
Inside: `traceJSON-<vehId>-<pseudo>-A<attackId>-<start>-<run>.json`, one log per vehicle.
Log line types: **type 2 = receiver's own state; type 3 = received BSM** (`sender`, `rcvTime`, `pos`, `spd`, `hed`). (The original code had these swapped.)
**Labels come from the file name**: `A0` benign, `A<n>` attacker. BSM `sender` ids are vehicle ids, so a sender's label is looked up from the vehicle's own filename.
Attack ids -> names (14 used): 1 ConstPos, 2 ConstPosOffset, 3 RandomPos, 4 RandomPosOffset, 5 ConstSpeed, 6 ConstSpeedOffset, 7 RandomSpeed, 9 EventualStop,
10 Disruptive, 11 DataReplay, 12 DelayedMessages, 13 DoS, 14 DoSRandom, 15 DoSDisruptive. (8 = RandomSpeedOffset, excluded, see section 7.)

**Windows** (`nambd/data.py: load_veremi`): messages binned to 1 s; a window = (receiver, end time `te`), every 3 s (`stride=3`); K=16 nearest senders by *claimed* distance at `te`;
T=10 steps; a window is skipped if the receiver's own state is missing in any of the 10 steps. Features per sender per step (F=8): claimed position relative to receiver /300 m (2), speed/30, cos and sin heading,
position delta between consecutive steps x3 (2), valid flag. With `rate=True` a 9th feature: `log1p(messages heard from that sender in that second)/3`. **Needed for DoS attacks** (a flood is invisible once messages are binned to one per second).
Sender identity and the simulated noise fields are not features. `load_veremi(..., max_receivers=N)` samples receivers evenly.

**Models** (`nambd/model.py`, `nambd/train.py`): `Detector` = factorised temporal then (optionally) spatial transformer, d=64, 4 heads, 2 layers, dropout 0.1. `MODES`:
`full` = spatial attention on, all features; `nonbr` = spatial off, all features (the **fair no-neighbour baseline**); `persender` = spatial off and features 0,1 zeroed (restricted view).
Training: weighted BCE (`pos_weight=2`), AdamW lr 2e-3, wd 1e-2, OneCycle, 5 epochs, batch 128. Alarm threshold = grid search maximising F1 on the validation block (never on test).
Label for training is binary (attacker or not); attack id is only used for per-attack evaluation. `fit()` sizes the input layer from the data (`fin = X.shape[-1]`).

**Evaluation** (`nambd/evalutil.py`, `run_analysis.py`): overall P/R/F1/FPR/AUC; **per-attack F1 is scored against the benign senders of that attack's own simulation run** (`attack_mask`), because scoring against
all benign senders across 14 runs deflates every number; latency per (subset, receiver, sender) pair; paired bootstrap over receivers (B=2000) for dF1 CIs; McNemar on paired decisions; Holm across attacks;
rule-based baselines (VeReMi paper's range check and speed-consistency check) computed on the same windows with thresholds picked on validation.

## 5. Repo map

```
README.md                  results + limitations (kept current; update when results change)
HANDOFF.md                 this file
nambd/data.py              loader for real logs (+ simulator windows); optional rate feature
nambd/model.py train.py    Detector, MODES, fit(), scores(), best_thr()
nambd/evalutil.py          shared metrics, latency, bootstrap, McNemar, Holm, rule baselines, attack_mask
nambd/sim.py               our own highway simulator (old, not used for claims)
run_full.py                MAIN experiment: loads all subsets under data/, trains, saves per-window predictions + models (resumable; skips existing preds)
run_analysis.py            analyses saved predictions -> results JSON (env: PREDS, OUT, BOOT)
run_collusion.py           malicious-neighbour / collusion study on saved preds + models -> results/results_collusion.json (env: PREDS, MODELS, NWIN, MS, OUT)
make_collusion_fig.py      -> paper/tables_collusion.tex + paper/fig_collusion.pdf
nambd/collusion.py         collusion generator (offset / stop / approach; coordinated or independent)
tests/test_collusion.py    python -m pytest tests -q (simulator windows; no data needed)
run_dense.py               dense-traffic transfer for the 8-attack models (14-attack dense numbers are inside results_full14.json["res"]["dense"])
make_tables.py             results JSON -> paper/tables.tex + paper/fig_perattack.pdf (defaults to results_full14.json if present)
run_real.py, run_real_extra.py, save_model.py, run_experiments.py   older scripts (2-attack runs / simulator); superseded but kept
scripts/download_veremi_ext.sh   resumable Zenodo downloader + nested unzip
make_blueprint_pdf.py make_worksheet_pdf.py make_plan_pdf.py make_litreview_docx.py   generators for the documents in docs/
presentation/build_deck.js progress_update.pptx   deck generator + deck (OUTDATED numbers)
docs/                      blueprint PDF, worksheet PDF, research plan PDF, literature review docx
results/results_full14.json   FINAL numbers (14 attacks)   | results_full.json, results_dense.json: 8-attack run
results/models14/ models/ models (small .pt files, committed)   | results/preds*/ (large, git-ignored; regenerate)
results/full14_log.txt     training log of the final run
```
Git-ignored on purpose: `data/` (several GB), `papers/` (downloaded PDFs, copyright), `results/preds/`, `results/preds14/` (big), `*.npz`, `*.log` (except `results/log.txt`).

## 6. Reproduce

```bash
pip install -r requirements.txt
# data: about 180-250 MB per attack, 2 slices each; Zenodo is slow (0.1-1 MB/s), expect long waits
scripts/download_veremi_ext.sh RandomPos_1416 ConstSpeed_1416 ConstPos_1416 ConstPosOffset_1416 RandomPosOffset_1416 ConstSpeedOffset_1416 \
  RandomSpeed_1416 EventualStop_1416 Disruptive_1416 DataReplay_1416 DelayedMessages_1416 DoS_1416 DoSRandom_1416 DoSDisruptive_1416 \
  RandomPos_0709 ConstSpeed_0709
# final 14-attack run (about 20-25 min per model-seed on 4 CPU cores when nothing else is running)
RATE=1 MAXR=250 MODES=nonbr,full SEEDS=2 PREDS=results/preds14 MODELS=results/models14 python3 -u run_full.py > results/full14_log.txt 2>&1
PREDS=results/preds14 OUT=results/results_full14.json python3 run_analysis.py
python3 make_tables.py
```
Notes: `run_full.py` reuses a saved model `MODELS/<mode>_<seed>.pt` instead of retraining when it exists (`REUSE=0` forces training); this rebuilt
`results/preds14` on 2026-10-15 and reproduced `results_full14.json` exactly (log: `results/rebuild14_log.txt`). Collusion study:
`PREDS=results/preds14 MODELS=results/models14 python run_collusion.py && python make_collusion_fig.py`.
`run_full.py` is resumable (it skips any `PREDS/<mode>_<seed>.npz` that exists) and **picks up every subset found under `data/`**; the 8-attack run was made before the six extra subsets were downloaded.
To reproduce it, set `EXCLUDE=RandomSpeed,ConstSpeedOffset,Disruptive,DoS` and `RATE=0 MAXR=300 PREDS=results/preds MODES=persender,full` (then `MODES=nonbr`), then `python3 run_analysis.py` and `python3 run_dense.py`.
`EXCLUDE` defaults to `RandomSpeedOffset` (see section 7). Env knobs: `MAXR` (receivers per slice), `SEEDS`, `MODES`, `EPOCHS`, `RATE`, `PREDS`, `MODELS`, `EXCLUDE`.

## 7. Data facts and traps

1. **Zenodo is slow and drops connections.** Expect 0.1-1 MB/s. Use the resumable script; run it in the background (`setsid nohup ... &`).
2. **`RandomSpeedOffset_1416` is mislabeled**: its "50400_54000" archive contains a folder named `54000_57600`, and both slices are byte-identical later-hour data. Using it leaks train into test. It is excluded by `EXCLUDE`, and `run_full.py` also skips any slice that does not start inside the advertised window (`load_checked`).
3. Some archives (DataReplay, DelayedMessages, EventualStop) contain extra tiny slices (`57600_61200`); the glob ignores them because tags are `50400_54000`, `54000_57600`, `25200_28800`.
4. Slices run slightly past the hour (first-hour windows end at about 54166 s), so do not "validate" slices with strict end-time bounds; check the start time.
5. The VeReMi Extension is called "VeReMi++" in some papers (PAMPOS); it has **19** attack types, not "about 20".
6. Sybil attacks (DataReplaySybil, GridSybil, DoSRandomSybil, DoSDisruptiveSybil) forge sender identities; the filename-based labelling may not be valid for ghost ids. Not run. Inspect before using.
7. NextGen (Zenodo 19665762, InTAS scenario) and original VeReMi (20081895, 3.6 GB) have **different formats/ids**; the loader will need changes. MixAll_0024 is 3.6 GB.

## 8. TODO (priority order)

1. **Update the human-facing documents to the final numbers** (section 9). Highest value for the human's next presentation. The human said "don't update the deck yet": ask before touching the deck.
2. **Write the paper**: IEEE-style `paper/main.tex` using `paper/tables.tex` and `paper/fig_perattack.pdf`. Sections: abstract, introduction, related work (from `docs/literature_review.docx`), method, setup, results, malicious-neighbour/robustness discussion, limitations, conclusion, references with full bibliographic details (several literature rows lack authors/venues; see section 10).
3. **More evidence**: external check on VeReMi NextGen (needs loader work) and/or the original VeReMi; MixAll_0024; Sybil attacks; a 3rd seed; dense-traffic evaluation on more than 2 attacks.
4. **Professor's point 2**: done as a stress test (section 3b) and largely addressed by v2 (section 3c); open: on-road consistent lies, Sybil. Open follow-ups: train with injected consistent lies (does `full` then learn real cross-checking?); add a sender-vs-sender
   consistency input (e.g. claimed inter-vehicle distances vs radio range); re-select window senders after injection; Sybil attacks.
5. **A published-detector comparison** on the same split (we only compare to our own models and the two VeReMi rule checks). Possible leads: PAMPOS, AttentionGuard (see `docs/literature_review.docx`), but they use different data/splits.
6. Possible model improvement: add an explicit speed-vs-displacement consistency input (the rule check beats the learned models on some attacks); more epochs; unsupervised variant for unseen attacks.
7. Housekeeping: pin library versions; add a tiny test for `load_veremi`; consider committing a small sample of preds.

## 9. Documents that are OUT OF DATE (do not present them as final)

- `presentation/progress_update.pptx` (8 slides, built by `presentation/build_deck.js`): quotes the old 2-attack results (F1 0.982 vs 0.973, latency 0.15 s) and the retracted claim that neighbours raise F1 by 0.9 points.
- `docs/research_methodology_blueprint.pdf`, `docs/research_methodology_worksheet.pdf`, `docs/research_plan.pdf`: same old numbers and "2 of about 20 attacks"; the validation section says "no significance test yet", which is no longer true.
  Regenerate with `make_blueprint_pdf.py`, `make_worksheet_pdf.py`, `make_plan_pdf.py` after editing the numbers/wording. Blueprint and worksheet are **one page each and the human pinned the header format**: one line
  `Student Name / Roll No: Shlok (UAI05BTA2317), Jiya (UAI05BTA2313), Caleb (UAI05BTA2319)`, then `Branch: BTech AI ML`, then the project title; do not list names twice. The blueprint follows the university template (5 numbered sections, with a one-line explanation under each evaluation metric).
  The worksheet's question 2 ("Interest") is a **draft written by the AI**; the students must replace it with their real reasons.
- `docs/literature_review.docx`: 20 sources + this work in the university's 8-column format. Reading depth is stated per row (2 full texts, about 14 abstract-only, 4 second-hand through the 2025 survey or search snippets). It still says "only 2 of 19 attacks" in the last row: update to 14.
- The deck/blueprint line "neighbour context raises F1 0.973 to 0.982" is **misleading** (position features, not neighbours); the corrected statement is in section 3.

## 10. Rules set by the human and by the environment

**Honesty rules (the human relies on these; do not break them)**
- Say "preliminary"/"in progress" where true; never claim a result that is not in a results file. Never say "real-world data" for VeReMi: it is a simulated benchmark.
- Mark how much of each cited paper you actually read (full text / abstract / via survey / search snippet). Do not invent authors, venues or numbers. Flag second-hand figures (e.g. 37% collusion threshold, 95.91% precision / 83.73% recall) as unverified.
- The human asked not to claim models are untrained; they are trained. The framing allowed: "preliminary results, evaluation in progress".
- When you find a flaw in earlier claims (this happened three times: persender confound, per-attack deflation, mislabeled archive), tell the human plainly and fix the repo, then the documents.
- Statistical wording: 2 seeds, bootstrap CIs over receivers, Holm across attacks; do not call anything "proved".

**Working style the human wants**
- Act, do not ask permission for routine steps; short plain-English explanations; they present to a professor with little notice. Give crash-course summaries when asked.
- Deliverable files: put them under `docs/` (or the relevant folder) in the repo, commit, push, and attach/send the file to the human. PDFs are generated with `reportlab`, Word files with `python-docx`.
- Header/format instructions for blueprint and worksheet are in section 9.

**Git rules**
- Work only on `claude/ecstatic-pasteur-0piqiz`; `git push -u origin claude/ecstatic-pasteur-0piqiz`. Do not create a PR unless asked.
- A Stop hook (`~/.claude/stop-hook-git-check.sh`) blocks finishing while there are uncommitted or untracked files: commit and push before ending a turn. Do not commit `data/`, `papers/`, `results/preds*/`.
- End commit messages with the attribution lines that the harness specifies (in this session: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and a `Claude-Session:` URL). Never put model identifiers in code, docs or PR text.
- GitHub is reached through the harness; the `gh` CLI is not available here.

**Environment traps (cost real time)**
- Since 2026-10-15 the work also runs on Shlok's Windows laptop (Git Bash + PowerShell, Python 3.12, torch with CUDA on an RTX 3050 Ti, 20 cores); `data/` is downloaded there
  (14 x 1416 archives; no 0709 dense archives yet). The Linux-sandbox traps below may not apply there. Parallel per-archive downloads reach about 0.8 MB/s total.
- **`pkill -f` / `pgrep -f` / `kill $(pgrep -f ...)` inside a Bash call kills your own shell** (the pattern matches the command line). Kill by explicit PID, or use `ps -eo pid,args | grep "[p]attern"`.
- A built-in safety check **blocks any command that contains `rm`** (even inside scripts passed to `bash -c`); the whole command is refused. Avoid deletions; leave partial files and let `curl -C -` resume.
- Foreground `sleep` is blocked: run long jobs with `setsid nohup python3 -u ... > log 2>&1 < /dev/null &`, then wait with a background `until ... ; do sleep 30; done` or the Monitor tool. A background command stops after its timeout (max 2 h); long waits need re-arming.
- LibreOffice cannot open files here (even a trivial .pptx), so **slides cannot be rendered to images**; PDFs can be checked with `pdftoppm`. Validate pptx with the skill's `validate.py` only.
- Zenodo throughput is low (section 7); run downloads in the background and plan for it. CPU is 4 cores; two training processes at once roughly halve each other's speed.
- WebFetch cannot read some publisher pages (bot checks); arXiv abs/pdf pages work (`curl` the PDF and use `pdftotext`).
- The sandbox forgets scratch files: anything needed later must be in the repo (the deck builder and literature-table generator were only in scratch until this handoff).

## 11. Open questions for the human

- The human decided (2026-10-15) to **finish the implementation before writing the paper**; scope chosen for that round: the collusion test only.
- Is the next deadline the paper, the deck, or both? Should the deck be updated now (they previously said not yet)?
- Do they want NextGen / original VeReMi added, or is 14 attacks on VeReMi Extension sufficient for the submission?
- Roll-number mapping was confirmed: Shlok 2317, Jiya 2313, Caleb 2319.
- The "Interest" answer in the worksheet needs the students' own words.
