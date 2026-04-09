# S1 Typical Density And Thermal Calibration V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recalibrate the active `s1_typical` benchmark so it uses a `component_area_ratio` target around `0.45`, enforces real minimum gaps in both generation and optimization, gives all fifteen components explicit localized waste-heat footprints, and adds weak ambient outer-boundary cooling without changing the paper-facing optimizer contract.

**Architecture:** Keep the active `s1_typical -> repair -> cheap constraints -> solve -> evaluate -> representative bundle` pipeline intact. Put the new realism into the template contract, generator scoring, shared legality helpers, and moderate solver physics, then surface the new density and ambient signals through evaluation and page rendering. Do not add optimizer-side family windows, new objectives, or new constraints.

**Tech Stack:** Python 3, YAML scenario templates, FEniCSx, Shapely, PyYAML, Pytest

---

## File Map

**Template and schema contract**

- Modify: `scenarios/templates/s1_typical.yaml`
- Modify: `core/schema/models.py`
- Modify: `core/schema/validation.py`
- Modify: `core/generator/case_builder.py`

**Layout density and generation**

- Modify: `core/generator/layout_engine.py`
- Modify: `core/generator/layout_metrics.py`
- Modify: `core/generator/parameter_sampler.py`

**Shared legality and optimizer repair**

- Modify: `core/geometry/layout_rules.py`
- Modify: `optimizers/cheap_constraints.py`
- Modify: `optimizers/repair.py`

**Solver interpretation and ambient boundary physics**

- Modify: `core/solver/case_to_geometry.py`
- Modify: `core/solver/physics_builder.py`

**Evaluation and visualization**

- Modify: `evaluation/metrics.py`
- Modify: `visualization/case_pages.py`

**Tests**

- Modify: `tests/schema/test_s1_typical_template.py`
- Modify: `tests/schema/test_schema_validation.py`
- Modify: `tests/generator/test_layout_engine.py`
- Modify: `tests/generator/test_layout_metrics.py`
- Modify: `tests/optimizers/test_cheap_constraints.py`
- Modify: `tests/optimizers/test_repair.py`
- Modify: `tests/solver/test_case_to_geometry.py`
- Modify: `tests/solver/test_generated_case.py`
- Modify: `tests/evaluation/test_engine.py`
- Modify: `tests/visualization/test_case_pages.py`

**Docs**

- Modify: `README.md`

## Task 1: Lock The Template And Physics Contract

**Files:**
- Modify: `core/schema/models.py`
- Modify: `core/schema/validation.py`
- Modify: `core/generator/case_builder.py`
- Modify: `scenarios/templates/s1_typical.yaml`
- Test: `tests/schema/test_s1_typical_template.py`
- Test: `tests/schema/test_schema_validation.py`

- [ ] **Step 1: Write the failing template-shape tests**

```python
def test_s1_typical_template_declares_source_area_ratio_for_all_families() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    source_ratios = {
        rule["target_family"]: rule.get("source_area_ratio")
        for rule in payload["load_rules"]
    }

    assert source_ratios.keys() == {f"c{i:02d}" for i in range(1, 16)}
    assert all(source_ratios[family_id] is not None for family_id in source_ratios)


def test_s1_typical_template_declares_explicit_background_boundary_cooling() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    physics = payload["physics"]
    background = physics["background_boundary_cooling"]

    assert physics["ambient_temperature"] > 0.0
    assert background["transfer_coefficient"] > 0.0
    assert 0.0 < background["emissivity"] <= 1.0
```

- [ ] **Step 2: Run the template tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s1_typical_template.py -k "source_area_ratio_for_all_families or background_boundary_cooling" -v`

Expected: FAIL because the current template only gives `source_area_ratio` to a subset of families and does not declare a `physics.background_boundary_cooling` block.

- [ ] **Step 3: Write the failing schema-validation tests**

```python
def test_validate_scenario_template_accepts_background_boundary_cooling() -> None:
    payload = _base_template_payload()
    payload["physics"] = {
        "kind": "steady_heat_radiation",
        "ambient_temperature": 292.0,
        "background_boundary_cooling": {
            "transfer_coefficient": 1.2,
            "emissivity": 0.72,
        },
    }
    payload["load_rules"] = [
        {"target_family": "c01", "total_power": 8.0, "source_area_ratio": 0.35}
    ]

    validate_scenario_template_payload(payload)


def test_validate_scenario_template_rejects_invalid_background_boundary_emissivity() -> None:
    payload = _base_template_payload()
    payload["physics"] = {
        "kind": "steady_heat_radiation",
        "ambient_temperature": 292.0,
        "background_boundary_cooling": {
            "transfer_coefficient": 1.2,
            "emissivity": 1.5,
        },
    }

    with pytest.raises(SchemaValidationError, match="background_boundary_cooling"):
        validate_scenario_template_payload(payload)
```

- [ ] **Step 4: Run the schema-validation tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_schema_validation.py -k "background_boundary" -v`

Expected: FAIL because `ScenarioTemplate` does not currently accept `physics` and the validator does not know the background-cooling block.

- [ ] **Step 5: Implement the template physics contract**

```python
@dataclass(slots=True)
class ScenarioTemplate:
    schema_version: str
    template_meta: dict[str, Any]
    coordinate_system: dict[str, Any]
    panel_domain: dict[str, Any]
    placement_regions: list[dict[str, Any]]
    keep_out_regions: list[dict[str, Any]]
    component_families: list[dict[str, Any]]
    boundary_feature_families: list[dict[str, Any]]
    load_rules: list[dict[str, Any]]
    material_rules: list[dict[str, Any]]
    physics: dict[str, Any]
    mesh_profile: dict[str, Any]
    solver_profile: dict[str, Any]
    generation_rules: dict[str, Any]
```

```python
def _validate_background_boundary_cooling(payload: Any, label: str) -> None:
    _require_mapping(payload, label)
    _require_positive_real(payload.get("transfer_coefficient"), f"{label}.transfer_coefficient")
    emissivity = _require_real(payload.get("emissivity"), f"{label}.emissivity")
    if not 0.0 < emissivity <= 1.0:
        raise SchemaValidationError(f"{label}.emissivity must satisfy 0 < value <= 1.")
```

```python
physics_payload = dict(template.physics)
payload["physics"] = physics_payload
```

- [ ] **Step 6: Update the hand-authored template**

```yaml
physics:
  kind: steady_heat_radiation
  ambient_temperature: 292.0
  background_boundary_cooling:
    transfer_coefficient: 1.2
    emissivity: 0.72
```

```yaml
load_rules:
  - target_family: c01
    total_power: 10.0
    source_area_ratio: 0.30
  - target_family: c02
    total_power: 13.5
    source_area_ratio: 0.14
```

Add a `source_area_ratio` entry for every family from `c01` through `c15`.

- [ ] **Step 7: Run the schema tests to verify they pass**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s1_typical_template.py tests/schema/test_schema_validation.py -v`

Expected: PASS with the new template contract and background-cooling validation accepted.

- [ ] **Step 8: Commit the contract changes**

```bash
git add core/schema/models.py core/schema/validation.py core/generator/case_builder.py scenarios/templates/s1_typical.yaml tests/schema/test_s1_typical_template.py tests/schema/test_schema_validation.py
git commit -m "feat: add s1_typical density and ambient physics contract"
```

## Task 2: Recalibrate Density And Generation Compactness

**Files:**
- Modify: `scenarios/templates/s1_typical.yaml`
- Modify: `core/generator/layout_engine.py`
- Modify: `core/generator/layout_metrics.py`
- Modify: `core/generator/parameter_sampler.py`
- Test: `tests/generator/test_layout_engine.py`
- Test: `tests/generator/test_layout_metrics.py`

- [ ] **Step 1: Write the failing layout-density tests**

```python
def test_measure_layout_quality_reports_v3_density_targets() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11).to_dict()
    metrics = measure_layout_quality(case, placement_region=MAIN_DECK, active_deck=ACTIVE_DECK)

    assert metrics.component_area_ratio >= 0.44
    assert metrics.component_area_ratio <= 0.46
    assert metrics.bbox_fill_ratio >= 0.48


def test_layout_quality_is_stable_across_seed_sample_for_v3_density() -> None:
    ratios = []
    fill_ratios = []
    for seed in (11, 17, 23, 29, 31):
        case = generate_case("scenarios/templates/s1_typical.yaml", seed=seed).to_dict()
        metrics = measure_layout_quality(case, placement_region=MAIN_DECK, active_deck=ACTIVE_DECK)
        ratios.append(metrics.component_area_ratio)
        fill_ratios.append(metrics.bbox_fill_ratio)

    assert min(ratios) >= 0.44
    assert max(ratios) <= 0.46
    assert min(fill_ratios) >= 0.48
```

- [ ] **Step 2: Run the layout-metric tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_layout_metrics.py -v`

Expected: FAIL because the current geometry budget and zones still produce `component_area_ratio ~= 0.37`.

- [ ] **Step 3: Write the failing placement-behavior tests**

```python
def test_place_components_keeps_v3_anchor_families_inside_tighter_zones() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")
    sampled = sample_template_parameters(template, seed=11)
    placed_components = place_components(template=template, sampled_components=sampled["components"], seed=11)
    by_family = {component["family_id"]: component for component in placed_components}

    assert by_family["c12"]["pose"]["y"] >= 0.60
    assert by_family["c11"]["pose"]["x"] <= 0.17
    assert by_family["c08"]["pose"]["x"] >= 0.83
```

- [ ] **Step 4: Run the placement test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_layout_engine.py -k "v3_anchor_families" -v`

Expected: FAIL because the current zones and refinement weights still allow broader placement.

- [ ] **Step 5: Recalibrate template geometry, zones, and power tiers**

```yaml
placement_regions:
  - region_id: main-deck
    kind: rect
    x_min: 0.07
    x_max: 0.93
    y_min: 0.06
    y_max: 0.69
```

```yaml
generation_rules:
  layout_strategy:
    zones:
      active_deck:
        x_min: 0.12
        x_max: 0.88
        y_min: 0.10
        y_max: 0.67
      dense_core:
        x_min: 0.24
        x_max: 0.76
        y_min: 0.18
        y_max: 0.55
```

Scale component sizes selectively so the total footprint budget rises by about `8%~10%` while keeping the mixed shape inventory visually believable.

- [ ] **Step 6: Strengthen generator compactness scoring**

```python
penalty += 0.20 * _group_dispersion_penalty(components, family_profiles)
penalty += 0.55 * layout_metrics.nearest_neighbor_gap_mean
penalty += 1.80 * layout_metrics.largest_dense_core_void_ratio
penalty -= 0.80 * layout_metrics.bbox_fill_ratio
```

Keep the score generic. Do not add family-window logic. Do not add runtime optimizer penalties here.

- [ ] **Step 7: Run the generator tests to verify they pass**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_layout_engine.py tests/generator/test_layout_metrics.py -v`

Expected: PASS with the denser template and stronger compactness refinement.

- [ ] **Step 8: Commit the density-calibration changes**

```bash
git add scenarios/templates/s1_typical.yaml core/generator/layout_engine.py core/generator/layout_metrics.py core/generator/parameter_sampler.py tests/generator/test_layout_engine.py tests/generator/test_layout_metrics.py
git commit -m "feat: recalibrate s1_typical layout density"
```

## Task 3: Enforce Clearance In Cheap Constraints And Repair

**Files:**
- Modify: `core/geometry/layout_rules.py`
- Modify: `optimizers/cheap_constraints.py`
- Modify: `optimizers/repair.py`
- Test: `tests/optimizers/test_cheap_constraints.py`
- Test: `tests/optimizers/test_repair.py`

- [ ] **Step 1: Write the failing cheap-constraint tests**

```python
def test_problem_skips_pde_when_components_violate_clearance(monkeypatch: pytest.MonkeyPatch) -> None:
    base_case = _base_case()
    optimization_spec = _impossible_overlap_spec()
    evaluation_spec = load_spec(EVALUATION_SPEC_PATH)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec)
    vector = np.asarray([0.16, 0.16, 0.28, 0.16, 0.2, 0.65], dtype=np.float64)

    record, objective_vector, constraint_vector = problem.evaluate_vector(vector, source="optimizer")

    assert record["failure_reason"] == "cheap_constraint_violation"
    assert any("clearance_violation" in issue for issue in record["geometry_issues"])
```

- [ ] **Step 2: Run the cheap-constraint test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_cheap_constraints.py -k "clearance" -v`

Expected: FAIL because the current geometry issues only report direct overlap.

- [ ] **Step 3: Write the failing repair test**

```python
def test_repair_case_from_vector_restores_required_clearance_gap() -> None:
    case = _case()
    spec = _spec()
    vector = extract_decision_vector(case, spec)

    vector[0] = 0.22
    vector[1] = 0.22
    vector[2] = 0.33
    vector[3] = 0.22

    repaired = repair_case_from_vector(case, spec, np.asarray(vector, dtype=np.float64), radiator_span_max=RADIATOR_SPAN_MAX)

    left = repaired.components[0].to_dict() if hasattr(repaired.components[0], "to_dict") else repaired.components[0]
    right = repaired.components[1].to_dict() if hasattr(repaired.components[1], "to_dict") else repaired.components[1]
    assert required_clearance_gap(left, right, {"c01": 0.02, "c02": 0.02}) >= 0.0
```

- [ ] **Step 4: Run the repair test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_repair.py -k "required_clearance_gap" -v`

Expected: FAIL because repair only removes overlap and does not restore the required minimum gap.

- [ ] **Step 5: Add shared clearance helpers**

```python
def required_clearance_gap(component_a: dict[str, Any], component_b: dict[str, Any], clearance_by_family: Mapping[str, float]) -> float:
    clearance_a = float(clearance_by_family.get(str(component_a.get("family_id")), 0.0))
    clearance_b = float(clearance_by_family.get(str(component_b.get("family_id")), 0.0))
    required_gap = max(clearance_a, clearance_b)
    return component_polygon(component_a).distance(component_polygon(component_b)) - required_gap


def components_violate_clearance(component_a: dict[str, Any], component_b: dict[str, Any], clearance_by_family: Mapping[str, float]) -> bool:
    if components_overlap(component_a, component_b):
        return True
    return required_clearance_gap(component_a, component_b, clearance_by_family) < -1.0e-12
```

- [ ] **Step 6: Use the shared helper in cheap constraints and repair**

```python
if components_violate_clearance(left, right, clearance_by_family):
    issues.append(f"clearance_violation:{left['component_id']}:{right['component_id']}")
```

```python
shortfall = max(0.0, -required_clearance_gap(left, right, clearance_by_family))
shift = shortfall + REPAIR_EPSILON
```

Make `repair_case_payload_from_vector(...)` build `clearance_by_family` from the benchmark case and thread it through `_resolve_component_overlaps(...)` and `_restore_local_legality(...)`.

- [ ] **Step 7: Run the optimizer legality tests to verify they pass**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_cheap_constraints.py tests/optimizers/test_repair.py -v`

Expected: PASS with clearance-invalid layouts rejected before PDE solve and repaired layouts separated by the required minimum gap.

- [ ] **Step 8: Commit the legality changes**

```bash
git add core/geometry/layout_rules.py optimizers/cheap_constraints.py optimizers/repair.py tests/optimizers/test_cheap_constraints.py tests/optimizers/test_repair.py
git commit -m "feat: enforce clearance in optimizer legality"
```

## Task 4: Add Explicit Source Localization And Weak Ambient Boundary Cooling

**Files:**
- Modify: `core/solver/case_to_geometry.py`
- Modify: `core/solver/physics_builder.py`
- Modify: `tests/solver/test_case_to_geometry.py`
- Modify: `tests/solver/test_generated_case.py`

- [ ] **Step 1: Write the failing interpretation tests**

```python
def test_interpret_case_surfaces_background_boundary_cooling() -> None:
    payload = _case_with_source_ratio(0.25).to_dict()
    payload["physics"] = {
        "kind": "steady_heat_radiation",
        "ambient_temperature": 292.0,
        "background_boundary_cooling": {
            "transfer_coefficient": 1.2,
            "emissivity": 0.72,
        },
    }

    interpreted = interpret_case(ThermalCase.from_dict(payload))

    assert interpreted["ambient_temperature"] == pytest.approx(292.0)
    assert interpreted["background_boundary_cooling"]["transfer_coefficient"] == pytest.approx(1.2)
    assert interpreted["background_boundary_cooling"]["emissivity"] == pytest.approx(0.72)
```

- [ ] **Step 2: Run the interpretation test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/solver/test_case_to_geometry.py -k "background_boundary_cooling" -v`

Expected: FAIL because `interpret_case(...)` does not currently expose background-boundary settings.

- [ ] **Step 3: Write the failing generated-case thermal test**

```python
def test_generated_s1_typical_case_uses_explicit_localized_sources_and_ambient_background_cooling() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    interpreted = interpret_case(case)

    assert interpreted["ambient_temperature"] > 0.0
    assert interpreted["background_boundary_cooling"]["transfer_coefficient"] > 0.0
    assert len(interpreted["components"]) == 15
    assert all(component["total_power"] > 0.0 for component in interpreted["components"])
    assert all(component["source_area"] < component["area"] for component in interpreted["components"])
```

- [ ] **Step 4: Run the generated-case thermal test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/solver/test_generated_case.py -k "ambient_background_cooling" -v`

Expected: FAIL because not every family currently has an explicit localized source policy and the interpreted case has no background-boundary block.

- [ ] **Step 5: Extend solver interpretation**

```python
background_boundary = dict(physics.get("background_boundary_cooling", {}))

return {
    "panel_domain": payload["panel_domain"],
    "mesh_profile": payload["mesh_profile"],
    "solver_profile": payload["solver_profile"],
    "default_conductivity": float(panel_material["conductivity"]),
    "default_emissivity": float(panel_material.get("emissivity", 0.8)),
    "ambient_temperature": float(physics.get("ambient_temperature", 290.0)),
    "background_boundary_cooling": {
        "transfer_coefficient": float(background_boundary.get("transfer_coefficient", 0.0)),
        "emissivity": float(background_boundary.get("emissivity", panel_material.get("emissivity", 0.8))),
    },
    "components": components,
    "line_sinks": payload["boundary_features"],
}
```

- [ ] **Step 6: Add weak outer-boundary cooling in the variational form**

```python
background = solver_inputs["background_boundary_cooling"]
background_h = float(background["transfer_coefficient"])
background_emissivity = float(background["emissivity"])

if background_h > 0.0:
    residual += background_h * (temperature - ambient_temperature) * test_function * background_ds
if background_emissivity > 0.0:
    residual += background_emissivity * sigma * ((temperature**4) - (ambient_temperature**4)) * test_function * background_ds
```

Tag the background boundary as the outer-boundary complement of the named `line_sink` facets so the strong sink remains the dominant special boundary.

- [ ] **Step 7: Run the solver tests to verify they pass**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/solver/test_case_to_geometry.py tests/solver/test_generated_case.py -v`

Expected: PASS with all fifteen sources localized explicitly and ambient background cooling visible in interpreted solver inputs.

- [ ] **Step 8: Commit the solver-physics changes**

```bash
git add core/solver/case_to_geometry.py core/solver/physics_builder.py tests/solver/test_case_to_geometry.py tests/solver/test_generated_case.py
git commit -m "feat: add localized sources and ambient boundary cooling"
```

## Task 5: Surface Density, Gap, And Ambient Signals In Reports And Pages

**Files:**
- Modify: `evaluation/metrics.py`
- Modify: `visualization/case_pages.py`
- Modify: `tests/evaluation/test_engine.py`
- Modify: `tests/visualization/test_case_pages.py`

- [ ] **Step 1: Write the failing evaluation-derived-signal test**

```python
def test_evaluate_case_solution_surfaces_ambient_and_heat_source_signals() -> None:
    payload = _case_with_layout_metrics().to_dict()
    payload["physics"] = {
        "kind": "steady_heat_radiation",
        "ambient_temperature": 292.0,
        "background_boundary_cooling": {
            "transfer_coefficient": 1.2,
            "emissivity": 0.72,
        },
    }
    payload["loads"] = [
        {"load_id": f"load-{index}", "target_component_id": f"comp-{index:03d}", "total_power": 4.0}
        for index in range(1, 3)
    ]
    report = evaluate_case_solution(ThermalCase.from_dict(payload), _solution(), _spec())

    assert report.derived_signals["ambient_temperature"] == pytest.approx(292.0)
    assert report.derived_signals["background_boundary_transfer_coefficient"] == pytest.approx(1.2)
    assert report.derived_signals["active_heat_source_count"] == pytest.approx(2.0)
```

- [ ] **Step 2: Run the evaluation test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/evaluation/test_engine.py -k "ambient_and_heat_source_signals" -v`

Expected: FAIL because the current derived-signal builder only forwards layout metrics and hotspot information.

- [ ] **Step 3: Write the failing case-page test**

```python
def test_render_case_page_surfaces_background_cooling_and_heat_source_counts(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"
    output_path = render_case_page(representative_root)
    html = output_path.read_text(encoding="utf-8")

    assert "Ambient Temperature" in html
    assert "Background Boundary Cooling" in html
    assert "Active Heat Sources" in html
```

- [ ] **Step 4: Run the case-page test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/visualization/test_case_pages.py -k "background_cooling_and_heat_source_counts" -v`

Expected: FAIL because the current page only shows layout metrics and core solver metrics.

- [ ] **Step 5: Extend derived signals and page rows**

```python
physics = case_payload.get("physics", {})
background = dict(physics.get("background_boundary_cooling", {}))
derived["ambient_temperature"] = float(physics["ambient_temperature"])
derived["background_boundary_transfer_coefficient"] = float(background.get("transfer_coefficient", 0.0))
derived["background_boundary_emissivity"] = float(background.get("emissivity", 0.0))
derived["active_heat_source_count"] = float(
    sum(1 for load in case_payload.get("loads", []) if float(load.get("total_power", 0.0)) > 0.0)
)
```

```python
rows.extend(
    [
        ["Ambient Temperature", _format_scalar(case_payload["physics"].get("ambient_temperature"))],
        ["Background Boundary Cooling", _format_scalar(case_payload["physics"].get("background_boundary_cooling", {}).get("transfer_coefficient"))],
        ["Active Heat Sources", _format_scalar(len([load for load in case_payload.get("loads", []) if float(load.get("total_power", 0.0)) > 0.0]))],
    ]
)
```

- [ ] **Step 6: Run the reporting tests to verify they pass**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/evaluation/test_engine.py tests/visualization/test_case_pages.py -v`

Expected: PASS with ambient settings and heat-source count visible in reports and representative pages.

- [ ] **Step 7: Commit the reporting changes**

```bash
git add evaluation/metrics.py visualization/case_pages.py tests/evaluation/test_engine.py tests/visualization/test_case_pages.py
git commit -m "feat: surface density and ambient thermal diagnostics"
```

## Task 6: Refresh Docs And Run Focused End-To-End Validation

**Files:**
- Modify: `README.md`
- Verify: `scenarios/templates/s1_typical.yaml`
- Verify: `scenarios/evaluation/s1_typical_eval.yaml`
- Verify: `scenarios/optimization/s1_typical_raw.yaml`
- Verify: `scenarios/optimization/s1_typical_union.yaml`

- [ ] **Step 1: Update the README benchmark description**

```markdown
- `s1_typical` now targets `component_area_ratio ~= 0.45`, where the denominator is the official placement region rather than the full panel area.
- All fifteen components generate waste heat and use explicit source localization.
- The solver keeps the official top-edge sink and adds weak ambient outer-boundary cooling for background heat leakage.
```

- [ ] **Step 2: Run the full focused pytest set**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s1_typical_template.py tests/schema/test_schema_validation.py tests/generator/test_layout_engine.py tests/generator/test_layout_metrics.py tests/optimizers/test_cheap_constraints.py tests/optimizers/test_repair.py tests/solver/test_case_to_geometry.py tests/solver/test_generated_case.py tests/evaluation/test_engine.py tests/visualization/test_case_pages.py -v`

Expected: PASS across all touched subsystems.

- [ ] **Step 3: Validate the template through the CLI**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s1_typical.yaml`

Expected: PASS with no schema validation errors.

- [ ] **Step 4: Run one real generate/solve/evaluate cycle**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s1_typical.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s1_typical/seed-11`

Expected: writes `./scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml`

- [ ] **Step 5: Solve the generated case**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml --output-root ./scenario_runs`

Expected: PASS with a converged solution and a representative span in the intended `8~15 K` band.

- [ ] **Step 6: Evaluate the solved case**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/s1_typical/s1_typical-seed-0011/case.yaml --solution ./scenario_runs/s1_typical/s1_typical-seed-0011/solution.yaml --spec scenarios/evaluation/s1_typical_eval.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/s1_typical/s1_typical-seed-0011`

Expected: PASS with refreshed derived signals including layout density and ambient settings.

- [ ] **Step 7: Run raw and union smoke optimizations**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_raw.yaml --output-root ./scenario_runs/s1_typical/raw-smoke`

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_union.yaml --output-root ./scenario_runs/s1_typical/union-smoke`

Expected: PASS with cheap constraints rejecting clearance-invalid candidates before PDE solve and representative pages showing the updated density/ambient information.

- [ ] **Step 8: Commit docs and validation-adjusted fixtures**

```bash
git add README.md scenarios/templates/s1_typical.yaml tests/schema/test_s1_typical_template.py tests/schema/test_schema_validation.py tests/generator/test_layout_engine.py tests/generator/test_layout_metrics.py tests/optimizers/test_cheap_constraints.py tests/optimizers/test_repair.py tests/solver/test_case_to_geometry.py tests/solver/test_generated_case.py tests/evaluation/test_engine.py tests/visualization/test_case_pages.py
git commit -m "docs: document s1_typical v3 density and thermal calibration"
```

## Notes For The Implementer

- Keep `raw`, `union`, and `llm` optimization specs structurally unchanged.
- Do not add optimizer-side family windows or zone-restore logic.
- Do not turn `component_area_ratio` or `panel_fill_ratio` into a runtime optimizer penalty.
- Prefer one shared clearance helper in `core/geometry/layout_rules.py` instead of duplicating distance math across generator and optimizers.
- When tuning the template, keep shape diversity visible. The result should not look like a field of nearly identical rectangles.
- If the new ambient boundary term creates a misleading bottom cold patch, reduce its coefficient before introducing a more complex model.
