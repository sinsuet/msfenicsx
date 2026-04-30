# LLM Semantic Prior Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Status: superseded by `2026-04-30-llm-semantic-ranker-controller.md`; keep as historical context only. Current active YAML work targets S5-S7.

**Goal:** Replace the active LLM route's direct operator selection with an LLM semantic/operator prior contract plus a lightweight constrained sampler, while leaving `raw` and `union` unchanged.

**Architecture:** Keep the existing `raw / union / llm` ladder and reuse the current semantic task taxonomy, prompt panels, policy annotations, repair path, and operator pool. Add a parallel prior-advice client contract and a new LLM-only sampler; `LLMOperatorController` selects the legacy path unless `controller_parameters.selection_strategy == "semantic_prior_sampler"`.

**Tech Stack:** Python 3.12, pytest, existing OpenAI-compatible client, existing `ControllerState`, `PolicySnapshot`, semantic task helpers, and JSONL trace writers.

---

## File Map

- Create: `optimizers/operator_pool/semantic_prior_sampler.py`
  - Owns sampler config, probability normalization, risk penalty, generation/rolling exposure caps, probability floor, and RNG sampling.
- Create: `tests/optimizers/test_semantic_prior_sampler.py`
  - Focused unit tests for sampler probability math and cap behavior.
- Modify: `llm/openai_compatible/schemas.py`
  - Add `build_operator_prior_advice_schema(...)`.
- Modify: `llm/openai_compatible/client.py`
  - Add `OperatorPrior`, `SemanticTaskPrior`, `OpenAICompatiblePriorAdvice`.
  - Add `request_operator_prior_advice(...)`.
  - Add parser and retry prompt for prior advice.
  - Keep `request_operator_decision(...)` unchanged for legacy direct path.
- Modify: `optimizers/operator_pool/llm_controller.py`
  - Parse `selection_strategy`.
  - Add semantic-prior branch in `select_decision(...)`.
  - Add prior-specific system prompt.
  - Record prior and sampler metadata in traces and `ControllerDecision.metadata`.
- Modify: active S5-S7 LLM specs only:
  - `scenarios/optimization/s5_aggressive15_llm.yaml`
  - `scenarios/optimization/s6_aggressive20_llm.yaml`
  - `scenarios/optimization/s7_aggressive25_llm.yaml`
- Modify focused tests:
  - `tests/optimizers/test_llm_client.py`
  - `tests/optimizers/test_llm_controller.py`
  - `tests/optimizers/test_optimizer_io.py`
  - `tests/optimizers/test_s5_aggressive15_specs.py`
  - `tests/optimizers/test_s6_aggressive20_specs.py`
  - `tests/optimizers/test_s7_aggressive25_specs.py`

Do not modify `*_raw.yaml`, `*_union.yaml`, raw drivers, union random controller, or primitive operator definitions.

---

### Task 1: Add Prior Advice Schema And Client Parser

**Files:**
- Modify: `llm/openai_compatible/schemas.py`
- Modify: `llm/openai_compatible/client.py`
- Modify: `tests/optimizers/test_llm_client.py`

- [ ] **Step 1: Add prior schema test**

Append to `tests/optimizers/test_llm_client.py`:

```python
def test_operator_prior_advice_schema_requires_operator_priors() -> None:
    from llm.openai_compatible.schemas import build_operator_prior_advice_schema

    schema = build_operator_prior_advice_schema(("sink_shift", "component_jitter_1"))

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert "operator_priors" in schema["required"]
    operator_prior_items = schema["properties"]["operator_priors"]["items"]
    assert operator_prior_items["properties"]["operator_id"]["enum"] == [
        "sink_shift",
        "component_jitter_1",
    ]
    assert operator_prior_items["properties"]["prior"]["minimum"] == 0.0
    assert operator_prior_items["properties"]["prior"]["maximum"] == 1.0
    assert operator_prior_items["properties"]["risk"]["minimum"] == 0.0
    assert operator_prior_items["properties"]["risk"]["maximum"] == 1.0
    assert operator_prior_items["properties"]["confidence"]["minimum"] == 0.0
    assert operator_prior_items["properties"]["confidence"]["maximum"] == 1.0
```

- [ ] **Step 2: Run schema test and confirm it fails**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_client.py::test_operator_prior_advice_schema_requires_operator_priors
```

Expected: FAIL with import error for `build_operator_prior_advice_schema`.

- [ ] **Step 3: Implement `build_operator_prior_advice_schema`**

Add to `llm/openai_compatible/schemas.py` below `build_operator_decision_schema(...)`:

```python
def build_operator_prior_advice_schema(candidate_operator_ids: Sequence[str]) -> dict[str, Any]:
    operator_ids = [str(operator_id) for operator_id in candidate_operator_ids]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "phase": {"type": "string"},
            "rationale": {"type": "string"},
            "semantic_task_priors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "semantic_task": {"type": "string"},
                        "prior": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "risk": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    },
                    "required": ["semantic_task", "prior"],
                },
            },
            "operator_priors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "operator_id": {"type": "string", "enum": operator_ids},
                        "prior": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "risk": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "rationale": {"type": "string"},
                    },
                    "required": ["operator_id", "prior"],
                },
            },
        },
        "required": ["operator_priors"],
    }
```

- [ ] **Step 4: Run schema test and confirm it passes**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_client.py::test_operator_prior_advice_schema_requires_operator_priors
```

Expected: PASS.

- [ ] **Step 5: Add parser tests**

Append to `tests/optimizers/test_llm_client.py`:

```python
def test_chat_compatible_json_client_parses_operator_prior_advice() -> None:
    config = _config(capability_profile="chat_compatible_json")
    sdk_client = _FakeChatSDK(
        '{"phase":"post_feasible_expand","rationale":"balance local cleanup and expansion",'
        '"semantic_task_priors":[{"semantic_task":"local_polish","prior":0.6,"risk":0.2,"confidence":0.7}],'
        '"operator_priors":['
        '{"operator_id":"anchored_component_jitter","prior":0.7,"risk":0.2,"confidence":0.8,"rationale":"bounded local polish"},'
        '{"operator_id":"sink_shift","prior":0.3,"risk":0.5,"confidence":0.4,"rationale":"limited sink alignment"}'
        "]}"
    )
    client = OpenAICompatibleClient(config, sdk_client=sdk_client, environ=_env())

    advice = client.request_operator_prior_advice(
        system_prompt="return priors",
        user_prompt="{}",
        candidate_operator_ids=("anchored_component_jitter", "sink_shift"),
    )

    assert advice.phase == "post_feasible_expand"
    assert advice.rationale == "balance local cleanup and expansion"
    assert advice.operator_priors[0].operator_id == "anchored_component_jitter"
    assert advice.operator_priors[0].prior == pytest.approx(0.7)
    assert advice.operator_priors[0].risk == pytest.approx(0.2)
    assert advice.operator_priors[0].confidence == pytest.approx(0.8)
    assert advice.semantic_task_priors[0].semantic_task == "local_polish"


def test_operator_prior_advice_rejects_unknown_operator_id() -> None:
    config = _config(capability_profile="chat_compatible_json")
    sdk_client = _FakeChatSDK(
        '{"operator_priors":[{"operator_id":"not_in_pool","prior":1.0}]}'
    )
    client = OpenAICompatibleClient(config, sdk_client=sdk_client, environ=_env())

    with pytest.raises(ValueError, match="outside the requested operator registry"):
        client.request_operator_prior_advice(
            system_prompt="return priors",
            user_prompt="{}",
            candidate_operator_ids=("anchored_component_jitter", "sink_shift"),
        )
```

- [ ] **Step 6: Run parser tests and confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_llm_client.py::test_chat_compatible_json_client_parses_operator_prior_advice \
  tests/optimizers/test_llm_client.py::test_operator_prior_advice_rejects_unknown_operator_id
```

Expected: FAIL because `request_operator_prior_advice` and prior dataclasses do not exist.

- [ ] **Step 7: Add prior dataclasses and client method**

Modify the import in `llm/openai_compatible/client.py`:

```python
from llm.openai_compatible.schemas import build_operator_decision_schema, build_operator_prior_advice_schema
```

Add below `OpenAICompatibleDecision`:

```python
@dataclass(frozen=True, slots=True)
class OperatorPrior:
    operator_id: str
    prior: float
    risk: float = 0.5
    confidence: float = 0.5
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class SemanticTaskPrior:
    semantic_task: str
    prior: float
    risk: float = 0.5
    confidence: float = 0.5


@dataclass(frozen=True, slots=True)
class OpenAICompatiblePriorAdvice:
    operator_priors: tuple[OperatorPrior, ...]
    semantic_task_priors: tuple[SemanticTaskPrior, ...]
    phase: str
    rationale: str
    provider: str
    model: str
    capability_profile: str
    performance_profile: str
    raw_payload: dict[str, Any]
```

Add this method inside `OpenAICompatibleClient` after `request_operator_decision(...)`:

```python
def request_operator_prior_advice(
    self,
    *,
    system_prompt: str,
    user_prompt: str,
    candidate_operator_ids: Sequence[str],
    attempt_trace: list[dict[str, Any]] | None = None,
) -> OpenAICompatiblePriorAdvice:
    operator_ids = tuple(str(operator_id) for operator_id in candidate_operator_ids)
    if not operator_ids:
        raise ValueError("OpenAICompatibleClient requires at least one candidate operator id.")

    last_error: Exception | None = None
    current_system_prompt = system_prompt
    for attempt_index in range(self.config.max_attempts):
        try:
            raw_text = self._request_raw_text(
                system_prompt=current_system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=operator_ids,
                response_schema=build_operator_prior_advice_schema(operator_ids),
                response_schema_name="operator_prior_advice",
            )
            advice = self._parse_prior_advice(raw_text, operator_ids)
            if attempt_trace is not None:
                attempt_trace.append(
                    {
                        "attempt_index": int(attempt_index + 1),
                        "valid": True,
                        "raw_text": raw_text,
                        "operator_priors": [
                            {
                                "operator_id": prior.operator_id,
                                "prior": prior.prior,
                                "risk": prior.risk,
                                "confidence": prior.confidence,
                            }
                            for prior in advice.operator_priors
                        ],
                    }
                )
            return advice
        except ValueError as exc:
            if attempt_trace is not None:
                attempt_trace.append(
                    {
                        "attempt_index": int(attempt_index + 1),
                        "valid": False,
                        "error": str(exc),
                    }
                )
            last_error = exc
            current_system_prompt = self._build_retry_prior_system_prompt(
                system_prompt,
                operator_ids,
                str(exc),
            )
        except Exception as exc:
            if attempt_trace is not None:
                attempt_trace.append(
                    {
                        "attempt_index": int(attempt_index + 1),
                        "valid": False,
                        "error": str(exc),
                    }
                )
            last_error = exc
            raise
    assert last_error is not None
    raise last_error
```

- [ ] **Step 8: Allow `_request_raw_text` to use a caller-provided schema**

Change `_request_raw_text(...)` signature:

```python
def _request_raw_text(
    self,
    *,
    system_prompt: str,
    user_prompt: str,
    candidate_operator_ids: Sequence[str],
    response_schema: dict[str, Any] | None = None,
    response_schema_name: str = "operator_decision",
) -> str:
```

Pass those arguments to `_request_via_responses_native(...)`:

```python
return self._request_via_responses_native(
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    candidate_operator_ids=candidate_operator_ids,
    response_schema=response_schema,
    response_schema_name=response_schema_name,
)
```

Change `_request_via_responses_native(...)` signature:

```python
def _request_via_responses_native(
    self,
    *,
    system_prompt: str,
    user_prompt: str,
    candidate_operator_ids: Sequence[str],
    response_schema: dict[str, Any] | None = None,
    response_schema_name: str = "operator_decision",
) -> str:
```

Replace schema construction:

```python
schema = build_operator_decision_schema(candidate_operator_ids) if response_schema is None else response_schema
```

Replace the format name:

```python
"name": response_schema_name,
```

The chat-compatible JSON path does not need schema changes because it already requests JSON object output.

- [ ] **Step 9: Add prior parsing helpers**

Add inside `OpenAICompatibleClient` below `_parse_decision(...)`:

```python
def _parse_prior_advice(
    self,
    raw_text: str,
    operator_ids: Sequence[str],
) -> OpenAICompatiblePriorAdvice:
    resolved_model = self.config.resolve_model(self._environ)
    normalized_raw_text = self._unwrap_markdown_code_fence(raw_text)
    payload = json.loads(normalized_raw_text)
    raw_operator_priors = payload.get("operator_priors")
    if not isinstance(raw_operator_priors, list):
        raise ValueError("LLM prior advice must include an operator_priors array.")
    operator_priors: list[OperatorPrior] = []
    seen_operator_ids: set[str] = set()
    for row in raw_operator_priors:
        if not isinstance(row, dict):
            raise ValueError("Each operator_prior entry must be an object.")
        operator_id = str(row.get("operator_id", "")).strip()
        if operator_id not in operator_ids:
            raise ValueError(
                "LLM prior advice included operator id outside the requested operator registry: "
                f"{operator_id!r} not in {list(operator_ids)}."
            )
        if operator_id in seen_operator_ids:
            continue
        seen_operator_ids.add(operator_id)
        operator_priors.append(
            OperatorPrior(
                operator_id=operator_id,
                prior=_clamp_unit(row.get("prior", 0.0)),
                risk=_clamp_unit(row.get("risk", 0.5)),
                confidence=_clamp_unit(row.get("confidence", 0.5)),
                rationale=str(row.get("rationale", "")),
            )
        )
    if not operator_priors:
        raise ValueError("LLM prior advice did not include any valid operator priors.")

    semantic_task_priors: list[SemanticTaskPrior] = []
    raw_task_priors = payload.get("semantic_task_priors", [])
    if raw_task_priors is None:
        raw_task_priors = []
    if not isinstance(raw_task_priors, list):
        raise ValueError("semantic_task_priors must be an array when present.")
    seen_task_ids: set[str] = set()
    for row in raw_task_priors:
        if not isinstance(row, dict):
            raise ValueError("Each semantic_task_prior entry must be an object.")
        task_id = str(row.get("semantic_task", "")).strip()
        if not task_id or task_id in seen_task_ids:
            continue
        seen_task_ids.add(task_id)
        semantic_task_priors.append(
            SemanticTaskPrior(
                semantic_task=task_id,
                prior=_clamp_unit(row.get("prior", 0.0)),
                risk=_clamp_unit(row.get("risk", 0.5)),
                confidence=_clamp_unit(row.get("confidence", 0.5)),
            )
        )
    return OpenAICompatiblePriorAdvice(
        operator_priors=tuple(operator_priors),
        semantic_task_priors=tuple(semantic_task_priors),
        phase=str(payload.get("phase", "")),
        rationale=str(payload.get("rationale", "")),
        provider=self.config.provider,
        model=resolved_model,
        capability_profile=self.config.capability_profile,
        performance_profile=self.config.performance_profile,
        raw_payload=dict(payload),
    )
```

Add module-level clamp helper near `_semantic_task_for_operator(...)`:

```python
def _clamp_unit(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return float(numeric)
```

- [ ] **Step 10: Add retry prompt for prior advice**

Add inside `OpenAICompatibleClient` near `_build_retry_system_prompt(...)`:

```python
@staticmethod
def _build_retry_prior_system_prompt(
    original_system_prompt: str,
    operator_ids: Sequence[str],
    error_message: str,
) -> str:
    return (
        f"{original_system_prompt}\n"
        "Previous response was invalid: "
        f"{error_message}\n"
        "Return JSON only. Required key: operator_priors. "
        "Each operator_priors item must include operator_id and prior. "
        f"operator_id must exactly equal one of {list(operator_ids)}. "
        "Optional keys: phase, rationale, semantic_task_priors, risk, confidence."
    )
```

- [ ] **Step 11: Run client focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_client.py
```

Expected: PASS.

- [ ] **Step 12: Commit client contract**

```bash
git add llm/openai_compatible/schemas.py llm/openai_compatible/client.py tests/optimizers/test_llm_client.py
git commit -m "feat: add llm operator prior advice contract"
```

---

### Task 2: Implement Semantic Prior Sampler

**Files:**
- Create: `optimizers/operator_pool/semantic_prior_sampler.py`
- Create: `tests/optimizers/test_semantic_prior_sampler.py`

- [ ] **Step 1: Add sampler tests**

Create `tests/optimizers/test_semantic_prior_sampler.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

from optimizers.operator_pool.semantic_prior_sampler import (
    OperatorPriorInput,
    SemanticPriorSamplerConfig,
    SemanticTaskPriorInput,
    sample_operator_from_semantic_priors,
)
from optimizers.operator_pool.state import ControllerState


def _state(
    *,
    recent_decisions: list[dict[str, object]] | None = None,
    generation_operator_counts: dict[str, int] | None = None,
    target_offsprings: int = 20,
) -> ControllerState:
    operator_counts = {
        operator_id: {"accepted_count": count}
        for operator_id, count in (generation_operator_counts or {}).items()
    }
    accepted_count = sum(generation_operator_counts.values()) if generation_operator_counts else 0
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=120,
        parent_count=2,
        vector_size=32,
        metadata={
            "recent_decisions": recent_decisions or [],
            "generation_local_memory": {
                "accepted_count": accepted_count,
                "target_offsprings": target_offsprings,
                "operator_counts": operator_counts,
            },
        },
    )


def test_sampler_blends_llm_prior_with_uniform_floor() -> None:
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("sink_shift", "component_jitter_1", "component_relocate_1"),
        operator_priors=(
            OperatorPriorInput("sink_shift", prior=1.0, risk=0.0, confidence=0.9),
        ),
        semantic_task_priors=(),
        state=_state(),
        config=SemanticPriorSamplerConfig(uniform_mix=0.15, min_probability_floor=0.03),
        rng=np.random.default_rng(4),
    )

    probabilities = result.sampler_probabilities
    assert set(probabilities) == {"sink_shift", "component_jitter_1", "component_relocate_1"}
    assert probabilities["sink_shift"] > probabilities["component_jitter_1"]
    assert probabilities["component_jitter_1"] >= 0.03
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert result.selected_operator_id in probabilities


def test_sampler_applies_risk_penalty_before_sampling() -> None:
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        operator_priors=(
            OperatorPriorInput("sink_shift", prior=0.8, risk=1.0, confidence=0.9),
            OperatorPriorInput("component_jitter_1", prior=0.2, risk=0.0, confidence=0.9),
        ),
        semantic_task_priors=(),
        state=_state(),
        config=SemanticPriorSamplerConfig(
            uniform_mix=0.0,
            min_probability_floor=0.0,
            risk_penalty_weight=0.75,
        ),
        rng=np.random.default_rng(2),
    )

    assert result.normalized_operator_priors["sink_shift"] == pytest.approx(0.8)
    assert result.adjusted_operator_weights["sink_shift"] == pytest.approx(0.2)
    assert result.sampler_probabilities["component_jitter_1"] > result.sampler_probabilities["sink_shift"]


def test_sampler_suppresses_generation_cap_when_alternative_exists() -> None:
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("component_subspace_sbx", "component_jitter_1", "sink_resize"),
        operator_priors=(
            OperatorPriorInput("component_subspace_sbx", prior=0.9, risk=0.0, confidence=0.9),
            OperatorPriorInput("component_jitter_1", prior=0.1, risk=0.0, confidence=0.5),
        ),
        semantic_task_priors=(),
        state=_state(
            generation_operator_counts={"component_subspace_sbx": 7},
            target_offsprings=20,
        ),
        config=SemanticPriorSamplerConfig(
            uniform_mix=0.0,
            min_probability_floor=0.03,
            generation_operator_cap_fraction=0.35,
        ),
        rng=np.random.default_rng(9),
    )

    assert "component_subspace_sbx" in result.suppressed_operator_ids
    assert result.sampler_probabilities["component_subspace_sbx"] == 0.0
    assert sum(result.sampler_probabilities.values()) == pytest.approx(1.0)


def test_sampler_suppresses_rolling_semantic_task_cap() -> None:
    recent_decisions = [
        {"selected_operator_id": "sink_shift", "llm_valid": True}
        for _ in range(10)
    ] + [
        {"selected_operator_id": "component_jitter_1", "llm_valid": True}
        for _ in range(6)
    ]
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("sink_shift", "sink_resize", "component_jitter_1"),
        operator_priors=(
            OperatorPriorInput("sink_shift", prior=0.5, risk=0.0, confidence=0.9),
            OperatorPriorInput("sink_resize", prior=0.3, risk=0.0, confidence=0.8),
            OperatorPriorInput("component_jitter_1", prior=0.2, risk=0.0, confidence=0.7),
        ),
        semantic_task_priors=(),
        state=_state(recent_decisions=recent_decisions),
        config=SemanticPriorSamplerConfig(
            uniform_mix=0.0,
            min_probability_floor=0.0,
            rolling_window=16,
            rolling_semantic_task_cap_fraction=0.55,
        ),
        rng=np.random.default_rng(11),
    )

    assert "sink_shift" in result.suppressed_operator_ids
    assert result.sampler_probabilities["sink_shift"] == 0.0
    assert result.sampler_probabilities["component_jitter_1"] > 0.0


def test_sampler_expands_semantic_task_priors_when_operator_priors_are_empty() -> None:
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("component_jitter_1", "anchored_component_jitter", "sink_shift"),
        operator_priors=(),
        semantic_task_priors=(
            SemanticTaskPriorInput("local_polish", prior=1.0, risk=0.1, confidence=0.8),
        ),
        state=_state(),
        config=SemanticPriorSamplerConfig(uniform_mix=0.0, min_probability_floor=0.0),
        rng=np.random.default_rng(5),
    )

    assert result.sampler_probabilities["component_jitter_1"] == pytest.approx(0.5)
    assert result.sampler_probabilities["anchored_component_jitter"] == pytest.approx(0.5)
    assert result.sampler_probabilities["sink_shift"] == pytest.approx(0.0)
```

- [ ] **Step 2: Run sampler tests and confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_semantic_prior_sampler.py
```

Expected: FAIL because `optimizers.operator_pool.semantic_prior_sampler` does not exist.

- [ ] **Step 3: Implement sampler module**

Create `optimizers/operator_pool/semantic_prior_sampler.py`:

```python
"""Lightweight constrained sampler for LLM semantic/operator priors."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from optimizers.operator_pool.semantic_tasks import semantic_task_for_operator
from optimizers.operator_pool.state import ControllerState


@dataclass(frozen=True, slots=True)
class OperatorPriorInput:
    operator_id: str
    prior: float
    risk: float = 0.5
    confidence: float = 0.5
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class SemanticTaskPriorInput:
    semantic_task: str
    prior: float
    risk: float = 0.5
    confidence: float = 0.5


@dataclass(frozen=True, slots=True)
class SemanticPriorSamplerConfig:
    uniform_mix: float = 0.15
    min_probability_floor: float = 0.03
    generation_operator_cap_fraction: float = 0.35
    rolling_operator_cap_fraction: float = 0.40
    rolling_semantic_task_cap_fraction: float = 0.55
    rolling_window: int = 16
    risk_penalty_weight: float = 0.50

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "SemanticPriorSamplerConfig":
        data = {} if payload is None else dict(payload)
        return cls(
            uniform_mix=_clamp_unit(data.get("uniform_mix", cls.uniform_mix)),
            min_probability_floor=_clamp_unit(data.get("min_probability_floor", cls.min_probability_floor)),
            generation_operator_cap_fraction=_clamp_unit(
                data.get("generation_operator_cap_fraction", cls.generation_operator_cap_fraction)
            ),
            rolling_operator_cap_fraction=_clamp_unit(
                data.get("rolling_operator_cap_fraction", cls.rolling_operator_cap_fraction)
            ),
            rolling_semantic_task_cap_fraction=_clamp_unit(
                data.get("rolling_semantic_task_cap_fraction", cls.rolling_semantic_task_cap_fraction)
            ),
            rolling_window=max(1, int(data.get("rolling_window", cls.rolling_window))),
            risk_penalty_weight=_clamp_unit(data.get("risk_penalty_weight", cls.risk_penalty_weight)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "uniform_mix": float(self.uniform_mix),
            "min_probability_floor": float(self.min_probability_floor),
            "generation_operator_cap_fraction": float(self.generation_operator_cap_fraction),
            "rolling_operator_cap_fraction": float(self.rolling_operator_cap_fraction),
            "rolling_semantic_task_cap_fraction": float(self.rolling_semantic_task_cap_fraction),
            "rolling_window": int(self.rolling_window),
            "risk_penalty_weight": float(self.risk_penalty_weight),
        }


@dataclass(frozen=True, slots=True)
class SemanticPriorSamplerResult:
    selected_operator_id: str
    selected_probability: float
    sampler_probabilities: dict[str, float]
    normalized_operator_priors: dict[str, float]
    adjusted_operator_weights: dict[str, float]
    suppressed_operator_ids: tuple[str, ...]
    cap_reasons: dict[str, str]
    config: dict[str, Any]


def sample_operator_from_semantic_priors(
    *,
    candidate_operator_ids: Sequence[str],
    operator_priors: Sequence[OperatorPriorInput],
    semantic_task_priors: Sequence[SemanticTaskPriorInput],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
    rng: np.random.Generator,
) -> SemanticPriorSamplerResult:
    candidates = tuple(str(operator_id) for operator_id in candidate_operator_ids)
    if not candidates:
        raise ValueError("Semantic prior sampler requires at least one candidate operator.")
    normalized_priors = _operator_prior_distribution(candidates, operator_priors)
    if not any(value > 0.0 for value in normalized_priors.values()):
        normalized_priors = _semantic_task_prior_distribution(candidates, semantic_task_priors)
    if not any(value > 0.0 for value in normalized_priors.values()):
        normalized_priors = {operator_id: 1.0 / float(len(candidates)) for operator_id in candidates}

    risk_by_operator = {
        str(prior.operator_id): _clamp_unit(prior.risk)
        for prior in operator_priors
        if str(prior.operator_id) in candidates
    }
    adjusted_weights = {
        operator_id: float(prior)
        * max(0.0, 1.0 - float(config.risk_penalty_weight) * float(risk_by_operator.get(operator_id, 0.5)))
        for operator_id, prior in normalized_priors.items()
    }
    adjusted_probabilities = _normalize_distribution(adjusted_weights, candidates)
    uniform_probability = 1.0 / float(len(candidates))
    mixed_probabilities = {
        operator_id: (1.0 - float(config.uniform_mix)) * adjusted_probabilities[operator_id]
        + float(config.uniform_mix) * uniform_probability
        for operator_id in candidates
    }

    suppressed, cap_reasons = _suppressed_by_caps(candidates, state, config)
    active_candidates = [operator_id for operator_id in candidates if operator_id not in suppressed]
    if not active_candidates:
        suppressed = set()
        cap_reasons = {}
        active_candidates = list(candidates)

    capped_probabilities = {
        operator_id: (0.0 if operator_id in suppressed else mixed_probabilities[operator_id])
        for operator_id in candidates
    }
    floored_probabilities = _apply_probability_floor(
        capped_probabilities,
        active_candidates,
        floor=float(config.min_probability_floor),
    )
    probabilities = _normalize_distribution(floored_probabilities, candidates)
    selected_operator_id = str(rng.choice(list(candidates), p=[probabilities[operator_id] for operator_id in candidates]))
    return SemanticPriorSamplerResult(
        selected_operator_id=selected_operator_id,
        selected_probability=float(probabilities[selected_operator_id]),
        sampler_probabilities={operator_id: float(probabilities[operator_id]) for operator_id in candidates},
        normalized_operator_priors={operator_id: float(normalized_priors.get(operator_id, 0.0)) for operator_id in candidates},
        adjusted_operator_weights={operator_id: float(adjusted_weights.get(operator_id, 0.0)) for operator_id in candidates},
        suppressed_operator_ids=tuple(operator_id for operator_id in candidates if operator_id in suppressed),
        cap_reasons={str(operator_id): str(reason) for operator_id, reason in cap_reasons.items()},
        config=config.to_dict(),
    )


def _operator_prior_distribution(
    candidates: tuple[str, ...],
    operator_priors: Sequence[OperatorPriorInput],
) -> dict[str, float]:
    weights = {operator_id: 0.0 for operator_id in candidates}
    for prior in operator_priors:
        operator_id = str(prior.operator_id)
        if operator_id in weights:
            weights[operator_id] = max(weights[operator_id], _clamp_unit(prior.prior))
    return _normalize_distribution(weights, candidates)


def _semantic_task_prior_distribution(
    candidates: tuple[str, ...],
    semantic_task_priors: Sequence[SemanticTaskPriorInput],
) -> dict[str, float]:
    task_weights: dict[str, float] = {}
    for prior in semantic_task_priors:
        task_id = str(prior.semantic_task).strip()
        if task_id:
            task_weights[task_id] = max(task_weights.get(task_id, 0.0), _clamp_unit(prior.prior))
    operator_weights = {operator_id: 0.0 for operator_id in candidates}
    for task_id, task_weight in task_weights.items():
        task_candidates = [operator_id for operator_id in candidates if semantic_task_for_operator(operator_id) == task_id]
        if not task_candidates:
            continue
        share = float(task_weight) / float(len(task_candidates))
        for operator_id in task_candidates:
            operator_weights[operator_id] += share
    return _normalize_distribution(operator_weights, candidates)


def _suppressed_by_caps(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
) -> tuple[set[str], dict[str, str]]:
    suppressed: set[str] = set()
    reasons: dict[str, str] = {}
    _apply_generation_cap(candidates, state, config, suppressed, reasons)
    _apply_rolling_operator_cap(candidates, state, config, suppressed, reasons)
    _apply_rolling_semantic_task_cap(candidates, state, config, suppressed, reasons)
    return suppressed, reasons


def _apply_generation_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
    suppressed: set[str],
    reasons: dict[str, str],
) -> None:
    memory = state.metadata.get("generation_local_memory")
    if not isinstance(memory, Mapping):
        return
    target = int(memory.get("target_offsprings") or 0)
    if target <= 0:
        return
    cap_count = max(1, int(math.ceil(float(target) * float(config.generation_operator_cap_fraction))))
    operator_counts = memory.get("operator_counts")
    if not isinstance(operator_counts, Mapping):
        return
    for operator_id in candidates:
        summary = operator_counts.get(operator_id)
        accepted_count = int(dict(summary).get("accepted_count", 0)) if isinstance(summary, Mapping) else 0
        if accepted_count >= cap_count:
            suppressed.add(operator_id)
            reasons[operator_id] = "generation_operator_cap"


def _apply_rolling_operator_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
    suppressed: set[str],
    reasons: dict[str, str],
) -> None:
    recent = _recent_operator_sequence(state, candidates, int(config.rolling_window))
    if not recent:
        return
    counter = Counter(recent)
    total = float(len(recent))
    for operator_id, count in counter.items():
        if float(count) / total >= float(config.rolling_operator_cap_fraction):
            suppressed.add(operator_id)
            reasons[operator_id] = "rolling_operator_cap"


def _apply_rolling_semantic_task_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
    suppressed: set[str],
    reasons: dict[str, str],
) -> None:
    recent = _recent_operator_sequence(state, candidates, int(config.rolling_window))
    if not recent:
        return
    task_counter = Counter(semantic_task_for_operator(operator_id) for operator_id in recent)
    total = float(len(recent))
    capped_tasks = {
        task_id
        for task_id, count in task_counter.items()
        if float(count) / total >= float(config.rolling_semantic_task_cap_fraction)
    }
    for operator_id in candidates:
        if semantic_task_for_operator(operator_id) in capped_tasks:
            suppressed.add(operator_id)
            reasons.setdefault(operator_id, "rolling_semantic_task_cap")


def _recent_operator_sequence(
    state: ControllerState,
    candidates: tuple[str, ...],
    rolling_window: int,
) -> tuple[str, ...]:
    recent_decisions = state.metadata.get("recent_decisions", [])
    sequence: list[str] = []
    for row in recent_decisions:
        if not isinstance(row, Mapping):
            continue
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if operator_id not in candidates:
            continue
        if row.get("fallback_used") is True:
            continue
        sequence.append(operator_id)
    return tuple(sequence[-max(1, int(rolling_window)):])


def _apply_probability_floor(
    probabilities: Mapping[str, float],
    active_candidates: Sequence[str],
    *,
    floor: float,
) -> dict[str, float]:
    active = tuple(str(operator_id) for operator_id in active_candidates)
    if not active:
        return {str(operator_id): float(value) for operator_id, value in probabilities.items()}
    floor_value = min(max(float(floor), 0.0), 1.0 / float(len(active)))
    floor_total = floor_value * float(len(active))
    remaining_mass = max(0.0, 1.0 - floor_total)
    active_sum = sum(max(float(probabilities.get(operator_id, 0.0)), 0.0) for operator_id in active)
    result = {str(operator_id): 0.0 for operator_id in probabilities}
    for operator_id in active:
        normalized = 1.0 / float(len(active)) if active_sum <= 0.0 else max(float(probabilities.get(operator_id, 0.0)), 0.0) / active_sum
        result[operator_id] = floor_value + remaining_mass * normalized
    return result


def _normalize_distribution(weights: Mapping[str, float], candidates: tuple[str, ...]) -> dict[str, float]:
    cleaned = {operator_id: max(float(weights.get(operator_id, 0.0)), 0.0) for operator_id in candidates}
    total = sum(cleaned.values())
    if total <= 0.0:
        return {operator_id: 1.0 / float(len(candidates)) for operator_id in candidates}
    return {operator_id: float(value) / float(total) for operator_id, value in cleaned.items()}


def _clamp_unit(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return float(numeric)
```

- [ ] **Step 4: Run sampler tests and fix exact probability expectations if needed**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_semantic_prior_sampler.py
```

Expected: PASS. If a probability assertion differs only because of deterministic normalization, update the assertion to the exact value produced by the implemented formula, not to a looser behavioral statement.

- [ ] **Step 5: Commit sampler**

```bash
git add optimizers/operator_pool/semantic_prior_sampler.py tests/optimizers/test_semantic_prior_sampler.py
git commit -m "feat: add semantic prior sampler"
```

---

### Task 3: Integrate Prior Strategy In LLM Controller

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Add controller integration test**

Append to `tests/optimizers/test_llm_controller.py`:

```python
def test_llm_controller_semantic_prior_sampler_records_probabilities() -> None:
    from llm.openai_compatible.client import (
        OpenAICompatiblePriorAdvice,
        OperatorPrior,
        SemanticTaskPrior,
    )

    class _PriorClient:
        def request_operator_prior_advice(self, **kwargs):
            return OpenAICompatiblePriorAdvice(
                operator_priors=(
                    OperatorPrior("component_subspace_sbx", prior=0.9, risk=0.0, confidence=0.9),
                    OperatorPrior("component_jitter_1", prior=0.1, risk=0.0, confidence=0.5),
                ),
                semantic_task_priors=(
                    SemanticTaskPrior("semantic_subspace_recombine", prior=0.8, risk=0.2, confidence=0.8),
                ),
                phase="post_feasible_expand",
                rationale="subspace has high prior but current generation is saturated",
                provider="openai-compatible",
                model="fake-model",
                capability_profile="chat_compatible_json",
                performance_profile="balanced",
                raw_payload={
                    "operator_priors": [
                        {"operator_id": "component_subspace_sbx", "prior": 0.9, "risk": 0.0, "confidence": 0.9},
                        {"operator_id": "component_jitter_1", "prior": 0.1, "risk": 0.0, "confidence": 0.5},
                    ],
                    "semantic_task_priors": [
                        {"semantic_task": "semantic_subspace_recombine", "prior": 0.8, "risk": 0.2, "confidence": 0.8}
                    ],
                    "phase": "post_feasible_expand",
                    "rationale": "subspace has high prior but current generation is saturated",
                },
            )

    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "model_env_var": "LLM_MODEL",
            "api_key_env_var": "LLM_API_KEY",
            "base_url_env_var": "LLM_BASE_URL",
            "selection_strategy": "semantic_prior_sampler",
            "semantic_prior_sampler": {
                "uniform_mix": 0.0,
                "min_probability_floor": 0.0,
                "generation_operator_cap_fraction": 0.35,
            },
        },
        client=_PriorClient(),
    )
    state = _state_with_metadata(
        {
            "decision_index": 7,
            "search_phase": "post_feasible_expand",
            "progress_state": {"phase": "post_feasible_expand", "post_feasible_mode": "expand"},
            "generation_local_memory": {
                "accepted_count": 7,
                "target_offsprings": 20,
                "operator_counts": {"component_subspace_sbx": {"accepted_count": 7}},
            },
            "recent_decisions": [],
            "prompt_panels": {
                "run_panel": {"feasible_rate": 0.55, "pareto_size": 2},
                "operator_panel": {"rows": []},
                "semantic_task_panel": {
                    "recommended_task_order": ["semantic_subspace_recombine", "local_polish"],
                    "task_operator_candidates": {
                        "semantic_subspace_recombine": ["component_subspace_sbx"],
                        "local_polish": ["component_jitter_1"],
                    },
                },
            },
        }
    )

    decision = controller.select_decision(
        state,
        ("component_subspace_sbx", "component_jitter_1"),
        np.random.default_rng(3),
    )

    assert decision.selected_operator_id == "component_jitter_1"
    assert decision.metadata["selection_strategy"] == "semantic_prior_sampler"
    assert decision.metadata["selected_semantic_task"] == "local_polish"
    assert decision.metadata["sampler_probabilities"]["component_subspace_sbx"] == 0.0
    assert decision.metadata["sampler_probabilities"]["component_jitter_1"] == 1.0
    assert decision.metadata["selected_probability"] == 1.0
    assert "component_subspace_sbx" in decision.metadata["sampler_suppressed_operator_ids"]
    assert controller.response_trace[0]["selected_operator_id"] == "component_jitter_1"
    assert controller.response_trace[0]["llm_operator_priors"][0]["operator_id"] == "component_subspace_sbx"
    assert controller.response_trace[0]["sampler_probabilities"]["component_jitter_1"] == 1.0
```

If `_state_with_metadata` is not available in the final local test file scope, add this helper near the other controller test helpers:

```python
def _state_with_metadata(metadata: dict[str, object]) -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=120,
        parent_count=2,
        vector_size=32,
        metadata=metadata,
    )
```

- [ ] **Step 2: Run integration test and confirm it fails**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller.py::test_llm_controller_semantic_prior_sampler_records_probabilities
```

Expected: FAIL because `selection_strategy` and prior sampling are not wired into `LLMOperatorController`.

- [ ] **Step 3: Add imports and config fields**

Modify imports in `optimizers/operator_pool/llm_controller.py`:

```python
from llm.openai_compatible.client import OpenAICompatiblePriorAdvice
from optimizers.operator_pool.semantic_prior_sampler import (
    OperatorPriorInput,
    SemanticPriorSamplerConfig,
    SemanticTaskPriorInput,
    sample_operator_from_semantic_priors,
)
from optimizers.operator_pool.semantic_tasks import semantic_task_for_operator
```

If `semantic_task_for_operator` is already imported, keep a single import.

Inside `LLMOperatorController.__init__(...)`, add after fallback setup:

```python
self.selection_strategy = str(self.controller_parameters.get("selection_strategy", "direct_operator")).strip()
if self.selection_strategy not in {"direct_operator", "semantic_prior_sampler"}:
    raise ValueError(f"Unsupported llm selection_strategy '{self.selection_strategy}'.")
self.semantic_prior_sampler_config = SemanticPriorSamplerConfig.from_mapping(
    self.controller_parameters.get("semantic_prior_sampler")
)
```

- [ ] **Step 4: Add prior prompt helper**

Add near `_build_system_prompt(...)`:

```python
def _build_prior_system_prompt(
    self,
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    *,
    policy_snapshot: PolicySnapshot,
    guardrail: dict[str, Any] | None,
) -> str:
    del candidate_operator_ids
    prompt = (
        "Return semantic/operator priors for constrained thermal MOO; do not return a final selected operator. "
        "Estimate probability mass over semantic tasks and candidate operators from metadata.decision_axes, "
        "operator_panel, semantic_task_panel, phase, objective balance, feasibility pressure, retrieval evidence, "
        "recent exposure, and risk. Keep priors calibrated: low sample support means lower confidence. "
        "Penalize recently saturated operators and saturated semantic tasks. "
        "The downstream sampler will enforce exposure caps and sample from your priors. Return JSON only."
    )
    phase_policy_guidance = self._build_phase_policy_guidance(policy_snapshot)
    if phase_policy_guidance:
        prompt = f"{prompt} {phase_policy_guidance}"
    objective_balance_guidance = self._build_objective_balance_guidance(state, policy_snapshot.allowed_operator_ids)
    if objective_balance_guidance:
        prompt = f"{prompt} {objective_balance_guidance}"
    if guardrail is not None and str(guardrail.get("dominant_operator_id", "")).strip():
        prompt = (
            f"{prompt} Recent dominance advice is provided as context; express it by lowering prior mass "
            "for saturated choices when alternatives are applicable."
        )
    return prompt
```

- [ ] **Step 5: Add prior request helper**

Add near `_request_operator_decision(...)`:

```python
def _request_operator_prior_advice(
    self,
    *,
    system_prompt: str,
    user_prompt: str,
    candidate_operator_ids: Sequence[str],
    attempt_trace: list[dict[str, Any]],
) -> OpenAICompatiblePriorAdvice:
    if not hasattr(self.client, "request_operator_prior_advice"):
        raise TypeError("Configured LLM client does not support request_operator_prior_advice.")
    return self.client.request_operator_prior_advice(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        candidate_operator_ids=candidate_operator_ids,
        attempt_trace=attempt_trace,
    )
```

- [ ] **Step 6: Add conversion helpers for trace metadata**

Add static helpers near other metadata helpers:

```python
@staticmethod
def _operator_prior_inputs(advice: OpenAICompatiblePriorAdvice) -> tuple[OperatorPriorInput, ...]:
    return tuple(
        OperatorPriorInput(
            operator_id=prior.operator_id,
            prior=prior.prior,
            risk=prior.risk,
            confidence=prior.confidence,
            rationale=prior.rationale,
        )
        for prior in advice.operator_priors
    )


@staticmethod
def _semantic_task_prior_inputs(advice: OpenAICompatiblePriorAdvice) -> tuple[SemanticTaskPriorInput, ...]:
    return tuple(
        SemanticTaskPriorInput(
            semantic_task=prior.semantic_task,
            prior=prior.prior,
            risk=prior.risk,
            confidence=prior.confidence,
        )
        for prior in advice.semantic_task_priors
    )


@staticmethod
def _operator_prior_trace_rows(advice: OpenAICompatiblePriorAdvice) -> list[dict[str, Any]]:
    return [
        {
            "operator_id": prior.operator_id,
            "prior": float(prior.prior),
            "risk": float(prior.risk),
            "confidence": float(prior.confidence),
            "rationale": prior.rationale,
        }
        for prior in advice.operator_priors
    ]


@staticmethod
def _semantic_task_prior_trace_rows(advice: OpenAICompatiblePriorAdvice) -> list[dict[str, Any]]:
    return [
        {
            "semantic_task": prior.semantic_task,
            "prior": float(prior.prior),
            "risk": float(prior.risk),
            "confidence": float(prior.confidence),
        }
        for prior in advice.semantic_task_priors
    ]
```

- [ ] **Step 7: Split `select_decision(...)` by strategy**

In `select_decision(...)`, keep the existing logic for building `policy_snapshot`, `guardrail`, `entry_convert_metadata`, `prompt_metadata`, `user_prompt`, `request_surface`, `decision_id`, and `input_state_digest`.

Replace the current `system_prompt = self._build_system_prompt(...)` line with:

```python
if self.selection_strategy == "semantic_prior_sampler":
    system_prompt = self._build_prior_system_prompt(
        state,
        candidate_operator_ids,
        policy_snapshot=policy_snapshot,
        guardrail=guardrail,
    )
else:
    system_prompt = self._build_system_prompt(
        state,
        candidate_operator_ids,
        policy_snapshot=policy_snapshot,
        guardrail=guardrail,
    )
```

Then, immediately before the existing direct `_request_operator_decision(...)` try block, add:

```python
if self.selection_strategy == "semantic_prior_sampler":
    return self._select_decision_from_semantic_prior(
        state=state,
        rng=rng,
        candidate_operator_ids=candidate_operator_ids,
        original_candidate_operator_ids=original_candidate_operator_ids,
        policy_snapshot=policy_snapshot,
        guardrail=guardrail,
        entry_convert_metadata=entry_convert_metadata,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        request_surface=request_surface,
        request_entry=request_entry,
        decision_id=decision_id,
        input_state_digest=input_state_digest,
    )
```

- [ ] **Step 8: Implement `_select_decision_from_semantic_prior`**

Add this method inside `LLMOperatorController` before `_record_elapsed_seconds(...)`:

```python
def _select_decision_from_semantic_prior(
    self,
    *,
    state: ControllerState,
    rng: np.random.Generator,
    candidate_operator_ids: Sequence[str],
    original_candidate_operator_ids: Sequence[str],
    policy_snapshot: PolicySnapshot,
    guardrail: dict[str, Any] | None,
    entry_convert_metadata: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    request_surface: dict[str, Any],
    request_entry: dict[str, Any],
    decision_id: str,
    input_state_digest: str,
) -> ControllerDecision:
    del original_candidate_operator_ids
    self.request_trace.append(request_entry)
    self.metrics["request_count"] = int(self.metrics["request_count"]) + 1
    started_at = time.perf_counter()
    attempt_trace: list[dict[str, Any]] = []
    try:
        advice = self._request_operator_prior_advice(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            candidate_operator_ids=candidate_operator_ids,
            attempt_trace=attempt_trace,
        )
        sampler_result = sample_operator_from_semantic_priors(
            candidate_operator_ids=candidate_operator_ids,
            operator_priors=self._operator_prior_inputs(advice),
            semantic_task_priors=self._semantic_task_prior_inputs(advice),
            state=state,
            config=self.semantic_prior_sampler_config,
            rng=rng,
        )
    except Exception as exc:
        elapsed_seconds = max(0.0, float(time.perf_counter() - started_at))
        self.metrics["fallback_count"] = int(self.metrics["fallback_count"]) + 1
        self._record_attempt_metrics(attempt_trace)
        self._record_elapsed_seconds(elapsed_seconds)
        fallback_decision = self.fallback_controller.select_decision(state, candidate_operator_ids, rng)
        response_entry = {
            "decision_id": decision_id,
            "generation_index": state.generation_index,
            "evaluation_index": state.evaluation_index,
            "decision_index": (
                None if state.metadata.get("decision_index") is None else int(state.metadata.get("decision_index"))
            ),
            "provider": self.config.provider,
            "model": self.config.model,
            "candidate_operator_ids": list(candidate_operator_ids),
            "selection_strategy": self.selection_strategy,
            "policy_phase": policy_snapshot.phase,
            "phase_source": "policy_kernel",
            "model_phase": "",
            "model_rationale_present": False,
            "policy_reason_codes": list(policy_snapshot.reason_codes),
            "policy_reset_active": policy_snapshot.reset_active,
            "guardrail": None if guardrail is None else dict(guardrail),
            "fallback_used": True,
            "error": str(exc),
            "attempt_trace": list(attempt_trace),
            "attempt_count": int(len(attempt_trace)),
            "retry_count": int(max(0, len(attempt_trace) - 1)),
            "elapsed_seconds": elapsed_seconds,
            "accepted_for_evaluation": False,
            "accepted_evaluation_indices": [],
            "accepted_evaluation_index": None,
            "rejection_reason": str(exc),
            **entry_convert_metadata,
        }
        self.response_trace.append(response_entry)
        prompt_ref, response_ref = self._emit_controller_trace(
            decision_id=decision_id,
            phase=policy_snapshot.phase,
            operator_selected=fallback_decision.selected_operator_id,
            operator_pool_snapshot=list(candidate_operator_ids),
            input_state_digest=input_state_digest,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_body=str(exc),
            rationale="",
            fallback_used=True,
            latency_ms=elapsed_seconds * 1000.0,
            http_status=None,
            retries=max(0, len(attempt_trace) - 1),
            tokens=None,
            finish_reason=None,
            request_surface=request_entry,
            response_surface=response_entry,
        )
        if prompt_ref is not None:
            request_entry["prompt_ref"] = prompt_ref
        if response_ref is not None:
            response_entry["response_ref"] = response_ref
        metadata = dict(fallback_decision.metadata)
        metadata.update(
            {
                "decision_id": decision_id,
                "selection_strategy": self.selection_strategy,
                "fallback_used": True,
                "fallback_controller": self.fallback_controller_id,
                "fallback_reason": str(exc),
                "elapsed_seconds": elapsed_seconds,
                **self._decision_phase_metadata(
                    policy_phase=policy_snapshot.phase,
                    model_phase="",
                    model_rationale_present=False,
                ),
                **entry_convert_metadata,
                **self._selected_entry_metadata(policy_snapshot, fallback_decision.selected_operator_id),
                "guardrail_reason_codes": list(policy_snapshot.reason_codes),
            }
        )
        metadata.update(self._decision_guardrail_metadata(guardrail))
        return ControllerDecision(
            selected_operator_id=fallback_decision.selected_operator_id,
            phase=policy_snapshot.phase,
            rationale=fallback_decision.rationale,
            metadata=metadata,
        )

    elapsed_seconds = max(0.0, float(time.perf_counter() - started_at))
    self.metrics["response_count"] = int(self.metrics["response_count"]) + 1
    self._record_attempt_metrics(attempt_trace)
    self._record_elapsed_seconds(elapsed_seconds)
    selected_operator_id = sampler_result.selected_operator_id
    selected_semantic_task = semantic_task_for_operator(selected_operator_id)
    llm_operator_priors = self._operator_prior_trace_rows(advice)
    llm_semantic_task_priors = self._semantic_task_prior_trace_rows(advice)
    response_entry = {
        "decision_id": decision_id,
        "generation_index": state.generation_index,
        "evaluation_index": state.evaluation_index,
        "decision_index": (
            None if state.metadata.get("decision_index") is None else int(state.metadata.get("decision_index"))
        ),
        "provider": advice.provider,
        "model": advice.model,
        "capability_profile": advice.capability_profile,
        "performance_profile": advice.performance_profile,
        "selected_operator_id": selected_operator_id,
        "selected_semantic_task": selected_semantic_task,
        "selected_intent": None,
        "selection_strategy": self.selection_strategy,
        "phase": policy_snapshot.phase,
        "phase_source": "policy_kernel",
        "model_phase": advice.phase,
        "model_rationale_present": bool(advice.rationale.strip()),
        "rationale": advice.rationale,
        "raw_payload": dict(advice.raw_payload),
        "llm_operator_priors": llm_operator_priors,
        "llm_semantic_task_priors": llm_semantic_task_priors,
        "sampler_probabilities": dict(sampler_result.sampler_probabilities),
        "selected_probability": float(sampler_result.selected_probability),
        "sampler_suppressed_operator_ids": list(sampler_result.suppressed_operator_ids),
        "sampler_cap_reasons": dict(sampler_result.cap_reasons),
        "sampler_config": dict(sampler_result.config),
        "candidate_operator_ids": list(candidate_operator_ids),
        "guardrail": None if guardrail is None else dict(guardrail),
        "fallback_used": False,
        "policy_phase": policy_snapshot.phase,
        "policy_reason_codes": list(policy_snapshot.reason_codes),
        "policy_reset_active": policy_snapshot.reset_active,
        "attempt_trace": list(attempt_trace),
        "attempt_count": int(len(attempt_trace)),
        "retry_count": int(max(0, len(attempt_trace) - 1)),
        "elapsed_seconds": elapsed_seconds,
        "accepted_for_evaluation": False,
        "accepted_evaluation_indices": [],
        "accepted_evaluation_index": None,
        "rejection_reason": "",
        **entry_convert_metadata,
        **self._selected_entry_metadata(policy_snapshot, selected_operator_id),
    }
    self.response_trace.append(response_entry)
    prompt_ref, response_ref = self._emit_controller_trace(
        decision_id=decision_id,
        phase=policy_snapshot.phase,
        operator_selected=selected_operator_id,
        operator_pool_snapshot=list(candidate_operator_ids),
        input_state_digest=input_state_digest,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_body=json.dumps(advice.raw_payload, ensure_ascii=False, indent=2),
        rationale=advice.rationale,
        fallback_used=False,
        latency_ms=elapsed_seconds * 1000.0,
        http_status=None,
        retries=max(0, len(attempt_trace) - 1),
        tokens=None,
        finish_reason=None,
        request_surface=request_entry,
        response_surface=response_entry,
    )
    if prompt_ref is not None:
        request_entry["prompt_ref"] = prompt_ref
    if response_ref is not None:
        response_entry["response_ref"] = response_ref
    response_metadata = {
        "decision_id": decision_id,
        "provider": advice.provider,
        "model": advice.model,
        "capability_profile": advice.capability_profile,
        "performance_profile": advice.performance_profile,
        "raw_payload": dict(advice.raw_payload),
        "selection_strategy": self.selection_strategy,
        "selected_semantic_task": selected_semantic_task,
        "selected_intent": None,
        "fallback_used": False,
        "elapsed_seconds": elapsed_seconds,
        "llm_operator_priors": llm_operator_priors,
        "llm_semantic_task_priors": llm_semantic_task_priors,
        "sampler_probabilities": dict(sampler_result.sampler_probabilities),
        "selected_probability": float(sampler_result.selected_probability),
        "sampler_suppressed_operator_ids": list(sampler_result.suppressed_operator_ids),
        "sampler_cap_reasons": dict(sampler_result.cap_reasons),
        "sampler_config": dict(sampler_result.config),
        **self._decision_phase_metadata(
            policy_phase=policy_snapshot.phase,
            model_phase=advice.phase,
            model_rationale_present=bool(advice.rationale.strip()),
        ),
        **entry_convert_metadata,
        **self._selected_entry_metadata(policy_snapshot, selected_operator_id),
        "guardrail_reason_codes": list(policy_snapshot.reason_codes),
    }
    response_metadata.update(self._decision_guardrail_metadata(guardrail))
    return ControllerDecision(
        selected_operator_id=selected_operator_id,
        phase=policy_snapshot.phase,
        rationale=advice.rationale,
        metadata=response_metadata,
    )
```

- [ ] **Step 9: Run controller integration test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller.py::test_llm_controller_semantic_prior_sampler_records_probabilities
```

Expected: PASS.

- [ ] **Step 10: Run full LLM controller focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller.py
```

Expected: PASS. Existing direct-selector tests should keep passing because default `selection_strategy` is `direct_operator`.

- [ ] **Step 11: Commit controller integration**

```bash
git add optimizers/operator_pool/llm_controller.py tests/optimizers/test_llm_controller.py
git commit -m "feat: sample llm semantic prior advice"
```

---

### Task 4: Enable New Strategy In Active LLM Specs

**Files:**
- Modify: `scenarios/optimization/s5_aggressive15_llm.yaml`
- Modify: `scenarios/optimization/s6_aggressive20_llm.yaml`
- Modify: `scenarios/optimization/s7_aggressive25_llm.yaml`
- Modify: `tests/optimizers/test_optimizer_io.py`
- Modify: `tests/optimizers/test_s5_aggressive15_specs.py`
- Modify: `tests/optimizers/test_s6_aggressive20_specs.py`
- Modify: `tests/optimizers/test_s7_aggressive25_specs.py`

- [ ] **Step 1: Add S5 spec assertion**

In `tests/optimizers/test_s5_aggressive15_specs.py`, add assertions in the existing LLM spec test:

```python
params = llm["operator_control"]["controller_parameters"]
assert params["selection_strategy"] == "semantic_prior_sampler"
assert params["max_output_tokens"] == 512
assert params["semantic_prior_sampler"] == {
    "uniform_mix": 0.15,
    "min_probability_floor": 0.03,
    "generation_operator_cap_fraction": 0.35,
    "rolling_operator_cap_fraction": 0.40,
    "rolling_semantic_task_cap_fraction": 0.55,
    "rolling_window": 16,
    "risk_penalty_weight": 0.50,
}
```

- [ ] **Step 2: Add optimizer IO acceptance test**

Append to `tests/optimizers/test_optimizer_io.py`:

```python
def test_llm_spec_accepts_semantic_prior_sampler_parameters() -> None:
    spec = load_optimization_spec("scenarios/optimization/s5_aggressive15_llm.yaml")
    params = spec.operator_control["controller_parameters"]

    assert params["selection_strategy"] == "semantic_prior_sampler"
    assert params["semantic_prior_sampler"]["rolling_window"] == 16
    assert params["semantic_prior_sampler"]["generation_operator_cap_fraction"] == pytest.approx(0.35)
```

- [ ] **Step 3: Run spec tests and confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_s5_aggressive15_specs.py \
  tests/optimizers/test_optimizer_io.py::test_llm_spec_accepts_semantic_prior_sampler_parameters
```

Expected: FAIL because LLM YAML files have not been updated.

- [ ] **Step 4: Update active LLM YAML controller parameters**

In each active LLM spec listed in the file map, under `operator_control.controller_parameters`, set:

```yaml
    max_output_tokens: 512
    selection_strategy: semantic_prior_sampler
    semantic_prior_sampler:
      uniform_mix: 0.15
      min_probability_floor: 0.03
      generation_operator_cap_fraction: 0.35
      rolling_operator_cap_fraction: 0.40
      rolling_semantic_task_cap_fraction: 0.55
      rolling_window: 16
      risk_penalty_weight: 0.50
```

Keep existing provider/model/retry/memory/fallback fields unchanged. Do not edit any raw or union YAML.

- [ ] **Step 5: Run spec tests again**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_s5_aggressive15_specs.py \
  tests/optimizers/test_optimizer_io.py::test_llm_spec_accepts_semantic_prior_sampler_parameters
```

Expected: PASS.

- [ ] **Step 6: Confirm raw and union specs are not modified**

Run:

```bash
git diff -- scenarios/optimization/*_raw.yaml scenarios/optimization/*_union.yaml
```

Expected: no diff output for raw/union specs.

- [ ] **Step 7: Commit spec activation**

```bash
git add \
  scenarios/optimization/s5_aggressive15_llm.yaml \
  scenarios/optimization/s6_aggressive20_llm.yaml \
  scenarios/optimization/s7_aggressive25_llm.yaml \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_s5_aggressive15_specs.py \
  tests/optimizers/test_s6_aggressive20_specs.py \
  tests/optimizers/test_s7_aggressive25_specs.py
git commit -m "feat: enable semantic prior sampler for llm specs"
```

---

### Task 5: Trace Contract And Focused Verification

**Files:**
- Modify: `tests/optimizers/test_controller_trace_new_schema.py`
- Modify: `tests/optimizers/test_llm_decision_summary.py` only if summary tests need to account for new metadata.

- [ ] **Step 1: Add trace schema coverage for prior fields**

Append to `tests/optimizers/test_controller_trace_new_schema.py`:

```python
def test_llm_semantic_prior_trace_surfaces_sampler_metadata(tmp_path: Path) -> None:
    from llm.openai_compatible.client import (
        OpenAICompatiblePriorAdvice,
        OperatorPrior,
    )

    class _PriorClient:
        def request_operator_prior_advice(self, **kwargs):
            return OpenAICompatiblePriorAdvice(
                operator_priors=(
                    OperatorPrior("component_jitter_1", prior=1.0, risk=0.0, confidence=0.9),
                ),
                semantic_task_priors=(),
                phase="post_feasible_preserve",
                rationale="bounded local polish",
                provider="openai-compatible",
                model="fake-model",
                capability_profile="chat_compatible_json",
                performance_profile="balanced",
                raw_payload={
                    "operator_priors": [
                        {"operator_id": "component_jitter_1", "prior": 1.0, "risk": 0.0, "confidence": 0.9}
                    ],
                    "phase": "post_feasible_preserve",
                    "rationale": "bounded local polish",
                },
            )

    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "model_env_var": "LLM_MODEL",
            "api_key_env_var": "LLM_API_KEY",
            "base_url_env_var": "LLM_BASE_URL",
            "selection_strategy": "semantic_prior_sampler",
        },
        client=_PriorClient(),
    )
    controller.configure_trace_outputs(
        controller_trace_path=tmp_path / "controller_trace.jsonl",
        llm_request_trace_path=tmp_path / "llm_request_trace.jsonl",
        llm_response_trace_path=tmp_path / "llm_response_trace.jsonl",
        prompt_store=PromptStore(tmp_path / "prompts"),
    )
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=42,
        parent_count=2,
        vector_size=32,
        metadata={
            "decision_index": 3,
            "search_phase": "post_feasible_preserve",
            "progress_state": {"phase": "post_feasible_preserve", "post_feasible_mode": "preserve"},
            "prompt_panels": {"run_panel": {}, "operator_panel": {"rows": []}},
            "recent_decisions": [],
        },
    )

    controller.select_decision(state, ("component_jitter_1", "sink_shift"), np.random.default_rng(1))

    response_rows = [json.loads(line) for line in (tmp_path / "llm_response_trace.jsonl").read_text().splitlines()]
    assert response_rows[0]["selection_strategy"] == "semantic_prior_sampler"
    assert response_rows[0]["llm_operator_priors"][0]["operator_id"] == "component_jitter_1"
    assert response_rows[0]["sampler_probabilities"]["component_jitter_1"] > 0.0
    assert response_rows[0]["selected_probability"] > 0.0
```

Add imports at the top of the test file if missing:

```python
import json
import numpy as np
from optimizers.operator_pool.llm_controller import LLMOperatorController
from optimizers.operator_pool.state import ControllerState
from optimizers.traces.prompt_store import PromptStore
```

- [ ] **Step 2: Run trace test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_controller_trace_new_schema.py::test_llm_semantic_prior_trace_surfaces_sampler_metadata
```

Expected: PASS after Task 3 implementation.

- [ ] **Step 3: Run focused LLM tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_semantic_prior_sampler.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_controller_trace_new_schema.py \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_s5_aggressive15_specs.py
```

Expected: PASS.

- [ ] **Step 4: Run ladder contract tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_algorithm_ladder_contracts.py \
  tests/optimizers/test_operator_pool_contracts.py
```

Expected: PASS.

- [ ] **Step 5: Check raw/union cleanliness**

Run:

```bash
git diff --name-only -- scenarios/optimization/*_raw.yaml scenarios/optimization/*_union.yaml optimizers/operator_pool/random_controller.py optimizers/drivers/raw_driver.py optimizers/drivers/union_driver.py
```

Expected: no output.

- [ ] **Step 6: Check formatting whitespace**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 7: Commit trace and verification updates**

```bash
git add tests/optimizers/test_controller_trace_new_schema.py
git commit -m "test: cover llm semantic prior trace metadata"
```

---

## Post-Implementation Run Guidance

After all focused tests pass, use a cheap run before spending GPT 20×10 budget:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-llm gpt \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --population-size 10 \
  --num-generations 5 \
  --output-root ./scenario_runs/s5_aggressive15/<MMDD_HHMM>__llm_gpt_10x5_semantic_prior
```

Then render:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli render-assets \
  --run ./scenario_runs/s5_aggressive15/<MMDD_HHMM>__llm_gpt_10x5_semantic_prior
```

Inspect:

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

run = Path("./scenario_runs/s5_aggressive15/<MMDD_HHMM>__llm_gpt_10x5_semantic_prior/llm/seeds/seed-11/traces/llm_response_trace.jsonl")
rows = [json.loads(line) for line in run.read_text().splitlines() if line.strip()]
print("selection_strategy", Counter(row.get("selection_strategy") for row in rows))
print("selected_operator", Counter(row.get("selected_operator_id") for row in rows))
print("has_priors", sum(1 for row in rows if row.get("llm_operator_priors")))
print("has_sampler_probabilities", sum(1 for row in rows if row.get("sampler_probabilities")))
PY
```

Expected:

- `selection_strategy` is `semantic_prior_sampler`.
- `has_priors` equals response row count.
- `has_sampler_probabilities` equals response row count.
- No late-generation collapse into only `component_subspace_sbx` and `sink_shift`.

Only after this smoke passes should a 20×10 S5 GPT run be used for paper-facing comparison.

---

## Self-Review Checklist

- Spec coverage: prior contract, sampler, controller integration, LLM-only YAML activation, trace metadata, raw/union cleanliness are each covered by tasks.
- Baseline scope: `llm_direct` and `uniform_prior_sampler` are not implemented in this plan.
- Type consistency: plan uses `OpenAICompatiblePriorAdvice`, `OperatorPrior`, `SemanticTaskPrior`, `SemanticPriorSamplerConfig`, and `SemanticPriorSamplerResult` consistently.
- Test order: each implementation task begins with a failing focused test.
- Verification: focused LLM tests, ladder contracts, raw/union diff check, and `git diff --check` are included.
