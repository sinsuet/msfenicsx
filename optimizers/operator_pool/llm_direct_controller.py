"""Mechanism-free LLM top-1 operator controller for direct ablations."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from llm.openai_compatible import OpenAICompatibleClient, OpenAICompatibleConfig
from optimizers.operator_pool.decisions import ControllerDecision
from optimizers.operator_pool.operators import get_operator_behavior_profile
from optimizers.operator_pool.random_controller import RandomUniformController
from optimizers.operator_pool.state import ControllerState
from optimizers.traces.correlation import format_decision_id
from optimizers.traces.jsonl_writer import append_jsonl
from optimizers.traces.prompt_store import PromptStore


class LLMDirectOperatorController:
    """Ask the LLM to choose one operator without semantic-control mechanisms."""

    controller_id = "llm_direct"
    selection_strategy = "llm_direct_top1"

    def __init__(
        self,
        *,
        controller_parameters: dict[str, Any],
        client: Any | None = None,
    ) -> None:
        self.controller_parameters = dict(controller_parameters)
        self.config = OpenAICompatibleConfig.from_dict(controller_parameters)
        self.client = OpenAICompatibleClient(self.config) if client is None else client
        self.fallback_controller = RandomUniformController()
        self.request_trace: list[dict[str, Any]] = []
        self.response_trace: list[dict[str, Any]] = []
        self.reflection_trace: list[dict[str, Any]] = []
        self._controller_trace_path: Path | None = None
        self._llm_request_trace_path: Path | None = None
        self._llm_response_trace_path: Path | None = None
        self._prompt_store: PromptStore | None = None
        self.metrics: dict[str, Any] = {
            "provider": self.config.provider,
            "model": self._trace_model_label(),
            "capability_profile": self.config.capability_profile,
            "performance_profile": self.config.performance_profile,
            "request_count": 0,
            "response_count": 0,
            "fallback_count": 0,
            "retry_count": 0,
            "invalid_response_count": 0,
            "schema_invalid_count": 0,
            "semantic_invalid_count": 0,
            "elapsed_seconds_total": 0.0,
            "elapsed_seconds_avg": 0.0,
            "elapsed_seconds_max": 0.0,
        }

    def select_operator(
        self,
        state: ControllerState,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> str:
        return self.select_decision(state, operator_ids, rng).selected_operator_id

    def select_decision(
        self,
        state: ControllerState,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> ControllerDecision:
        candidate_operator_ids = tuple(str(operator_id) for operator_id in operator_ids)
        if not candidate_operator_ids:
            raise ValueError("LLMDirectOperatorController requires at least one candidate operator.")

        decision_id = self._decision_id(state)
        system_prompt = self._build_system_prompt(candidate_operator_ids)
        user_prompt = self._build_user_prompt(state, candidate_operator_ids)
        input_state_digest = self._input_state_digest(state, candidate_operator_ids)
        request_entry = {
            "decision_id": decision_id,
            "generation_index": int(state.generation_index),
            "evaluation_index": int(state.evaluation_index),
            "decision_index": self._decision_index(state),
            "provider": self.config.provider,
            "model": self._trace_model_label(),
            "capability_profile": self.config.capability_profile,
            "performance_profile": self.config.performance_profile,
            "controller_id": self.controller_id,
            "selection_strategy": self.selection_strategy,
            "candidate_operator_ids": list(candidate_operator_ids),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "accepted_for_evaluation": False,
            "accepted_evaluation_indices": [],
            "accepted_evaluation_index": None,
            "rejection_reason": "",
        }
        self.request_trace.append(request_entry)
        self.metrics["request_count"] = int(self.metrics["request_count"]) + 1
        started_at = time.perf_counter()
        attempt_trace: list[dict[str, Any]] = []
        try:
            response = self._request_operator_decision(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=candidate_operator_ids,
                attempt_trace=attempt_trace,
            )
        except Exception as exc:
            elapsed_seconds = max(0.0, float(time.perf_counter() - started_at))
            self.metrics["fallback_count"] = int(self.metrics["fallback_count"]) + 1
            self._record_attempt_metrics(attempt_trace)
            self._record_elapsed_seconds(elapsed_seconds)
            fallback_decision = self.fallback_controller.select_decision(state, candidate_operator_ids, rng)
            response_entry = {
                "decision_id": decision_id,
                "generation_index": int(state.generation_index),
                "evaluation_index": int(state.evaluation_index),
                "decision_index": self._decision_index(state),
                "provider": self.config.provider,
                "model": self._trace_model_label(),
                "controller_id": self.controller_id,
                "selection_strategy": self.selection_strategy,
                "candidate_operator_ids": list(candidate_operator_ids),
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
            }
            self.response_trace.append(response_entry)
            self._emit_controller_trace(
                decision_id=decision_id,
                phase="llm_direct",
                operator_selected=fallback_decision.selected_operator_id,
                operator_pool_snapshot=list(candidate_operator_ids),
                input_state_digest=input_state_digest,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_body=str(exc),
                rationale="",
                fallback_used=True,
                latency_ms=elapsed_seconds * 1000.0,
                retries=max(0, len(attempt_trace) - 1),
                request_surface=request_entry,
                response_surface=response_entry,
            )
            metadata = {
                "decision_id": decision_id,
                "controller_id": self.controller_id,
                "selection_strategy": self.selection_strategy,
                "fallback_used": True,
                "fallback_controller": "random_uniform",
                "fallback_reason": str(exc),
                "elapsed_seconds": elapsed_seconds,
            }
            return ControllerDecision(
                selected_operator_id=fallback_decision.selected_operator_id,
                phase="llm_direct",
                rationale=fallback_decision.rationale,
                metadata=metadata,
            )

        elapsed_seconds = max(0.0, float(time.perf_counter() - started_at))
        self.metrics["response_count"] = int(self.metrics["response_count"]) + 1
        self._record_attempt_metrics(attempt_trace)
        self._record_elapsed_seconds(elapsed_seconds)
        response_entry = {
            "decision_id": decision_id,
            "generation_index": int(state.generation_index),
            "evaluation_index": int(state.evaluation_index),
            "decision_index": self._decision_index(state),
            "provider": response.provider,
            "model": response.model,
            "capability_profile": response.capability_profile,
            "performance_profile": response.performance_profile,
            "controller_id": self.controller_id,
            "selection_strategy": self.selection_strategy,
            "selected_operator_id": response.selected_operator_id,
            "selected_intent": response.selected_intent,
            "selected_semantic_task": response.selected_semantic_task,
            "phase": "llm_direct",
            "model_phase": response.phase,
            "model_rationale_present": bool(response.rationale.strip()),
            "rationale": response.rationale,
            "raw_payload": dict(response.raw_payload),
            "candidate_operator_ids": list(candidate_operator_ids),
            "fallback_used": False,
            "attempt_trace": list(attempt_trace),
            "attempt_count": int(len(attempt_trace)),
            "retry_count": int(max(0, len(attempt_trace) - 1)),
            "elapsed_seconds": elapsed_seconds,
            "accepted_for_evaluation": False,
            "accepted_evaluation_indices": [],
            "accepted_evaluation_index": None,
            "rejection_reason": "",
        }
        self.response_trace.append(response_entry)
        self._emit_controller_trace(
            decision_id=decision_id,
            phase="llm_direct",
            operator_selected=response.selected_operator_id,
            operator_pool_snapshot=list(candidate_operator_ids),
            input_state_digest=input_state_digest,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_body=json.dumps(response.raw_payload, ensure_ascii=False, indent=2),
            rationale=response.rationale,
            fallback_used=False,
            latency_ms=elapsed_seconds * 1000.0,
            retries=max(0, len(attempt_trace) - 1),
            request_surface=request_entry,
            response_surface=response_entry,
        )
        metadata = {
            "decision_id": decision_id,
            "provider": response.provider,
            "model": response.model,
            "capability_profile": response.capability_profile,
            "performance_profile": response.performance_profile,
            "controller_id": self.controller_id,
            "selection_strategy": self.selection_strategy,
            "selected_intent": response.selected_intent,
            "selected_semantic_task": response.selected_semantic_task,
            "fallback_used": False,
            "elapsed_seconds": elapsed_seconds,
            "raw_payload": dict(response.raw_payload),
        }
        return ControllerDecision(
            selected_operator_id=response.selected_operator_id,
            phase="llm_direct",
            rationale=response.rationale,
            metadata=metadata,
        )

    def configure_trace_outputs(
        self,
        *,
        controller_trace_path: Path,
        llm_request_trace_path: Path,
        llm_response_trace_path: Path,
        prompt_store: PromptStore,
    ) -> None:
        self._controller_trace_path = Path(controller_trace_path)
        self._llm_request_trace_path = Path(llm_request_trace_path)
        self._llm_response_trace_path = Path(llm_response_trace_path)
        self._prompt_store = prompt_store

    def _build_system_prompt(self, candidate_operator_ids: Sequence[str]) -> str:
        return (
            "You are selecting exactly one optimization operator for the next offspring proposal. "
            "Return valid JSON only with required key selected_operator_id. "
            f"The selected_operator_id value must exactly equal one of {list(candidate_operator_ids)}. "
            "Optional keys are phase and rationale. "
            "Do not output a layout, coordinates, rankings, probabilities, or multiple alternatives."
        )

    def _build_user_prompt(
        self,
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        payload = {
            "task": (
                "Choose one operator for an expensive constrained multi-objective thermal layout search. "
                "Objectives are summary.temperature_max and summary.temperature_gradient_rms; lower is better. "
                "The run must respect the radiator span budget."
            ),
            "state": self._plain_state_payload(state),
            "candidate_operators": [
                self._operator_description(operator_id)
                for operator_id in candidate_operator_ids
            ],
            "response_contract": {
                "required": ["selected_operator_id"],
                "selected_operator_id_choices": list(candidate_operator_ids),
            },
        }
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)

    def _plain_state_payload(self, state: ControllerState) -> dict[str, Any]:
        metadata = state.metadata
        return {
            "family": str(state.family),
            "backbone": str(state.backbone),
            "generation_index": int(state.generation_index),
            "evaluation_index": int(state.evaluation_index),
            "parent_count": int(state.parent_count),
            "vector_size": int(state.vector_size),
            "run_state": self._compact_mapping(
                metadata.get("run_state"),
                (
                    "evaluations_used",
                    "evaluations_remaining",
                    "feasible_rate",
                    "first_feasible_eval",
                    "peak_temperature",
                    "temperature_gradient_rms",
                    "sink_span",
                    "sink_budget_utilization",
                    "objective_extremes",
                ),
            ),
            "progress_state": self._compact_mapping(
                metadata.get("progress_state"),
                (
                    "phase",
                    "first_feasible_found",
                    "recent_no_progress_count",
                    "last_progress_eval",
                    "recent_best_near_feasible_improvement",
                    "recent_best_feasible_improvement",
                    "recent_frontier_stagnation_count",
                ),
            ),
            "recent_operator_sequence": [
                str(row.get("selected_operator_id"))
                for row in self._sequence(metadata.get("recent_decisions"))[-8:]
                if isinstance(row, Mapping) and str(row.get("selected_operator_id", "")).strip()
            ],
        }

    def _operator_description(self, operator_id: str) -> dict[str, str]:
        profile = get_operator_behavior_profile(str(operator_id))
        return {
            "operator_id": str(operator_id),
            "family": str(profile.family),
            "role": str(profile.role),
            "exploration_class": str(profile.exploration_class),
        }

    @staticmethod
    def _compact_mapping(value: Any, keys: Sequence[str]) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            return {}
        return {
            str(key): LLMDirectOperatorController._json_safe(value[key])
            for key in keys
            if key in value
        }

    @staticmethod
    def _sequence(value: Any) -> list[Any]:
        if isinstance(value, list):
            return list(value)
        if isinstance(value, tuple):
            return list(value)
        return []

    @staticmethod
    def _decision_index(state: ControllerState) -> int | None:
        value = state.metadata.get("decision_index")
        return None if value is None else int(value)

    @staticmethod
    def _decision_id(state: ControllerState) -> str:
        return format_decision_id(
            int(state.generation_index),
            int(state.evaluation_index),
            int(state.metadata.get("decision_index", 0) or 0),
        )

    def _input_state_digest(
        self,
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        payload = {
            "controller_id": self.controller_id,
            "selection_strategy": self.selection_strategy,
            "candidate_operator_ids": [str(operator_id) for operator_id in candidate_operator_ids],
            "state": self._plain_state_payload(state),
        }
        serialized = json.dumps(
            self._json_safe(payload),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha1(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Mapping):
            return {str(key): LLMDirectOperatorController._json_safe(item) for key, item in value.items()}
        if isinstance(value, np.ndarray):
            return [LLMDirectOperatorController._json_safe(item) for item in value.tolist()]
        if isinstance(value, (list, tuple, set, frozenset)):
            return [LLMDirectOperatorController._json_safe(item) for item in value]
        return str(value)

    def _trace_model_label(self, *surfaces: Mapping[str, Any] | None) -> str:
        for surface in surfaces:
            if not isinstance(surface, Mapping):
                continue
            value = surface.get("model")
            if value is not None and str(value).strip() and str(value).strip().lower() not in {"none", "null"}:
                return str(value).strip()
        try:
            return self.config.resolve_model()
        except RuntimeError:
            literal_model = "" if self.config.model is None else str(self.config.model).strip()
            if literal_model:
                return literal_model
            env_var = "" if self.config.model_env_var is None else str(self.config.model_env_var).strip()
            return f"unresolved:{env_var}" if env_var else "unresolved"

    def _request_operator_decision(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        candidate_operator_ids: Sequence[str],
        attempt_trace: list[dict[str, Any]],
    ) -> Any:
        try:
            return self.client.request_operator_decision(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=tuple(str(operator_id) for operator_id in candidate_operator_ids),
                attempt_trace=attempt_trace,
            )
        except TypeError as exc:
            if "attempt_trace" not in str(exc):
                raise
            attempt_trace.clear()
            return self.client.request_operator_decision(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=tuple(str(operator_id) for operator_id in candidate_operator_ids),
            )

    @staticmethod
    def _request_markdown_body(*, system_prompt: str, user_prompt: str) -> str:
        return f"# System\n\n{system_prompt.strip()}\n\n# User\n\n{user_prompt.strip()}\n"

    def _emit_controller_trace(
        self,
        *,
        decision_id: str,
        phase: str,
        operator_selected: str,
        operator_pool_snapshot: list[str],
        input_state_digest: str,
        system_prompt: str,
        user_prompt: str,
        response_body: str,
        rationale: str,
        fallback_used: bool,
        latency_ms: float,
        retries: int,
        request_surface: Mapping[str, Any] | None,
        response_surface: Mapping[str, Any] | None,
    ) -> tuple[str | None, str | None]:
        if self._controller_trace_path is None or self._prompt_store is None:
            return None, None
        model_label = self._trace_model_label(response_surface, request_surface)
        prompt_ref = self._prompt_store.store(
            kind="request",
            body=self._request_markdown_body(system_prompt=system_prompt, user_prompt=user_prompt),
            model=model_label,
            decision_id=decision_id,
        )
        response_ref = self._prompt_store.store(
            kind="response",
            body=response_body,
            model=model_label,
            decision_id=decision_id,
        )
        append_jsonl(
            self._controller_trace_path,
            {
                "decision_id": decision_id,
                "phase": phase,
                "operator_selected": operator_selected,
                "operator_pool_snapshot": list(operator_pool_snapshot),
                "input_state_digest": input_state_digest,
                "prompt_ref": prompt_ref,
                "rationale": rationale,
                "fallback_used": fallback_used,
                "latency_ms": float(latency_ms),
            },
        )
        prompt_size = {
            "system_chars": len(system_prompt),
            "user_chars": len(user_prompt),
            "total_chars": len(system_prompt) + len(user_prompt),
        }
        request_payload = {
            **({} if request_surface is None else dict(request_surface)),
            "decision_id": decision_id,
            "prompt_ref": prompt_ref,
            "http_status": None,
            "retries": int(retries),
            "latency_ms": float(latency_ms),
            "prompt_size": prompt_size,
            "model": model_label,
        }
        append_jsonl(self._llm_request_trace_path, request_payload)
        response_payload = {
            **({} if response_surface is None else self._trace_surface_without_bodies(response_surface)),
            "decision_id": decision_id,
            "response_ref": response_ref,
            "tokens": {},
            "finish_reason": None,
            "http_status": None,
            "retries": int(retries),
            "latency_ms": float(latency_ms),
            "model": model_label,
        }
        append_jsonl(self._llm_response_trace_path, response_payload)
        return prompt_ref, response_ref

    @staticmethod
    def _trace_surface_without_bodies(surface: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(surface)
        for key in ("system_prompt", "user_prompt", "response_text", "raw_payload"):
            payload.pop(key, None)
        return payload

    def _record_attempt_metrics(self, attempt_trace: Sequence[Mapping[str, Any]]) -> None:
        retry_count = max(0, len(attempt_trace) - 1)
        self.metrics["retry_count"] = int(self.metrics["retry_count"]) + retry_count
        invalid_count = sum(1 for item in attempt_trace if not bool(item.get("valid", False)))
        self.metrics["invalid_response_count"] = int(self.metrics["invalid_response_count"]) + invalid_count
        self.metrics["schema_invalid_count"] = int(self.metrics["schema_invalid_count"]) + invalid_count

    def _record_elapsed_seconds(self, elapsed_seconds: float) -> None:
        total = float(self.metrics["elapsed_seconds_total"]) + float(elapsed_seconds)
        count = int(self.metrics["response_count"]) + int(self.metrics["fallback_count"])
        self.metrics["elapsed_seconds_total"] = total
        self.metrics["elapsed_seconds_avg"] = 0.0 if count <= 0 else total / float(count)
        self.metrics["elapsed_seconds_max"] = max(
            float(self.metrics.get("elapsed_seconds_max", 0.0)),
            float(elapsed_seconds),
        )
