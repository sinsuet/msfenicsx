# LLM Semantic Ranker Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the LLM-only `semantic_ranked_pick` route so the model returns an ordered semantic/operator ranking and the controller deterministically picks the highest ranked non-saturated operator.

**Architecture:** Keep `raw` and `union` unchanged, keep the current semantic taxonomy, semantic task panels, adaptive sink gate, summary logic, and existing `semantic_prior_sampler` legacy path. Add a parallel rank-advice client contract, a focused deterministic ranked picker, and a new `LLMOperatorController` strategy branch; switch only active LLM YAMLs to the new strategy.

**Tech Stack:** Python 3.12, pytest, existing OpenAI-compatible client, existing `ControllerState`, existing LLM trace JSONL writers, YAML optimization specs.

---

## File Map

- Modify: `llm/openai_compatible/schemas.py`
  - Add `build_operator_rank_advice_schema(...)`.
- Modify: `llm/openai_compatible/client.py`
  - Add `RankedOperatorCandidate`, `OpenAICompatibleRankAdvice`.
  - Add `request_operator_rank_advice(...)`, parser, retry prompt, and chat JSON instruction branch.
- Create: `optimizers/operator_pool/semantic_ranked_picker.py`
  - Own deterministic ranked-pick config, cap calculation, missing-candidate tail append, low-confidence near-tie risk tiebreak, and result payload.
- Modify: `optimizers/operator_pool/llm_controller.py`
  - Add `selection_strategy == "semantic_ranked_pick"` branch.
  - Add rank prompt, rank-advice request wrapper, rank input/trace helpers, fallback metadata, and response trace metadata.
- Modify: active LLM specs only:
  - `scenarios/optimization/s1_typical_llm.yaml`
  - `scenarios/optimization/s2_staged_llm.yaml`
  - `scenarios/optimization/s3_scale20_llm.yaml`
  - `scenarios/optimization/s4_dense25_llm.yaml`
  - `scenarios/optimization/s5_aggressive15_llm.yaml`
- Modify tests:
  - `tests/optimizers/test_llm_client.py`
  - `tests/optimizers/test_semantic_ranked_picker.py`
  - `tests/optimizers/test_llm_controller.py`
  - `tests/optimizers/test_controller_trace_new_schema.py`
  - `tests/optimizers/test_optimizer_io.py`
  - `tests/optimizers/test_s5_aggressive15_specs.py`

Do not modify:

- `scenarios/optimization/*_raw.yaml`
- `scenarios/optimization/*_union.yaml`
- `optimizers/drivers/raw_driver.py`
- `optimizers/drivers/union_driver.py`
- `optimizers/operator_pool/random_controller.py`
- primitive operator definitions or registry profiles

---

### Task 1: Rank Advice Schema And Client Parser

**Files:**
- Modify: `llm/openai_compatible/schemas.py`
- Modify: `llm/openai_compatible/client.py`
- Modify: `tests/optimizers/test_llm_client.py`

- [ ] **Step 1: Write the failing schema test**

Append to `tests/optimizers/test_llm_client.py`:

```python
def test_operator_rank_advice_schema_requires_ranked_operators() -> None:
    from llm.openai_compatible.schemas import build_operator_rank_advice_schema

    schema = build_operator_rank_advice_schema(("sink_shift", "component_jitter_1"))

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert "ranked_operators" in schema["required"]
    ranked_items = schema["properties"]["ranked_operators"]["items"]
    assert ranked_items["additionalProperties"] is False
    assert ranked_items["required"] == [
        "operator_id",
        "semantic_task",
        "score",
        "risk",
        "confidence",
        "rationale",
    ]
    assert ranked_items["properties"]["operator_id"]["enum"] == [
        "sink_shift",
        "component_jitter_1",
    ]
    for key in ("score", "risk", "confidence"):
        assert ranked_items["properties"][key]["minimum"] == 0.0
        assert ranked_items["properties"][key]["maximum"] == 1.0
```

- [ ] **Step 2: Run the schema test and verify red**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_client.py::test_operator_rank_advice_schema_requires_ranked_operators
```

Expected: FAIL with `ImportError` or `AttributeError` for `build_operator_rank_advice_schema`.

- [ ] **Step 3: Add parser tests**

Append to `tests/optimizers/test_llm_client.py`:

```python
def test_chat_compatible_json_client_parses_operator_rank_advice() -> None:
    chat_api = _FakeChatCompletionsAPI(
        '{"phase":"post_feasible_expand",'
        '"rationale":"rank sink alignment above local cleanup",'
        '"ranked_operators":['
        '{"operator_id":"sink_shift","semantic_task":"sink_alignment","score":0.82,'
        '"risk":0.22,"confidence":0.74,"rationale":"align sink"},'
        '{"operator_id":"component_jitter_1","semantic_task":"local_polish","score":0.71,'
        '"risk":0.18,"confidence":0.61,"rationale":"bounded local move"}'
        "]}",
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    advice = client.request_operator_rank_advice(
        system_prompt="return ranked operators",
        user_prompt="{}",
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
    )

    assert advice.phase == "post_feasible_expand"
    assert advice.rationale == "rank sink alignment above local cleanup"
    assert advice.ranked_operators[0].operator_id == "sink_shift"
    assert advice.ranked_operators[0].semantic_task == "sink_alignment"
    assert advice.ranked_operators[0].score == pytest.approx(0.82)
    assert advice.ranked_operators[0].risk == pytest.approx(0.22)
    assert advice.ranked_operators[0].confidence == pytest.approx(0.74)
    assert chat_api.last_kwargs is not None
    system_message = str(chat_api.last_kwargs["messages"][0]["content"])
    assert "ranked_operators" in system_message
    assert "operator_priors" not in system_message


def test_operator_rank_advice_rejects_unknown_operator_id() -> None:
    chat_api = _FakeChatCompletionsAPI(
        '{"ranked_operators":[{"operator_id":"not_in_pool","semantic_task":"local_polish",'
        '"score":0.8,"risk":0.1,"confidence":0.6,"rationale":"bad id"}]}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    with pytest.raises(ValueError, match="outside the requested operator registry"):
        client.request_operator_rank_advice(
            system_prompt="return ranked operators",
            user_prompt="{}",
            candidate_operator_ids=("sink_shift", "component_jitter_1"),
        )


def test_operator_rank_advice_requires_explicit_risk_and_confidence() -> None:
    chat_api = _FakeChatCompletionsAPI(
        '{"ranked_operators":[{"operator_id":"sink_shift","semantic_task":"sink_alignment",'
        '"score":0.8,"confidence":0.6,"rationale":"missing risk"}]}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    with pytest.raises(ValueError, match="risk"):
        client.request_operator_rank_advice(
            system_prompt="return ranked operators",
            user_prompt="{}",
            candidate_operator_ids=("sink_shift", "component_jitter_1"),
        )
```

- [ ] **Step 4: Run parser tests and verify red**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_llm_client.py::test_chat_compatible_json_client_parses_operator_rank_advice \
  tests/optimizers/test_llm_client.py::test_operator_rank_advice_rejects_unknown_operator_id \
  tests/optimizers/test_llm_client.py::test_operator_rank_advice_requires_explicit_risk_and_confidence
```

Expected: FAIL because `request_operator_rank_advice` and rank dataclasses do not exist.

- [ ] **Step 5: Implement the schema helper**

In `llm/openai_compatible/schemas.py`, add below `build_operator_prior_advice_schema(...)`:

```python
def build_operator_rank_advice_schema(candidate_operator_ids: Sequence[str]) -> dict[str, Any]:
    operator_ids = [str(operator_id) for operator_id in candidate_operator_ids]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "phase": {"type": "string"},
            "rationale": {"type": "string"},
            "ranked_operators": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "operator_id": {"type": "string", "enum": operator_ids},
                        "semantic_task": {"type": "string"},
                        "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "risk": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "rationale": {"type": "string"},
                    },
                    "required": [
                        "operator_id",
                        "semantic_task",
                        "score",
                        "risk",
                        "confidence",
                        "rationale",
                    ],
                },
            },
        },
        "required": ["ranked_operators"],
    }
```

- [ ] **Step 6: Implement rank dataclasses and parser**

In `llm/openai_compatible/client.py`, update the schema import:

```python
from llm.openai_compatible.schemas import (
    build_operator_decision_schema,
    build_operator_prior_advice_schema,
    build_operator_rank_advice_schema,
)
```

Add below `OpenAICompatiblePriorAdvice`:

```python
@dataclass(frozen=True, slots=True)
class RankedOperatorCandidate:
    operator_id: str
    semantic_task: str
    score: float
    risk: float
    confidence: float
    rationale: str


@dataclass(frozen=True, slots=True)
class OpenAICompatibleRankAdvice:
    ranked_operators: tuple[RankedOperatorCandidate, ...]
    phase: str
    rationale: str
    provider: str
    model: str
    capability_profile: str
    performance_profile: str
    raw_payload: dict[str, Any]
```

Add `request_operator_rank_advice(...)` after `request_operator_prior_advice(...)`:

```python
def request_operator_rank_advice(
    self,
    *,
    system_prompt: str,
    user_prompt: str,
    candidate_operator_ids: Sequence[str],
    attempt_trace: list[dict[str, Any]] | None = None,
) -> OpenAICompatibleRankAdvice:
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
                response_schema=build_operator_rank_advice_schema(operator_ids),
                response_schema_name="operator_rank_advice",
            )
            advice = self._parse_rank_advice(raw_text, operator_ids)
            if attempt_trace is not None:
                attempt_trace.append(
                    {
                        "attempt_index": int(attempt_index + 1),
                        "valid": True,
                        "raw_text": raw_text,
                        "ranked_operators": [
                            {
                                "operator_id": row.operator_id,
                                "semantic_task": row.semantic_task,
                                "score": row.score,
                                "risk": row.risk,
                                "confidence": row.confidence,
                            }
                            for row in advice.ranked_operators
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
            current_system_prompt = self._build_retry_rank_system_prompt(system_prompt, operator_ids, str(exc))
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

Add parser helpers:

```python
def _parse_rank_advice(
    self,
    raw_text: str,
    operator_ids: Sequence[str],
) -> OpenAICompatibleRankAdvice:
    resolved_model = self.config.resolve_model(self._environ)
    normalized_raw_text = self._unwrap_markdown_code_fence(raw_text)
    payload = json.loads(normalized_raw_text)
    raw_ranked = payload.get("ranked_operators")
    if not isinstance(raw_ranked, list) or not raw_ranked:
        raise ValueError("LLM rank advice must include a non-empty ranked_operators array.")

    ranked: list[RankedOperatorCandidate] = []
    seen_operator_ids: set[str] = set()
    for row in raw_ranked:
        if not isinstance(row, dict):
            raise ValueError("Each ranked_operators entry must be an object.")
        operator_id = str(row.get("operator_id", "")).strip()
        if operator_id not in operator_ids:
            raise ValueError(
                "LLM rank advice included operator id outside the requested operator registry: "
                f"{operator_id!r} not in {list(operator_ids)}."
            )
        if operator_id in seen_operator_ids:
            continue
        missing_keys = [
            key
            for key in ("semantic_task", "score", "risk", "confidence", "rationale")
            if key not in row
        ]
        if missing_keys:
            raise ValueError(f"ranked_operators entry for {operator_id!r} missing {', '.join(missing_keys)}.")
        seen_operator_ids.add(operator_id)
        ranked.append(
            RankedOperatorCandidate(
                operator_id=operator_id,
                semantic_task=str(row.get("semantic_task", "")).strip(),
                score=_clamp_unit(row.get("score")),
                risk=_clamp_unit(row.get("risk")),
                confidence=_clamp_unit(row.get("confidence")),
                rationale=str(row.get("rationale", "")),
            )
        )
    if not ranked:
        raise ValueError("LLM rank advice did not include any valid ranked operators.")
    return OpenAICompatibleRankAdvice(
        ranked_operators=tuple(ranked),
        phase=str(payload.get("phase", "")),
        rationale=str(payload.get("rationale", "")),
        provider=self.config.provider,
        model=resolved_model,
        capability_profile=self.config.capability_profile,
        performance_profile=self.config.performance_profile,
        raw_payload=dict(payload),
    )


@staticmethod
def _build_retry_rank_system_prompt(
    original_system_prompt: str,
    operator_ids: Sequence[str],
    error_message: str,
) -> str:
    return (
        f"{original_system_prompt}\n"
        "Previous response was invalid: "
        f"{error_message}\n"
        "Return JSON only. Required key: ranked_operators. "
        "Each ranked_operators item must include operator_id, semantic_task, score, risk, confidence, rationale. "
        f"operator_id must exactly equal one of {list(operator_ids)}."
    )
```

Update `_build_chat_json_system_prompt(...)` before the `operator_prior_advice` branch:

```python
if response_schema_name == "operator_rank_advice":
    return (
        f"{normalized_prompt.rstrip()} "
        "Return exactly one JSON object. "
        "Required key: ranked_operators. "
        "Each ranked_operators item must include operator_id, semantic_task, score, risk, confidence, rationale. "
        f"The operator_id value must exactly equal one of {list(candidate_operator_ids)}. "
        "Rank operators in descending preference order. "
        "Use explicit risk and confidence values; do not omit them. "
        "If rationale is present, keep each rationale concise."
    )
```

- [ ] **Step 7: Run focused client tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_client.py
```

Expected: PASS.

- [ ] **Step 8: Commit Task 1**

Run:

```bash
git add llm/openai_compatible/schemas.py llm/openai_compatible/client.py tests/optimizers/test_llm_client.py
git commit -m "feat: add llm operator rank advice contract"
```

---

### Task 2: Deterministic Semantic Ranked Picker

**Files:**
- Create: `optimizers/operator_pool/semantic_ranked_picker.py`
- Create: `tests/optimizers/test_semantic_ranked_picker.py`

- [ ] **Step 1: Write failing picker tests**

Create `tests/optimizers/test_semantic_ranked_picker.py`:

```python
from __future__ import annotations

import pytest

from optimizers.operator_pool.semantic_ranked_picker import (
    RankedOperatorInput,
    SemanticRankedPickConfig,
    pick_operator_from_semantic_ranking,
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


def test_ranked_picker_selects_top_rank_without_caps() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput("sink_shift", "sink_alignment", score=0.82, risk=0.22, confidence=0.74, rationale="align"),
            RankedOperatorInput("component_jitter_1", "local_polish", score=0.71, risk=0.18, confidence=0.61, rationale="local"),
        ),
        state=_state(),
        config=SemanticRankedPickConfig(),
    )

    assert result.selected_operator_id == "sink_shift"
    assert result.selected_rank == 1
    assert result.override_reason == ""
    assert result.suppressed_operator_ids == ()


def test_ranked_picker_skips_generation_capped_top_rank() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput("sink_shift", "sink_alignment", score=0.82, risk=0.22, confidence=0.74, rationale="align"),
            RankedOperatorInput("component_jitter_1", "local_polish", score=0.71, risk=0.18, confidence=0.61, rationale="local"),
        ),
        state=_state(generation_operator_counts={"sink_shift": 7}, target_offsprings=20),
        config=SemanticRankedPickConfig(generation_operator_cap_fraction=0.35),
    )

    assert result.selected_operator_id == "component_jitter_1"
    assert result.selected_rank == 2
    assert result.suppressed_operator_ids == ("sink_shift",)
    assert result.cap_reasons["sink_shift"] == "generation_operator_cap"
    assert result.override_reason == "rank_1_suppressed"


def test_ranked_picker_applies_rolling_semantic_task_cap() -> None:
    recent_decisions = [
        {"selected_operator_id": "sink_shift", "fallback_used": False}
        for _ in range(10)
    ] + [
        {"selected_operator_id": "component_jitter_1", "fallback_used": False}
        for _ in range(6)
    ]
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "hotspot_pull_toward_sink", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput("sink_shift", "sink_alignment", score=0.90, risk=0.20, confidence=0.80, rationale="align"),
            RankedOperatorInput("hotspot_pull_toward_sink", "sink_alignment", score=0.85, risk=0.25, confidence=0.70, rationale="pull"),
            RankedOperatorInput("component_jitter_1", "local_polish", score=0.70, risk=0.15, confidence=0.60, rationale="local"),
        ),
        state=_state(recent_decisions=recent_decisions),
        config=SemanticRankedPickConfig(rolling_window=16, rolling_semantic_task_cap_fraction=0.55),
    )

    assert result.selected_operator_id == "component_jitter_1"
    assert "sink_shift" in result.suppressed_operator_ids
    assert "hotspot_pull_toward_sink" in result.suppressed_operator_ids
    assert result.cap_reasons["sink_shift"] == "rolling_semantic_task_cap"


def test_ranked_picker_uses_lower_risk_for_low_confidence_near_tie() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput("sink_shift", "sink_alignment", score=0.80, risk=0.70, confidence=0.30, rationale="uncertain"),
            RankedOperatorInput("component_jitter_1", "local_polish", score=0.79, risk=0.10, confidence=0.58, rationale="safer"),
        ),
        state=_state(),
        config=SemanticRankedPickConfig(near_tie_score_margin=0.03, low_confidence_threshold=0.35),
    )

    assert result.selected_operator_id == "component_jitter_1"
    assert result.selected_rank == 2
    assert result.override_reason == "low_confidence_near_tie_lower_risk"


def test_ranked_picker_records_missing_candidates_and_appends_them_to_tail() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1", "component_swap_2"),
        ranked_operators=(
            RankedOperatorInput("sink_shift", "sink_alignment", score=0.80, risk=0.20, confidence=0.70, rationale="align"),
        ),
        state=_state(generation_operator_counts={"sink_shift": 7}, target_offsprings=20),
        config=SemanticRankedPickConfig(generation_operator_cap_fraction=0.35),
    )

    assert result.selected_operator_id == "component_jitter_1"
    assert result.selected_rank == 2
    assert result.missing_operator_ids == ("component_jitter_1", "component_swap_2")


def test_ranked_picker_releases_caps_when_every_candidate_is_suppressed() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput("sink_shift", "sink_alignment", score=0.80, risk=0.20, confidence=0.70, rationale="align"),
            RankedOperatorInput("component_jitter_1", "local_polish", score=0.70, risk=0.20, confidence=0.70, rationale="local"),
        ),
        state=_state(
            generation_operator_counts={"sink_shift": 7, "component_jitter_1": 7},
            target_offsprings=20,
        ),
        config=SemanticRankedPickConfig(generation_operator_cap_fraction=0.35),
    )

    assert result.selected_operator_id == "sink_shift"
    assert result.selected_rank == 1
    assert result.override_reason == "all_candidates_suppressed_release"
    assert set(result.suppressed_operator_ids) == {"sink_shift", "component_jitter_1"}
```

- [ ] **Step 2: Run picker tests and verify red**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_semantic_ranked_picker.py
```

Expected: FAIL because `optimizers.operator_pool.semantic_ranked_picker` does not exist.

- [ ] **Step 3: Implement the picker module**

Create `optimizers/operator_pool/semantic_ranked_picker.py`:

```python
"""Deterministic constrained picker for LLM semantic operator rankings."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from optimizers.operator_pool.semantic_tasks import semantic_task_for_operator
from optimizers.operator_pool.state import ControllerState


@dataclass(frozen=True, slots=True)
class RankedOperatorInput:
    operator_id: str
    semantic_task: str
    score: float
    risk: float
    confidence: float
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class SemanticRankedPickConfig:
    max_rank_scan: int = 9
    generation_operator_cap_fraction: float = 0.35
    rolling_operator_cap_fraction: float = 0.40
    rolling_semantic_task_cap_fraction: float = 0.55
    rolling_window: int = 16
    near_tie_score_margin: float = 0.03
    low_confidence_threshold: float = 0.35

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "SemanticRankedPickConfig":
        data = {} if payload is None else dict(payload)
        defaults = cls()
        return cls(
            max_rank_scan=max(1, int(data.get("max_rank_scan", defaults.max_rank_scan))),
            generation_operator_cap_fraction=_clamp_unit(
                data.get("generation_operator_cap_fraction", defaults.generation_operator_cap_fraction)
            ),
            rolling_operator_cap_fraction=_clamp_unit(
                data.get("rolling_operator_cap_fraction", defaults.rolling_operator_cap_fraction)
            ),
            rolling_semantic_task_cap_fraction=_clamp_unit(
                data.get("rolling_semantic_task_cap_fraction", defaults.rolling_semantic_task_cap_fraction)
            ),
            rolling_window=max(1, int(data.get("rolling_window", defaults.rolling_window))),
            near_tie_score_margin=_clamp_unit(data.get("near_tie_score_margin", defaults.near_tie_score_margin)),
            low_confidence_threshold=_clamp_unit(
                data.get("low_confidence_threshold", defaults.low_confidence_threshold)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_rank_scan": int(self.max_rank_scan),
            "generation_operator_cap_fraction": float(self.generation_operator_cap_fraction),
            "rolling_operator_cap_fraction": float(self.rolling_operator_cap_fraction),
            "rolling_semantic_task_cap_fraction": float(self.rolling_semantic_task_cap_fraction),
            "rolling_window": int(self.rolling_window),
            "near_tie_score_margin": float(self.near_tie_score_margin),
            "low_confidence_threshold": float(self.low_confidence_threshold),
        }


@dataclass(frozen=True, slots=True)
class SemanticRankedPickResult:
    selected_operator_id: str
    selected_rank: int
    ranked_operator_rows: tuple[dict[str, Any], ...]
    suppressed_operator_ids: tuple[str, ...]
    cap_reasons: dict[str, str]
    override_reason: str
    missing_operator_ids: tuple[str, ...]
    config: dict[str, Any]


def pick_operator_from_semantic_ranking(
    *,
    candidate_operator_ids: Sequence[str],
    ranked_operators: Sequence[RankedOperatorInput],
    state: ControllerState,
    config: SemanticRankedPickConfig,
) -> SemanticRankedPickResult:
    candidates = tuple(str(operator_id) for operator_id in candidate_operator_ids)
    if not candidates:
        raise ValueError("Semantic ranked picker requires at least one candidate operator.")
    ranked_rows, missing_operator_ids = _complete_ranking(candidates, ranked_operators)
    suppressed, cap_reasons = _suppressed_by_caps(candidates, state, config)
    scanned_rows = ranked_rows[: min(len(ranked_rows), int(config.max_rank_scan))]
    active_rows = [row for row in scanned_rows if row["operator_id"] not in suppressed]
    if not active_rows:
        selected_row = scanned_rows[0]
        override_reason = "all_candidates_suppressed_release"
    else:
        selected_row = _select_with_near_tie_policy(active_rows, config)
        if selected_row["rank"] == 1 and not _near_tie_triggered(active_rows, config):
            override_reason = ""
        elif selected_row["rank"] != active_rows[0]["rank"]:
            override_reason = "low_confidence_near_tie_lower_risk"
        elif scanned_rows[0]["operator_id"] in suppressed:
            override_reason = "rank_1_suppressed"
        else:
            override_reason = ""
    return SemanticRankedPickResult(
        selected_operator_id=str(selected_row["operator_id"]),
        selected_rank=int(selected_row["rank"]),
        ranked_operator_rows=tuple(dict(row) for row in ranked_rows),
        suppressed_operator_ids=tuple(operator_id for operator_id in candidates if operator_id in suppressed),
        cap_reasons={str(operator_id): str(reason) for operator_id, reason in cap_reasons.items()},
        override_reason=override_reason,
        missing_operator_ids=tuple(missing_operator_ids),
        config=config.to_dict(),
    )
```

Add private helpers in the same file:

```python
def _complete_ranking(
    candidates: tuple[str, ...],
    ranked_operators: Sequence[RankedOperatorInput],
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ranked in ranked_operators:
        operator_id = str(ranked.operator_id)
        if operator_id not in candidates or operator_id in seen:
            continue
        seen.add(operator_id)
        rows.append(
            {
                "rank": len(rows) + 1,
                "operator_id": operator_id,
                "semantic_task": str(ranked.semantic_task),
                "canonical_semantic_task": semantic_task_for_operator(operator_id),
                "score": _clamp_unit(ranked.score),
                "risk": _clamp_unit(ranked.risk),
                "confidence": _clamp_unit(ranked.confidence),
                "rationale": str(ranked.rationale),
                "rank_source": "llm",
            }
        )
    missing = tuple(operator_id for operator_id in candidates if operator_id not in seen)
    for operator_id in missing:
        rows.append(
            {
                "rank": len(rows) + 1,
                "operator_id": operator_id,
                "semantic_task": semantic_task_for_operator(operator_id),
                "canonical_semantic_task": semantic_task_for_operator(operator_id),
                "score": 0.0,
                "risk": 1.0,
                "confidence": 0.0,
                "rationale": "not ranked by model",
                "rank_source": "missing_tail",
            }
        )
    return rows, missing


def _select_with_near_tie_policy(
    active_rows: list[dict[str, Any]],
    config: SemanticRankedPickConfig,
) -> dict[str, Any]:
    top = active_rows[0]
    tie_rows = [top]
    for row in active_rows[1:]:
        if float(top["score"]) - float(row["score"]) <= float(config.near_tie_score_margin):
            tie_rows.append(row)
        else:
            break
    if len(tie_rows) <= 1 and float(top["confidence"]) >= float(config.low_confidence_threshold):
        return top
    if float(top["confidence"]) < float(config.low_confidence_threshold) and len(active_rows) > 1:
        tie_rows = active_rows[: min(len(active_rows), 2)]
    return sorted(tie_rows, key=lambda row: (float(row["risk"]), -float(row["confidence"]), int(row["rank"])))[0]


def _near_tie_triggered(active_rows: list[dict[str, Any]], config: SemanticRankedPickConfig) -> bool:
    if not active_rows:
        return False
    if float(active_rows[0]["confidence"]) < float(config.low_confidence_threshold):
        return True
    if len(active_rows) < 2:
        return False
    return float(active_rows[0]["score"]) - float(active_rows[1]["score"]) <= float(config.near_tie_score_margin)
```

Add cap helpers:

```python
def _suppressed_by_caps(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticRankedPickConfig,
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
    config: SemanticRankedPickConfig,
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
    config: SemanticRankedPickConfig,
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
            reasons.setdefault(operator_id, "rolling_operator_cap")


def _apply_rolling_semantic_task_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticRankedPickConfig,
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

- [ ] **Step 4: Run picker tests and verify green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_semantic_ranked_picker.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add optimizers/operator_pool/semantic_ranked_picker.py tests/optimizers/test_semantic_ranked_picker.py
git commit -m "feat: add deterministic semantic ranked picker"
```

---

### Task 3: LLM Controller Strategy Integration

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write failing controller integration test**

Append to `tests/optimizers/test_llm_controller.py` near the existing semantic prior sampler test:

```python
def test_llm_controller_semantic_ranked_pick_uses_model_ranking() -> None:
    from llm.openai_compatible.client import OpenAICompatibleRankAdvice, RankedOperatorCandidate

    class _RankClient:
        def __init__(self) -> None:
            self.last_kwargs: dict[str, object] | None = None

        def request_operator_rank_advice(self, **kwargs):
            self.last_kwargs = dict(kwargs)
            return OpenAICompatibleRankAdvice(
                ranked_operators=(
                    RankedOperatorCandidate(
                        operator_id="sink_shift",
                        semantic_task="sink_alignment",
                        score=0.82,
                        risk=0.22,
                        confidence=0.74,
                        rationale="align sink",
                    ),
                    RankedOperatorCandidate(
                        operator_id="component_jitter_1",
                        semantic_task="local_polish",
                        score=0.71,
                        risk=0.18,
                        confidence=0.61,
                        rationale="bounded local move",
                    ),
                ),
                phase="post_feasible_expand",
                rationale="rank sink alignment first",
                provider="openai-compatible",
                model="fake-model",
                capability_profile="chat_compatible_json",
                performance_profile="balanced",
                raw_payload={"ranked_operators": [{"operator_id": "sink_shift"}]},
            )

    client = _RankClient()
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "model_env_var": "LLM_MODEL",
            "api_key_env_var": "LLM_API_KEY",
            "base_url_env_var": "LLM_BASE_URL",
            "max_output_tokens": 512,
            "selection_strategy": "semantic_ranked_pick",
            "semantic_ranked_pick": {"rolling_window": 16},
        },
        client=client,
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
            "search_phase": "post_feasible_expand",
            "progress_state": {"phase": "post_feasible_stagnation", "post_feasible_mode": "expand"},
            "prompt_panels": {"run_panel": {}, "operator_panel": {"rows": []}},
            "recent_decisions": [],
        },
    )

    decision = controller.select_decision(
        state,
        ("sink_shift", "component_jitter_1"),
        np.random.default_rng(1),
    )

    assert decision.selected_operator_id == "sink_shift"
    assert decision.metadata["selection_strategy"] == "semantic_ranked_pick"
    assert decision.metadata["selected_rank"] == 1
    assert decision.metadata["llm_ranked_operators"][0]["operator_id"] == "sink_shift"
    assert decision.metadata["ranker_override_reason"] == ""
    assert "sampler_probabilities" not in decision.metadata
    assert client.last_kwargs is not None
    assert "ranked_operators" in str(client.last_kwargs["system_prompt"])
    assert "operator_priors" not in str(client.last_kwargs["system_prompt"])
```

- [ ] **Step 2: Run the integration test and verify red**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller.py::test_llm_controller_semantic_ranked_pick_uses_model_ranking
```

Expected: FAIL because `OpenAICompatibleRankAdvice` or `semantic_ranked_pick` controller branch is not wired yet.

- [ ] **Step 3: Add imports and strategy config**

In `optimizers/operator_pool/llm_controller.py`, update imports:

```python
from llm.openai_compatible.client import OpenAICompatiblePriorAdvice, OpenAICompatibleRankAdvice
from optimizers.operator_pool.semantic_ranked_picker import (
    RankedOperatorInput,
    SemanticRankedPickConfig,
    pick_operator_from_semantic_ranking,
)
```

In `LLMOperatorController.__init__(...)`, update the strategy set and config:

```python
if self.selection_strategy not in {"direct_operator", "semantic_prior_sampler", "semantic_ranked_pick"}:
    raise ValueError(f"Unsupported llm selection_strategy '{self.selection_strategy}'.")
self.semantic_ranked_pick_config = SemanticRankedPickConfig.from_mapping(
    self.controller_parameters.get("semantic_ranked_pick")
)
```

- [ ] **Step 4: Add rank prompt and branch selection**

In `select_decision(...)`, replace the prompt branch with:

```python
if self.selection_strategy == "semantic_prior_sampler":
    system_prompt = self._build_prior_system_prompt(
        state,
        candidate_operator_ids,
        policy_snapshot=policy_snapshot,
        guardrail=guardrail,
    )
elif self.selection_strategy == "semantic_ranked_pick":
    system_prompt = self._build_rank_system_prompt(
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

After the existing semantic prior branch return, add:

```python
if self.selection_strategy == "semantic_ranked_pick":
    return self._select_decision_from_semantic_rank(
        state=state,
        rng=rng,
        candidate_operator_ids=candidate_operator_ids,
        policy_snapshot=policy_snapshot,
        guardrail=guardrail,
        entry_convert_metadata=entry_convert_metadata,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        request_entry=request_entry,
        decision_id=decision_id,
        input_state_digest=input_state_digest,
    )
```

Add `_build_rank_system_prompt(...)` near `_build_prior_system_prompt(...)`:

```python
def _build_rank_system_prompt(
    self,
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    *,
    policy_snapshot: PolicySnapshot,
    guardrail: dict[str, Any] | None,
) -> str:
    prompt = (
        "Return an ordered ranking of candidate operators for constrained thermal MOO; "
        "do not return probabilities and do not return a design vector. "
        "Rank by semantic task fit, operator_panel evidence, semantic_task_panel, phase, "
        "objective balance, feasibility risk, recent saturation, and confidence. "
        "The controller will pick the highest ranked operator that is not saturated by deterministic caps. "
        "Each ranked_operators item must include operator_id, semantic_task, score, risk, confidence, rationale. "
        "Use explicit risk and confidence values; do not leave them implicit. Return JSON only."
    )
    phase_policy_guidance = self._build_phase_policy_guidance(policy_snapshot)
    if phase_policy_guidance:
        prompt = f"{prompt} {phase_policy_guidance}"
    objective_balance_guidance = self._build_objective_balance_guidance(state, candidate_operator_ids)
    if objective_balance_guidance:
        prompt = f"{prompt} {objective_balance_guidance}"
    if guardrail is not None and str(guardrail.get("dominant_operator_id", "")).strip():
        prompt = (
            f"{prompt} Recent dominance advice is context; express saturation by ranking viable alternatives above repeated choices."
        )
    return prompt
```

- [ ] **Step 5: Add request and conversion helpers**

Add below `_request_operator_prior_advice(...)`:

```python
def _request_operator_rank_advice(
    self,
    *,
    system_prompt: str,
    user_prompt: str,
    candidate_operator_ids: Sequence[str],
    attempt_trace: list[dict[str, Any]],
) -> OpenAICompatibleRankAdvice:
    if not hasattr(self.client, "request_operator_rank_advice"):
        raise TypeError("Configured LLM client does not support request_operator_rank_advice.")
    try:
        return self.client.request_operator_rank_advice(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            candidate_operator_ids=candidate_operator_ids,
            attempt_trace=attempt_trace,
        )
    except TypeError as exc:
        if "attempt_trace" not in str(exc):
            raise
        attempt_trace.clear()
        return self.client.request_operator_rank_advice(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            candidate_operator_ids=candidate_operator_ids,
        )
```

Add rank conversion helpers:

```python
@staticmethod
def _ranked_operator_inputs(advice: OpenAICompatibleRankAdvice) -> tuple[RankedOperatorInput, ...]:
    return tuple(
        RankedOperatorInput(
            operator_id=row.operator_id,
            semantic_task=row.semantic_task,
            score=row.score,
            risk=row.risk,
            confidence=row.confidence,
            rationale=row.rationale,
        )
        for row in advice.ranked_operators
    )


@staticmethod
def _ranked_operator_trace_rows(advice: OpenAICompatibleRankAdvice) -> list[dict[str, Any]]:
    return [
        {
            "rank": index,
            "operator_id": row.operator_id,
            "semantic_task": row.semantic_task,
            "score": float(row.score),
            "risk": float(row.risk),
            "confidence": float(row.confidence),
            "rationale": row.rationale,
        }
        for index, row in enumerate(advice.ranked_operators, start=1)
    ]
```

- [ ] **Step 6: Add semantic rank decision branch**

Add `_select_decision_from_semantic_rank(...)` next to `_select_decision_from_semantic_prior(...)`. Use the same metrics, fallback, trace, and metadata shape as the prior branch, but replace sampler fields with ranker fields:

```python
def _select_decision_from_semantic_rank(
    self,
    *,
    state: ControllerState,
    rng: np.random.Generator,
    candidate_operator_ids: Sequence[str],
    policy_snapshot: PolicySnapshot,
    guardrail: dict[str, Any] | None,
    entry_convert_metadata: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    request_entry: dict[str, Any],
    decision_id: str,
    input_state_digest: str,
) -> ControllerDecision:
    self.request_trace.append(request_entry)
    self.metrics["request_count"] = int(self.metrics["request_count"]) + 1
    started_at = time.perf_counter()
    attempt_trace: list[dict[str, Any]] = []
    try:
        advice = self._request_operator_rank_advice(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            candidate_operator_ids=candidate_operator_ids,
            attempt_trace=attempt_trace,
        )
        ranker_result = pick_operator_from_semantic_ranking(
            candidate_operator_ids=candidate_operator_ids,
            ranked_operators=self._ranked_operator_inputs(advice),
            state=state,
            config=self.semantic_ranked_pick_config,
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
            "decision_index": None if state.metadata.get("decision_index") is None else int(state.metadata.get("decision_index")),
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
                **self._decision_phase_metadata(policy_phase=policy_snapshot.phase, model_phase="", model_rationale_present=False),
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
    selected_operator_id = ranker_result.selected_operator_id
    selected_semantic_task = semantic_task_for_operator(selected_operator_id)
    llm_ranked_operators = self._ranked_operator_trace_rows(advice)
    response_entry = {
        "decision_id": decision_id,
        "generation_index": state.generation_index,
        "evaluation_index": state.evaluation_index,
        "decision_index": None if state.metadata.get("decision_index") is None else int(state.metadata.get("decision_index")),
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
        "llm_ranked_operators": llm_ranked_operators,
        "selected_rank": int(ranker_result.selected_rank),
        "ranker_ranked_operator_rows": list(ranker_result.ranked_operator_rows),
        "ranker_suppressed_operator_ids": list(ranker_result.suppressed_operator_ids),
        "ranker_cap_reasons": dict(ranker_result.cap_reasons),
        "ranker_override_reason": ranker_result.override_reason,
        "ranker_missing_operator_ids": list(ranker_result.missing_operator_ids),
        "ranker_config": dict(ranker_result.config),
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
```

After creating `response_entry`, append it, emit controller trace, and return `ControllerDecision` with metadata that includes all ranker fields from `response_entry`:

```python
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
    "llm_ranked_operators": llm_ranked_operators,
    "selected_rank": int(ranker_result.selected_rank),
    "ranker_ranked_operator_rows": list(ranker_result.ranked_operator_rows),
    "ranker_suppressed_operator_ids": list(ranker_result.suppressed_operator_ids),
    "ranker_cap_reasons": dict(ranker_result.cap_reasons),
    "ranker_override_reason": ranker_result.override_reason,
    "ranker_missing_operator_ids": list(ranker_result.missing_operator_ids),
    "ranker_config": dict(ranker_result.config),
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

- [ ] **Step 7: Verify existing RNG is passed into the rank branch**

In the `select_decision(...)` call to `_select_decision_from_semantic_rank(...)`, confirm the call includes:

```python
rng=rng,
```

- [ ] **Step 8: Run controller integration test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller.py::test_llm_controller_semantic_ranked_pick_uses_model_ranking
```

Expected: PASS.

- [ ] **Step 9: Run existing semantic prior controller test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller.py::test_llm_controller_semantic_prior_sampler_records_probabilities
```

Expected: PASS, confirming legacy prior sampler remains intact.

- [ ] **Step 10: Commit Task 3**

Run:

```bash
git add optimizers/operator_pool/llm_controller.py tests/optimizers/test_llm_controller.py
git commit -m "feat: wire semantic ranked pick controller"
```

---

### Task 4: Ranker Trace Contract

**Files:**
- Modify: `tests/optimizers/test_controller_trace_new_schema.py`
- Modify: `optimizers/operator_pool/llm_controller.py`

- [ ] **Step 1: Write failing trace test**

Append to `tests/optimizers/test_controller_trace_new_schema.py`:

```python
def test_llm_semantic_ranked_pick_trace_surfaces_ranker_metadata(tmp_path: Path) -> None:
    from llm.openai_compatible.client import OpenAICompatibleRankAdvice, RankedOperatorCandidate

    class _RankClient:
        def request_operator_rank_advice(self, **kwargs):
            return OpenAICompatibleRankAdvice(
                ranked_operators=(
                    RankedOperatorCandidate(
                        operator_id="component_jitter_1",
                        semantic_task="local_polish",
                        score=0.82,
                        risk=0.10,
                        confidence=0.70,
                        rationale="bounded local polish",
                    ),
                    RankedOperatorCandidate(
                        operator_id="sink_shift",
                        semantic_task="sink_alignment",
                        score=0.70,
                        risk=0.30,
                        confidence=0.60,
                        rationale="alignment backup",
                    ),
                ),
                phase="post_feasible_preserve",
                rationale="rank local polish first",
                provider="openai-compatible",
                model="fake-model",
                capability_profile="chat_compatible_json",
                performance_profile="balanced",
                raw_payload={"ranked_operators": [{"operator_id": "component_jitter_1"}]},
            )

    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "model_env_var": "LLM_MODEL",
            "api_key_env_var": "LLM_API_KEY",
            "base_url_env_var": "LLM_BASE_URL",
            "max_output_tokens": 512,
            "selection_strategy": "semantic_ranked_pick",
        },
        client=_RankClient(),
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
            "progress_state": {"phase": "post_feasible_stagnation", "post_feasible_mode": "preserve"},
            "prompt_panels": {"run_panel": {}, "operator_panel": {"rows": []}},
            "recent_decisions": [],
        },
    )

    controller.select_decision(state, ("component_jitter_1", "sink_shift"), np.random.default_rng(1))

    response_rows = [
        json.loads(line) for line in (tmp_path / "llm_response_trace.jsonl").read_text().splitlines()
    ]
    assert response_rows[0]["selection_strategy"] == "semantic_ranked_pick"
    assert response_rows[0]["llm_ranked_operators"][0]["operator_id"] == "component_jitter_1"
    assert response_rows[0]["selected_rank"] == 1
    assert response_rows[0]["ranker_config"]["rolling_window"] == 16
    assert response_rows[0]["ranker_override_reason"] == ""
    assert "sampler_probabilities" not in response_rows[0]
```

- [ ] **Step 2: Run trace test and verify red if Task 3 did not fully surface trace fields**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_controller_trace_new_schema.py::test_llm_semantic_ranked_pick_trace_surfaces_ranker_metadata
```

Expected: FAIL until the response trace contains all ranker fields.

- [ ] **Step 3: Complete trace field propagation**

In `_select_decision_from_semantic_rank(...)`, ensure `response_entry` and returned `response_metadata` both include:

```python
"llm_ranked_operators": llm_ranked_operators,
"selected_rank": int(ranker_result.selected_rank),
"ranker_ranked_operator_rows": list(ranker_result.ranked_operator_rows),
"ranker_suppressed_operator_ids": list(ranker_result.suppressed_operator_ids),
"ranker_cap_reasons": dict(ranker_result.cap_reasons),
"ranker_override_reason": ranker_result.override_reason,
"ranker_missing_operator_ids": list(ranker_result.missing_operator_ids),
"ranker_config": dict(ranker_result.config),
```

Also ensure `_trace_surface_without_bodies(...)` does not remove these fields.

- [ ] **Step 4: Run trace tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_controller_trace_new_schema.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

Run:

```bash
git add optimizers/operator_pool/llm_controller.py tests/optimizers/test_controller_trace_new_schema.py
git commit -m "test: cover semantic ranked pick traces"
```

---

### Task 5: Switch Active LLM Specs And Contracts

**Files:**
- Modify: `scenarios/optimization/s1_typical_llm.yaml`
- Modify: `scenarios/optimization/s2_staged_llm.yaml`
- Modify: `scenarios/optimization/s3_scale20_llm.yaml`
- Modify: `scenarios/optimization/s4_dense25_llm.yaml`
- Modify: `scenarios/optimization/s5_aggressive15_llm.yaml`
- Modify: `tests/optimizers/test_optimizer_io.py`
- Modify: `tests/optimizers/test_s5_aggressive15_specs.py`

- [ ] **Step 1: Write failing optimizer IO contract test**

In `tests/optimizers/test_optimizer_io.py`, replace `test_llm_spec_accepts_semantic_prior_sampler_parameters` with:

```python
def test_llm_spec_accepts_semantic_ranked_pick_parameters() -> None:
    spec = load_optimization_spec("scenarios/optimization/s5_aggressive15_llm.yaml")

    params = spec.operator_control["controller_parameters"]

    assert params["selection_strategy"] == "semantic_ranked_pick"
    assert params["semantic_ranked_pick"]["max_rank_scan"] == 9
    assert params["semantic_ranked_pick"]["rolling_window"] == 16
    assert params["semantic_ranked_pick"]["generation_operator_cap_fraction"] == pytest.approx(0.35)
    assert "semantic_prior_sampler" not in params
```

- [ ] **Step 2: Update S5 spec test expectation first**

In `tests/optimizers/test_s5_aggressive15_specs.py`, replace the semantic prior assertions with:

```python
assert params["selection_strategy"] == "semantic_ranked_pick"
assert params["max_output_tokens"] == 512
assert params["semantic_ranked_pick"] == {
    "max_rank_scan": 9,
    "generation_operator_cap_fraction": 0.35,
    "rolling_operator_cap_fraction": 0.40,
    "rolling_semantic_task_cap_fraction": 0.55,
    "rolling_window": 16,
    "near_tie_score_margin": 0.03,
    "low_confidence_threshold": 0.35,
}
assert "semantic_prior_sampler" not in params
```

- [ ] **Step 3: Run YAML contract tests and verify red**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_optimizer_io.py::test_llm_spec_accepts_semantic_ranked_pick_parameters \
  tests/optimizers/test_s5_aggressive15_specs.py::test_s5_registry_split_uses_structured_primitives_for_union_and_llm
```

Expected: FAIL because active LLM YAMLs still use `semantic_prior_sampler`.

- [ ] **Step 4: Update active LLM YAMLs**

In each active LLM YAML listed in this task, replace:

```yaml
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

with:

```yaml
selection_strategy: semantic_ranked_pick
semantic_ranked_pick:
  max_rank_scan: 9
  generation_operator_cap_fraction: 0.35
  rolling_operator_cap_fraction: 0.40
  rolling_semantic_task_cap_fraction: 0.55
  rolling_window: 16
  near_tie_score_margin: 0.03
  low_confidence_threshold: 0.35
```

- [ ] **Step 5: Run YAML contract tests and verify green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_optimizer_io.py::test_llm_spec_accepts_semantic_ranked_pick_parameters \
  tests/optimizers/test_s5_aggressive15_specs.py::test_s5_registry_split_uses_structured_primitives_for_union_and_llm
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

Run:

```bash
git add \
  scenarios/optimization/s1_typical_llm.yaml \
  scenarios/optimization/s2_staged_llm.yaml \
  scenarios/optimization/s3_scale20_llm.yaml \
  scenarios/optimization/s4_dense25_llm.yaml \
  scenarios/optimization/s5_aggressive15_llm.yaml \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_s5_aggressive15_specs.py
git commit -m "config: switch llm specs to semantic ranked pick"
```

---

### Task 6: Final Focused Verification

**Files:**
- No source edits unless a focused test exposes a defect in the new ranker route.

- [ ] **Step 1: Run focused LLM tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_semantic_prior_sampler.py \
  tests/optimizers/test_semantic_ranked_picker.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_controller_trace_new_schema.py
```

Expected: PASS. This verifies new ranker behavior and confirms legacy prior sampler did not regress.

- [ ] **Step 2: Run ladder contract tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_s5_aggressive15_specs.py \
  tests/optimizers/test_s3_s4_specs.py \
  tests/optimizers/test_operator_pool_contracts.py
```

Expected: PASS. This verifies LLM specs still share the `union` operator pool and active optimizer ladder contracts remain coherent.

- [ ] **Step 3: Check raw/union protected files have no diff**

Run:

```bash
git diff -- \
  'scenarios/optimization/*_raw.yaml' \
  'scenarios/optimization/*_union.yaml' \
  optimizers/drivers/raw_driver.py \
  optimizers/drivers/union_driver.py \
  optimizers/operator_pool/random_controller.py
```

Expected: no output.

- [ ] **Step 4: Run whitespace diff check**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 5: Inspect final git status**

Run:

```bash
git status --short
```

Expected: either clean after the per-task commits, or only intentional files if the implementer deferred commits.

- [ ] **Step 6: Do not run live GPT benchmark**

No command should be run for S5 20 x 10 live GPT benchmarking during this implementation. The first live command remains blocked until the user explicitly asks for it.
