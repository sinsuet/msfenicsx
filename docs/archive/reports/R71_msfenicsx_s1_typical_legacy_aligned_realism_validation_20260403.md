# R71 msfenicsx s1_typical Legacy-Aligned Realism Validation 2026-04-03

## Scope

Validate the `legacy-aligned, mainline-compatible` update for the active paper-facing `s1_typical` line after:

- density-driven layout zoning
- denser fixed component area budget
- `panel_substrate = 5`, `electronics_housing = 20`
- localized heat-source support via `source_area_ratio`
- layout realism metrics surfaced into case provenance, evaluation signals, and rendered pages

Template and spec references:

- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `docs/superpowers/specs/2026-04-03-s1-typical-legacy-aligned-layout-and-thermal-design.md`

## Verification Commands

Focused regression suite:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema/test_s1_typical_template.py \
  tests/schema/test_schema_validation.py \
  tests/generator/test_parameter_sampler.py \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py \
  tests/solver/test_case_to_geometry.py \
  tests/solver/test_generated_case.py \
  tests/evaluation/test_engine.py \
  tests/visualization/test_case_pages.py \
  tests/optimizers/test_repair.py -v
```

Observed result:

- `42 passed in 9.34s`

Real chain verification used seeds:

- `11`
- `17`
- `23`
- `29`
- `31`

Runtime root:

- `scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/`

## Seed Results

| Seed | Active Deck Occupancy | BBox Fill Ratio | Tmin (K) | Tmax (K) | Span (K) | Gradient RMS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 11 | 0.4013 | 0.3804 | 303.737 | 313.152 | 9.415 | 13.047 |
| 17 | 0.4013 | 0.3882 | 304.873 | 315.215 | 10.342 | 14.465 |
| 23 | 0.4013 | 0.3798 | 304.929 | 315.292 | 10.363 | 14.198 |
| 29 | 0.4013 | 0.4038 | 304.557 | 314.838 | 10.281 | 14.324 |
| 31 | 0.4013 | 0.3831 | 305.298 | 315.060 | 9.763 | 13.762 |

Aggregate readout:

- `active_deck_occupancy` is stable at approximately `0.401`
- `bbox_fill_ratio` ranges from `0.3798` to `0.4038`
- `temperature_span` ranges from `9.41 K` to `10.36 K`

## Representative Artifacts

Seed `11` canonical bundle:

- `scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-0011/case.yaml`
- `scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-0011/solution.yaml`
- `scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-0011/evaluation.yaml`
- `scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-0011/summaries/field_view.json`
- `scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-0011/figures/layout.svg`
- `scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-0011/figures/temperature-field.svg`
- `scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-0011/pages/index.html`

## Conclusion

The updated mainline now matches the intended realism band much more closely than the previous sparse baseline:

- layout density moved from the previous representative `bbox_fill_ratio ~0.24` regime to approximately `0.38~0.40`
- thermal contrast moved from the previous `~1.8 K` regime to approximately `9.4~10.4 K`
- five calibration seeds generated, solved, evaluated, and rendered without component dropout

Relative to the design targets:

- `active_deck_occupancy 0.38~0.45`: met
- `temperature_span 8~20 K`: met
- five-seed no-drop generation: met

One residual note remains:

- `bbox_fill_ratio` is now on target overall, but one calibration seed (`23`) lands just under `0.38` at `0.3798`, so there is still a small amount of sensitivity near the density threshold.
