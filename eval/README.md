# eval

Evaluation harness. Runs the agent against a labeled benchmark of
already-triaged issues and reports label accuracy/F1, duplicate detection
precision/recall, and escalation calibration.

## Status

Implemented:

- `metrics.py` — pure functions: `label_metrics` (micro-averaged
  precision/recall/F1 over predicted vs. true label sets), `duplicate_metrics`
  (precision/recall of `duplicate_of` links — a link to the wrong issue
  counts as wrong, not partially right), `escalation_calibration` (of the
  items the agent acted on autonomously, what fraction were fully
  correct — the number that actually tells you whether
  `AUTONOMY_CONFIDENCE_THRESHOLD` is set correctly).
- `loader.py` — joins `eval_labels` (ground truth) with each issue's most
  recent `actions` row (the agent's real prediction) straight out of
  Postgres. This is exactly the audit log build order step 6 added, doing
  double duty as the eval data source per docs/ARCHITECTURE.md.
- `report.py` / `main.py` — `python -m eval.main` (from the repo root)
  prints a formatted report against whatever's in the DB.

Not yet implemented: a real labeled benchmark. docs/ARCHITECTURE.md calls
for "~100-200 already-triaged issues from a real repo", which doesn't
exist yet (no live GitHub App installation). `fixtures/sample_benchmark.py`
is a small (8-issue) synthetic stand-in — deliberately includes a few
wrong predictions (a misclassified type, an under-labeled issue, a missed
duplicate link) so the harness's metrics aren't trivially 100% on first
run. `seed.py` loads it into Postgres; safe to re-run (upserts).

## Local development

```bash
cd eval
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest   # pure metrics tests + a real-Postgres loader/report integration
         # test (hand-computed expected values); skips cleanly if
         # Postgres isn't reachable

# from the repo root, with Postgres up:
export DATABASE_URL=postgresql+psycopg://triage:triage@localhost:5432/triage_agent
python -m eval.seed   # load the synthetic benchmark
python -m eval.main   # print the report
```

Running it against the synthetic fixture prints:

```
Evaluated 8 labeled issue(s)

Label accuracy
  precision=81.8%  recall=81.8%  f1=81.8%

Duplicate detection
  precision=100.0%  recall=50.0%  (predicted=1, true=2, correct=1)

Escalation calibration (precision of auto-acted items)
  precision=66.7%  (acted_count=6)
```

Once a real installation has triage history, the loader works unchanged
against real `actions`/`eval_labels` rows — populating `eval_labels` with
real ground truth (e.g. a maintainer backfilling correct labels for past
issues) is the only remaining step to eval real performance instead of
the synthetic fixture.
