# S3/S4 Scale Benchmarks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `s3_scale20` and `s4_dense25` as higher-occupancy companion benchmarks with full raw / union / llm optimizer specs and validation coverage.

**Architecture:** Keep benchmarks as hand-authored scenario inputs under `scenarios/`; do not add scenario business logic. Reuse existing generator, solver, optimizer spec, legality, and operator-pool contracts, which already derive dimensionality from template components and optimization design variables. Implement S3 first and calibrate it before implementing S4.

**Tech Stack:** Python 3.12, pytest, YAML scenario contracts, FEniCSx solver pipeline, existing `core`, `evaluation`, and `optimizers` CLIs.

---

## File Structure

Create:

- `scenarios/templates/s3_scale20.yaml`: 20-component staged scale template.
- `scenarios/templates/s4_dense25.yaml`: 25-component dense staged template.
- `scenarios/evaluation/s3_scale20_eval.yaml`: S3 objectives and constraints.
- `scenarios/evaluation/s4_dense25_eval.yaml`: S4 objectives and constraints.
- `scenarios/optimization/s3_scale20_raw.yaml`
- `scenarios/optimization/s3_scale20_union.yaml`
- `scenarios/optimization/s3_scale20_llm.yaml`
- `scenarios/optimization/s4_dense25_raw.yaml`
- `scenarios/optimization/s4_dense25_union.yaml`
- `scenarios/optimization/s4_dense25_llm.yaml`
- `scenarios/optimization/profiles/s3_scale20_raw.yaml`
- `scenarios/optimization/profiles/s3_scale20_union.yaml`
- `scenarios/optimization/profiles/s4_dense25_raw.yaml`
- `scenarios/optimization/profiles/s4_dense25_union.yaml`
- `tests/schema/test_s3_s4_templates.py`
- `tests/generator/test_s3_s4_templates.py`
- `tests/solver/test_s3_s4_generated_cases.py`
- `tests/optimizers/test_s3_s4_specs.py`

Modify:

- `README.md`: document S3/S4 after they pass focused validation.
- `AGENTS.md`: add S3/S4 to repository guidance after implementation is validated.

Do not modify optimizer runtime code unless a focused test proves an existing generic contract breaks for 42D/52D specs.

---

## Task 1: Add S3/S4 Template Schema Tests

**Files:**
- Create: `tests/schema/test_s3_s4_templates.py`
- Read: `docs/superpowers/specs/2026-04-27-s3-s4-scale-benchmarks-design.md`
- Read: `scenarios/templates/s2_staged.yaml`

- [ ] **Step 1: Write failing schema and occupancy tests**

Create `tests/schema/test_s3_s4_templates.py`:

```python
from __future__ import annotations

from math import pi
from pathlib import Path
from typing import Any

import pytest
import yaml


SCENARIOS = {
    "s3_scale20": {
        "path": Path("scenarios/templates/s3_scale20.yaml"),
        "component_count": 20,
        "area_ratio": (0.52, 0.55),
        "load_power": (150.0, 158.0),
        "sink_span": (0.40, 0.44),
    },
    "s4_dense25": {
        "path": Path("scenarios/templates/s4_dense25.yaml"),
        "component_count": 25,
        "area_ratio": (0.60, 0.63),
        "load_power": (172.0, 182.0),
        "sink_span": (0.44, 0.48),
    },
}


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _spec_value(spec: Any) -> float:
    if isinstance(spec, dict):
        return float(spec["min"])
    return float(spec)


def _family_area(family: dict[str, Any]) -> float:
    geometry = family["geometry"]
    shape = family["shape"]
    if shape == "rect":
        return _spec_value(geometry["width"]) * _spec_value(geometry["height"])
    if shape == "circle":
        radius = _spec_value(geometry["radius"])
        return pi * radius * radius
    if shape == "capsule":
        length = _spec_value(geometry["length"])
        radius = _spec_value(geometry["radius"])
        return max(0.0, length - 2.0 * radius) * (2.0 * radius) + pi * radius * radius
    if shape == "slot":
        length = _spec_value(geometry["length"])
        width = _spec_value(geometry["width"])
        return max(0.0, length - width) * width + pi * (0.5 * width) ** 2
    raise AssertionError(f"Unexpected shape in S3/S4 template: {shape}")


def _placement_area(payload: dict[str, Any]) -> float:
    region = payload["placement_regions"][0]
    return (float(region["x_max"]) - float(region["x_min"])) * (
        float(region["y_max"]) - float(region["y_min"])
    )


@pytest.mark.parametrize("template_id, expected", SCENARIOS.items())
def test_scale_template_identity_and_contract(template_id: str, expected: dict[str, Any]) -> None:
    payload = _load(expected["path"])

    assert payload["template_meta"]["template_id"] == template_id
    assert "operating_case_profiles" not in payload
    assert len(payload["component_families"]) == expected["component_count"]
    assert len(payload["load_rules"]) == expected["component_count"]
    assert [family["family_id"] for family in payload["component_families"]] == [
        f"c{index:02d}" for index in range(1, expected["component_count"] + 1)
    ]
    assert [rule["target_family"] for rule in payload["load_rules"]] == [
        f"c{index:02d}" for index in range(1, expected["component_count"] + 1)
    ]
    assert len(payload["boundary_feature_families"]) == 1
    assert payload["boundary_feature_families"][0]["edge"] == "top"


@pytest.mark.parametrize("template_id, expected", SCENARIOS.items())
def test_scale_template_uses_higher_occupancy(template_id: str, expected: dict[str, Any]) -> None:
    payload = _load(expected["path"])

    component_area = sum(_family_area(family) for family in payload["component_families"])
    area_ratio = component_area / _placement_area(payload)

    lower, upper = expected["area_ratio"]
    assert lower <= area_ratio <= upper


@pytest.mark.parametrize("template_id, expected", SCENARIOS.items())
def test_scale_template_power_and_sink_budget_shape(template_id: str, expected: dict[str, Any]) -> None:
    payload = _load(expected["path"])

    total_power = sum(float(rule["total_power"]) for rule in payload["load_rules"])
    power_lower, power_upper = expected["load_power"]
    assert power_lower <= total_power <= power_upper
    assert all(rule.get("source_area_ratio") is not None for rule in payload["load_rules"])

    sink = payload["boundary_feature_families"][0]
    sink_span = float(sink["span"]["max"]) - float(sink["span"]["min"])
    span_lower, span_upper = expected["sink_span"]
    assert span_lower <= sink_span <= span_upper


@pytest.mark.parametrize("template_id, expected", SCENARIOS.items())
def test_scale_template_declares_layout_semantics(template_id: str, expected: dict[str, Any]) -> None:
    payload = _load(expected["path"])

    hints = {family.get("placement_hint") for family in payload["component_families"]}
    assert {"adversarial_core", "center_mass", "left_edge", "right_edge", "bottom_band"} <= hints
    for family in payload["component_families"]:
        assert "layout_tags" in family
        assert "placement_hint" in family
        assert 0.0 < float(family.get("clearance", 0.0)) <= 0.014
```

- [ ] **Step 2: Run tests to verify they fail because templates do not exist**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s3_s4_templates.py -v
```

Expected: FAIL with `FileNotFoundError` for `scenarios/templates/s3_scale20.yaml`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/schema/test_s3_s4_templates.py
git commit -m "test: define S3 S4 template contracts"
```

---

## Task 2: Add The S3 Template

**Files:**
- Create: `scenarios/templates/s3_scale20.yaml`
- Test: `tests/schema/test_s3_s4_templates.py`

- [ ] **Step 1: Create S3 by copying S2**

Start from `scenarios/templates/s2_staged.yaml` and save it as `scenarios/templates/s3_scale20.yaml`.

Then apply these exact top-level edits:

```yaml
template_meta:
  template_id: s3_scale20
  description: Single-case S3 20-component scale benchmark with higher occupancy, a right-shifted staged thermal core, and a secondary hot lane.
placement_regions:
  - region_id: main-deck
    kind: rect
    x_min: 0.06
    x_max: 0.94
    y_min: 0.05
    y_max: 0.70
```

Change the sink family to:

```yaml
boundary_feature_families:
  - family_id: sink-top-window
    kind: line_sink
    edge: top
    span:
      min: 0.10
      max: 0.52
    sink_temperature:
      min: 290.5
      max: 290.5
    transfer_coefficient:
      min: 7.5
      max: 7.5
```

Change physics background cooling to:

```yaml
physics:
  kind: steady_heat_radiation
  ambient_temperature: 292.0
  background_boundary_cooling:
    transfer_coefficient: 0.04
    emissivity: 0.05
```

Change generation rules to:

```yaml
generation_rules:
  seed_policy: external
  max_placement_attempts: 3200
  placement_retries: 10
  layout_strategy:
    kind: s3_scale20_dual_core_v1
    zones:
      active_deck:
        x_min: 0.07
        x_max: 0.93
        y_min: 0.07
        y_max: 0.69
      dense_core:
        x_min: 0.48
        x_max: 0.82
        y_min: 0.15
        y_max: 0.42
      adversarial_core:
        x_min: 0.50
        x_max: 0.88
        y_min: 0.13
        y_max: 0.52
      secondary_core:
        x_min: 0.34
        x_max: 0.68
        y_min: 0.22
        y_max: 0.56
      top_sink_band:
        x_min: 0.12
        x_max: 0.52
        y_min: 0.56
        y_max: 0.69
      left_io_edge:
        x_min: 0.08
        x_max: 0.25
        y_min: 0.08
        y_max: 0.68
      right_service_edge:
        x_min: 0.78
        x_max: 0.94
        y_min: 0.08
        y_max: 0.68
```

- [ ] **Step 2: Append S3 component families**

Append these component families after `c15` and before `boundary_feature_families`:

```yaml
  - family_id: c16
    role: memory_stack_01
    shape: rect
    count_range: {min: 1, max: 1}
    geometry:
      width: {min: 0.13, max: 0.13}
      height: {min: 0.10, max: 0.10}
    material_ref: electronics_housing
    thermal_tags: [payload, memory]
    layout_tags: [logic_board, compute_cluster]
    placement_hint: center_mass
    adjacency_group: compute-cluster
    clearance: 0.009
  - family_id: c17
    role: aux_power_stage
    shape: rect
    count_range: {min: 1, max: 1}
    geometry:
      width: {min: 0.135, max: 0.135}
      height: {min: 0.095, max: 0.095}
    material_ref: electronics_housing
    thermal_tags: [payload, high_power]
    layout_tags: [power_dense, sink_aware]
    placement_hint: center_mass
    adjacency_group: secondary-thermal-cluster
    clearance: 0.011
  - family_id: c18
    role: rf_frontend
    shape: capsule
    count_range: {min: 1, max: 1}
    geometry:
      length: {min: 0.205, max: 0.205}
      radius: {min: 0.033, max: 0.033}
    material_ref: electronics_housing
    rotation_deg: 90.0
    thermal_tags: [payload, io]
    layout_tags: [service_routed, elongated]
    placement_hint: right_edge
    adjacency_group: io-cluster
    clearance: 0.009
  - family_id: c19
    role: sensor_hub
    shape: circle
    count_range: {min: 1, max: 1}
    geometry:
      radius: {min: 0.058, max: 0.058}
    material_ref: electronics_housing
    thermal_tags: [payload, sensor]
    layout_tags: [rounded_housing, sensor_sensitive]
    placement_hint: bottom_band
    adjacency_group: support-cluster
    clearance: 0.008
  - family_id: c20
    role: edge_io_micro
    shape: slot
    count_range: {min: 1, max: 1}
    geometry:
      length: {min: 0.245, max: 0.245}
      width: {min: 0.054, max: 0.054}
    material_ref: electronics_housing
    rotation_deg: 0.0
    thermal_tags: [payload, io]
    layout_tags: [edge_connector, elongated]
    placement_hint: left_edge
    adjacency_group: io-cluster
    clearance: 0.009
```

- [ ] **Step 3: Append S3 load rules**

Append these load rules after the `c15` load rule:

```yaml
  - target_family: c16
    total_power: 6.2
    source_area_ratio: 0.30
  - target_family: c17
    total_power: 9.0
    source_area_ratio: 0.16
  - target_family: c18
    total_power: 5.0
    source_area_ratio: 0.36
  - target_family: c19
    total_power: 3.4
    source_area_ratio: 0.46
  - target_family: c20
    total_power: 4.2
    source_area_ratio: 0.40
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s3_s4_templates.py::test_scale_template_identity_and_contract tests/schema/test_s3_s4_templates.py::test_scale_template_uses_higher_occupancy tests/schema/test_s3_s4_templates.py::test_scale_template_power_and_sink_budget_shape tests/schema/test_s3_s4_templates.py::test_scale_template_declares_layout_semantics -v
```

Expected: S3 parameter rows PASS; S4 rows still fail because S4 has not been created.

- [ ] **Step 5: Validate S3 template through CLI**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s3_scale20.yaml
```

Expected: exit code 0.

- [ ] **Step 6: Commit S3 template**

```bash
git add scenarios/templates/s3_scale20.yaml
git commit -m "feat: add S3 scale20 template"
```

---

## Task 3: Add S3 Generation And Solver Tests

**Files:**
- Create: `tests/generator/test_s3_s4_templates.py`
- Create: `tests/solver/test_s3_s4_generated_cases.py`
- Modify: `scenarios/templates/s3_scale20.yaml` only if tests expose generation instability.

- [ ] **Step 1: Write failing generation tests**

Create `tests/generator/test_s3_s4_templates.py`:

```python
from __future__ import annotations

import pytest

from core.generator.pipeline import generate_case
from core.geometry.layout_rules import component_within_domain, components_violate_clearance


def _clearance_by_family(case_payload: dict) -> dict[str, float]:
    return {
        str(component.get("family_id", "")): float(component.get("clearance", 0.0))
        for component in case_payload["components"]
        if component.get("family_id") is not None
    }


def _assert_no_clearance_violations(case_payload: dict) -> None:
    clearance_by_family = _clearance_by_family(case_payload)
    components = case_payload["components"]
    for index, component in enumerate(components):
        assert component_within_domain(component, case_payload["panel_domain"])
        for other in components[index + 1 :]:
            assert not components_violate_clearance(component, other, clearance_by_family), (
                f"clearance violation between {component['component_id']} and {other['component_id']}"
            )


def test_s3_scale20_generates_twenty_legal_components_for_seed_11() -> None:
    case_payload = generate_case("scenarios/templates/s3_scale20.yaml", seed=11).to_dict()

    assert case_payload["case_meta"]["scenario_id"] == "s3_scale20"
    assert len(case_payload["components"]) == 20
    assert len(case_payload["loads"]) == 20
    _assert_no_clearance_violations(case_payload)


def test_s3_scale20_layout_metrics_hit_scale_band_for_seed_11() -> None:
    case_payload = generate_case("scenarios/templates/s3_scale20.yaml", seed=11).to_dict()
    metrics = case_payload["provenance"]["layout_metrics"]

    assert 0.52 <= metrics["component_area_ratio"] <= 0.55
    assert metrics["nearest_neighbor_gap_mean"] >= 0.0
    assert metrics["bbox_fill_ratio"] >= 0.45


@pytest.mark.parametrize("seed", [11, 17, 23])
def test_s3_scale20_generation_is_stable_for_seed_sample(seed: int) -> None:
    case_payload = generate_case("scenarios/templates/s3_scale20.yaml", seed=seed).to_dict()

    assert len(case_payload["components"]) == 20
    _assert_no_clearance_violations(case_payload)
```

- [ ] **Step 2: Run generation tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_s3_s4_templates.py -v
```

Expected: PASS. If S3 generation fails, adjust only S3 generation zones, `max_placement_attempts`, `placement_retries`, or added-module clearances. Keep target raw area ratio within `0.52-0.55`.

- [ ] **Step 3: Write S3 solver smoke test**

Create `tests/solver/test_s3_s4_generated_cases.py`:

```python
from __future__ import annotations

import pytest

from core.generator.pipeline import generate_case
from core.solver.nonlinear_solver import solve_case


@pytest.mark.slow
def test_generated_s3_scale20_case_solves_for_seed_11() -> None:
    case = generate_case("scenarios/templates/s3_scale20.yaml", seed=11)

    solution = solve_case(case)
    temperature_span = solution.summary_metrics["temperature_max"] - solution.summary_metrics["temperature_min"]

    assert solution.solver_diagnostics["converged"] is True
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
    assert temperature_span >= 10.0
    assert solution.solution_meta["case_id"] == "s3_scale20-seed-0011"
```

- [ ] **Step 4: Run S3 solver smoke test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/solver/test_s3_s4_generated_cases.py::test_generated_s3_scale20_case_solves_for_seed_11 -v
```

Expected: PASS with a converged solve.

- [ ] **Step 5: Commit S3 generation and solver tests**

```bash
git add tests/generator/test_s3_s4_templates.py tests/solver/test_s3_s4_generated_cases.py scenarios/templates/s3_scale20.yaml
git commit -m "test: validate S3 scale20 generation and solve"
```

---

## Task 4: Add S3 Evaluation And Optimizer Spec Tests

**Files:**
- Create: `tests/optimizers/test_s3_s4_specs.py`
- Test later: S3 evaluation/spec/profile YAML files.

- [ ] **Step 1: Write failing S3 optimizer spec tests**

Create `tests/optimizers/test_s3_s4_specs.py`:

```python
from __future__ import annotations

from pathlib import Path

from evaluation.io import load_spec
from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.operator_pool.operators import approved_operator_pool


S3_RAW = Path("scenarios/optimization/s3_scale20_raw.yaml")
S3_UNION = Path("scenarios/optimization/s3_scale20_union.yaml")
S3_LLM = Path("scenarios/optimization/s3_scale20_llm.yaml")
S3_EVAL = Path("scenarios/evaluation/s3_scale20_eval.yaml")

S4_RAW = Path("scenarios/optimization/s4_dense25_raw.yaml")
S4_UNION = Path("scenarios/optimization/s4_dense25_union.yaml")
S4_LLM = Path("scenarios/optimization/s4_dense25_llm.yaml")
S4_EVAL = Path("scenarios/evaluation/s4_dense25_eval.yaml")


def _variable_ids(spec_path: Path) -> list[str]:
    return [str(item["variable_id"]) for item in load_optimization_spec(spec_path).design_variables]


def test_s3_optimization_specs_load_with_42_variables() -> None:
    raw = load_optimization_spec(S3_RAW)
    union = load_optimization_spec(S3_UNION)
    llm = load_optimization_spec(S3_LLM)

    assert raw.benchmark_source["template_path"] == "scenarios/templates/s3_scale20.yaml"
    assert raw.evaluation_protocol["evaluation_spec_path"] == "scenarios/evaluation/s3_scale20_eval.yaml"
    assert len(raw.design_variables) == 42
    assert len(union.design_variables) == 42
    assert len(llm.design_variables) == 42
    assert _variable_ids(S3_RAW)[-4:] == ["c20_x", "c20_y", "sink_start", "sink_end"]


def test_s3_registry_split_matches_active_ladder() -> None:
    raw = load_optimization_spec(S3_RAW).to_dict()
    union = load_optimization_spec(S3_UNION).to_dict()
    llm = load_optimization_spec(S3_LLM).to_dict()

    assert raw["algorithm"]["mode"] == "raw"
    assert "operator_control" not in raw
    assert union["operator_control"]["controller"] == "random_uniform"
    assert union["operator_control"]["registry_profile"] == "primitive_clean"
    assert tuple(union["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_clean")
    assert llm["operator_control"]["controller"] == "llm"
    assert llm["operator_control"]["registry_profile"] == "primitive_plus_assisted"
    assert tuple(llm["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_plus_assisted")
    assert llm["evaluation_protocol"]["legality_policy_id"] == "projection_plus_local_restore"


def test_s3_profiles_resolve_algorithm_parameters() -> None:
    raw = load_optimization_spec(S3_RAW)
    union = load_optimization_spec(S3_UNION)

    raw_algorithm = resolve_algorithm_config(S3_RAW, raw)
    union_algorithm = resolve_algorithm_config(S3_UNION, union)

    assert raw_algorithm["parameters"]["crossover"]["eta"] == 10
    assert raw_algorithm["parameters"]["mutation"]["eta"] == 15
    assert union_algorithm["parameters"]["crossover"]["eta"] == 10
    assert union_algorithm["parameters"]["mutation"]["eta"] == 15


def test_s3_evaluation_spec_has_expected_constraints() -> None:
    spec = load_spec(S3_EVAL).to_dict()
    constraint_ids = {constraint["constraint_id"] for constraint in spec["constraints"]}

    assert [objective["metric"] for objective in spec["objectives"]] == [
        "summary.temperature_max",
        "summary.temperature_gradient_rms",
    ]
    assert {
        "radiator_span_budget",
        "c02_peak_temperature_limit",
        "c04_peak_temperature_limit",
        "c06_peak_temperature_limit",
        "c12_peak_temperature_limit",
        "c17_peak_temperature_limit",
        "panel_temperature_spread_limit",
    } <= constraint_ids


def test_s3_spec_generates_twenty_component_case() -> None:
    spec = load_optimization_spec(S3_RAW)
    case = generate_benchmark_case(S3_RAW, spec)

    assert case.case_meta["scenario_id"] == "s3_scale20"
    assert len(case.components) == 20
```

- [ ] **Step 2: Run S3 optimizer spec tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_s3_s4_specs.py -k s3 -v
```

Expected: FAIL with missing S3 evaluation or optimization spec files.

- [ ] **Step 3: Commit failing S3 optimizer spec tests**

```bash
git add tests/optimizers/test_s3_s4_specs.py
git commit -m "test: define S3 optimizer spec contract"
```

---

## Task 5: Add S3 Evaluation Spec, Optimization Specs, And Profiles

**Files:**
- Create: `scenarios/evaluation/s3_scale20_eval.yaml`
- Create: `scenarios/optimization/s3_scale20_raw.yaml`
- Create: `scenarios/optimization/s3_scale20_union.yaml`
- Create: `scenarios/optimization/s3_scale20_llm.yaml`
- Create: `scenarios/optimization/profiles/s3_scale20_raw.yaml`
- Create: `scenarios/optimization/profiles/s3_scale20_union.yaml`
- Test: `tests/optimizers/test_s3_s4_specs.py`

- [ ] **Step 1: Calibrate and write the S3 evaluation spec**

Run this command. It solves the generated seed-11 case, projects the seed-11 baseline through the intended S3 42D legality bounds, solves the projected case, and writes `scenarios/evaluation/s3_scale20_eval.yaml` with concrete decimal limits.

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python - <<'PY'
from pathlib import Path

import yaml

from core.generator.pipeline import generate_case
from core.schema.models import ThermalCase
from core.solver.nonlinear_solver import solve_case_artifacts
from optimizers.codec import extract_decision_vector
from optimizers.repair import repair_case_payload_from_vector


def _component_variables(component_count: int) -> list[dict[str, object]]:
    variables: list[dict[str, object]] = []
    for index in range(1, component_count + 1):
        x_lower = 0.45 if index in {2, 4, 6, 12} else 0.30 if index in {17, 21} else 0.1
        y_upper = 0.72 if index == 12 else 0.68
        variables.extend(
            [
                {
                    "variable_id": f"c{index:02d}_x",
                    "path": f"components[{index - 1}].pose.x",
                    "lower_bound": x_lower,
                    "upper_bound": 0.9,
                },
                {
                    "variable_id": f"c{index:02d}_y",
                    "path": f"components[{index - 1}].pose.y",
                    "lower_bound": 0.1,
                    "upper_bound": y_upper,
                },
            ]
        )
    return variables


def _metric_values(solution_payload: dict[str, object]) -> tuple[dict[str, float], float]:
    component_summaries = solution_payload["component_summaries"]
    by_id = {
        str(component["component_id"]): float(component["temperature_max"])
        for component in component_summaries
    }
    means = [float(component["temperature_mean"]) for component in component_summaries]
    return by_id, max(means) - min(means)


case = generate_case("scenarios/templates/s3_scale20.yaml", seed=11)
generated_solution = solve_case_artifacts(case)["solution"]
print("generated_summary", generated_solution.summary_metrics)
print("generated_component_count", len(case.components))
print("generated_power", sum(load["total_power"] for load in case.loads))
print("generated_sink", case.boundary_features[0])

temporary_spec = {
    "schema_version": "1.0",
    "spec_meta": {"spec_id": "s3_probe", "description": "S3 calibration probe."},
    "benchmark_source": {"template_path": "scenarios/templates/s3_scale20.yaml", "seed": 11},
    "design_variables": [
        *_component_variables(20),
        {"variable_id": "sink_start", "path": "boundary_features[0].start", "lower_bound": 0.05, "upper_bound": 0.7},
        {"variable_id": "sink_end", "path": "boundary_features[0].end", "lower_bound": 0.2, "upper_bound": 0.95},
    ],
    "algorithm": {"family": "genetic", "backbone": "nsga2", "mode": "raw", "population_size": 20, "num_generations": 10, "seed": 7},
    "evaluation_protocol": {"evaluation_spec_path": "scenarios/evaluation/s3_scale20_eval.yaml", "legality_policy_id": "minimal_canonicalization"},
}
vector = extract_decision_vector(case, temporary_spec)
repaired = repair_case_payload_from_vector(case, temporary_spec, vector, radiator_span_max=0.35)
repaired_case = ThermalCase.from_dict(repaired)
repaired_solution = solve_case_artifacts(repaired_case)["solution"]
component_max, spread = _metric_values(repaired_solution.to_dict())
limits = {
    "c02": round(component_max["c02-001"] - 2.5, 3),
    "c04": round(component_max["c04-001"] + 7.0, 3),
    "c06": round(component_max["c06-001"] + 7.0, 3),
    "c12": round(component_max["c12-001"] + 7.0, 3),
    "c17": round(component_max["c17-001"] - 1.5, 3),
    "spread": round(spread + 20.0, 3),
}
payload = {
    "schema_version": "1.0",
    "spec_meta": {
        "spec_id": "s3_scale20_eval",
        "description": "Single-case evaluation spec for the S3 20-component scale benchmark.",
    },
    "objectives": [
        {
            "objective_id": "minimize_peak_temperature",
            "metric": "summary.temperature_max",
            "sense": "minimize",
        },
        {
            "objective_id": "minimize_temperature_gradient_rms",
            "metric": "summary.temperature_gradient_rms",
            "sense": "minimize",
        },
    ],
    "constraints": [
        {"constraint_id": "radiator_span_budget", "metric": "case.total_radiator_span", "relation": "<=", "limit": 0.35},
        {"constraint_id": "c02_peak_temperature_limit", "metric": "component.c02-001.temperature_max", "relation": "<=", "limit": limits["c02"]},
        {"constraint_id": "c04_peak_temperature_limit", "metric": "component.c04-001.temperature_max", "relation": "<=", "limit": limits["c04"]},
        {"constraint_id": "c06_peak_temperature_limit", "metric": "component.c06-001.temperature_max", "relation": "<=", "limit": limits["c06"]},
        {"constraint_id": "c12_peak_temperature_limit", "metric": "component.c12-001.temperature_max", "relation": "<=", "limit": limits["c12"]},
        {"constraint_id": "c17_peak_temperature_limit", "metric": "component.c17-001.temperature_max", "relation": "<=", "limit": limits["c17"]},
        {"constraint_id": "panel_temperature_spread_limit", "metric": "components.max_temperature_spread", "relation": "<=", "limit": limits["spread"]},
    ],
}
Path("scenarios/evaluation/s3_scale20_eval.yaml").write_text(
    yaml.safe_dump(payload, sort_keys=False),
    encoding="utf-8",
)
print("projected_sink", repaired["boundary_features"][0])
print("projected_layout_metrics", repaired["provenance"]["layout_metrics"])
print("projected_summary", repaired_solution.summary_metrics)
print("written_limits", limits)
PY
```

Expected: prints generated summary, projected summary, projected sink, and `written_limits`; `scenarios/evaluation/s3_scale20_eval.yaml` exists.

- [ ] **Step 2: Inspect the generated S3 evaluation spec**

Run:

```bash
sed -n '1,140p' scenarios/evaluation/s3_scale20_eval.yaml
```

Expected: the file contains the two objectives, `radiator_span_budget` with limit `0.35`, component limits for `c02/c04/c06/c12/c17`, and a `panel_temperature_spread_limit`. Every `limit:` value is a concrete number.

- [ ] **Step 3: Add S3 profiles**

Create `scenarios/optimization/profiles/s3_scale20_raw.yaml`:

```yaml
schema_version: "1.0"
profile_meta:
  profile_id: s3_scale20_nsga2_raw_profile
  description: S3 scale20 tuning for NSGA-II raw variation, matching the active staged ladder.
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

Create `scenarios/optimization/profiles/s3_scale20_union.yaml`:

```yaml
schema_version: "1.0"
profile_meta:
  profile_id: s3_scale20_nsga2_union_profile
  description: S3 scale20 tuning for NSGA-II union and llm variation, matching the active staged ladder.
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

- [ ] **Step 4: Add S3 optimization specs**

Create `scenarios/optimization/s3_scale20_raw.yaml` by copying `s2_staged_raw.yaml`, then:

- set `spec_meta.spec_id` to `s3_scale20_nsga2_raw`
- set description to `S3 scale20 single-case NSGA-II raw baseline with fixed 42D placement and sink-interval encoding.`
- set `benchmark_source.template_path` to `scenarios/templates/s3_scale20.yaml`
- keep seed `11`
- add `c16_x/c16_y` through `c20_x/c20_y` before sink variables:

```yaml
  - variable_id: c16_x
    path: components[15].pose.x
    lower_bound: 0.1
    upper_bound: 0.9
  - variable_id: c16_y
    path: components[15].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
  - variable_id: c17_x
    path: components[16].pose.x
    lower_bound: 0.30
    upper_bound: 0.9
  - variable_id: c17_y
    path: components[16].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
  - variable_id: c18_x
    path: components[17].pose.x
    lower_bound: 0.1
    upper_bound: 0.9
  - variable_id: c18_y
    path: components[17].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
  - variable_id: c19_x
    path: components[18].pose.x
    lower_bound: 0.1
    upper_bound: 0.9
  - variable_id: c19_y
    path: components[18].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
  - variable_id: c20_x
    path: components[19].pose.x
    lower_bound: 0.1
    upper_bound: 0.9
  - variable_id: c20_y
    path: components[19].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
```

- set `algorithm.profile_path` to `scenarios/optimization/profiles/s3_scale20_raw.yaml`
- set `evaluation_protocol.evaluation_spec_path` to `scenarios/evaluation/s3_scale20_eval.yaml`

Create `s3_scale20_union.yaml` and `s3_scale20_llm.yaml` from the raw file, then apply:

For union:

```yaml
spec_meta:
  spec_id: s3_scale20_nsga2_union
  description: S3 scale20 single-case NSGA-II union-uniform mode with the primitive clean action registry and fixed 42D encoding.
algorithm:
  family: genetic
  backbone: nsga2
  mode: union
  population_size: 20
  num_generations: 10
  seed: 7
  profile_path: scenarios/optimization/profiles/s3_scale20_union.yaml
operator_control:
  controller: random_uniform
  registry_profile: primitive_clean
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - anchored_component_jitter
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
evaluation_protocol:
  evaluation_spec_path: scenarios/evaluation/s3_scale20_eval.yaml
  legality_policy_id: minimal_canonicalization
```

For llm:

```yaml
spec_meta:
  spec_id: s3_scale20_nsga2_llm
  description: S3 scale20 single-case NSGA-II union-llm mode with primitive plus assisted registries.
algorithm:
  family: genetic
  backbone: nsga2
  mode: union
  population_size: 20
  num_generations: 10
  seed: 7
  profile_path: scenarios/optimization/profiles/s3_scale20_union.yaml
operator_control:
  controller: llm
  registry_profile: primitive_plus_assisted
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - anchored_component_jitter
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
    - hotspot_pull_toward_sink
    - hotspot_spread
    - gradient_band_smooth
    - congestion_relief
    - sink_retarget
    - layout_rebalance
  controller_parameters:
    provider: openai-compatible
    capability_profile: chat_compatible_json
    performance_profile: balanced
    model_env_var: LLM_MODEL
    api_key_env_var: LLM_API_KEY
    base_url_env_var: LLM_BASE_URL
    max_output_tokens: 256
    temperature: 1.0
    reasoning:
      effort: medium
    retry:
      max_attempts: 2
      timeout_seconds: 45
    memory:
      recent_window: 32
      reflection_interval: 1
    fallback_controller: random_uniform
evaluation_protocol:
  evaluation_spec_path: scenarios/evaluation/s3_scale20_eval.yaml
  legality_policy_id: projection_plus_local_restore
```

- [ ] **Step 5: Run S3 optimizer spec tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_s3_s4_specs.py -k s3 -v
```

Expected: PASS.

- [ ] **Step 6: Commit S3 specs**

```bash
git add scenarios/evaluation/s3_scale20_eval.yaml scenarios/optimization/s3_scale20_raw.yaml scenarios/optimization/s3_scale20_union.yaml scenarios/optimization/s3_scale20_llm.yaml scenarios/optimization/profiles/s3_scale20_raw.yaml scenarios/optimization/profiles/s3_scale20_union.yaml tests/optimizers/test_s3_s4_specs.py
git commit -m "feat: add S3 scale20 optimizer specs"
```

---

## Task 6: Run S3 Smoke Optimization Gate

**Files:**
- Runtime output only under `scenario_runs/s3_scale20/`
- No source files unless smoke reveals a calibrated S3 contract issue.

- [ ] **Step 1: Run raw S3 smoke**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s3_scale20_raw.yaml --evaluation-workers 2 --population-size 20 --num-generations 10 --skip-render --output-root ./scenario_runs/s3_scale20/raw-smoke
```

Expected: `scenario_runs/s3_scale20/raw-smoke/optimization_result.json` exists and reports at least one feasible optimizer record.

- [ ] **Step 2: Run union S3 smoke**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s3_scale20_union.yaml --evaluation-workers 2 --population-size 20 --num-generations 10 --skip-render --output-root ./scenario_runs/s3_scale20/union-smoke
```

Expected: `scenario_runs/s3_scale20/union-smoke/optimization_result.json` exists. The run must not have every optimizer candidate skipped by cheap geometry failure.

- [ ] **Step 3: Inspect S3 smoke summaries**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path

for path in [
    Path("scenario_runs/s3_scale20/raw-smoke/optimization_result.json"),
    Path("scenario_runs/s3_scale20/union-smoke/optimization_result.json"),
]:
    data = json.loads(path.read_text(encoding="utf-8"))
    aggregate = data["aggregate_metrics"]
    feasible = [row for row in data["history"] if row.get("feasible") and row.get("source") != "baseline"]
    skipped = [row for row in data["history"] if row.get("solver_skipped") and row.get("source") != "baseline"]
    print(path)
    print("  optimizer_evaluations", aggregate["optimizer_num_evaluations"])
    print("  feasible_rate", aggregate["optimizer_feasible_rate"])
    print("  first_feasible_eval", aggregate["first_feasible_eval"])
    print("  pareto_size", aggregate["pareto_size"])
    print("  feasible_records", len(feasible))
    print("  solver_skipped_records", len(skipped))
    if not feasible:
        raise SystemExit(f"{path} did not produce feasible optimizer records")
PY
```

Expected: both runs print at least one feasible optimizer record. If union is weaker than raw, keep it visible; do not retune S3 just to force union superiority.

- [ ] **Step 4: Commit any S3 calibration fixes**

If evaluation limits or bounds had to change, commit only the changed S3 source files:

```bash
git add scenarios/templates/s3_scale20.yaml scenarios/evaluation/s3_scale20_eval.yaml scenarios/optimization/s3_scale20_raw.yaml scenarios/optimization/s3_scale20_union.yaml scenarios/optimization/s3_scale20_llm.yaml
git commit -m "fix: calibrate S3 scale20 smoke contract"
```

If no source files changed, record the smoke results in the final implementation summary and do not create an empty commit.

---

## Task 7: Add The S4 Template

**Files:**
- Create: `scenarios/templates/s4_dense25.yaml`
- Test: `tests/schema/test_s3_s4_templates.py`
- Test: `tests/generator/test_s3_s4_templates.py`

- [ ] **Step 1: Create S4 by copying S3**

Copy `scenarios/templates/s3_scale20.yaml` to `scenarios/templates/s4_dense25.yaml`.

Apply these exact edits:

```yaml
template_meta:
  template_id: s4_dense25
  description: Single-case S4 25-component dense benchmark with higher occupancy, staged thermal pressure, and retained optimizer feasibility.
placement_regions:
  - region_id: main-deck
    kind: rect
    x_min: 0.05
    x_max: 0.95
    y_min: 0.05
    y_max: 0.71
boundary_feature_families:
  - family_id: sink-top-window
    kind: line_sink
    edge: top
    span:
      min: 0.10
      max: 0.56
    sink_temperature:
      min: 290.5
      max: 290.5
    transfer_coefficient:
      min: 7.5
      max: 7.5
generation_rules:
  seed_policy: external
  max_placement_attempts: 4400
  placement_retries: 12
  layout_strategy:
    kind: s4_dense25_dual_core_v1
    zones:
      active_deck:
        x_min: 0.06
        x_max: 0.94
        y_min: 0.07
        y_max: 0.70
      dense_core:
        x_min: 0.48
        x_max: 0.83
        y_min: 0.14
        y_max: 0.43
      adversarial_core:
        x_min: 0.50
        x_max: 0.89
        y_min: 0.13
        y_max: 0.53
      secondary_core:
        x_min: 0.32
        x_max: 0.70
        y_min: 0.20
        y_max: 0.58
      top_sink_band:
        x_min: 0.12
        x_max: 0.54
        y_min: 0.56
        y_max: 0.70
      left_io_edge:
        x_min: 0.07
        x_max: 0.26
        y_min: 0.08
        y_max: 0.69
      right_service_edge:
        x_min: 0.78
        x_max: 0.95
        y_min: 0.08
        y_max: 0.69
```

- [ ] **Step 2: Append S4 component families**

Append these component families after `c20` and before `boundary_feature_families`:

```yaml
  - family_id: c21
    role: micro_power_stage_02
    shape: rect
    count_range: {min: 1, max: 1}
    geometry:
      width: {min: 0.13, max: 0.13}
      height: {min: 0.095, max: 0.095}
    material_ref: electronics_housing
    thermal_tags: [payload, high_power]
    layout_tags: [power_dense, sink_aware]
    placement_hint: center_mass
    adjacency_group: secondary-thermal-cluster
    clearance: 0.011
  - family_id: c22
    role: memory_stack_02
    shape: rect
    count_range: {min: 1, max: 1}
    geometry:
      width: {min: 0.125, max: 0.125}
      height: {min: 0.092, max: 0.092}
    material_ref: electronics_housing
    thermal_tags: [payload, memory]
    layout_tags: [logic_board, compute_cluster]
    placement_hint: center_mass
    adjacency_group: compute-cluster
    clearance: 0.009
  - family_id: c23
    role: service_radio
    shape: rect
    count_range: {min: 1, max: 1}
    geometry:
      width: {min: 0.15, max: 0.15}
      height: {min: 0.078, max: 0.078}
    material_ref: electronics_housing
    thermal_tags: [payload, io]
    layout_tags: [service_routed]
    placement_hint: right_edge
    adjacency_group: io-cluster
    clearance: 0.009
  - family_id: c24
    role: aux_sensor_disc
    shape: circle
    count_range: {min: 1, max: 1}
    geometry:
      radius: {min: 0.058, max: 0.058}
    material_ref: electronics_housing
    thermal_tags: [payload, sensor]
    layout_tags: [rounded_housing, sensor_sensitive]
    placement_hint: bottom_band
    adjacency_group: support-cluster
    clearance: 0.008
  - family_id: c25
    role: bottom_bus
    shape: slot
    count_range: {min: 1, max: 1}
    geometry:
      length: {min: 0.255, max: 0.255}
      width: {min: 0.054, max: 0.054}
    material_ref: electronics_housing
    rotation_deg: 0.0
    thermal_tags: [payload, io]
    layout_tags: [edge_connector, elongated]
    placement_hint: bottom_band
    adjacency_group: support-cluster
    clearance: 0.009
```

- [ ] **Step 3: Append S4 load rules**

Append these load rules after the `c20` load rule:

```yaml
  - target_family: c21
    total_power: 7.2
    source_area_ratio: 0.16
  - target_family: c22
    total_power: 5.0
    source_area_ratio: 0.30
  - target_family: c23
    total_power: 4.8
    source_area_ratio: 0.36
  - target_family: c24
    total_power: 3.0
    source_area_ratio: 0.46
  - target_family: c25
    total_power: 3.5
    source_area_ratio: 0.40
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s3_s4_templates.py -v
```

Expected: PASS.

- [ ] **Step 5: Extend generation tests for S4**

Modify `tests/generator/test_s3_s4_templates.py` by adding:

```python
def test_s4_dense25_generates_twenty_five_legal_components_for_seed_11() -> None:
    case_payload = generate_case("scenarios/templates/s4_dense25.yaml", seed=11).to_dict()

    assert case_payload["case_meta"]["scenario_id"] == "s4_dense25"
    assert len(case_payload["components"]) == 25
    assert len(case_payload["loads"]) == 25
    _assert_no_clearance_violations(case_payload)


def test_s4_dense25_layout_metrics_hit_dense_band_for_seed_11() -> None:
    case_payload = generate_case("scenarios/templates/s4_dense25.yaml", seed=11).to_dict()
    metrics = case_payload["provenance"]["layout_metrics"]

    assert 0.60 <= metrics["component_area_ratio"] <= 0.63
    assert metrics["nearest_neighbor_gap_mean"] >= 0.0
    assert metrics["bbox_fill_ratio"] >= 0.45


@pytest.mark.parametrize("seed", [11, 17, 23])
def test_s4_dense25_generation_is_stable_for_seed_sample(seed: int) -> None:
    case_payload = generate_case("scenarios/templates/s4_dense25.yaml", seed=seed).to_dict()

    assert len(case_payload["components"]) == 25
    _assert_no_clearance_violations(case_payload)
```

- [ ] **Step 6: Run S4 generation tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_s3_s4_templates.py -k s4 -v
```

Expected: PASS. If S4 generation fails, adjust only S4 zones, attempts, retries, or added-module clearances. Keep raw area ratio in `0.60-0.63`.

- [ ] **Step 7: Commit S4 template and generation tests**

```bash
git add scenarios/templates/s4_dense25.yaml tests/generator/test_s3_s4_templates.py
git commit -m "feat: add S4 dense25 template"
```

---

## Task 8: Add S4 Solver And Optimizer Spec Tests

**Files:**
- Modify: `tests/solver/test_s3_s4_generated_cases.py`
- Modify: `tests/optimizers/test_s3_s4_specs.py`

- [ ] **Step 1: Add S4 solver smoke test**

Append to `tests/solver/test_s3_s4_generated_cases.py`:

```python
@pytest.mark.slow
def test_generated_s4_dense25_case_solves_for_seed_11() -> None:
    case = generate_case("scenarios/templates/s4_dense25.yaml", seed=11)

    solution = solve_case(case)
    temperature_span = solution.summary_metrics["temperature_max"] - solution.summary_metrics["temperature_min"]

    assert solution.solver_diagnostics["converged"] is True
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
    assert temperature_span >= 10.0
    assert solution.solution_meta["case_id"] == "s4_dense25-seed-0011"
```

- [ ] **Step 2: Run S4 solver smoke test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/solver/test_s3_s4_generated_cases.py::test_generated_s4_dense25_case_solves_for_seed_11 -v
```

Expected: PASS with a converged solve.

- [ ] **Step 3: Add S4 optimizer spec tests**

Append to `tests/optimizers/test_s3_s4_specs.py`:

```python
def test_s4_optimization_specs_load_with_52_variables() -> None:
    raw = load_optimization_spec(S4_RAW)
    union = load_optimization_spec(S4_UNION)
    llm = load_optimization_spec(S4_LLM)

    assert raw.benchmark_source["template_path"] == "scenarios/templates/s4_dense25.yaml"
    assert raw.evaluation_protocol["evaluation_spec_path"] == "scenarios/evaluation/s4_dense25_eval.yaml"
    assert len(raw.design_variables) == 52
    assert len(union.design_variables) == 52
    assert len(llm.design_variables) == 52
    assert _variable_ids(S4_RAW)[-4:] == ["c25_x", "c25_y", "sink_start", "sink_end"]


def test_s4_registry_split_matches_active_ladder() -> None:
    raw = load_optimization_spec(S4_RAW).to_dict()
    union = load_optimization_spec(S4_UNION).to_dict()
    llm = load_optimization_spec(S4_LLM).to_dict()

    assert raw["algorithm"]["mode"] == "raw"
    assert "operator_control" not in raw
    assert union["operator_control"]["controller"] == "random_uniform"
    assert union["operator_control"]["registry_profile"] == "primitive_clean"
    assert tuple(union["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_clean")
    assert llm["operator_control"]["controller"] == "llm"
    assert llm["operator_control"]["registry_profile"] == "primitive_plus_assisted"
    assert tuple(llm["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_plus_assisted")
    assert llm["evaluation_protocol"]["legality_policy_id"] == "projection_plus_local_restore"


def test_s4_profiles_resolve_algorithm_parameters() -> None:
    raw = load_optimization_spec(S4_RAW)
    union = load_optimization_spec(S4_UNION)

    raw_algorithm = resolve_algorithm_config(S4_RAW, raw)
    union_algorithm = resolve_algorithm_config(S4_UNION, union)

    assert raw_algorithm["parameters"]["crossover"]["eta"] == 10
    assert raw_algorithm["parameters"]["mutation"]["eta"] == 15
    assert union_algorithm["parameters"]["crossover"]["eta"] == 10
    assert union_algorithm["parameters"]["mutation"]["eta"] == 15


def test_s4_evaluation_spec_has_expected_constraints() -> None:
    spec = load_spec(S4_EVAL).to_dict()
    constraint_ids = {constraint["constraint_id"] for constraint in spec["constraints"]}

    assert [objective["metric"] for objective in spec["objectives"]] == [
        "summary.temperature_max",
        "summary.temperature_gradient_rms",
    ]
    assert {
        "radiator_span_budget",
        "c02_peak_temperature_limit",
        "c04_peak_temperature_limit",
        "c06_peak_temperature_limit",
        "c12_peak_temperature_limit",
        "c17_peak_temperature_limit",
        "c21_peak_temperature_limit",
        "panel_temperature_spread_limit",
    } <= constraint_ids


def test_s4_spec_generates_twenty_five_component_case() -> None:
    spec = load_optimization_spec(S4_RAW)
    case = generate_benchmark_case(S4_RAW, spec)

    assert case.case_meta["scenario_id"] == "s4_dense25"
    assert len(case.components) == 25
```

- [ ] **Step 4: Run S4 optimizer spec tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_s3_s4_specs.py -k s4 -v
```

Expected: FAIL with missing S4 evaluation or optimization spec files.

- [ ] **Step 5: Commit S4 tests**

```bash
git add tests/solver/test_s3_s4_generated_cases.py tests/optimizers/test_s3_s4_specs.py
git commit -m "test: define S4 dense25 solver and optimizer contracts"
```

---

## Task 9: Add S4 Evaluation Spec, Optimization Specs, And Profiles

**Files:**
- Create: `scenarios/evaluation/s4_dense25_eval.yaml`
- Create: `scenarios/optimization/s4_dense25_raw.yaml`
- Create: `scenarios/optimization/s4_dense25_union.yaml`
- Create: `scenarios/optimization/s4_dense25_llm.yaml`
- Create: `scenarios/optimization/profiles/s4_dense25_raw.yaml`
- Create: `scenarios/optimization/profiles/s4_dense25_union.yaml`
- Test: `tests/optimizers/test_s3_s4_specs.py`

- [ ] **Step 1: Calibrate and write the S4 evaluation spec**

Run this command. It solves the generated seed-11 case, projects the seed-11 baseline through the intended S4 52D legality bounds, solves the projected case, and writes `scenarios/evaluation/s4_dense25_eval.yaml` with concrete decimal limits.

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python - <<'PY'
from pathlib import Path

import yaml

from core.generator.pipeline import generate_case
from core.schema.models import ThermalCase
from core.solver.nonlinear_solver import solve_case_artifacts
from optimizers.codec import extract_decision_vector
from optimizers.repair import repair_case_payload_from_vector


def _component_variables(component_count: int) -> list[dict[str, object]]:
    variables: list[dict[str, object]] = []
    for index in range(1, component_count + 1):
        x_lower = 0.45 if index in {2, 4, 6, 12} else 0.30 if index in {17, 21} else 0.1
        y_upper = 0.72 if index == 12 else 0.68
        variables.extend(
            [
                {
                    "variable_id": f"c{index:02d}_x",
                    "path": f"components[{index - 1}].pose.x",
                    "lower_bound": x_lower,
                    "upper_bound": 0.9,
                },
                {
                    "variable_id": f"c{index:02d}_y",
                    "path": f"components[{index - 1}].pose.y",
                    "lower_bound": 0.1,
                    "upper_bound": y_upper,
                },
            ]
        )
    return variables


def _metric_values(solution_payload: dict[str, object]) -> tuple[dict[str, float], float]:
    component_summaries = solution_payload["component_summaries"]
    by_id = {
        str(component["component_id"]): float(component["temperature_max"])
        for component in component_summaries
    }
    means = [float(component["temperature_mean"]) for component in component_summaries]
    return by_id, max(means) - min(means)


case = generate_case("scenarios/templates/s4_dense25.yaml", seed=11)
generated_solution = solve_case_artifacts(case)["solution"]
print("generated_summary", generated_solution.summary_metrics)
print("generated_component_count", len(case.components))
print("generated_power", sum(load["total_power"] for load in case.loads))
print("generated_sink", case.boundary_features[0])

temporary_spec = {
    "schema_version": "1.0",
    "spec_meta": {"spec_id": "s4_probe", "description": "S4 calibration probe."},
    "benchmark_source": {"template_path": "scenarios/templates/s4_dense25.yaml", "seed": 11},
    "design_variables": [
        *_component_variables(25),
        {"variable_id": "sink_start", "path": "boundary_features[0].start", "lower_bound": 0.05, "upper_bound": 0.7},
        {"variable_id": "sink_end", "path": "boundary_features[0].end", "lower_bound": 0.2, "upper_bound": 0.95},
    ],
    "algorithm": {"family": "genetic", "backbone": "nsga2", "mode": "raw", "population_size": 20, "num_generations": 10, "seed": 7},
    "evaluation_protocol": {"evaluation_spec_path": "scenarios/evaluation/s4_dense25_eval.yaml", "legality_policy_id": "minimal_canonicalization"},
}
vector = extract_decision_vector(case, temporary_spec)
repaired = repair_case_payload_from_vector(case, temporary_spec, vector, radiator_span_max=0.38)
repaired_case = ThermalCase.from_dict(repaired)
repaired_solution = solve_case_artifacts(repaired_case)["solution"]
component_max, spread = _metric_values(repaired_solution.to_dict())
limits = {
    "c02": round(component_max["c02-001"] - 2.5, 3),
    "c04": round(component_max["c04-001"] + 6.0, 3),
    "c06": round(component_max["c06-001"] + 6.0, 3),
    "c12": round(component_max["c12-001"] + 6.0, 3),
    "c17": round(component_max["c17-001"] - 1.5, 3),
    "c21": round(component_max["c21-001"] - 1.5, 3),
    "spread": round(spread + 20.0, 3),
}
payload = {
    "schema_version": "1.0",
    "spec_meta": {
        "spec_id": "s4_dense25_eval",
        "description": "Single-case evaluation spec for the S4 25-component dense benchmark.",
    },
    "objectives": [
        {
            "objective_id": "minimize_peak_temperature",
            "metric": "summary.temperature_max",
            "sense": "minimize",
        },
        {
            "objective_id": "minimize_temperature_gradient_rms",
            "metric": "summary.temperature_gradient_rms",
            "sense": "minimize",
        },
    ],
    "constraints": [
        {"constraint_id": "radiator_span_budget", "metric": "case.total_radiator_span", "relation": "<=", "limit": 0.38},
        {"constraint_id": "c02_peak_temperature_limit", "metric": "component.c02-001.temperature_max", "relation": "<=", "limit": limits["c02"]},
        {"constraint_id": "c04_peak_temperature_limit", "metric": "component.c04-001.temperature_max", "relation": "<=", "limit": limits["c04"]},
        {"constraint_id": "c06_peak_temperature_limit", "metric": "component.c06-001.temperature_max", "relation": "<=", "limit": limits["c06"]},
        {"constraint_id": "c12_peak_temperature_limit", "metric": "component.c12-001.temperature_max", "relation": "<=", "limit": limits["c12"]},
        {"constraint_id": "c17_peak_temperature_limit", "metric": "component.c17-001.temperature_max", "relation": "<=", "limit": limits["c17"]},
        {"constraint_id": "c21_peak_temperature_limit", "metric": "component.c21-001.temperature_max", "relation": "<=", "limit": limits["c21"]},
        {"constraint_id": "panel_temperature_spread_limit", "metric": "components.max_temperature_spread", "relation": "<=", "limit": limits["spread"]},
    ],
}
Path("scenarios/evaluation/s4_dense25_eval.yaml").write_text(
    yaml.safe_dump(payload, sort_keys=False),
    encoding="utf-8",
)
print("projected_sink", repaired["boundary_features"][0])
print("projected_layout_metrics", repaired["provenance"]["layout_metrics"])
print("projected_summary", repaired_solution.summary_metrics)
print("written_limits", limits)
PY
```

Expected: prints generated summary, projected summary, projected sink, and `written_limits`; `scenarios/evaluation/s4_dense25_eval.yaml` exists.

- [ ] **Step 2: Inspect the generated S4 evaluation spec**

Run:

```bash
sed -n '1,160p' scenarios/evaluation/s4_dense25_eval.yaml
```

Expected: the file contains the two objectives, `radiator_span_budget` with limit `0.38`, component limits for `c02/c04/c06/c12/c17/c21`, and a `panel_temperature_spread_limit`. Every `limit:` value is a concrete number.

- [ ] **Step 3: Add S4 profiles**

Create `scenarios/optimization/profiles/s4_dense25_raw.yaml`:

```yaml
schema_version: "1.0"
profile_meta:
  profile_id: s4_dense25_nsga2_raw_profile
  description: S4 dense25 tuning for NSGA-II raw variation, matching the active staged ladder.
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

Create `scenarios/optimization/profiles/s4_dense25_union.yaml`:

```yaml
schema_version: "1.0"
profile_meta:
  profile_id: s4_dense25_nsga2_union_profile
  description: S4 dense25 tuning for NSGA-II union and llm variation, matching the active staged ladder.
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

- [ ] **Step 4: Add S4 optimization specs**

Create S4 raw/union/llm specs by copying the S3 specs and replacing:

- `s3_scale20` with `s4_dense25`
- `s3_scale20_eval` with `s4_dense25_eval`
- `s3_scale20_nsga2_*` with `s4_dense25_nsga2_*`
- `42D` with `52D`
- `scenarios/templates/s3_scale20.yaml` with `scenarios/templates/s4_dense25.yaml`
- profile paths with S4 profile paths

Append `c21_x/c21_y` through `c25_x/c25_y` before sink variables:

```yaml
  - variable_id: c21_x
    path: components[20].pose.x
    lower_bound: 0.30
    upper_bound: 0.9
  - variable_id: c21_y
    path: components[20].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
  - variable_id: c22_x
    path: components[21].pose.x
    lower_bound: 0.1
    upper_bound: 0.9
  - variable_id: c22_y
    path: components[21].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
  - variable_id: c23_x
    path: components[22].pose.x
    lower_bound: 0.1
    upper_bound: 0.9
  - variable_id: c23_y
    path: components[22].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
  - variable_id: c24_x
    path: components[23].pose.x
    lower_bound: 0.1
    upper_bound: 0.9
  - variable_id: c24_y
    path: components[23].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
  - variable_id: c25_x
    path: components[24].pose.x
    lower_bound: 0.1
    upper_bound: 0.9
  - variable_id: c25_y
    path: components[24].pose.y
    lower_bound: 0.1
    upper_bound: 0.68
```

- [ ] **Step 5: Run S4 optimizer spec tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_s3_s4_specs.py -k s4 -v
```

Expected: PASS.

- [ ] **Step 6: Commit S4 specs**

```bash
git add scenarios/evaluation/s4_dense25_eval.yaml scenarios/optimization/s4_dense25_raw.yaml scenarios/optimization/s4_dense25_union.yaml scenarios/optimization/s4_dense25_llm.yaml scenarios/optimization/profiles/s4_dense25_raw.yaml scenarios/optimization/profiles/s4_dense25_union.yaml tests/optimizers/test_s3_s4_specs.py
git commit -m "feat: add S4 dense25 optimizer specs"
```

---

## Task 10: Run S4 Smoke Optimization Gate

**Files:**
- Runtime output only under `scenario_runs/s4_dense25/`
- No source files unless smoke reveals a calibrated S4 contract issue.

- [ ] **Step 1: Run raw S4 smoke**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s4_dense25_raw.yaml --evaluation-workers 2 --population-size 20 --num-generations 10 --skip-render --output-root ./scenario_runs/s4_dense25/raw-smoke
```

Expected: `scenario_runs/s4_dense25/raw-smoke/optimization_result.json` exists. At least one feasible optimizer record is preferred. If no feasible record appears under 20x10, rerun raw once with `--population-size 32 --num-generations 14 --skip-render`; the official S4 budget is allowed to be larger.

- [ ] **Step 2: Run union S4 smoke**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s4_dense25_union.yaml --evaluation-workers 2 --population-size 20 --num-generations 10 --skip-render --output-root ./scenario_runs/s4_dense25/union-smoke
```

Expected: run completes and does not collapse entirely into solver-skipped geometry failures.

- [ ] **Step 3: Inspect S4 smoke summaries**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path

for path in [
    Path("scenario_runs/s4_dense25/raw-smoke/optimization_result.json"),
    Path("scenario_runs/s4_dense25/union-smoke/optimization_result.json"),
]:
    data = json.loads(path.read_text(encoding="utf-8"))
    aggregate = data["aggregate_metrics"]
    feasible = [row for row in data["history"] if row.get("feasible") and row.get("source") != "baseline"]
    skipped = [row for row in data["history"] if row.get("solver_skipped") and row.get("source") != "baseline"]
    print(path)
    print("  optimizer_evaluations", aggregate["optimizer_num_evaluations"])
    print("  feasible_rate", aggregate["optimizer_feasible_rate"])
    print("  first_feasible_eval", aggregate["first_feasible_eval"])
    print("  pareto_size", aggregate["pareto_size"])
    print("  feasible_records", len(feasible))
    print("  solver_skipped_records", len(skipped))
    if len(skipped) == aggregate["optimizer_num_evaluations"]:
        raise SystemExit(f"{path} collapsed into all skipped evaluations")
PY
```

Expected: both runs print summaries. S4 may be hard, but it must not be a pure geometry-skip benchmark.

- [ ] **Step 4: Commit any S4 calibration fixes**

If evaluation limits or bounds had to change, commit only the changed S4 source files:

```bash
git add scenarios/templates/s4_dense25.yaml scenarios/evaluation/s4_dense25_eval.yaml scenarios/optimization/s4_dense25_raw.yaml scenarios/optimization/s4_dense25_union.yaml scenarios/optimization/s4_dense25_llm.yaml
git commit -m "fix: calibrate S4 dense25 smoke contract"
```

If no source files changed, record the smoke results in the final implementation summary and do not create an empty commit.

---

## Task 11: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Update README active benchmark section**

Modify `README.md` active benchmark text to describe:

```markdown
The active paper-facing mainlines are `s1_typical` and `s2_staged`. The scale companion candidates are `s3_scale20` and `s4_dense25`; they preserve the same single-case x/y-only layout contract while intentionally raising component count and layout occupancy.
```

Add bullets:

```markdown
- `s3_scale20`: 20 components, 42 decision variables, target raw component area ratio `0.52-0.55`
- `s4_dense25`: 25 components, 52 decision variables, target raw component area ratio `0.60-0.63`
```

Add implemented file listings for S3/S4 after the existing S2 listing.

- [ ] **Step 2: Update AGENTS repository guidance**

Modify `AGENTS.md` to include:

```markdown
- The scale companion benchmark candidates are:
  - `s3_scale20`
  - `s4_dense25`
- `s3_scale20` uses 20 named components and 42 decision variables.
- `s4_dense25` uses 25 named components and 52 decision variables.
- S3/S4 intentionally use higher raw component area ratios than S2 and should be compared within their own raw / union / llm ladders.
```

Add S3/S4 template/evaluation/optimization paths to the implemented inputs list.

- [ ] **Step 3: Run documentation-sensitive tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s3_s4_templates.py tests/generator/test_s3_s4_templates.py tests/optimizers/test_s3_s4_specs.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit docs**

```bash
git add README.md AGENTS.md
git commit -m "docs: document S3 S4 scale benchmarks"
```

---

## Task 12: Final Focused Verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Run focused schema/generator/optimizer tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s3_s4_templates.py tests/generator/test_s3_s4_templates.py tests/optimizers/test_s3_s4_specs.py -v
```

Expected: PASS.

- [ ] **Step 2: Run focused solver tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/solver/test_s3_s4_generated_cases.py -v
```

Expected: PASS. If runtime is high, record elapsed time in the final summary.

- [ ] **Step 3: Validate all new templates and specs through CLIs**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s3_scale20.yaml
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s4_dense25.yaml
/home/hymn/miniconda3/bin/conda run -n msfenicsx python - <<'PY'
from optimizers.io import load_optimization_spec

for path in [
    "scenarios/optimization/s3_scale20_raw.yaml",
    "scenarios/optimization/s3_scale20_union.yaml",
    "scenarios/optimization/s3_scale20_llm.yaml",
    "scenarios/optimization/s4_dense25_raw.yaml",
    "scenarios/optimization/s4_dense25_union.yaml",
    "scenarios/optimization/s4_dense25_llm.yaml",
]:
    spec = load_optimization_spec(path)
    print(path, len(spec.design_variables), spec.algorithm["mode"])
PY
```

Expected: template validation exits 0; optimizer spec printout shows S3 specs with 42 variables and S4 specs with 52 variables.

- [ ] **Step 4: Confirm git state**

Run:

```bash
git status --short
```

Expected: only pre-existing unrelated dirty files remain, or the worktree is clean except generated `scenario_runs/` outputs intentionally ignored from commits.

- [ ] **Step 5: Final implementation summary**

Report:

- created S3/S4 files
- final occupancy ratios
- generated seed-11 solver summaries
- S3/S4 raw and union smoke result paths
- feasible rates and first feasible evals
- any source files intentionally adjusted during calibration
