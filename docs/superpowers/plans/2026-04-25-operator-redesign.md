# Operator Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the active `nsga2_raw` / `nsga2_union` / `nsga2_llm` ladder so `raw` and `union` become clean baselines, `llm` keeps explicit assisted advantages, and logs/rendering reflect the true evaluated geometry instead of silently replaying full repair.

**Architecture:** Implement the refactor in four cuts. First, introduce explicit legality-policy ids and a new vector contract (`proposal` vs `evaluated`) without changing operator behavior. Second, make artifacts, traces, and replay consume the new contract. Third, replace the current shared semantic union registry with a primitive clean registry for `union` and a primitive-plus-assisted registry for `llm`. Fourth, gate semantic analytics and docs to the new baseline/framework split.

**Tech Stack:** Python 3.11, numpy, pymoo, PyYAML, pytest, existing `core/`, `optimizers/`, `visualization/` packages.

**Spec:** [docs/superpowers/specs/2026-04-25-operator-redesign-design.md](../specs/2026-04-25-operator-redesign-design.md)

---

## File Map

### Core contract and evaluation flow

- Create: `optimizers/legality.py`
- Modify: `optimizers/problem.py`
- Modify: `optimizers/repair.py`
- Modify: `optimizers/validation.py`
- Modify: `optimizers/run_manifest.py`
- Modify: `optimizers/cli.py`
- Modify: `optimizers/run_suite.py`

### Operator registries and union execution

- Create: `optimizers/operator_pool/primitive_registry.py`
- Create: `optimizers/operator_pool/assisted_registry.py`
- Modify: `optimizers/operator_pool/operators.py`
- Modify: `optimizers/adapters/genetic_family.py`
- Modify: `optimizers/operator_pool/trace.py`
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `optimizers/operator_pool/route_families.py`

### Artifacts, replay, and analytics

- Modify: `optimizers/artifacts.py`
- Modify: `optimizers/render_assets.py`

### Active paper-facing specs and docs

- Modify: `scenarios/optimization/s1_typical_raw.yaml`
- Modify: `scenarios/optimization/s1_typical_union.yaml`
- Modify: `scenarios/optimization/s1_typical_llm.yaml`
- Modify: `scenarios/optimization/s2_staged_raw.yaml`
- Modify: `scenarios/optimization/s2_staged_union.yaml`
- Modify: `scenarios/optimization/s2_staged_llm.yaml`
- Modify: `README.md`
- Modify: `AGENTS.md`

### Tests

- Create: `tests/optimizers/test_legality_policy.py`
- Create: `tests/optimizers/test_problem_legality_pipeline.py`
- Modify: `tests/optimizers/test_operator_pool_contracts.py`
- Modify: `tests/optimizers/test_operator_pool_adapters.py`
- Modify: `tests/optimizers/test_s2_staged_baseline.py`
- Modify: `tests/visualization/test_render_assets_fixtures.py`

## Task 1: Add Explicit Legality Policy To Active Specs And Validation

**Files:**
- Modify: `optimizers/validation.py`
- Modify: `scenarios/optimization/s1_typical_raw.yaml`
- Modify: `scenarios/optimization/s1_typical_union.yaml`
- Modify: `scenarios/optimization/s1_typical_llm.yaml`
- Modify: `scenarios/optimization/s2_staged_raw.yaml`
- Modify: `scenarios/optimization/s2_staged_union.yaml`
- Modify: `scenarios/optimization/s2_staged_llm.yaml`
- Test: `tests/optimizers/test_legality_policy.py`

- [ ] **Step 1: Write the failing spec-contract tests**

```python
# tests/optimizers/test_legality_policy.py
from __future__ import annotations

from pathlib import Path

import pytest

from optimizers.io import load_optimization_spec
from optimizers.models import OptimizationSpec


ACTIVE_SPECS = {
    "s1_raw": Path("scenarios/optimization/s1_typical_raw.yaml"),
    "s1_union": Path("scenarios/optimization/s1_typical_union.yaml"),
    "s1_llm": Path("scenarios/optimization/s1_typical_llm.yaml"),
    "s2_raw": Path("scenarios/optimization/s2_staged_raw.yaml"),
    "s2_union": Path("scenarios/optimization/s2_staged_union.yaml"),
    "s2_llm": Path("scenarios/optimization/s2_staged_llm.yaml"),
}


def test_active_specs_declare_legality_policy_ids() -> None:
    expected = {
        "s1_raw": "minimal_canonicalization",
        "s1_union": "minimal_canonicalization",
        "s1_llm": "projection_plus_local_restore",
        "s2_raw": "minimal_canonicalization",
        "s2_union": "minimal_canonicalization",
        "s2_llm": "projection_plus_local_restore",
    }
    for key, path in ACTIVE_SPECS.items():
        spec = load_optimization_spec(path).to_dict()
        assert spec["evaluation_protocol"]["legality_policy_id"] == expected[key]


def test_invalid_legality_policy_id_is_rejected() -> None:
    payload = load_optimization_spec(ACTIVE_SPECS["s1_raw"]).to_dict()
    payload["evaluation_protocol"]["legality_policy_id"] = "mystery_mode"

    with pytest.raises(ValueError, match="legality_policy_id"):
        OptimizationSpec.from_dict(payload)
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_legality_policy.py -v`  
Expected: FAIL because `evaluation_protocol.legality_policy_id` does not exist and validation does not recognize it.

- [ ] **Step 3: Add the legality-policy enum to validation**

```python
# optimizers/validation.py
SUPPORTED_LEGALITY_POLICIES = {
    "minimal_canonicalization",
    "projection_plus_local_restore",
}


def _validate_evaluation_protocol(protocol: Any) -> None:
    _require_mapping(protocol, "evaluation_protocol")
    _require_text(protocol.get("evaluation_spec_path"), "evaluation_protocol.evaluation_spec_path")
    legality_policy_id = _require_text(
        protocol.get("legality_policy_id"),
        "evaluation_protocol.legality_policy_id",
    )
    if legality_policy_id not in SUPPORTED_LEGALITY_POLICIES:
        raise OptimizationValidationError(
            "evaluation_protocol.legality_policy_id must be one of "
            f"{sorted(SUPPORTED_LEGALITY_POLICIES)}."
        )
```

- [ ] **Step 4: Update every active paper-facing optimization spec**

```yaml
# scenarios/optimization/s1_typical_raw.yaml
evaluation_protocol:
  evaluation_spec_path: scenarios/evaluation/s1_typical_eval.yaml
  legality_policy_id: minimal_canonicalization
```

```yaml
# scenarios/optimization/s1_typical_union.yaml
evaluation_protocol:
  evaluation_spec_path: scenarios/evaluation/s1_typical_eval.yaml
  legality_policy_id: minimal_canonicalization
```

```yaml
# scenarios/optimization/s1_typical_llm.yaml
evaluation_protocol:
  evaluation_spec_path: scenarios/evaluation/s1_typical_eval.yaml
  legality_policy_id: projection_plus_local_restore
```

Use the same explicit values in the staged specs:

- `scenarios/optimization/s2_staged_raw.yaml` -> `minimal_canonicalization`
- `scenarios/optimization/s2_staged_union.yaml` -> `minimal_canonicalization`
- `scenarios/optimization/s2_staged_llm.yaml` -> `projection_plus_local_restore`

- [ ] **Step 5: Re-run the focused test**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_legality_policy.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/validation.py \
  scenarios/optimization/s1_typical_raw.yaml \
  scenarios/optimization/s1_typical_union.yaml \
  scenarios/optimization/s1_typical_llm.yaml \
  scenarios/optimization/s2_staged_raw.yaml \
  scenarios/optimization/s2_staged_union.yaml \
  scenarios/optimization/s2_staged_llm.yaml \
  tests/optimizers/test_legality_policy.py
git commit -m "feat(optimizers): add explicit legality policy ids to active specs"
```

## Task 2: Implement The Legality-Policy Module

**Files:**
- Create: `optimizers/legality.py`
- Modify: `optimizers/repair.py`
- Modify: `tests/optimizers/test_repair.py`
- Test: `tests/optimizers/test_legality_policy.py`

- [ ] **Step 1: Extend the failing tests to cover minimal vs assisted behavior**

```python
# tests/optimizers/test_legality_policy.py
import pytest

from core.generator.pipeline import generate_case
from optimizers.codec import extract_decision_vector
from optimizers.io import load_optimization_spec
from optimizers.legality import apply_legality_policy_from_vector


def _case():
    return generate_case("scenarios/templates/s1_typical.yaml", seed=11)


def _raw_spec():
    return load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml")


def test_minimal_canonicalization_projects_sink_but_does_not_restore_overlap() -> None:
    case = _case()
    spec = _raw_spec()
    vector = extract_decision_vector(case, spec)
    vector[0] = 0.18
    vector[1] = 0.18
    vector[2] = 0.18
    vector[3] = 0.18
    vector[-2] = 0.90
    vector[-1] = 0.05

    evaluated = apply_legality_policy_from_vector(
        case,
        spec,
        vector,
        legality_policy_id="minimal_canonicalization",
    )

    assert evaluated.legality_policy_id == "minimal_canonicalization"
    assert "sink_reorder" in evaluated.vector_transform_codes
    assert "sink_project" in evaluated.vector_transform_codes
    assert evaluated.proposal_vector[0] == pytest.approx(0.18)
    assert evaluated.evaluated_vector[0] == pytest.approx(0.18)


def test_projection_plus_local_restore_matches_existing_repair_contract() -> None:
    case = _case()
    spec = _raw_spec()
    vector = extract_decision_vector(case, spec)
    for component_index in range(4):
        vector[component_index * 2] = 0.18
        vector[component_index * 2 + 1] = 0.18
    vector[-2] = 0.05
    vector[-1] = 0.95

    evaluated = apply_legality_policy_from_vector(
        case,
        spec,
        vector,
        legality_policy_id="projection_plus_local_restore",
    )

    assert evaluated.legality_policy_id == "projection_plus_local_restore"
    assert evaluated.evaluated_vector[-1] - evaluated.evaluated_vector[-2] <= 0.48 + 1.0e-6
    assert evaluated.evaluated_vector[0] != pytest.approx(0.18)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_legality_policy.py tests/optimizers/test_repair.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'optimizers.legality'`.

- [ ] **Step 3: Create the legality module and a minimal projection helper**

```python
# optimizers/legality.py
"""Explicit legality-policy application for optimizer proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from core.schema.models import ThermalCase
from optimizers.codec import extract_decision_vector
from optimizers.repair import project_case_payload_from_vector, repair_case_payload_from_vector

LegalityPolicyId = Literal["minimal_canonicalization", "projection_plus_local_restore"]


@dataclass(frozen=True, slots=True)
class LegalityEvaluation:
    proposal_vector: np.ndarray
    evaluated_vector: np.ndarray
    case_payload: dict[str, Any]
    legality_policy_id: str
    vector_transform_codes: tuple[str, ...]


def apply_legality_policy_from_vector(
    base_case: Any,
    optimization_spec: Any,
    vector: np.ndarray,
    *,
    legality_policy_id: LegalityPolicyId,
    radiator_span_max: float | None = None,
) -> LegalityEvaluation:
    proposal_vector = np.asarray(vector, dtype=np.float64)
    if legality_policy_id == "minimal_canonicalization":
        payload = project_case_payload_from_vector(
            base_case,
            optimization_spec,
            proposal_vector,
            radiator_span_max=radiator_span_max,
        )
    elif legality_policy_id == "projection_plus_local_restore":
        payload = repair_case_payload_from_vector(
            base_case,
            optimization_spec,
            proposal_vector,
            radiator_span_max=radiator_span_max,
        )
    else:  # pragma: no cover - validation guards this
        raise ValueError(f"Unsupported legality policy id: {legality_policy_id!r}")

    evaluated_case = ThermalCase.from_dict(payload)
    evaluated_vector = extract_decision_vector(evaluated_case, optimization_spec)
    return LegalityEvaluation(
        proposal_vector=np.asarray(proposal_vector, dtype=np.float64),
        evaluated_vector=np.asarray(evaluated_vector, dtype=np.float64),
        case_payload=payload,
        legality_policy_id=str(legality_policy_id),
        vector_transform_codes=_vector_transform_codes(
            proposal_vector=np.asarray(proposal_vector, dtype=np.float64),
            evaluated_vector=np.asarray(evaluated_vector, dtype=np.float64),
        ),
    )


def _vector_transform_codes(
    *,
    proposal_vector: np.ndarray,
    evaluated_vector: np.ndarray,
) -> tuple[str, ...]:
    codes: list[str] = []
    if not np.allclose(proposal_vector, evaluated_vector):
        codes.append("bound_clip")
    if proposal_vector[-2] > proposal_vector[-1]:
        codes.append("sink_reorder")
    if not np.allclose(proposal_vector[-2:], evaluated_vector[-2:]):
        codes.append("sink_project")
    return tuple(dict.fromkeys(codes))
```

```python
# optimizers/repair.py
def project_case_payload_from_vector(
    base_case: Any,
    optimization_spec: Any,
    vector: np.ndarray,
    *,
    radiator_span_max: float | None = None,
) -> dict[str, Any]:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    payload = _apply_vector_without_case_validation(base_case, spec_payload, vector)
    component_bounds, radiator_bounds = _collect_variable_bounds(spec_payload)
    _clamp_target_components(payload["components"], component_bounds)
    _repair_radiator_intervals(
        payload["boundary_features"],
        radiator_bounds,
        radiator_span_max=radiator_span_max,
    )
    return payload


def repair_case_payload_from_vector(
    base_case: Any,
    optimization_spec: Any,
    vector: np.ndarray,
    *,
    radiator_span_max: float | None = None,
) -> dict[str, Any]:
    payload = project_case_payload_from_vector(
        base_case,
        optimization_spec,
        vector,
        radiator_span_max=radiator_span_max,
    )
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    component_bounds, _ = _collect_variable_bounds(spec_payload)
    clearance_by_family = {
        str(component.get("family_id", "")): float(component.get("clearance", 0.0))
        for component in payload["components"]
        if component.get("family_id") is not None
    }
    _resolve_component_overlaps(
        payload["components"],
        component_bounds,
        panel_domain=payload["panel_domain"],
        clearance_by_family=clearance_by_family,
    )
    return payload
```

- [ ] **Step 4: Update the repair-focused tests to keep asserting the strong policy**

```python
# tests/optimizers/test_repair.py
from core.schema.models import ThermalCase
from optimizers.legality import apply_legality_policy_from_vector


def test_repair_case_from_vector_projects_sink_budget_and_restores_case_geometry() -> None:
    case = _case()
    spec = _spec()
    vector = extract_decision_vector(case, spec)
    for component_index in range(5):
        vector[component_index * 2] = 0.18
        vector[component_index * 2 + 1] = 0.18
    vector[-2] = 0.05
    vector[-1] = 0.95

    evaluated = apply_legality_policy_from_vector(
        case,
        spec,
        np.asarray(vector, dtype=np.float64),
        legality_policy_id="projection_plus_local_restore",
        radiator_span_max=RADIATOR_SPAN_MAX,
    )
    repaired = ThermalCase.from_dict(evaluated.case_payload)

    assert_case_geometry_contracts(repaired)
    feature = repaired.boundary_features[0]
    assert feature["end"] - feature["start"] == pytest.approx(RADIATOR_SPAN_MAX)
```

- [ ] **Step 5: Re-run the focused legality tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_legality_policy.py tests/optimizers/test_repair.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add optimizers/legality.py optimizers/repair.py tests/optimizers/test_legality_policy.py tests/optimizers/test_repair.py
git commit -m "feat(optimizers): add explicit legality policy module"
```

## Task 3: Thread Proposal/Evaluated Vectors Through Problem History And Result Contracts

**Files:**
- Modify: `optimizers/problem.py`
- Modify: `optimizers/validation.py`
- Test: `tests/optimizers/test_problem_legality_pipeline.py`

- [ ] **Step 1: Write a failing history-contract test**

```python
# tests/optimizers/test_problem_legality_pipeline.py
from __future__ import annotations

import numpy as np

from evaluation.io import load_spec
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.problem import ThermalOptimizationProblem


def test_problem_records_proposal_and_evaluated_vectors_separately() -> None:
    spec_path = "scenarios/optimization/s1_typical_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    vector = np.asarray(problem.xl, dtype=np.float64).copy()
    vector[-2] = 0.90
    vector[-1] = 0.05

    record, _, _ = problem.evaluate_vector(vector, source="optimizer")
    problem.close()

    assert record["legality_policy_id"] == "minimal_canonicalization"
    assert "proposal_decision_vector" in record
    assert "evaluated_decision_vector" in record
    assert record["proposal_decision_vector"]["sink_start"] == 0.90
    assert record["evaluated_decision_vector"]["sink_start"] <= record["evaluated_decision_vector"]["sink_end"]
    assert "vector_transform_codes" in record
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_problem_legality_pipeline.py -v`  
Expected: FAIL because the current record only contains `decision_vector`.

- [ ] **Step 3: Update `ThermalOptimizationProblem` and the candidate dataclass**

```python
# optimizers/problem.py
from optimizers.legality import apply_legality_policy_from_vector


@dataclass(slots=True)
class PreparedCandidate:
    evaluation_index: int
    source: str
    proposal_decision_vector: dict[str, float]
    evaluated_decision_vector: dict[str, float]
    legality_policy_id: str
    vector_transform_codes: tuple[str, ...]
    metadata: dict[str, Any] | None
    candidate_payload: dict[str, Any] | None = None
    immediate_record: dict[str, Any] | None = None
    immediate_objective_vector: np.ndarray | None = None
    immediate_constraint_vector: np.ndarray | None = None


def _prepare_candidate(self, vector: np.ndarray, *, source: str, metadata: dict[str, Any] | None) -> PreparedCandidate:
    evaluation_index = self._next_evaluation_index
    self._next_evaluation_index += 1
    legality_policy_id = str(self.evaluation_spec["evaluation_protocol"]["legality_policy_id"])
    proposal_decision_vector = {
        variable["variable_id"]: float(value)
        for variable, value in zip(self.optimization_spec["design_variables"], vector.tolist(), strict=True)
    }
    evaluated = apply_legality_policy_from_vector(
        self.base_case,
        self.optimization_spec,
        vector,
        legality_policy_id=legality_policy_id,
        radiator_span_max=self.radiator_span_max,
    )
    evaluated_decision_vector = {
        variable["variable_id"]: float(value)
        for variable, value in zip(
            self.optimization_spec["design_variables"],
            evaluated.evaluated_vector.tolist(),
            strict=True,
        )
    }
    vector_transform_codes = tuple(evaluated.vector_transform_codes)
    cheap_result = evaluate_cheap_constraints(evaluated.case_payload, self.evaluation_spec)
    if not cheap_result.feasible:
        return self._build_immediate_penalty(
            evaluation_index=evaluation_index,
            source=source,
            proposal_decision_vector=proposal_decision_vector,
            evaluated_decision_vector=evaluated_decision_vector,
            legality_policy_id=legality_policy_id,
            vector_transform_codes=vector_transform_codes,
            metadata=metadata,
            failure_reason="cheap_constraint_violation",
            constraint_values={
                constraint["constraint_id"]: cheap_result.constraint_values.get(
                    constraint["constraint_id"],
                    PENALTY_VALUE,
                )
                for constraint in self.evaluation_spec["constraints"]
            },
            solver_skipped=True,
            cheap_constraint_issues=list(cheap_result.geometry_issues),
        )
    return PreparedCandidate(
        evaluation_index=evaluation_index,
        source=source,
        proposal_decision_vector=proposal_decision_vector,
        evaluated_decision_vector=evaluated_decision_vector,
        legality_policy_id=legality_policy_id,
        vector_transform_codes=vector_transform_codes,
        metadata=metadata,
        candidate_payload=evaluated.case_payload,
    )


def _build_immediate_penalty(
    self,
    *,
    evaluation_index: int,
    source: str,
    proposal_decision_vector: dict[str, float],
    evaluated_decision_vector: dict[str, float],
    legality_policy_id: str,
    vector_transform_codes: tuple[str, ...],
    metadata: dict[str, Any] | None,
    failure_reason: str,
    constraint_values: dict[str, float] | None = None,
    solver_skipped: bool = False,
    cheap_constraint_issues: list[str] | None = None,
) -> PreparedCandidate:
    record = {
        "evaluation_index": evaluation_index,
        "source": source,
        "feasible": False,
        "proposal_decision_vector": proposal_decision_vector,
        "evaluated_decision_vector": evaluated_decision_vector,
        "legality_policy_id": legality_policy_id,
        "vector_transform_codes": list(vector_transform_codes),
        "objective_values": {
            objective["objective_id"]: PENALTY_VALUE
            for objective in self.evaluation_spec["objectives"]
        },
        "constraint_values": dict(constraint_values or {}),
        "failure_reason": failure_reason,
        "solver_skipped": solver_skipped,
        "cheap_constraint_issues": list(cheap_constraint_issues or []),
        "evaluation_report": {"feasible": False, "metric_values": {}},
    }
    return PreparedCandidate(
        evaluation_index=evaluation_index,
        source=source,
        proposal_decision_vector=proposal_decision_vector,
        evaluated_decision_vector=evaluated_decision_vector,
        legality_policy_id=legality_policy_id,
        vector_transform_codes=vector_transform_codes,
        metadata=metadata,
        immediate_record=record,
        immediate_objective_vector=np.full(self.n_obj, PENALTY_VALUE, dtype=np.float64),
        immediate_constraint_vector=np.asarray(
            [float(record["constraint_values"].get(item["constraint_id"], PENALTY_VALUE)) for item in self.evaluation_spec["constraints"]],
            dtype=np.float64,
        ),
    )
```

```python
# optimizers/problem.py
record = {
    "evaluation_index": evaluation_index,
    "source": source,
    "feasible": False,
    "proposal_decision_vector": proposal_decision_vector,
    "evaluated_decision_vector": evaluated_decision_vector,
    "legality_policy_id": legality_policy_id,
    "vector_transform_codes": list(vector_transform_codes),
    "objective_values": objective_values,
    "constraint_values": constraint_values,
    "solver_skipped": solver_skipped,
    "evaluation_report": evaluation_report,
}
```

- [ ] **Step 4: Update result validation to require the new fields**

```python
# optimizers/validation.py
def _validate_candidate_record(record: Any, label: str) -> None:
    required_keys = (
        "evaluation_index",
        "source",
        "feasible",
        "proposal_decision_vector",
        "evaluated_decision_vector",
        "legality_policy_id",
        "vector_transform_codes",
        "objective_values",
        "constraint_values",
    )
    _require_mapping(record, label)
    _require_required_keys(record, required_keys, label)
    proposal_vector = _require_mapping(record["proposal_decision_vector"], f"{label}.proposal_decision_vector")
    evaluated_vector = _require_mapping(record["evaluated_decision_vector"], f"{label}.evaluated_decision_vector")
    _require_text(record["legality_policy_id"], f"{label}.legality_policy_id")
    transform_codes = _require_sequence(record["vector_transform_codes"], f"{label}.vector_transform_codes")
    for value in transform_codes:
        _require_text(value, f"{label}.vector_transform_codes[]")
    for name, value in proposal_vector.items():
        _require_text(name, f"{label}.proposal_decision_vector key")
        _require_real(value, f"{label}.proposal_decision_vector['{name}']")
    for name, value in evaluated_vector.items():
        _require_text(name, f"{label}.evaluated_decision_vector key")
        _require_real(value, f"{label}.evaluated_decision_vector['{name}']")
    objective_values = _require_mapping(record["objective_values"], f"{label}.objective_values")
    constraint_values = _require_mapping(record["constraint_values"], f"{label}.constraint_values")
    for name, value in objective_values.items():
        _require_text(name, f"{label}.objective_values key")
        _require_real(value, f"{label}.objective_values['{name}']")
    for name, value in constraint_values.items():
        _require_text(name, f"{label}.constraint_values key")
        _require_real(value, f"{label}.constraint_values['{name}']")
```

- [ ] **Step 5: Re-run the focused problem-contract tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_problem_legality_pipeline.py tests/optimizers/test_legality_policy.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/problem.py \
  optimizers/validation.py \
  tests/optimizers/test_problem_legality_pipeline.py
git commit -m "feat(optimizers): record proposal and evaluated vectors in history"
```

## Task 4: Make Manifests, Traces, And Replay Use The Evaluated Geometry Contract

**Files:**
- Modify: `optimizers/run_manifest.py`
- Modify: `optimizers/cli.py`
- Modify: `optimizers/run_suite.py`
- Modify: `optimizers/operator_pool/trace.py`
- Modify: `optimizers/artifacts.py`
- Modify: `optimizers/render_assets.py`
- Modify: `tests/visualization/test_render_assets_fixtures.py`
- Modify: `tests/optimizers/test_operator_pool_contracts.py`

- [ ] **Step 1: Write failing replay and trace-row tests**

```python
# tests/visualization/test_render_assets_fixtures.py
def test_layout_frames_prefer_evaluated_geometry_for_optimizer_records(monkeypatch) -> None:
    from core.generator.pipeline import generate_case
    from optimizers.codec import extract_decision_vector
    from optimizers.io import load_optimization_spec
    from optimizers.render_assets import _layout_frame_from_record

    optimization_spec = load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml")
    base_case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    decision_vector = extract_decision_vector(base_case, optimization_spec)
    record = {
        "source": "optimizer",
        "proposal_decision_vector": {
            variable["variable_id"]: float(value)
            for variable, value in zip(optimization_spec.design_variables, decision_vector.tolist(), strict=True)
        },
        "evaluated_decision_vector": {
            variable["variable_id"]: float(value)
            for variable, value in zip(optimization_spec.design_variables, decision_vector.tolist(), strict=True)
        },
        "legality_policy_id": "minimal_canonicalization",
    }

    frame = _layout_frame_from_record(
        base_case,
        optimization_spec,
        record,
        generation=1,
        title="gen 1",
        default_legality_policy_id="minimal_canonicalization",
    )

    assert frame is not None
```

```python
# tests/optimizers/test_operator_pool_contracts.py
def test_operator_trace_rows_round_trip_with_evaluated_vector() -> None:
    from optimizers.operator_pool.trace import OperatorTraceRow

    row = OperatorTraceRow(
        generation_index=2,
        evaluation_index=9,
        operator_id="vector_sbx_pm",
        parent_count=2,
        parent_vectors=((0.1, 0.2), (0.3, 0.4)),
        proposal_vector=(0.11, 0.21),
        evaluated_vector=(0.12, 0.22),
        legality_policy_id="minimal_canonicalization",
        metadata={"decision_index": 4},
    )

    restored = OperatorTraceRow.from_dict(row.to_dict())
    assert restored.evaluated_vector == (0.12, 0.22)
    assert restored.legality_policy_id == "minimal_canonicalization"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/visualization/test_render_assets_fixtures.py tests/optimizers/test_operator_pool_contracts.py -v`  
Expected: FAIL because `OperatorTraceRow` and `_layout_frame_from_record` still use the old `decision_vector` / `repaired_vector` contract.

- [ ] **Step 3: Extend the trace-row schema and enrich serialized operator traces**

```python
# optimizers/operator_pool/trace.py
@dataclass(frozen=True, slots=True)
class OperatorTraceRow:
    generation_index: int
    evaluation_index: int
    operator_id: str
    parent_count: int
    parent_vectors: tuple[tuple[float, ...], ...]
    proposal_vector: tuple[float, ...]
    evaluated_vector: tuple[float, ...] = ()
    legality_policy_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
```

```python
# optimizers/artifacts.py
history_by_eval_index = {
    int(row["evaluation_index"]): row
    for row in run.result.history
}
operator_trace_rows = _coerce_operator_trace_rows(
    getattr(run, "operator_trace"),
    history_by_eval_index=history_by_eval_index,
)


def _coerce_operator_trace_rows(operator_trace: Any, *, history_by_eval_index: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in operator_trace or ():
        payload = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
        history_row = history_by_eval_index.get(int(payload.get("evaluation_index", -1)), {})
        evaluated_vector = history_row.get("evaluated_decision_vector", {})
        metadata = dict(payload.get("metadata", {}) or {})
        generation = int(payload.get("generation_index", payload.get("generation", 0)))
        evaluation_index = int(payload.get("evaluation_index", payload.get("provisional_evaluation_index", 0)))
        decision_id = _resolve_operator_decision_id(
            payload,
            metadata,
            generation=generation,
            evaluation_index=evaluation_index,
        )
        parents = _resolve_operator_parents(payload, metadata)
        rows.append(
            {
                "decision_id": decision_id,
                "generation": generation,
                "operator_name": str(payload.get("operator_name") or payload.get("operator_id") or "unknown"),
                "parents": parents,
                "offspring": _resolve_operator_offspring(
                    payload,
                    decision_id=decision_id,
                    generation=generation,
                    evaluation_index=evaluation_index,
                ),
                "params_digest": _resolve_operator_params_digest(payload, metadata),
                "wall_ms": _resolve_operator_wall_ms(payload, metadata),
                "proposal_vector": list(payload.get("proposal_vector", [])),
                "evaluated_vector": [float(value) for value in evaluated_vector.values()] if evaluated_vector else [],
                "legality_policy_id": str(history_row.get("legality_policy_id", "")),
            }
        )
    return rows
```

- [ ] **Step 4: Make `render_assets` replay the evaluated vector and read run policy metadata**

```python
# optimizers/run_manifest.py
def write_run_manifest(
    path: Path,
    *,
    mode: str,
    benchmark_seed: int,
    algorithm_seed: int,
    optimization_spec_path: str,
    evaluation_spec_path: str,
    population_size: int,
    num_generations: int,
    legality_policy_id: str,
    wall_seconds: float,
) -> None:
    payload = {
        "mode": mode,
        "seeds": {"benchmark": int(benchmark_seed), "algorithm": int(algorithm_seed)},
        "specs": {
            "optimization": optimization_spec_path,
            "evaluation": evaluation_spec_path,
        },
        "algorithm": {
            "population_size": int(population_size),
            "num_generations": int(num_generations),
        },
        "policies": {
            "legality": legality_policy_id,
            "replay_geometry_source": "evaluated_decision_vector",
        },
        "timing": {"wall_seconds": float(wall_seconds)},
    }
```

```python
# optimizers/cli.py
write_run_manifest(
    Path(output_root) / "run.yaml",
    mode=resolve_suite_mode_id(optimization_spec),
    benchmark_seed=int(optimization_spec.benchmark_source["seed"]),
    algorithm_seed=int(optimization_spec.algorithm["seed"]),
    optimization_spec_path=str(optimization_spec_path),
    evaluation_spec_path=str(evaluation_spec_path),
    population_size=int(optimization_spec.algorithm["population_size"]),
    num_generations=int(optimization_spec.algorithm["num_generations"]),
    legality_policy_id=str(optimization_spec.evaluation_protocol["legality_policy_id"]),
    wall_seconds=wall_seconds,
)
```

```python
# optimizers/run_suite.py
write_run_manifest(
    mode_root / "seeds" / f"seed-{seed}" / "run.yaml",
    mode=mode,
    benchmark_seed=int(seed),
    algorithm_seed=int(seeded_spec.algorithm["seed"]),
    optimization_spec_path=str(spec_path),
    evaluation_spec_path=str(evaluation_spec_path_for_seed),
    population_size=int(seeded_spec.algorithm["population_size"]),
    num_generations=int(seeded_spec.algorithm["num_generations"]),
    legality_policy_id=str(seeded_spec.evaluation_protocol["legality_policy_id"]),
    wall_seconds=_wall_seconds,
)
```

```python
# optimizers/render_assets.py
default_legality_policy_id = str(
    dict(_load_optional_yaml(run_root / "run.yaml") or {}).get("policies", {}).get("legality", "")
)
baseline_frame = _layout_frame_from_record(
    seed_base,
    optimization_spec,
    baseline_row,
    generation=0,
    title="initial layout",
    default_legality_policy_id=default_legality_policy_id,
)


def _layout_frame_from_record(
    base_case: Any,
    optimization_spec: Any,
    record: Mapping[str, Any],
    *,
    generation: int,
    title: str,
    default_legality_policy_id: str = "",
) -> dict[str, Any] | None:
decision_vector = dict(
    record.get("evaluated_decision_vector")
    or record.get("proposal_decision_vector")
    or {}
)
legality_policy_id = str(
    record.get("legality_policy_id")
    or default_legality_policy_id
)
values = [float(decision_vector[str(variable["variable_id"])]) for variable in optimization_spec.design_variables]
if record_source == "baseline":
    case_payload = base_case.to_dict() if hasattr(base_case, "to_dict") else dict(base_case)
elif legality_policy_id == "projection_plus_local_restore":
    case_payload = repair_case_payload_from_vector(
        base_case,
        spec_payload,
        values,
        radiator_span_max=dict(spec_payload.get("algorithm", {})).get("parameters", {}).get("radiator_span_max"),
    )
else:
    case = apply_decision_vector(base_case, optimization_spec, values)
    case_payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
```

- [ ] **Step 5: Re-run focused artifact and replay tests**

Run: `conda run -n msfenicsx pytest tests/visualization/test_render_assets_fixtures.py tests/optimizers/test_operator_pool_contracts.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/run_manifest.py \
  optimizers/cli.py \
  optimizers/run_suite.py \
  optimizers/operator_pool/trace.py \
  optimizers/artifacts.py \
  optimizers/render_assets.py \
  tests/visualization/test_render_assets_fixtures.py \
  tests/optimizers/test_operator_pool_contracts.py
git commit -m "feat(optimizers): make traces and replay use evaluated geometry"
```

## Task 5: Introduce Primitive And Assisted Operator Registries

**Files:**
- Create: `optimizers/operator_pool/primitive_registry.py`
- Create: `optimizers/operator_pool/assisted_registry.py`
- Modify: `optimizers/operator_pool/operators.py`
- Modify: `optimizers/validation.py`
- Modify: `scenarios/optimization/s1_typical_union.yaml`
- Modify: `scenarios/optimization/s1_typical_llm.yaml`
- Modify: `scenarios/optimization/s2_staged_union.yaml`
- Modify: `scenarios/optimization/s2_staged_llm.yaml`
- Modify: `tests/optimizers/test_operator_pool_contracts.py`

- [ ] **Step 1: Rewrite the operator-registry contract test first**

```python
# tests/optimizers/test_operator_pool_contracts.py
PRIMITIVE_OPERATOR_IDS = (
    "vector_sbx_pm",
    "component_jitter_1",
    "component_relocate_1",
    "component_swap_2",
    "sink_shift",
    "sink_resize",
)

ASSISTED_OPERATOR_IDS = (
    "hotspot_pull_toward_sink",
    "hotspot_spread",
    "gradient_band_smooth",
    "congestion_relief",
    "sink_retarget",
    "layout_rebalance",
)


def test_registry_profiles_expose_clean_vs_assisted_pools() -> None:
    from optimizers.operator_pool.operators import approved_operator_pool

    assert approved_operator_pool("primitive_clean") == PRIMITIVE_OPERATOR_IDS
    assert approved_operator_pool("primitive_plus_assisted") == (
        *PRIMITIVE_OPERATOR_IDS,
        *ASSISTED_OPERATOR_IDS,
    )


def test_registry_profile_contract_is_controller_agnostic() -> None:
    from optimizers.models import OptimizationSpec

    payload = load_optimization_spec("scenarios/optimization/s1_typical_union.yaml").to_dict()
    payload["operator_control"]["controller"] = "llm"
    payload["operator_control"]["registry_profile"] = "primitive_clean"
    payload["operator_control"]["operator_pool"] = list(PRIMITIVE_OPERATOR_IDS)

    assert OptimizationSpec.from_dict(payload).operator_control["registry_profile"] == "primitive_clean"
```

- [ ] **Step 2: Run the contract test to confirm it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_operator_pool_contracts.py::test_registry_profiles_expose_clean_vs_assisted_pools -v`  
Expected: FAIL because `approved_operator_pool` does not exist.

- [ ] **Step 3: Create the primitive and assisted registries**

```python
# optimizers/operator_pool/primitive_registry.py
"""Primitive, objective-agnostic operators for clean baselines."""

from __future__ import annotations

PRIMITIVE_OPERATOR_IDS = (
    "vector_sbx_pm",
    "component_jitter_1",
    "component_relocate_1",
    "component_swap_2",
    "sink_shift",
    "sink_resize",
)
```

```python
# optimizers/operator_pool/assisted_registry.py
"""State-aware assisted actions reserved for the llm framework line."""

from __future__ import annotations

ASSISTED_OPERATOR_IDS = (
    "hotspot_pull_toward_sink",
    "hotspot_spread",
    "gradient_band_smooth",
    "congestion_relief",
    "sink_retarget",
    "layout_rebalance",
)
```

```python
# optimizers/operator_pool/operators.py
from optimizers.operator_pool.assisted_registry import ASSISTED_OPERATOR_IDS
from optimizers.operator_pool.primitive_registry import PRIMITIVE_OPERATOR_IDS


def approved_operator_pool(registry_profile: str) -> tuple[str, ...]:
    if registry_profile == "primitive_clean":
        return PRIMITIVE_OPERATOR_IDS
    if registry_profile == "primitive_plus_assisted":
        return (*PRIMITIVE_OPERATOR_IDS, *ASSISTED_OPERATOR_IDS)
    raise KeyError(f"Unsupported registry profile: {registry_profile!r}")


def _component_jitter_1(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = np.array(parents.primary, dtype=np.float64, copy=True)
    component_pairs = _component_axes(variable_layout)
    component = component_pairs[int(rng.integers(0, len(component_pairs)))]
    x_slot = variable_layout.slot_for(component.x_id)
    y_slot = variable_layout.slot_for(component.y_id)
    proposal[x_slot.index] = float(
        np.clip(
            proposal[x_slot.index] + rng.normal(loc=0.0, scale=0.02 * (x_slot.upper_bound - x_slot.lower_bound)),
            x_slot.lower_bound,
            x_slot.upper_bound,
        )
    )
    proposal[y_slot.index] = float(
        np.clip(
            proposal[y_slot.index] + rng.normal(loc=0.0, scale=0.02 * (y_slot.upper_bound - y_slot.lower_bound)),
            y_slot.lower_bound,
            y_slot.upper_bound,
        )
    )
    return variable_layout.clip(proposal)


def _component_relocate_1(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = np.array(parents.primary, dtype=np.float64, copy=True)
    component_pairs = _component_axes(variable_layout)
    component = component_pairs[int(rng.integers(0, len(component_pairs)))]
    x_slot = variable_layout.slot_for(component.x_id)
    y_slot = variable_layout.slot_for(component.y_id)
    proposal[x_slot.index] = float(rng.uniform(x_slot.lower_bound, x_slot.upper_bound))
    proposal[y_slot.index] = float(rng.uniform(y_slot.lower_bound, y_slot.upper_bound))
    return variable_layout.clip(proposal)


def _component_swap_2(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = np.array(parents.primary, dtype=np.float64, copy=True)
    component_pairs = _component_axes(variable_layout)
    left_index, right_index = rng.choice(len(component_pairs), size=2, replace=False)
    left = component_pairs[int(left_index)]
    right = component_pairs[int(right_index)]
    left_x = proposal[variable_layout.index_of(left.x_id)]
    left_y = proposal[variable_layout.index_of(left.y_id)]
    proposal[variable_layout.index_of(left.x_id)] = proposal[variable_layout.index_of(right.x_id)]
    proposal[variable_layout.index_of(left.y_id)] = proposal[variable_layout.index_of(right.y_id)]
    proposal[variable_layout.index_of(right.x_id)] = left_x
    proposal[variable_layout.index_of(right.y_id)] = left_y
    return variable_layout.clip(proposal)


def _sink_shift(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = np.array(parents.primary, dtype=np.float64, copy=True)
    sink_state = _sink_state(proposal, variable_layout)
    if sink_state is None:
        return variable_layout.clip(proposal)
    _, _, start, end, center = sink_state
    span = float(end - start)
    shift = float(rng.normal(loc=0.0, scale=0.03))
    _slide_sink_to_center(
        proposal,
        state,
        variable_layout,
        target_center=center + shift,
        preserve_span=True,
    )
    return variable_layout.clip(proposal)


def _sink_resize(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = np.array(parents.primary, dtype=np.float64, copy=True)
    sink_state = _sink_state(proposal, variable_layout)
    if sink_state is None:
        return variable_layout.clip(proposal)
    _, _, start, end, center = sink_state
    span = max(_MIN_SINK_SPAN, float(end - start))
    target_span = max(_MIN_SINK_SPAN, span * float(1.0 + rng.normal(loc=0.0, scale=0.12)))
    _slide_sink_to_center(
        proposal,
        state,
        variable_layout,
        target_center=center,
        preserve_span=False,
        span_override=target_span,
    )
    return variable_layout.clip(proposal)


_REGISTERED_OPERATORS = (
    OperatorDefinition("vector_sbx_pm", _native_sbx_pm),
    OperatorDefinition("component_jitter_1", _component_jitter_1),
    OperatorDefinition("component_relocate_1", _component_relocate_1),
    OperatorDefinition("component_swap_2", _component_swap_2),
    OperatorDefinition("sink_shift", _sink_shift),
    OperatorDefinition("sink_resize", _sink_resize),
    OperatorDefinition("hotspot_pull_toward_sink", _move_hottest_cluster_toward_sink),
    OperatorDefinition("hotspot_spread", _spread_hottest_cluster),
    OperatorDefinition("gradient_band_smooth", _smooth_high_gradient_band),
    OperatorDefinition("congestion_relief", _reduce_local_congestion),
    OperatorDefinition("sink_retarget", _slide_sink),
    OperatorDefinition("layout_rebalance", _rebalance_layout),
)
```

- [ ] **Step 4: Add `registry_profile` to validation and update the active union/llm specs**

```python
# optimizers/validation.py
SUPPORTED_REGISTRY_PROFILES = {"primitive_clean", "primitive_plus_assisted"}


def _validate_operator_control(operator_control: Any, *, family: str, backbone: str, mode: str) -> None:
    if mode == "raw":
        if operator_control is not None:
            raise OptimizationValidationError("operator_control is allowed only when algorithm.mode is 'union'.")
        return
    if operator_control is None:
        raise OptimizationValidationError("operator_control is required when algorithm.mode is 'union'.")
    _require_mapping(operator_control, "operator_control")
    _require_required_keys(operator_control, ("controller", "registry_profile", "operator_pool"), "operator_control")
    controller = _require_text(operator_control["controller"], "operator_control.controller")
    if controller not in SUPPORTED_CONTROLLERS:
        raise OptimizationValidationError(
            f"operator_control.controller '{controller}' must be one of {sorted(SUPPORTED_CONTROLLERS)}."
        )
    registry_profile = _require_text(operator_control["registry_profile"], "operator_control.registry_profile")
    if registry_profile not in SUPPORTED_REGISTRY_PROFILES:
        raise OptimizationValidationError(
            f"operator_control.registry_profile must be one of {sorted(SUPPORTED_REGISTRY_PROFILES)}."
        )
    operator_pool = tuple(
        _require_text(operator_id, f"operator_control.operator_pool[{index}]")
        for index, operator_id in enumerate(
            _require_sequence(operator_control["operator_pool"], "operator_control.operator_pool")
        )
    )
    expected_pool = approved_operator_pool(registry_profile)
    if operator_pool != expected_pool:
        raise OptimizationValidationError(
            "operator_control.operator_pool must exactly match the approved pool for "
            f"registry_profile={registry_profile!r}."
        )
```

```yaml
# scenarios/optimization/s1_typical_union.yaml
operator_control:
  controller: random_uniform
  registry_profile: primitive_clean
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
```

```yaml
# scenarios/optimization/s1_typical_llm.yaml
operator_control:
  controller: llm
  registry_profile: primitive_plus_assisted
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
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
```

Mirror the same split in the staged specs:

- `scenarios/optimization/s2_staged_union.yaml` -> `controller: random_uniform`, `registry_profile: primitive_clean`, primitive pool only
- `scenarios/optimization/s2_staged_llm.yaml` -> `controller: llm`, `registry_profile: primitive_plus_assisted`, primitive + assisted pool

- [ ] **Step 5: Re-run the focused registry tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_operator_pool_contracts.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/operator_pool/primitive_registry.py \
  optimizers/operator_pool/assisted_registry.py \
  optimizers/operator_pool/operators.py \
  optimizers/validation.py \
  scenarios/optimization/s1_typical_union.yaml \
  scenarios/optimization/s1_typical_llm.yaml \
  scenarios/optimization/s2_staged_union.yaml \
  scenarios/optimization/s2_staged_llm.yaml \
  tests/optimizers/test_operator_pool_contracts.py
git commit -m "feat(optimizers): split primitive and assisted operator registries"
```

## Task 6: Make Genetic Union Clean For Baselines And Assisted For LLM

**Files:**
- Modify: `optimizers/adapters/genetic_family.py`
- Modify: `tests/optimizers/test_operator_pool_adapters.py`

- [ ] **Step 1: Add failing adapter tests for clean-union dedup behavior**

```python
# tests/optimizers/test_operator_pool_adapters.py
def test_clean_union_uses_primitive_pool_and_skips_repair_collapsed_dedup(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.union_driver import run_union_optimization

    spec_path = "scenarios/optimization/s1_typical_union.yaml"
    spec = _spec(spec_path)
    run = run_union_optimization(
        _base_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
    )

    assert {row.selected_operator_id for row in run.controller_trace}.issubset(
        {"vector_sbx_pm", "component_jitter_1", "component_relocate_1", "component_swap_2", "sink_shift", "sink_resize"}
    )
    assert all(not getattr(row, "repair_collapsed_duplicate", False) for row in run.operator_attempt_trace)


def test_llm_assisted_path_keeps_attempt_level_screening_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.union_driver import run_union_optimization

    spec_path = "scenarios/optimization/s1_typical_llm.yaml"
    spec = _spec(spec_path, population_size=4, num_generations=1)
    run = run_union_optimization(
        _base_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
    )

    assert run.operator_attempt_trace
    assert all(row.metadata.get("legality_policy_id") == "projection_plus_local_restore" for row in run.operator_attempt_trace)
```

- [ ] **Step 2: Run the focused adapter tests and verify failure**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_operator_pool_adapters.py -v`  
Expected: FAIL because the adapter still uses the old semantic pool and repair-collapsed duplicate filter for all union runs.

- [ ] **Step 3: Thread registry profile and legality policy into `GeneticFamilyUnionMating`**

```python
# optimizers/adapters/genetic_family.py
class GeneticFamilyUnionMating(InfillCriterion):
    def __init__(
        self,
        *,
        operator_ids: list[str],
        registry_profile: str,
        legality_policy_id: str,
        controller_id: str,
        variable_layout: VariableLayout,
        repair_reference_case: Any,
        optimization_spec: dict[str, Any],
        family: str,
        backbone: str,
        selection: Any,
        raw_mating: Any,
        native_parameters: dict[str, Any],
        radiator_span_max: float | None = None,
        controller_parameters: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            repair=raw_mating.repair,
            eliminate_duplicates=raw_mating.eliminate_duplicates,
            n_max_iterations=raw_mating.n_max_iterations,
        )
        self.registry_profile = str(registry_profile)
        self.legality_policy_id = str(legality_policy_id)
```

```python
# optimizers/adapters/genetic_family.py
mating = GeneticFamilyUnionMating(
    operator_ids=list(operator_control["operator_pool"]),
    registry_profile=str(operator_control["registry_profile"]),
    legality_policy_id=str(problem.evaluation_spec["evaluation_protocol"]["legality_policy_id"]),
    controller_id=controller_id,
    variable_layout=variable_layout,
    repair_reference_case=problem.base_case,
    optimization_spec=optimization_spec,
    family="genetic",
    backbone=backbone,
    selection=selection,
    raw_mating=raw_mating,
    native_parameters=native_parameters,
    radiator_span_max=problem.radiator_span_max,
    controller_parameters=operator_control.get("controller_parameters"),
)
```

- [ ] **Step 4: Gate repair-aware refresh and dedup to the assisted legality path**

```python
# optimizers/adapters/genetic_family.py
def _uses_assisted_screening(self) -> bool:
    return self.legality_policy_id == "projection_plus_local_restore"


if len(proposal_population) > 0:
    proposal_population = self.repair(problem, proposal_population, random_state=rng, **kwargs)
if self._uses_assisted_screening():
    self._refresh_repaired_payloads(proposal_population)
    proposal_population = self._filter_repaired_duplicates(
        proposal_population,
        pop,
        off,
        reference_keys=repaired_reference_keys | accepted_offspring_repaired_keys,
    )
else:
    for individual in proposal_population:
        payload = self._trace_payload(individual)
        payload["evaluated_vector"] = np.asarray(individual.X, dtype=np.float64)
        payload["evaluated_key"] = self._vector_key(payload["evaluated_vector"])
```

- [ ] **Step 5: Re-run the focused adapter tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_operator_pool_adapters.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add optimizers/adapters/genetic_family.py tests/optimizers/test_operator_pool_adapters.py
git commit -m "feat(optimizers): split clean and assisted genetic union paths"
```

## Task 7: Move Semantic Operator Semantics Behind The LLM Framework Layer

**Files:**
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `optimizers/operator_pool/route_families.py`
- Modify: `optimizers/operator_pool/operators.py`
- Modify: `tests/optimizers/test_s2_staged_baseline.py`

- [ ] **Step 1: Add a failing semantic-gating test**

```python
# tests/optimizers/test_s2_staged_baseline.py
def test_s2_staged_union_uses_clean_registry_while_llm_retains_assisted_pool() -> None:
    union = load_optimization_spec(UNION_SPEC_PATH).to_dict()
    llm = load_optimization_spec(LLM_SPEC_PATH).to_dict()

    assert union["operator_control"]["registry_profile"] == "primitive_clean"
    assert llm["operator_control"]["registry_profile"] == "primitive_plus_assisted"
    assert set(union["operator_control"]["operator_pool"]).issubset(
        {"vector_sbx_pm", "component_jitter_1", "component_relocate_1", "component_swap_2", "sink_shift", "sink_resize"}
    )
    assert set(llm["operator_control"]["operator_pool"]) - set(union["operator_control"]["operator_pool"]) == {
        "hotspot_pull_toward_sink",
        "hotspot_spread",
        "gradient_band_smooth",
        "congestion_relief",
        "sink_retarget",
        "layout_rebalance",
    }
```

- [ ] **Step 2: Run the test and confirm failure**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_s2_staged_baseline.py::test_s2_staged_union_uses_clean_registry_while_llm_retains_assisted_pool -v`  
Expected: FAIL because state-builder and route-family semantics still assume the old shared semantic pool.

- [ ] **Step 3: Make primitive operators neutral in state-builder panels**

```python
# optimizers/operator_pool/state_builder.py
_OPERATOR_EFFECTS = {
    "vector_sbx_pm": {"expected_peak_effect": "neutral", "expected_gradient_effect": "neutral"},
    "component_jitter_1": {"expected_peak_effect": "neutral", "expected_gradient_effect": "neutral"},
    "component_relocate_1": {"expected_peak_effect": "neutral", "expected_gradient_effect": "neutral"},
    "component_swap_2": {"expected_peak_effect": "neutral", "expected_gradient_effect": "neutral"},
    "sink_shift": {"expected_peak_effect": "neutral", "expected_gradient_effect": "neutral"},
    "sink_resize": {"expected_peak_effect": "neutral", "expected_gradient_effect": "neutral"},
    "hotspot_pull_toward_sink": {"expected_peak_effect": "improve", "expected_gradient_effect": "neutral"},
    "hotspot_spread": {"expected_peak_effect": "neutral", "expected_gradient_effect": "improve"},
    "gradient_band_smooth": {"expected_peak_effect": "neutral", "expected_gradient_effect": "improve"},
    "congestion_relief": {"expected_peak_effect": "neutral", "expected_gradient_effect": "improve"},
    "sink_retarget": {"expected_peak_effect": "improve", "expected_gradient_effect": "neutral"},
    "layout_rebalance": {"expected_peak_effect": "neutral", "expected_gradient_effect": "improve"},
}
```

- [ ] **Step 4: Move route-family labels to the assisted names only**

```python
# optimizers/operator_pool/route_families.py
ROUTE_FAMILY_BY_OPERATOR = {
    "vector_sbx_pm": "stable_local",
    "component_jitter_1": "stable_local",
    "component_relocate_1": "stable_global",
    "component_swap_2": "stable_global",
    "sink_shift": "stable_local",
    "sink_resize": "stable_local",
    "hotspot_pull_toward_sink": "sink_retarget",
    "hotspot_spread": "hotspot_spread",
    "gradient_band_smooth": "congestion_relief",
    "congestion_relief": "congestion_relief",
    "sink_retarget": "sink_retarget",
    "layout_rebalance": "layout_rebalance",
}
```

- [ ] **Step 5: Re-run the focused semantic-gating tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_s2_staged_baseline.py tests/optimizers/test_operator_pool_contracts.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/operator_pool/state_builder.py \
  optimizers/operator_pool/route_families.py \
  optimizers/operator_pool/operators.py \
  tests/optimizers/test_s2_staged_baseline.py
git commit -m "feat(optimizers): gate semantic operator semantics behind llm registry"
```

## Task 8: Update Docs And Run The Focused Regression Sweep

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Test: `tests/optimizers/test_legality_policy.py`
- Test: `tests/optimizers/test_problem_legality_pipeline.py`
- Test: `tests/optimizers/test_operator_pool_contracts.py`
- Test: `tests/optimizers/test_operator_pool_adapters.py`
- Test: `tests/optimizers/test_s2_staged_baseline.py`
- Test: `tests/visualization/test_render_assets_fixtures.py`

- [ ] **Step 1: Update README to describe the new baseline/framework split**

```markdown
# README.md
- `s2_staged` now shares the same paper-facing `raw / union / llm` ladder, but `union` is a clean primitive-operator baseline while `llm` is the assisted framework line.
- active optimizer flow:
  `paper-facing scenario case -> legality policy -> cheap constraints -> solve -> single-case evaluation_report -> Pareto search -> manifest-backed optimization bundle`
- clean baselines use `minimal_canonicalization`; assisted `llm` runs use `projection_plus_local_restore`
```

- [ ] **Step 2: Update AGENTS guidance to match the new contracts**

```markdown
# AGENTS.md
- replace “current controller line uses the semantic shared operator registry” with:
  - `raw`: native backbone + clean legality policy
  - `union`: primitive operator registry + random controller + clean legality policy
  - `llm`: primitive + assisted registries + assisted legality policy
- update the active optimizer mainline wording from `repair -> cheap constraints -> solve` to `legality policy -> cheap constraints -> solve`
- note that `render-assets` must replay the recorded evaluated geometry rather than silently applying full repair
```

- [ ] **Step 3: Run the focused regression sweep**

Run:

```bash
conda run -n msfenicsx pytest \
  tests/optimizers/test_legality_policy.py \
  tests/optimizers/test_problem_legality_pipeline.py \
  tests/optimizers/test_operator_pool_contracts.py \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_s2_staged_baseline.py \
  tests/visualization/test_render_assets_fixtures.py -v
```

Expected: PASS.

- [ ] **Step 4: Run one raw smoke and one union smoke without rendering**

Run:

```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --evaluation-workers 1 \
  --skip-render \
  --output-root ./scenario_runs/s1_typical/raw-operator-redesign-smoke

conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --evaluation-workers 1 \
  --skip-render \
  --output-root ./scenario_runs/s1_typical/union-operator-redesign-smoke
```

Expected:

- both runs finish successfully
- the raw run writes `run.yaml` with `policies.legality: minimal_canonicalization`
- the union run writes only primitive operator ids in controller/operator traces

- [ ] **Step 5: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs(optimizers): document clean baseline and assisted framework split"
```

## Review Checklist

- Task 1 covers spec-driven legality-policy ids.
- Task 2 covers minimal vs assisted legality behavior.
- Task 3 covers the new history/result contract.
- Task 4 covers manifest, trace, and replay policy alignment.
- Task 5 covers the primitive vs assisted registry split.
- Task 5 plus Task 1 intentionally keep `registry_profile` and `legality_policy_id` independent, which is the required contract base for later `llm_clean` and `union_assisted` ablations.
- Task 6 covers clean-union vs assisted-llm execution behavior.
- Task 7 covers semantic analytics/state gating.
- Task 8 covers docs and focused validation.

No task in this plan depends on an undefined file or unnamed schema field. The new identifiers introduced in early tasks are:

- `evaluation_protocol.legality_policy_id`
- `proposal_decision_vector`
- `evaluated_decision_vector`
- `vector_transform_codes`
- `operator_control.registry_profile`
- `primitive_clean`
- `primitive_plus_assisted`

These same names are reused consistently in the later tasks.
