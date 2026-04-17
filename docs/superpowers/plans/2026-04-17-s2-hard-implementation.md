# S2 Hard Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the `s2_hard` companion benchmark (template, evaluation spec, optimization specs, generator zone-routing change) alongside the existing `s1_typical` mainline so the `raw / union / llm` ablation can be re-run on a harder, cross-category-infeasible scenario.

**Architecture:** The spec at `docs/superpowers/specs/2026-04-17-s2-hard-design.md` is the source of truth. `s2_hard` reuses all kernel contracts (schema, solver, evaluation runner, repair, cheap constraints, optimizer backbones, trace/analytics). The only code change is a small zone-routing extension in `core/generator/layout_engine.py` to honor a new `adversarial_core` zone under a new `s2_adversarial_v1` layout strategy kind. Everything else is new YAML files copied from their `s1_typical` counterparts with targeted edits.

**Tech Stack:** Python 3.11+, FEniCSx, pymoo (NSGA-II backbone), pytest, PyYAML, conda env `msfenicsx`.

---

## File Structure

**New YAML (data only, no code):**

- `scenarios/templates/s2_hard.yaml` — the hard-scenario template. Copy of `s1_typical.yaml` with edits to `template_meta`, `component_families[*].placement_hint`, `boundary_feature_families[0].sink_temperature`/`transfer_coefficient`, `load_rules[*].total_power`, `physics.background_boundary_cooling`, and `generation_rules.layout_strategy`.
- `scenarios/evaluation/s2_hard_eval.yaml` — eight-constraint evaluation spec (two binding, six slack) per design §7.
- `scenarios/optimization/s2_hard_raw.yaml` — raw optimization spec, structurally a copy of `s1_typical_raw.yaml` with `template_path` / `evaluation_spec_path` / `profile_path` re-pointed to `s2_hard` siblings.
- `scenarios/optimization/s2_hard_union.yaml` — union spec, same pattern as raw. Operator pool identical to `s1_typical_union.yaml`.
- `scenarios/optimization/s2_hard_llm.yaml` — llm spec, same pattern. `controller_parameters` identical to `s1_typical_llm.yaml`.
- `scenarios/optimization/profiles/s2_hard_raw.yaml` — algorithm parameters for NSGA-II raw, verbatim copy of `s1_typical_raw.yaml` profile, only `profile_meta.profile_id` and `description` change.
- `scenarios/optimization/profiles/s2_hard_union.yaml` — same for union profile.

**Code (one file):**

- `core/generator/layout_engine.py` — modify `_strategy_regions_for_profile` so that `bottom_band` placements prefer the `adversarial_core` zone when present, falling back to the existing derived bottom-band region otherwise. No schema change required; `kind: s2_adversarial_v1` is opaque to the engine, the zone list drives behavior.

**Tests:**

- `tests/generator/test_layout_engine.py` — add new test cases for the `adversarial_core` zone-routing branch. Keep all existing `s1_typical` assertions green.
- `tests/generator/test_s2_hard_template.py` — new focused test file validating `s2_hard.yaml` loads cleanly, generates fifteen legal components under seed 11, and places the four power-dense modules (`c02/c04/c06/c12`) inside the adversarial-core zone.

**Docs (at end of implementation):**

- `README.md`, `CLAUDE.md`, `AGENTS.md` — flip the "pending-implementation" wording on `s2_hard` to "active" and move the input list accordingly.

---

## Task 1: Create `s2_hard.yaml` Template

**Files:**
- Create: `scenarios/templates/s2_hard.yaml`
- Reference (read-only): `scenarios/templates/s1_typical.yaml`

**What to produce:** A full 300+-line template file. Most fields are verbatim from `s1_typical.yaml`. Edits are confined to the locations listed below.

- [ ] **Step 1: Start from a verbatim copy of `s1_typical.yaml`**

Run:
```bash
cp scenarios/templates/s1_typical.yaml scenarios/templates/s2_hard.yaml
```

- [ ] **Step 2: Update `template_meta`**

Open `scenarios/templates/s2_hard.yaml` and change the top block:

```yaml
schema_version: "1.0"
template_meta:
  template_id: s2_hard
  description: Single-case S2 hard paper-facing template with cross-category-infeasible baseline (weakened sink plus amplified power-dense modules in the adversarial bottom zone).
```

- [ ] **Step 3: Update `boundary_feature_families[0]` (weaken the sink)**

Replace the `sink_temperature` and `transfer_coefficient` blocks:

```yaml
boundary_feature_families:
  - family_id: sink-top-window
    kind: line_sink
    edge: top
    span:
      min: 0.31
      max: 0.69
    sink_temperature:
      min: 293.0
      max: 293.0
    transfer_coefficient:
      min: 5.0
      max: 5.0
```

Leave the `span` block unchanged — the sink window range is identical to `s1_typical`; only the constraint limit (in the evaluation spec) changes.

- [ ] **Step 4: Update `physics.background_boundary_cooling` (remove background cooling)**

Replace the physics block:

```yaml
physics:
  kind: steady_heat_radiation
  ambient_temperature: 292.0
  background_boundary_cooling:
    transfer_coefficient: 0.0
    emissivity: 0.02
```

Keep `ambient_temperature: 292.0` unchanged.

- [ ] **Step 5: Update placement hints for the four amplified modules**

In `component_families`, change `placement_hint` from `top_band` to `bottom_band` for `c02`, `c04`, `c06`, `c12`. All other fields on these families (role, geometry, clearance, material_ref, etc.) stay identical.

Result: families `c02/c04/c06/c12` have `placement_hint: bottom_band`. All other families keep their current hint. Hints of unchanged families must remain exactly as in `s1_typical.yaml` (spec §6.3 table).

- [ ] **Step 6: Amplify power in `load_rules` for the four target families**

Replace only these four `load_rules` entries. All eleven other entries stay verbatim.

```yaml
  - target_family: c02
    total_power: 20.0
    source_area_ratio: 0.12
  - target_family: c04
    total_power: 19.0
    source_area_ratio: 0.13
  - target_family: c06
    total_power: 18.0
    source_area_ratio: 0.14
  - target_family: c12
    total_power: 16.0
    source_area_ratio: 0.18
```

`source_area_ratio` values are not changed — only `total_power`.

- [ ] **Step 7: Replace `generation_rules.layout_strategy`**

Replace the entire `layout_strategy` block (keep `seed_policy` and `max_placement_attempts` at the original `external` / `1400`):

```yaml
generation_rules:
  seed_policy: external
  max_placement_attempts: 1400
  layout_strategy:
    kind: s2_adversarial_v1
    zones:
      active_deck:
        x_min: 0.08
        x_max: 0.92
        y_min: 0.08
        y_max: 0.68
      adversarial_core:
        x_min: 0.15
        x_max: 0.85
        y_min: 0.10
        y_max: 0.35
      top_sink_band:
        x_min: 0.20
        x_max: 0.80
        y_min: 0.55
        y_max: 0.68
      left_io_edge:
        x_min: 0.10
        x_max: 0.24
        y_min: 0.10
        y_max: 0.66
      right_service_edge:
        x_min: 0.76
        x_max: 0.91
        y_min: 0.10
        y_max: 0.66
```

Note: `dense_core` is removed on purpose. `adversarial_core` replaces it.

- [ ] **Step 8: Verify the file is well-formed YAML and matches `s1_typical` everywhere else**

Run:
```bash
conda run -n msfenicsx python -c "import yaml; yaml.safe_load(open('scenarios/templates/s2_hard.yaml'))"
```
Expected: exits 0 with no output.

Sanity diff:
```bash
diff scenarios/templates/s1_typical.yaml scenarios/templates/s2_hard.yaml | head -200
```
Expected: diff lines should be confined to `template_meta`, `boundary_feature_families[0]` (sink_T/h), `physics.background_boundary_cooling`, `placement_hint` on c02/c04/c06/c12, `total_power` on c02/c04/c06/c12, and the entire `generation_rules.layout_strategy` block. Any other drift means a copy error — revert and retry.

- [ ] **Step 9: Commit**

```bash
git add scenarios/templates/s2_hard.yaml
git commit -m "feat(scenarios): add s2_hard template with weakened sink, amplified power-dense modules, and adversarial-core zone"
```

---

## Task 2: Teach `layout_engine` About `adversarial_core` Zone

**Files:**
- Modify: `core/generator/layout_engine.py:373-395` (`_strategy_regions_for_profile`)
- Test: `tests/generator/test_layout_engine.py` (append new tests)

**Why:** Spec §9 says the `s2_adversarial_v1` layout strategy must route `bottom_band` placements through the new `adversarial_core` zone. The current implementation at `core/generator/layout_engine.py:389-390` derives a bottom band from `active_deck`+`dense_core` via `_strategy_bottom_band`. We want: if an explicit `adversarial_core` zone is defined, use it; otherwise preserve existing derived behavior so `s1_typical` is untouched.

- [ ] **Step 1: Write the failing test — `adversarial_core` zone is used when present**

Append to `tests/generator/test_layout_engine.py`:

```python
def test_strategy_regions_for_profile_prefers_adversarial_core_for_bottom_band() -> None:
    from core.generator.layout_engine import _strategy_regions_for_profile

    layout_strategy = {
        "kind": "s2_adversarial_v1",
        "zones": {
            "active_deck": {"x_min": 0.08, "x_max": 0.92, "y_min": 0.08, "y_max": 0.68},
            "adversarial_core": {"x_min": 0.15, "x_max": 0.85, "y_min": 0.10, "y_max": 0.35},
            "top_sink_band": {"x_min": 0.20, "x_max": 0.80, "y_min": 0.55, "y_max": 0.68},
        },
    }
    profile = {"placement_hint": "bottom_band"}
    regions = _strategy_regions_for_profile(layout_strategy, profile)

    assert len(regions) == 1
    assert regions[0] == {"x_min": 0.15, "x_max": 0.85, "y_min": 0.10, "y_max": 0.35}


def test_strategy_regions_for_profile_falls_back_to_derived_bottom_band_without_adversarial_core() -> None:
    from core.generator.layout_engine import _strategy_regions_for_profile

    layout_strategy = {
        "kind": "legacy_aligned_dense_core_v1",
        "zones": {
            "active_deck": {"x_min": 0.12, "x_max": 0.88, "y_min": 0.10, "y_max": 0.67},
            "dense_core": {"x_min": 0.22, "x_max": 0.78, "y_min": 0.17, "y_max": 0.56},
        },
    }
    profile = {"placement_hint": "bottom_band"}
    regions = _strategy_regions_for_profile(layout_strategy, profile)

    assert len(regions) == 1
    region = regions[0]
    assert region["x_min"] > 0.12 - 1e-6
    assert region["x_max"] < 0.88 + 1e-6
    assert region["y_min"] < region["y_max"]
```

- [ ] **Step 2: Run the new tests to verify they fail correctly**

Run:
```bash
conda run -n msfenicsx pytest -v tests/generator/test_layout_engine.py::test_strategy_regions_for_profile_prefers_adversarial_core_for_bottom_band tests/generator/test_layout_engine.py::test_strategy_regions_for_profile_falls_back_to_derived_bottom_band_without_adversarial_core
```
Expected: `test_strategy_regions_for_profile_prefers_adversarial_core_for_bottom_band` FAILS (the returned region is the derived `_strategy_bottom_band`, not `adversarial_core`). The fallback test PASSES already.

- [ ] **Step 3: Implement the minimal change**

Edit `core/generator/layout_engine.py`, inside `_strategy_regions_for_profile`. Find the current `bottom_band` branch at line 389-390:

```python
    elif placement_hint == "bottom_band":
        candidates = [_strategy_bottom_band(zones)]
```

Replace it with:

```python
    elif placement_hint == "bottom_band":
        adversarial_core = zones.get("adversarial_core")
        if adversarial_core is not None:
            candidates = [adversarial_core]
        else:
            candidates = [_strategy_bottom_band(zones)]
```

Do not change any other branch in this function. `center_mass` already handles missing `dense_core` via the `None`-filtering return at the bottom of the function — no edit needed there.

- [ ] **Step 4: Run the new tests and the full existing `test_layout_engine.py`**

Run:
```bash
conda run -n msfenicsx pytest -v tests/generator/test_layout_engine.py
```
Expected: all tests PASS, including the three pre-existing `s1_typical` layout tests (placement, v3 anchor families, sink-aware band grouping).

- [ ] **Step 5: Commit**

```bash
git add core/generator/layout_engine.py tests/generator/test_layout_engine.py
git commit -m "feat(generator): route bottom_band placements through adversarial_core zone when present"
```

---

## Task 3: Focused Integration Test for `s2_hard` Template

**Files:**
- Create: `tests/generator/test_s2_hard_template.py`

**What this test proves:** The template loads through the real `load_template_model` path, `place_components` produces fifteen non-overlapping in-domain components, and the four amplified power-dense modules (`c02/c04/c06/c12`) land inside the `adversarial_core` zone `[0.15, 0.85] × [0.10, 0.35]`.

- [ ] **Step 1: Write the failing test**

Create `tests/generator/test_s2_hard_template.py`:

```python
import pytest

from core.generator.layout_engine import place_components
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.geometry.layout_rules import component_within_domain, components_overlap


TEMPLATE_PATH = "scenarios/templates/s2_hard.yaml"
ADVERSARIAL_CORE = {"x_min": 0.15, "x_max": 0.85, "y_min": 0.10, "y_max": 0.35}
POWER_DENSE_FAMILIES = ("c02", "c04", "c06", "c12")


def test_s2_hard_template_loads_with_expected_identity() -> None:
    template = load_template_model(TEMPLATE_PATH)
    assert template.template_meta["template_id"] == "s2_hard"
    assert len(template.component_families) == 15


def test_s2_hard_template_generates_fifteen_legal_components_for_seed_11() -> None:
    template = load_template_model(TEMPLATE_PATH)
    sampled = sample_template_parameters(template, seed=11)

    placed = place_components(template=template, sampled_components=sampled["components"], seed=11)

    assert len(placed) == 15
    assert all(component_within_domain(c, template.panel_domain) for c in placed)
    for index, component in enumerate(placed):
        for other in placed[index + 1 :]:
            assert not components_overlap(component, other), (
                f"overlap between {component['component_id']} and {other['component_id']}"
            )


def test_s2_hard_power_dense_families_land_inside_adversarial_core() -> None:
    template = load_template_model(TEMPLATE_PATH)
    sampled = sample_template_parameters(template, seed=11)

    placed = place_components(template=template, sampled_components=sampled["components"], seed=11)
    by_family = {c["family_id"]: c for c in placed}

    for family_id in POWER_DENSE_FAMILIES:
        x = float(by_family[family_id]["pose"]["x"])
        y = float(by_family[family_id]["pose"]["y"])
        assert ADVERSARIAL_CORE["x_min"] - 0.05 <= x <= ADVERSARIAL_CORE["x_max"] + 0.05, (
            f"{family_id} x={x} outside adversarial_core x-band"
        )
        assert ADVERSARIAL_CORE["y_min"] - 0.02 <= y <= ADVERSARIAL_CORE["y_max"] + 0.05, (
            f"{family_id} y={y} outside adversarial_core y-band"
        )


def test_s2_hard_load_rules_amplified_totals_match_spec() -> None:
    template = load_template_model(TEMPLATE_PATH)
    by_target = {rule["target_family"]: rule for rule in template.load_rules}
    assert by_target["c02"]["total_power"] == pytest.approx(20.0)
    assert by_target["c04"]["total_power"] == pytest.approx(19.0)
    assert by_target["c06"]["total_power"] == pytest.approx(18.0)
    assert by_target["c12"]["total_power"] == pytest.approx(16.0)
    # sanity: other eleven totals unchanged from s1_typical
    assert by_target["c01"]["total_power"] == pytest.approx(8.5)
    assert by_target["c05"]["total_power"] == pytest.approx(6.5)
    assert by_target["c15"]["total_power"] == pytest.approx(3.5)
```

- [ ] **Step 2: Run the tests**

Run:
```bash
conda run -n msfenicsx pytest -v tests/generator/test_s2_hard_template.py
```
Expected: all four tests PASS.

If `test_s2_hard_power_dense_families_land_inside_adversarial_core` fails because a component slightly overruns the `adversarial_core` bounds due to bounding-box math (the pose is the polygon centroid; hint regions are clamped by the half-widths), widen the `+ 0.05` tolerance — the test is checking the engine routed placements into the adversarial zone, not pixel-perfect containment.

- [ ] **Step 3: Also run the CLI template validator**

Run:
```bash
conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s2_hard.yaml
```
Expected: exits 0 and prints no errors (matches the `s1_typical` validation baseline).

- [ ] **Step 4: Commit**

```bash
git add tests/generator/test_s2_hard_template.py
git commit -m "test(generator): verify s2_hard template loads, places 15 components, and routes power-dense modules into adversarial_core"
```

---

## Task 4: Baseline Dry-Run Calibration Gate

**Files:** none created; this is a verification gate.

**Goal:** Confirm the generator + solver produce a baseline layout and thermal solve that land inside the acceptance bands from spec §10. If not, adjust sink / power parameters in `scenarios/templates/s2_hard.yaml` and repeat until the bands are met. This gate protects against the Risk 1 and Risk 2 items in the spec.

- [ ] **Step 1: Generate the seed-11 case**

Run:
```bash
conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s2_hard.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s2_hard/seed-11
```
Expected: exits 0; a `s2_hard-seed-0011.yaml` file appears under `./scenario_runs/generated_cases/s2_hard/seed-11/`.

- [ ] **Step 2: Solve the generated case**

Run:
```bash
conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s2_hard/seed-11/s2_hard-seed-0011.yaml --output-root ./scenario_runs
```
Expected: exits 0; writes a bundle under `./scenario_runs/s2_hard/s2_hard-seed-0011/` containing `case.yaml`, `solution.yaml`, `fields/*.npz`, `summaries/field_view.json`.

- [ ] **Step 3: Inspect the baseline solve against acceptance bands**

Run:
```bash
conda run -n msfenicsx python - <<'PY'
import yaml
from pathlib import Path

bundle = Path("scenario_runs/s2_hard/s2_hard-seed-0011")
solution = yaml.safe_load((bundle / "solution.yaml").read_text())
case = yaml.safe_load((bundle / "case.yaml").read_text())

summary_metrics = solution["summary_metrics"]
t_max = float(summary_metrics["temperature_max"])
t_min = float(summary_metrics["temperature_min"])
grad_rms = float(summary_metrics["temperature_gradient_rms"])
print(f"T_max           = {t_max:.2f} K (band 330-343)")
print(f"T_min           = {t_min:.2f} K")
print(f"T_span          = {t_max - t_min:.2f} K (band 22-33)")
print(f"grad_rms        = {grad_rms:.2f}")

total_radiator_span = sum(
    float(f["end"]) - float(f["start"])
    for f in case.get("boundary_features", [])
    if f.get("kind") == "line_sink"
)
print(f"radiator_span   = {total_radiator_span:.3f} (needs >= 0.33)")

by_id = {c["component_id"]: c for c in solution["component_summaries"]}
for cid in ("c02-001", "c04-001", "c06-001", "c12-001", "c01-001", "c08-001"):
    peak = float(by_id[cid]["temperature_max"])
    print(f"{cid} peak = {peak:.2f} K")
PY
```

Expected values (spec §10):
- `T_max` in `[330, 343]` K
- `T_span` in `[22, 33]` K
- `radiator_span >= 0.33`
- `c02-001 peak` in `[321, 330]` K
- Other component peaks below their 330 K limits

- [ ] **Step 4: If outside bands, adjust and iterate**

If `T_max` is too low (< 330 K): increase the four `c02/c04/c06/c12` powers by ~10% or reduce `sink_transfer_coefficient` from `5.0` toward `4.0`, re-run Steps 1-3.

If `T_max` is too high (> 343 K): reduce the four powers by ~10% or increase `sink_transfer_coefficient` toward `6.0`, re-run.

If only `c02-001 peak` is outside `[321, 330]`: adjust `c02`'s `total_power` (currently 20.0 W) by ±1 W, re-run.

If `radiator_span < 0.33`: the seed-11 sample is unlucky; extend the sink `span.min` from `0.31` to `0.33` so seed 11 lands above `0.33`.

**Do not** modify the eight evaluation-spec constraint limits (those come in Task 5) to force the baseline into the band. The constraints define "hard" — the template must meet them, not vice versa.

- [ ] **Step 5: Commit the final calibrated template (only if changes were made)**

If any template edits were needed:
```bash
git add scenarios/templates/s2_hard.yaml
git commit -m "calibrate(scenarios): tune s2_hard baseline to spec acceptance bands on seed 11"
```
If no edits were needed, skip this step.

---

## Task 5: Create `s2_hard_eval.yaml`

**Files:**
- Create: `scenarios/evaluation/s2_hard_eval.yaml`

- [ ] **Step 1: Write the file**

Create `scenarios/evaluation/s2_hard_eval.yaml`:

```yaml
schema_version: "1.0"
spec_meta:
  spec_id: s2_hard_eval
  description: Single-case evaluation spec for the S2 hard paper-facing baseline. Tightened radiator-span budget and c02 peak make the baseline violate exactly two constraints drawn from disjoint operator categories.
objectives:
  - objective_id: minimize_peak_temperature
    metric: summary.temperature_max
    sense: minimize
  - objective_id: minimize_temperature_gradient_rms
    metric: summary.temperature_gradient_rms
    sense: minimize
constraints:
  - constraint_id: radiator_span_budget
    metric: case.total_radiator_span
    relation: "<="
    limit: 0.32
  - constraint_id: c02_peak_temperature_limit
    metric: component.c02-001.temperature_max
    relation: "<="
    limit: 320.0
  - constraint_id: c04_peak_temperature_limit
    metric: component.c04-001.temperature_max
    relation: "<="
    limit: 330.0
  - constraint_id: c06_peak_temperature_limit
    metric: component.c06-001.temperature_max
    relation: "<="
    limit: 330.0
  - constraint_id: c12_peak_temperature_limit
    metric: component.c12-001.temperature_max
    relation: "<="
    limit: 330.0
  - constraint_id: c01_peak_temperature_limit
    metric: component.c01-001.temperature_max
    relation: "<="
    limit: 330.0
  - constraint_id: c08_peak_temperature_limit
    metric: component.c08-001.temperature_max
    relation: "<="
    limit: 330.0
  - constraint_id: panel_temperature_spread_limit
    metric: components.max_temperature_spread
    relation: "<="
    limit: 35.0
```

- [ ] **Step 2: Evaluate the Task-4 dry-run solution against this spec**

Run:
```bash
conda run -n msfenicsx python -m evaluation.cli evaluate-case \
    --case ./scenario_runs/s2_hard/s2_hard-seed-0011/case.yaml \
    --solution ./scenario_runs/s2_hard/s2_hard-seed-0011/solution.yaml \
    --spec scenarios/evaluation/s2_hard_eval.yaml \
    --output ./scenario_runs/s2_hard/s2_hard-seed-0011/evaluation_report.yaml \
    --bundle-root ./scenario_runs/s2_hard/s2_hard-seed-0011
```
Expected: exits 0; produces an evaluation report.

- [ ] **Step 3: Verify exactly two constraints are violated**

Run:
```bash
conda run -n msfenicsx python - <<'PY'
import yaml
report = yaml.safe_load(open("scenario_runs/s2_hard/s2_hard-seed-0011/evaluation_report.yaml"))
print(f"feasible: {report['feasible']}")
violations = report["violations"]
print(f"Total violations: {len(violations)}")
for v in violations:
    print(f"  {v['constraint_id']}: actual={v['actual']:.4f} limit={v['limit']:.4f} margin={v['margin']:.4f}")
assert report["feasible"] is False, "baseline must be infeasible"
assert len(violations) == 2, f"expected exactly 2 violations, got {len(violations)}"
ids = {v["constraint_id"] for v in violations}
assert ids == {"radiator_span_budget", "c02_peak_temperature_limit"}, ids
PY
```
Expected: assertion passes. If not, iterate on Task 4 (calibration); if only off by ±1 violation, check whether `c04_peak_temperature_limit` or `panel_temperature_spread_limit` is right on the edge and whether the spec band still allows the scenario to be usable.

- [ ] **Step 4: Commit**

```bash
git add scenarios/evaluation/s2_hard_eval.yaml
git commit -m "feat(scenarios): add s2_hard evaluation spec with tightened radiator-span budget and c02 peak limit"
```

---

## Task 6: Create NSGA-II Profile Files for `s2_hard`

**Files:**
- Create: `scenarios/optimization/profiles/s2_hard_raw.yaml`
- Create: `scenarios/optimization/profiles/s2_hard_union.yaml`

**Why separate task:** profile paths are referenced from the optimization specs in Task 7; build them first.

- [ ] **Step 1: Create the raw profile**

Create `scenarios/optimization/profiles/s2_hard_raw.yaml`:

```yaml
schema_version: "1.0"
profile_meta:
  profile_id: s2_hard_nsga2_raw_profile
  description: Active S2 hard tuning for NSGA-II raw variation. Parameters mirror s1_typical_raw profile so the benchmark-vs-benchmark comparison reflects scenario difficulty, not algorithm tuning.
family: genetic
backbone: nsga2
mode: raw
parameters:
  crossover:
    eta: 10
    prob: 0.9
  mutation:
    eta: 15
```

- [ ] **Step 2: Create the union profile**

Create `scenarios/optimization/profiles/s2_hard_union.yaml`:

```yaml
schema_version: "1.0"
profile_meta:
  profile_id: s2_hard_nsga2_union_profile
  description: Active S2 hard tuning for NSGA-II union variation. Parameters mirror s1_typical_union profile so the controller-ablation comparison reflects controller behavior, not algorithm tuning.
family: genetic
backbone: nsga2
mode: union
parameters:
  crossover:
    eta: 10
    prob: 0.9
  mutation:
    eta: 15
```

- [ ] **Step 3: Commit**

```bash
git add scenarios/optimization/profiles/s2_hard_raw.yaml scenarios/optimization/profiles/s2_hard_union.yaml
git commit -m "feat(scenarios): add s2_hard NSGA-II raw/union profiles mirroring s1_typical tuning"
```

---

## Task 7: Create Optimization Specs (`raw`, `union`, `llm`)

**Files:**
- Create: `scenarios/optimization/s2_hard_raw.yaml`
- Create: `scenarios/optimization/s2_hard_union.yaml`
- Create: `scenarios/optimization/s2_hard_llm.yaml`

**Invariant:** the `design_variables` list, the `operator_pool` list (for union/llm), and the llm `controller_parameters` block must be **identical** to the matching `s1_typical` files verbatim. Drift here breaks the ablation story. The only edits are path pointers and `spec_id` / `description`.

- [ ] **Step 1: Create `s2_hard_raw.yaml`**

Run:
```bash
cp scenarios/optimization/s1_typical_raw.yaml scenarios/optimization/s2_hard_raw.yaml
```

Edit the new file — change only:
- `spec_meta.spec_id` → `s2_hard_nsga2_raw`
- `spec_meta.description` → `S2 hard single-case NSGA-II raw baseline; same 32D encoding as s1_typical, different template and evaluation spec.`
- `benchmark_source.template_path` → `scenarios/templates/s2_hard.yaml`
- `algorithm.profile_path` → `scenarios/optimization/profiles/s2_hard_raw.yaml`
- `evaluation_protocol.evaluation_spec_path` → `scenarios/evaluation/s2_hard_eval.yaml`

Do not touch `benchmark_source.seed`, `design_variables`, or `algorithm.{family,backbone,mode,population_size,num_generations,seed}`.

Diff check:
```bash
diff scenarios/optimization/s1_typical_raw.yaml scenarios/optimization/s2_hard_raw.yaml
```
Expected: only the five lines listed above differ.

- [ ] **Step 2: Create `s2_hard_union.yaml`**

Run:
```bash
cp scenarios/optimization/s1_typical_union.yaml scenarios/optimization/s2_hard_union.yaml
```

Apply the same five edits as Step 1, substituting `union` for `raw`:
- `spec_meta.spec_id` → `s2_hard_nsga2_union`
- `spec_meta.description` → `S2 hard single-case NSGA-II union-uniform mode with shared native-plus-semantic action registry; identical operator pool to s1_typical_union.`
- `benchmark_source.template_path` → `scenarios/templates/s2_hard.yaml`
- `algorithm.profile_path` → `scenarios/optimization/profiles/s2_hard_union.yaml`
- `evaluation_protocol.evaluation_spec_path` → `scenarios/evaluation/s2_hard_eval.yaml`

Do not touch `operator_control.operator_pool` — all ten operator ids stay exactly as in `s1_typical_union.yaml`.

Diff check:
```bash
diff scenarios/optimization/s1_typical_union.yaml scenarios/optimization/s2_hard_union.yaml
```
Expected: only the five lines above differ.

- [ ] **Step 3: Create `s2_hard_llm.yaml`**

Run:
```bash
cp scenarios/optimization/s1_typical_llm.yaml scenarios/optimization/s2_hard_llm.yaml
```

Apply the same five edits:
- `spec_meta.spec_id` → `s2_hard_nsga2_llm`
- `spec_meta.description` → `S2 hard single-case NSGA-II union-llm mode with the same shared mixed action registry as s1_typical_llm and an OpenAI-compatible controller.`
- `benchmark_source.template_path` → `scenarios/templates/s2_hard.yaml`
- `algorithm.profile_path` → `scenarios/optimization/profiles/s2_hard_union.yaml` (llm shares the union profile; same pattern as `s1_typical_llm.yaml`)
- `evaluation_protocol.evaluation_spec_path` → `scenarios/evaluation/s2_hard_eval.yaml`

Do not touch `operator_control.operator_pool`, `operator_control.controller`, or `operator_control.controller_parameters`. The controller binary configuration must match `s1_typical_llm.yaml` so cross-scenario comparisons stay clean.

Diff check:
```bash
diff scenarios/optimization/s1_typical_llm.yaml scenarios/optimization/s2_hard_llm.yaml
```
Expected: only the five lines above differ.

- [ ] **Step 4: Verify all three parse**

Run:
```bash
conda run -n msfenicsx python - <<'PY'
import yaml
for name in ("s2_hard_raw.yaml", "s2_hard_union.yaml", "s2_hard_llm.yaml"):
    data = yaml.safe_load(open(f"scenarios/optimization/{name}"))
    assert data["benchmark_source"]["template_path"] == "scenarios/templates/s2_hard.yaml", name
    assert data["evaluation_protocol"]["evaluation_spec_path"] == "scenarios/evaluation/s2_hard_eval.yaml", name
    print(f"{name}: ok ({data['spec_meta']['spec_id']})")
PY
```
Expected: all three print `ok`.

- [ ] **Step 5: Commit**

```bash
git add scenarios/optimization/s2_hard_raw.yaml scenarios/optimization/s2_hard_union.yaml scenarios/optimization/s2_hard_llm.yaml
git commit -m "feat(scenarios): add s2_hard optimization specs for raw/union/llm (identical design vars and operator pool to s1_typical)"
```

---

## Task 8: Smoke Optimization Runs

**Files:** none created; writes run bundles under `scenario_runs/s2_hard/`.

**Purpose:** Confirm each mode runs end-to-end on `s2_hard` at a tiny budget without crashing and writes the expected run artifacts.

- [ ] **Step 1: Smoke `raw` at budget 10×5**

Run:
```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
    --optimization-spec scenarios/optimization/s2_hard_raw.yaml \
    --evaluation-workers 2 \
    --population-size 10 \
    --num-generations 5 \
    --skip-render \
    --output-root ./scenario_runs/s2_hard/smoke-raw
```
Expected: exits 0. Under `./scenario_runs/s2_hard/smoke-raw/` there is an `opt-R/` (or equivalent) subdirectory with `run.yaml`, `controller_trace.json`, `operator_trace.json`, and a `traces/` directory containing the JSONL sidecars.

- [ ] **Step 2: Smoke `union` at budget 10×5**

Run:
```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
    --optimization-spec scenarios/optimization/s2_hard_union.yaml \
    --evaluation-workers 2 \
    --population-size 10 \
    --num-generations 5 \
    --skip-render \
    --output-root ./scenario_runs/s2_hard/smoke-union
```
Expected: exits 0, same artifact layout. `operator_trace.json` should contain events drawn from the full ten-operator pool.

- [ ] **Step 3: Smoke `llm` at budget 10×5 (requires `.env` credentials)**

Run:
```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
    --optimization-spec scenarios/optimization/s2_hard_llm.yaml \
    --evaluation-workers 2 \
    --population-size 10 \
    --num-generations 5 \
    --skip-render \
    --output-root ./scenario_runs/s2_hard/smoke-llm
```
Expected: exits 0. `llm_metrics.json` and the `traces/llm_request_trace.jsonl` / `traces/llm_response_trace.jsonl` sidecars exist and are non-empty.

If the llm smoke fails because credentials are not configured, document that `.env` must contain `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` (or a provider profile such as `GPT_PROXY_*`); then re-run.

- [ ] **Step 4: Quick sanity — confirm artifacts name `s2_hard`**

Run:
```bash
ls scenario_runs/s2_hard/smoke-raw/ scenario_runs/s2_hard/smoke-union/ scenario_runs/s2_hard/smoke-llm/
```
Expected: each directory exists and contains per-mode subdirectory structure matching existing `s1_typical` smoke runs.

- [ ] **Step 5: Smoke-run output is scratch and not committed**

Add the smoke output to a local ignore if it is not already covered by `.gitignore`:
```bash
git status scenario_runs/s2_hard/ | head -5
```
If any of `scenario_runs/s2_hard/smoke-*` is reported as untracked and the repo does not already gitignore `scenario_runs/`, leave it uncommitted — smoke outputs are scratch.

No commit in this task.

---

## Task 9: Update Live Docs To Reflect `s2_hard` As Implemented

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`

**Why:** `CLAUDE.md`, `AGENTS.md`, and `README.md` currently list `s2_hard` as "approved-but-pending-implementation". After Tasks 1-8 land, promote it to an implemented, active benchmark. Archive docs and historical reports stay untouched.

- [ ] **Step 1: Update `CLAUDE.md`**

Replace the paragraph starting `- A harder companion benchmark \`s2_hard\` is approved per ...` with:

```markdown
- The second paper-facing mainline `s2_hard` is implemented per `docs/superpowers/specs/2026-04-17-s2-hard-design.md`. It shares the semantic shared operator registry and the same `raw / union / llm` ladder as `s1_typical`, but its baseline violates exactly two constraints from disjoint operator categories (`radiator_span_budget` + `c02_peak_temperature_limit`) to force state-dependent operator selection.
```

Under `The implemented paper-facing inputs are:` list, move the five `s2_hard` entries from the pending section into the implemented section, and delete the `Approved-but-not-yet-implemented` block.

- [ ] **Step 2: Apply the same changes to `AGENTS.md`**

`AGENTS.md` carries the same wording as `CLAUDE.md` in the `## Repository Status` and "active paper-facing inputs" sections. Apply the identical edit.

- [ ] **Step 3: Update `README.md`**

In the `## Active Mainline` section of `README.md`, replace the "approved per ... pending implementation" sentence with:

```markdown
The paper-facing mainlines are `s1_typical` (the easy baseline-feasible reference) and `s2_hard` (the harder baseline-infeasible companion). Both use the same semantic shared operator registry and the same `raw / union / llm` ladder; see `docs/superpowers/specs/2026-04-17-s2-hard-design.md` for scenario differences.
```

In the `## Active Inputs` section, replace the `Implemented (s1_typical):` / `Approved-but-pending-implementation (s2_hard, ...):` split with a single combined listing that presents both scenarios side by side.

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md AGENTS.md
git commit -m "docs: promote s2_hard to active paper-facing mainline after implementation"
```

---

## Follow-Up (Out Of Scope For This Plan)

These items live downstream of this plan and must be tracked separately. They are explicitly **not** tasks here because they are experiment execution, not implementation:

1. **Full budget-matched seed-11 runs** for each mode at population 20 × generations 10 (201 evals) on `s2_hard`, mirroring the existing `s1_typical` paper-facing runs. Required to reach Risk 2 (reachability) resolution. Gate: llm reaches ≥ 70% feasibility by eval 200 on seed 11.
2. **Multi-seed variance** across at least three algorithm seeds for `s2_hard` llm + union.
3. **Operator-attribution check (Risk 4)** — join `traces/operator_trace.jsonl` ↔ `traces/evaluation_events.jsonl` on at least one `s2_hard` llm run and confirm that evaluations improving `radiator_span_budget` are driven disproportionately by `repair_sink_budget` / `slide_sink` and that evaluations improving `c02-001.temperature_max` are driven disproportionately by `move_hottest_cluster_toward_sink` / `spread_hottest_cluster`.
4. **Paper narrative C3 update** — once validation clears, update the paper section on `s2_hard` to present objective-function dominance alongside feasibility-rate dominance.

These four items become their own planning exercise after this plan's artifacts land.

---

## Total Commits Expected

- Task 1: 1 (template)
- Task 2: 1 (generator code + tests)
- Task 3: 1 (template integration tests)
- Task 4: 0 or 1 (only if calibration adjustments were needed)
- Task 5: 1 (evaluation spec)
- Task 6: 1 (profiles)
- Task 7: 1 (optimization specs)
- Task 8: 0 (smoke scratch)
- Task 9: 1 (docs)

Total: 7-8 commits on `main` or on a feature branch, whichever the team chooses.
