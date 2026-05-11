# Superseded EAAI Experiments / Results / Mechanistic Analysis Plan

> Superseded on 2026-05-11. Do not execute this plan for active paper-facing work.

This plan was written when the paper still depended on early single-seed and incomplete final-block evidence. The active paper-facing database now contains completed S4/S5/S6 main aggregates, S4 semantic ablation, S6 seed23 mechanism / feedback-off diagnostic, S5 seed11 model sensitivity, and S5 raw-only algorithm baseline.

Use these current files instead:

- `docs/superpowers/plans/2026-05-11-s5-s6-main-results-paper-sync.md`
- `docs/reports/2026-05-10-stage-a-igd-and-paper-assets.md`
- `paper/msgalaxy/planning/evidence_register.md`

Active Results claim policy:

- `aggregate` claims come from `paper_database/paper_experiment_db/tables/aggregate_metrics.csv` and registered comparison bundles.
- S6 seed23 mechanism / feedback-off diagnostic is `diagnostic` and single-seed only.
- S5 seed11 model sensitivity is `diagnostic` and single-seed only.
- Historical comparison artifacts outside `paper_database/` are audit background unless explicitly admitted in `claim_evidence.csv`.

Retired assumptions from the old plan:

- Final S4/S5/S6 main claims are now aggregate evidence.
- The old single-seed semantic ablation is not the main mechanism evidence.
- The older representative diagnostic seed is not the active mechanism diagnostic.
- Kimi and `llm_direct` are not final requirements.
