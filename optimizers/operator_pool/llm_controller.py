"""LLM-guided controller for the hybrid-union operator registry."""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from llm.openai_compatible import OpenAICompatibleClient, OpenAICompatibleConfig
from optimizers.operator_pool.decisions import ControllerDecision
from optimizers.operator_pool.policy_kernel import PolicySnapshot, build_policy_snapshot
from optimizers.operator_pool.prompt_projection import build_prompt_projection
from optimizers.operator_pool.random_controller import RandomUniformController
from optimizers.operator_pool.route_families import (
    ROUTE_FAMILY_BY_OPERATOR,
    STABLE_ROUTE_FAMILIES,
    operator_route_family,
)
from optimizers.operator_pool.state import ControllerState
from optimizers.traces.correlation import format_decision_id
from optimizers.traces.jsonl_writer import append_jsonl
from optimizers.traces.prompt_store import PromptStore


_OPERATOR_ROLE_SUMMARIES: dict[str, str] = {
    "vector_sbx_pm": "native NSGA-II SBX plus polynomial mutation baseline proposal.",
    "component_jitter_1": "small one-component local perturbation around the current layout.",
    "anchored_component_jitter": "component perturbation paired with a right-shifted sink anchor.",
    "component_relocate_1": "relocate one component to broaden layout exploration.",
    "component_swap_2": "swap two component positions to explore a new layout ordering.",
    "sink_shift": "shift the sink window while preserving most of its current span.",
    "sink_resize": "adjust the sink window span within the allowed budget.",
    "component_block_translate_2_4": "translate a compact block of nearby components as a shared primitive layout move.",
    "component_subspace_sbx": "recombine and mutate a compact component subspace as a shared primitive layout move.",
    "hotspot_pull_toward_sink": "pull the active hotspot cluster toward the sink corridor.",
    "hotspot_spread": "separate a compact hotspot cluster to reduce local thermal pressure.",
    "gradient_band_smooth": "smooth a high-gradient band through local layout blending.",
    "congestion_relief": "open space around the most congested local component pair.",
    "sink_retarget": "retarget sink alignment toward the active hotspot geometry.",
    "layout_rebalance": "rebalance the overall component distribution across the panel.",
    "native_sbx_pm": "native NSGA-II SBX plus polynomial mutation baseline proposal.",
    "global_explore": "more aggressive full-vector SBX plus mutation exploration across the complete layout.",
    "local_refine": "small local cleanup around the current cluster arrangement and sink placement.",
    "move_hottest_cluster_toward_sink": "pull the currently hottest or most crowded component cluster toward the sink corridor.",
    "spread_hottest_cluster": "separate the hottest cluster to reduce crowding while keeping it sink-aware.",
    "smooth_high_gradient_band": "blend a high-gradient band toward a smoother neighborhood arrangement.",
    "reduce_local_congestion": "push the most congested local component pair apart.",
    "repair_sink_budget": "project the sink interval back inside the approved span budget while keeping it targeted.",
    "slide_sink": "slide the current sink window toward the active heat cluster without changing its span much.",
    "rebalance_layout": "rebalance the overall component distribution toward a more even panel layout.",
}
_RECENT_DOMINANCE_MIN_WINDOW = 6
_RECENT_DOMINANCE_MIN_COUNT = 5
_RECENT_DOMINANCE_MIN_SHARE = 0.75
_PREFEASIBLE_CUSTOM_DOMINANCE_MIN_WINDOW = 4
_PREFEASIBLE_CUSTOM_DOMINANCE_MIN_COUNT = 4
_PREFEASIBLE_CUSTOM_DOMINANCE_MIN_SHARE = 0.75
_NATIVE_BASELINE_OPERATOR_IDS = frozenset({"vector_sbx_pm", "native_sbx_pm"})
_GENERATION_LOCAL_DOMINANCE_PHASES = frozenset(
    {"post_feasible_expand", "post_feasible_recover", "post_feasible_preserve"}
)
_GENERATION_LOCAL_DOMINANCE_THRESHOLDS = {
    "post_feasible_expand": {"min_window": 4, "min_count": 4, "min_share": 0.75},
    "post_feasible_recover": {"min_window": 4, "min_count": 4, "min_share": 0.75},
    "post_feasible_preserve": {"min_window": 5, "min_count": 4, "min_share": 0.8},
}
_GENERATION_LOCAL_STRATEGY_GROUP_THRESHOLDS = {
    "post_feasible_expand": {"min_window": 6, "min_count": 5, "min_share": 0.75},
    "post_feasible_recover": {"min_window": 6, "min_count": 5, "min_share": 0.75},
    "post_feasible_preserve": {"min_window": 6, "min_count": 5, "min_share": 0.8},
}
_OPERATOR_STRATEGY_GROUPS: dict[str, str] = {
    "vector_sbx_pm": "baseline",
    "component_jitter_1": "local_peak_refine",
    "anchored_component_jitter": "local_peak_refine",
    "component_relocate_1": "global_explore",
    "component_swap_2": "global_explore",
    "sink_shift": "sink_retarget",
    "sink_resize": "sink_retarget",
    "component_block_translate_2_4": "structured_block",
    "component_subspace_sbx": "structured_subspace",
    "hotspot_pull_toward_sink": "hotspot_shift",
    "hotspot_spread": "gradient_smoothing",
    "gradient_band_smooth": "gradient_smoothing",
    "congestion_relief": "gradient_smoothing",
    "sink_retarget": "sink_retarget",
    "layout_rebalance": "layout_rebalance",
    "native_sbx_pm": "baseline",
    "global_explore": "global_explore",
    "local_refine": "local_peak_refine",
    "move_hottest_cluster_toward_sink": "hotspot_shift",
    "spread_hottest_cluster": "gradient_smoothing",
    "smooth_high_gradient_band": "gradient_smoothing",
    "reduce_local_congestion": "gradient_smoothing",
    "repair_sink_budget": "sink_retarget",
    "slide_sink": "sink_retarget",
    "rebalance_layout": "layout_rebalance",
}
_STABLE_PROMPT_OPERATOR_IDS = frozenset(
    {
        "vector_sbx_pm",
        "component_jitter_1",
        "anchored_component_jitter",
        "component_relocate_1",
        "component_swap_2",
        "sink_shift",
        "sink_resize",
        "component_block_translate_2_4",
        "component_subspace_sbx",
        "native_sbx_pm",
        "global_explore",
        "local_refine",
    }
)
_OPERATOR_INTENTS: dict[str, str] = {
    "vector_sbx_pm": "native_baseline",
    "component_jitter_1": "component_local_peak_cleanup",
    "anchored_component_jitter": "component_local_gradient_cleanup",
    "component_relocate_1": "component_frontier_expand",
    "component_swap_2": "layout_frontier_diversify",
    "sink_shift": "sink_alignment_adjust",
    "sink_resize": "sink_budget_adjust",
    "component_block_translate_2_4": "structured_block_reposition",
    "component_subspace_sbx": "structured_subspace_recombine",
    "hotspot_pull_toward_sink": "sink_retarget",
    "hotspot_spread": "hotspot_spread",
    "gradient_band_smooth": "congestion_relief",
    "congestion_relief": "congestion_relief",
    "sink_retarget": "sink_retarget",
    "layout_rebalance": "layout_rebalance",
    "native_sbx_pm": "native_baseline",
    "global_explore": "frontier_expand",
    "local_refine": "local_cleanup",
    "move_hottest_cluster_toward_sink": "sink_retarget",
    "spread_hottest_cluster": "hotspot_spread",
    "smooth_high_gradient_band": "local_cleanup",
    "reduce_local_congestion": "congestion_relief",
    "repair_sink_budget": "sink_budget_adjust",
    "slide_sink": "sink_alignment_adjust",
    "rebalance_layout": "congestion_relief",
}
_INTENT_SUMMARIES: dict[str, str] = {
    "native_baseline": "use the raw genetic recombination/mutation route as a fair-pool anchor when it is comparably applicable, not only as a last fallback.",
    "frontier_expand": "seek new Pareto support while preserving acceptable feasibility stability.",
    "component_local_peak_cleanup": "make a bounded local component move around the incumbent basin to relieve peak-temperature stagnation.",
    "component_local_gradient_cleanup": "make a bounded anchored component move to smooth local gradient pressure without global disruption.",
    "component_frontier_expand": "relocate one component to test a new layout basin when frontier pressure or peak stagnation is active.",
    "layout_frontier_diversify": "swap components to diversify the layout and improve gradient/frontier coverage.",
    "local_cleanup": "make a low-risk local refinement around the incumbent basin.",
    "sink_alignment_adjust": "shift sink alignment toward the active hotspot geometry when sink placement is the bottleneck.",
    "sink_budget_adjust": "adjust sink span only when sink budget, span, or alignment is the active bottleneck; do not use it as a generic preserve fallback.",
    "sink_retarget": "retarget sink alignment toward the active hotspot geometry.",
    "hotspot_spread": "disperse a compact hotspot cluster to reduce local thermal pressure.",
    "congestion_relief": "open space in locally congested regions of the layout.",
    "layout_rebalance": "rebalance the layout when global spatial distribution is the limiting factor.",
    "structured_block_reposition": "use a shared primitive block translation to reposition nearby components using only layout coordinates and bounds.",
    "structured_subspace_recombine": "use shared primitive subspace recombination to diversify compact component groups using only parent vectors and bounds.",
    "preserve_feasible": "protect feasibility and avoid sink-budget regressions.",
}


class LLMOperatorController:
    controller_id = "llm"

    def __init__(
        self,
        *,
        controller_parameters: dict[str, Any],
        client: Any | None = None,
    ) -> None:
        self.controller_parameters = dict(controller_parameters)
        self.config = OpenAICompatibleConfig.from_dict(controller_parameters)
        self.client = OpenAICompatibleClient(self.config) if client is None else client
        fallback_controller_id = str(self.controller_parameters.get("fallback_controller", "random_uniform"))
        if fallback_controller_id != "random_uniform":
            raise ValueError(f"Unsupported llm fallback controller '{fallback_controller_id}'.")
        self.fallback_controller = RandomUniformController()
        self.fallback_controller_id = fallback_controller_id
        self.request_trace: list[dict[str, Any]] = []
        self.response_trace: list[dict[str, Any]] = []
        self.reflection_trace: list[dict[str, Any]] = []
        self._controller_trace_path: Path | None = None
        self._llm_request_trace_path: Path | None = None
        self._llm_response_trace_path: Path | None = None
        self._prompt_store: PromptStore | None = None
        self.metrics: dict[str, Any] = {
            "provider": self.config.provider,
            "model": self.config.model,
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
        original_candidate_operator_ids = tuple(str(operator_id) for operator_id in operator_ids)
        if not original_candidate_operator_ids:
            raise ValueError("LLMOperatorController requires at least one candidate operator.")
        policy_snapshot = build_policy_snapshot(state, original_candidate_operator_ids)
        candidate_operator_ids = policy_snapshot.allowed_operator_ids
        _, recent_dominance_guardrail = self._apply_recent_dominance_guardrail(
            state,
            candidate_operator_ids,
        )
        _, generation_local_dominance_guardrail = (
            self._apply_generation_local_dominance_guardrail(
                state,
                candidate_operator_ids,
            )
        )
        _, generation_local_strategy_group_guardrail = (
            self._apply_generation_local_strategy_group_guardrail(
                state,
                candidate_operator_ids,
            )
        )
        guardrail = self._merge_guardrail_metadata(
            original_candidate_operator_ids=original_candidate_operator_ids,
            effective_candidate_operator_ids=candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            dominance_guardrails=[
                recent_dominance_guardrail,
                generation_local_dominance_guardrail,
                generation_local_strategy_group_guardrail,
            ],
        )
        entry_convert_metadata = self._entry_convert_metadata(
            state=state,
            policy_snapshot=policy_snapshot,
            candidate_operator_ids=candidate_operator_ids,
        )

        system_prompt = self._build_system_prompt(
            state,
            candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            guardrail=guardrail,
        )
        prompt_metadata = self._build_prompt_metadata(
            state,
            candidate_operator_ids,
            original_candidate_operator_ids=original_candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            guardrail=guardrail,
        )
        user_prompt = self._serialize_user_prompt(
            state,
            candidate_operator_ids,
            metadata=prompt_metadata,
        )
        request_surface = self._request_surface_metadata(
            candidate_operator_ids=candidate_operator_ids,
            original_candidate_operator_ids=original_candidate_operator_ids,
            guardrail=guardrail,
            metadata=prompt_metadata,
        )
        decision_id = self._decision_id(state)
        input_state_digest = self._input_state_digest(
            state,
            candidate_operator_ids=candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            guardrail=guardrail,
        )
        request_entry = {
            "decision_id": decision_id,
            "generation_index": state.generation_index,
            "evaluation_index": state.evaluation_index,
            "decision_index": (
                None
                if state.metadata.get("decision_index") is None
                else int(state.metadata.get("decision_index"))
            ),
            "provider": self.config.provider,
            "model": self.config.model,
            "capability_profile": self.config.capability_profile,
            "performance_profile": self.config.performance_profile,
            "candidate_operator_ids": list(candidate_operator_ids),
            "policy_phase": policy_snapshot.phase,
            "phase_source": "policy_kernel",
            "policy_reason_codes": list(policy_snapshot.reason_codes),
            "policy_reset_active": policy_snapshot.reset_active,
            "original_candidate_operator_ids": list(original_candidate_operator_ids),
            "guardrail": None if guardrail is None else dict(guardrail),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "accepted_for_evaluation": False,
            "accepted_evaluation_indices": [],
            "accepted_evaluation_index": None,
            "rejection_reason": "",
            **request_surface,
            **entry_convert_metadata,
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
            response_entry = {
                "decision_id": decision_id,
                "generation_index": state.generation_index,
                "evaluation_index": state.evaluation_index,
                "decision_index": (
                    None
                    if state.metadata.get("decision_index") is None
                    else int(state.metadata.get("decision_index"))
                ),
                "provider": self.config.provider,
                "model": self.config.model,
                "candidate_operator_ids": list(candidate_operator_ids),
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
                operator_selected="",
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
            fallback_decision = self.fallback_controller.select_decision(state, candidate_operator_ids, rng)
            metadata = dict(fallback_decision.metadata)
            metadata.update(
                {
                    "decision_id": decision_id,
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
        response_entry = {
            "decision_id": decision_id,
            "generation_index": state.generation_index,
            "evaluation_index": state.evaluation_index,
            "decision_index": (
                None
                if state.metadata.get("decision_index") is None
                else int(state.metadata.get("decision_index"))
            ),
            "provider": response.provider,
            "model": response.model,
            "capability_profile": response.capability_profile,
            "performance_profile": response.performance_profile,
            "selected_operator_id": response.selected_operator_id,
            "selected_intent": response.selected_intent,
            "phase": policy_snapshot.phase,
            "phase_source": "policy_kernel",
            "model_phase": response.phase,
            "model_rationale_present": bool(response.rationale.strip()),
            "rationale": response.rationale,
            "raw_payload": dict(response.raw_payload),
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
            **self._selected_entry_metadata(policy_snapshot, response.selected_operator_id),
        }
        self.response_trace.append(response_entry)
        prompt_ref, response_ref = self._emit_controller_trace(
            decision_id=decision_id,
            phase=policy_snapshot.phase,
            operator_selected=response.selected_operator_id,
            operator_pool_snapshot=list(candidate_operator_ids),
            input_state_digest=input_state_digest,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_body=json.dumps(response.raw_payload, ensure_ascii=False, indent=2),
            rationale=response.rationale,
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
            "provider": response.provider,
            "model": response.model,
            "capability_profile": response.capability_profile,
            "performance_profile": response.performance_profile,
            "raw_payload": dict(response.raw_payload),
            "selected_intent": response.selected_intent,
            "fallback_used": False,
            "elapsed_seconds": elapsed_seconds,
            **self._decision_phase_metadata(
                policy_phase=policy_snapshot.phase,
                model_phase=response.phase,
                model_rationale_present=bool(response.rationale.strip()),
            ),
            **entry_convert_metadata,
            **self._selected_entry_metadata(policy_snapshot, response.selected_operator_id),
            "guardrail_reason_codes": list(policy_snapshot.reason_codes),
        }
        response_metadata.update(self._decision_guardrail_metadata(guardrail))
        return ControllerDecision(
            selected_operator_id=response.selected_operator_id,
            phase=policy_snapshot.phase,
            rationale=response.rationale,
            metadata=response_metadata,
        )

    def _record_elapsed_seconds(self, elapsed_seconds: float) -> None:
        total = float(self.metrics.get("elapsed_seconds_total", 0.0)) + float(elapsed_seconds)
        count = int(self.metrics.get("request_count", 0))
        self.metrics["elapsed_seconds_total"] = total
        self.metrics["elapsed_seconds_avg"] = 0.0 if count <= 0 else total / count
        self.metrics["elapsed_seconds_max"] = max(float(self.metrics.get("elapsed_seconds_max", 0.0)), elapsed_seconds)

    @staticmethod
    def _decision_id(state: ControllerState) -> str:
        decision_index = int(state.metadata.get("decision_index", 0) or 0)
        return format_decision_id(state.generation_index, state.evaluation_index, decision_index)

    @staticmethod
    def _request_markdown_body(*, system_prompt: str, user_prompt: str) -> str:
        return f"# System\n\n{system_prompt.strip()}\n\n# User\n\n{user_prompt.strip()}\n"

    @staticmethod
    def _input_state_digest(
        state: ControllerState,
        *,
        candidate_operator_ids: Sequence[str],
        policy_snapshot: PolicySnapshot,
        guardrail: dict[str, Any] | None,
    ) -> str:
        payload = {
            "family": state.family,
            "backbone": state.backbone,
            "generation_index": int(state.generation_index),
            "evaluation_index": int(state.evaluation_index),
            "parent_count": int(state.parent_count),
            "vector_size": int(state.vector_size),
            "candidate_operator_ids": [str(operator_id) for operator_id in candidate_operator_ids],
            "metadata": dict(state.metadata),
            "policy_snapshot": {
                "phase": str(policy_snapshot.phase),
                "allowed_operator_ids": [str(operator_id) for operator_id in policy_snapshot.allowed_operator_ids],
                "reason_codes": [str(reason_code) for reason_code in policy_snapshot.reason_codes],
                "reset_active": bool(policy_snapshot.reset_active),
            },
            "guardrail": None if guardrail is None else dict(guardrail),
        }
        serialized = json.dumps(
            LLMOperatorController._json_digest_safe(payload),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha1(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _json_digest_safe(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Mapping):
            return {
                LLMOperatorController._json_digest_key(key): LLMOperatorController._json_digest_safe(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set, frozenset)):
            return [LLMOperatorController._json_digest_safe(item) for item in value]
        if isinstance(value, np.ndarray):
            return [LLMOperatorController._json_digest_safe(item) for item in value.tolist()]
        return str(value)

    @staticmethod
    def _json_digest_key(key: Any) -> str:
        if isinstance(key, str):
            return key
        normalized = LLMOperatorController._json_digest_safe(key)
        if normalized is None or isinstance(normalized, (int, float, bool)):
            return str(normalized)
        if isinstance(normalized, str):
            return normalized
        return json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"))

    def configure_trace_outputs(
        self,
        *,
        controller_trace_path: Path,
        llm_request_trace_path: Path,
        llm_response_trace_path: Path,
        prompt_store: PromptStore,
    ) -> None:
        """Wire the canonical JSONL trace outputs for persisted optimizer runs."""
        self._controller_trace_path = Path(controller_trace_path)
        self._llm_request_trace_path = Path(llm_request_trace_path)
        self._llm_response_trace_path = Path(llm_response_trace_path)
        self._prompt_store = prompt_store

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
        http_status: int | None,
        retries: int,
        tokens: dict | None,
        finish_reason: str | None,
        request_surface: Mapping[str, Any] | None,
        response_surface: Mapping[str, Any] | None,
    ) -> tuple[str | None, str | None]:
        """Emit § 4.4 controller_trace row + § 4.5 request/response rows when trace outputs are configured."""
        if self._controller_trace_path is None or self._prompt_store is None:
            return None, None
        prompt_ref = self._prompt_store.store(
            kind="request",
            body=self._request_markdown_body(system_prompt=system_prompt, user_prompt=user_prompt),
            model=self.config.model,
            decision_id=decision_id,
        )
        response_ref = self._prompt_store.store(
            kind="response",
            body=response_body,
            model=self.config.model,
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
        append_jsonl(
            self._llm_request_trace_path,
            {
                "decision_id": decision_id,
                "prompt_ref": prompt_ref,
                "model": self.config.model,
                "http_status": http_status,
                "retries": int(retries),
                "latency_ms": float(latency_ms),
                **({} if request_surface is None else dict(request_surface)),
            },
        )
        append_jsonl(
            self._llm_response_trace_path,
            {
                "decision_id": decision_id,
                "response_ref": response_ref,
                "model": self.config.model,
                "tokens": dict(tokens) if tokens else {},
                "finish_reason": finish_reason,
                "http_status": http_status,
                "retries": int(retries),
                "latency_ms": float(latency_ms),
                **({} if response_surface is None else self._trace_surface_without_bodies(response_surface)),
            },
        )
        return prompt_ref, response_ref

    @staticmethod
    def _trace_surface_without_bodies(surface: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(surface)
        for key in ("system_prompt", "user_prompt", "response_text", "raw_payload"):
            payload.pop(key, None)
        return payload

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
                candidate_operator_ids=candidate_operator_ids,
                attempt_trace=attempt_trace,
            )
        except TypeError as exc:
            if "attempt_trace" not in str(exc):
                raise
            attempt_trace.clear()
            return self.client.request_operator_decision(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=candidate_operator_ids,
            )

    def _record_attempt_metrics(self, attempt_trace: Sequence[dict[str, Any]]) -> None:
        invalid_attempts = [row for row in attempt_trace if not bool(row.get("valid", False))]
        self.metrics["retry_count"] = int(self.metrics.get("retry_count", 0)) + max(0, len(attempt_trace) - 1)
        self.metrics["invalid_response_count"] = int(self.metrics.get("invalid_response_count", 0)) + len(
            invalid_attempts
        )
        for row in invalid_attempts:
            error_message = str(row.get("error", ""))
            if "outside the requested operator registry" in error_message:
                self.metrics["semantic_invalid_count"] = int(self.metrics.get("semantic_invalid_count", 0)) + 1
            else:
                self.metrics["schema_invalid_count"] = int(self.metrics.get("schema_invalid_count", 0)) + 1

    def _build_system_prompt(
        self,
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
        *,
        policy_snapshot: PolicySnapshot,
        guardrail: dict[str, Any] | None,
    ) -> str:
        intent_panel = self._build_intent_panel(candidate_operator_ids)
        operator_intent_map = {
            str(operator_id): _OPERATOR_INTENTS.get(str(operator_id), "native_baseline")
            for operator_id in candidate_operator_ids
        }
        prompt = (
            "You are an operator-selection controller for constrained multiobjective thermal optimization. "
            "Return one operator from candidate_operator_ids; do not emit raw design vectors. "
            "Use metadata.prompt_panels, metadata.intent_panel, metadata.decision_axes, and phase_policy as the "
            "decision surface. Rank by preserve_score, frontier_score, regression_risk, objective balance, "
            "applicability, expected effects, retrieval evidence, and soft guardrails. Treat recent concentration as "
            "context, not an instruction to copy it. Keep every provided candidate operator available; policy guidance "
            "is soft unless the candidate list itself changes. Prefer shared primitive operators whose intent matches "
            "the current domain regime, but keep native_baseline as a valid fair-pool anchor rather than a fallback-only "
            "option. Use native_baseline when it is comparably applicable or when its frontier/feasibility evidence is "
            "not clearly weaker than domain primitives; reserve repeated native_baseline only when it is repeatedly "
            "dominant without corresponding diversity or progress. Use sink_budget_adjust only when sink span, sink budget, "
            "or sink alignment is the active bottleneck; do not treat it as a generic preserve-feasibility answer. If "
            "shared_primitive_trial_candidates are listed, treat them as bounded diversification choices over the same fair "
            "primitive pool. If semantic_trial_mode is encourage_bounded_trial, use at most one listed semantic trial before "
            "returning to native_baseline. "
            "Treat exact positive retrieval matches as strongest same-regime route evidence; when exact_positive_match_mode "
            "is prefer_exact_match, prioritize metadata.decision_axes.exact_positive_match_operator_ids when risk is "
            "comparable. When the hotspot is already inside the sink corridor, hotspot_spread is a direct expand move "
            "rather than a sink-retargeting detour. "
            f"Intent menu: {intent_panel}. Candidate operator intents: {operator_intent_map}."
        )
        phase_policy_guidance = self._build_phase_policy_guidance(policy_snapshot)
        if phase_policy_guidance:
            prompt = f"{prompt} {phase_policy_guidance}"
        objective_balance_guidance = self._build_objective_balance_guidance(state, candidate_operator_ids)
        if objective_balance_guidance:
            prompt = f"{prompt} {objective_balance_guidance}"
        generation_local_guidance = self._build_generation_local_guidance(state, candidate_operator_ids)
        if generation_local_guidance:
            prompt = f"{prompt} {generation_local_guidance}"
        if self._is_before_first_feasible(state):
            prompt = (
                f"{prompt} "
                "Before first feasible, prefer stable repeatable evidence over speculative one-off gains. "
                "Do not over-weight one-off large total-violation improvements from low-support operators."
            )
        route_family_guidance = self._build_route_family_guidance(
            candidate_operator_ids,
            policy_snapshot=policy_snapshot,
        )
        if route_family_guidance:
            prompt = f"{prompt} {route_family_guidance}"
        if guardrail is None:
            return prompt
        dominant_operator_id = str(guardrail.get("dominant_operator_id", "")).strip()
        if not dominant_operator_id:
            return prompt
        dominant_share = float(guardrail.get("dominant_operator_share", 0.0))
        return (
            f"{prompt} "
            f"A dominance guardrail detected {dominant_operator_id} at "
            f"{dominant_share:.0%} recent concentration. Treat this as soft advice: consider alternatives "
            "when they are comparably applicable, but keep every provided candidate operator available if the "
            "current state makes it necessary."
        )

    def _build_user_prompt(
        self,
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
        *,
        original_candidate_operator_ids: Sequence[str],
        policy_snapshot: PolicySnapshot,
        guardrail: dict[str, Any] | None,
        ) -> str:
        metadata = self._build_prompt_metadata(
            state,
            candidate_operator_ids,
            original_candidate_operator_ids=original_candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            guardrail=guardrail,
        )
        return self._serialize_user_prompt(
            state,
            candidate_operator_ids,
            metadata=metadata,
        )

    @staticmethod
    def _serialize_user_prompt(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
        *,
        metadata: Mapping[str, Any],
    ) -> str:
        payload = {
            "family": state.family,
            "backbone": state.backbone,
            "generation_index": state.generation_index,
            "evaluation_index": state.evaluation_index,
            "parent_count": state.parent_count,
            "vector_size": state.vector_size,
            "candidate_operator_ids": list(candidate_operator_ids),
            "metadata": metadata,
        }
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    @staticmethod
    def _build_prompt_metadata(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
        *,
        original_candidate_operator_ids: Sequence[str],
        policy_snapshot: PolicySnapshot,
        guardrail: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metadata = build_prompt_projection(
            state,
            candidate_operator_ids=candidate_operator_ids,
            original_candidate_operator_ids=original_candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            guardrail=guardrail,
        )
        metadata["intent_panel"] = LLMOperatorController._build_intent_panel(candidate_operator_ids)
        metadata["decision_axes"] = LLMOperatorController._build_decision_axes(metadata)
        return metadata

    @staticmethod
    def _build_intent_panel(candidate_operator_ids: Sequence[str]) -> dict[str, str]:
        intent_ids = [
            _OPERATOR_INTENTS.get(str(operator_id), "native_baseline")
            for operator_id in candidate_operator_ids
        ]
        ordered_intent_ids = list(dict.fromkeys(intent_ids))
        return {
            intent_id: _INTENT_SUMMARIES.get(intent_id, "match the current controller regime.")
            for intent_id in ordered_intent_ids
        }

    @staticmethod
    def _build_decision_axes(metadata: Mapping[str, Any]) -> dict[str, Any]:
        prompt_panels = metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            prompt_panels = {}
        regime_panel = prompt_panels.get("regime_panel")
        if not isinstance(regime_panel, Mapping):
            regime_panel = {}
        operator_panel = prompt_panels.get("operator_panel")
        if not isinstance(operator_panel, Mapping):
            operator_panel = {}
        spatial_panel = prompt_panels.get("spatial_panel")
        if not isinstance(spatial_panel, Mapping):
            spatial_panel = {}
        generation_panel = prompt_panels.get("generation_panel")
        if not isinstance(generation_panel, Mapping):
            generation_panel = {}
        retrieval_panel = prompt_panels.get("retrieval_panel")
        if not isinstance(retrieval_panel, Mapping):
            retrieval_panel = {}
        objective_balance = regime_panel.get("objective_balance")
        if not isinstance(objective_balance, Mapping):
            objective_balance = {}
        candidate_operator_ids = [str(operator_id) for operator_id in metadata.get("candidate_operator_ids", [])]
        if not candidate_operator_ids:
            candidate_operator_ids = [str(operator_id) for operator_id in operator_panel.keys()]
        preferred_effect = str(objective_balance.get("preferred_effect", "")).strip()

        peak_improve_candidates: list[str] = []
        gradient_improve_candidates: list[str] = []
        for operator_id, operator_row in operator_panel.items():
            if not isinstance(operator_row, Mapping):
                continue
            applicability = str(operator_row.get("applicability", "low"))
            if applicability == "low":
                continue
            normalized_operator_id = str(operator_id)
            if str(operator_row.get("expected_peak_effect", "")) == "improve":
                peak_improve_candidates.append(normalized_operator_id)
            if str(operator_row.get("expected_gradient_effect", "")) == "improve":
                gradient_improve_candidates.append(normalized_operator_id)

        pressure_to_score = {"low": 1, "medium": 2, "high": 3}
        preserve_score = pressure_to_score.get(str(regime_panel.get("preservation_pressure", "low")), 1)
        frontier_score = pressure_to_score.get(str(regime_panel.get("frontier_pressure", "low")), 1)
        regression_risk_rank = {"low": 1, "medium": 2, "high": 3}
        regression_risk = "low"
        for row in operator_panel.values():
            if not isinstance(row, Mapping):
                continue
            candidate_risk = str(
                row.get("expected_feasibility_risk", row.get("recent_regression_risk", "low"))
            )
            if regression_risk_rank.get(candidate_risk, 0) > regression_risk_rank.get(regression_risk, 0):
                regression_risk = candidate_risk
        if preserve_score >= 3 and frontier_score <= 1:
            primary_objective = "preserve_feasible"
        elif frontier_score >= preserve_score:
            primary_objective = "frontier_expand"
        else:
            primary_objective = "balanced"
        semantic_trial_mode = "none"
        semantic_trial_reason = ""
        semantic_trial_candidates: list[str] = []
        shared_primitive_trial_candidates: list[str] = []
        route_family_candidates: list[str] = []
        exact_positive_match_operator_ids = LLMOperatorController._build_exact_positive_match_operator_ids(
            retrieval_panel,
            operator_panel=operator_panel,
        )
        exact_positive_match_route_families = LLMOperatorController._build_exact_positive_match_route_families(
            retrieval_panel,
            exact_positive_match_operator_ids=exact_positive_match_operator_ids,
        )
        exact_positive_match_mode = "none"
        route_stage = "direct_operator"
        route_family_mode = "none"
        phase = str(regime_panel.get("phase", ""))
        if phase == "prefeasible_convert":
            semantic_trial_candidates = LLMOperatorController._build_semantic_trial_candidates(operator_panel)
            route_family_candidates = LLMOperatorController._build_route_family_candidates(
                operator_panel,
                semantic_trial_candidates=semantic_trial_candidates,
            )
            if route_family_candidates:
                route_stage = "family_then_operator"
                route_family_mode = "convert_family_mix"
                semantic_trial_mode = "encourage_bounded_trial"
                semantic_trial_reason = "prefeasible_convert_entry_mix"
        elif phase in {"post_feasible_expand", "post_feasible_recover", "post_feasible_preserve"} and preserve_score >= 2:
            semantic_trial_candidates = LLMOperatorController._build_semantic_trial_candidates(operator_panel)
            route_family_candidates = LLMOperatorController._build_route_family_candidates(
                operator_panel,
                semantic_trial_candidates=semantic_trial_candidates,
            )
            shared_primitive_trial_candidates = LLMOperatorController._build_shared_primitive_trial_candidates(
                operator_panel,
                preferred_effect=preferred_effect,
                frontier_score=frontier_score,
            )
            if phase == "post_feasible_expand":
                hotspot_spread_operator_id = ""
                for candidate_id in ("hotspot_spread", "spread_hottest_cluster"):
                    if candidate_id in semantic_trial_candidates:
                        hotspot_spread_operator_id = candidate_id
                        break
                if (
                    bool(spatial_panel.get("hotspot_inside_sink_window", False))
                    and hotspot_spread_operator_id
                ):
                    semantic_trial_mode = "encourage_bounded_trial"
                    semantic_trial_reason = "sink_aligned_compact_hotspot"
                    semantic_trial_candidates = [
                        hotspot_spread_operator_id,
                        *[
                            operator_id
                            for operator_id in semantic_trial_candidates
                            if operator_id != hotspot_spread_operator_id
                        ],
                    ]
                elif frontier_score >= 3 and semantic_trial_candidates:
                    semantic_trial_mode = "consider_semantic_expand"
                    semantic_trial_reason = "frontier_pressure_high"
            elif (
                phase in {"post_feasible_recover", "post_feasible_preserve"}
                and str(objective_balance.get("preferred_effect", "")).strip() == "gradient_improve"
                and str(objective_balance.get("balance_pressure", "")).strip() in {"high", "medium"}
                and route_family_candidates
            ):
                semantic_trial_mode = "encourage_bounded_trial"
                semantic_trial_reason = (
                    "recover_gradient_pressure"
                    if phase == "post_feasible_recover"
                    else "preserve_gradient_pressure"
                )
            if route_family_candidates:
                route_stage = "family_then_operator"
                if phase == "post_feasible_expand":
                    route_family_mode = "bounded_expand_mix"
                elif phase == "post_feasible_recover":
                    route_family_mode = "recover_family_mix"
                elif phase == "post_feasible_preserve":
                    route_family_mode = "preserve_family_mix"
        if route_family_mode != "none" and exact_positive_match_operator_ids:
            exact_positive_match_mode = "prefer_exact_match"
            semantic_trial_candidates = LLMOperatorController._prioritize_ordered_values(
                exact_positive_match_operator_ids,
                semantic_trial_candidates,
            )
            route_family_candidates = LLMOperatorController._prioritize_ordered_values(
                exact_positive_match_route_families,
                route_family_candidates,
            )
        if phase in {"post_feasible_expand", "post_feasible_recover", "post_feasible_preserve"} and preserve_score >= 2:
            shared_primitive_trial_candidates = LLMOperatorController._prioritize_shared_primitive_trial_candidates(
                candidate_operator_ids,
                operator_panel,
                shared_primitive_trial_candidates,
                preferred_effect=preferred_effect,
                frontier_score=frontier_score,
            )
            if not shared_primitive_trial_candidates:
                shared_primitive_trial_candidates = LLMOperatorController._build_shared_primitive_trial_candidates(
                    operator_panel,
                    preferred_effect=preferred_effect,
                    frontier_score=frontier_score,
                )
        return {
            "objective_balance_pressure": str(objective_balance.get("balance_pressure", "low")),
            "preferred_effect": objective_balance.get("preferred_effect"),
            "stagnant_objectives": [
                str(objective_id) for objective_id in objective_balance.get("stagnant_objectives", [])
            ],
            "improving_objectives": [
                str(objective_id) for objective_id in objective_balance.get("improving_objectives", [])
            ],
            "peak_improve_candidates": peak_improve_candidates,
            "gradient_improve_candidates": gradient_improve_candidates,
            "generation_dominant_operator_id": str(generation_panel.get("dominant_operator_id", "")),
            "generation_dominant_operator_share": float(generation_panel.get("dominant_operator_share", 0.0)),
            "generation_accepted_count": int(generation_panel.get("accepted_count", 0)),
            "preserve_score": preserve_score,
            "frontier_score": frontier_score,
            "regression_risk": regression_risk,
            "primary_objective": primary_objective,
            "semantic_trial_mode": semantic_trial_mode,
            "semantic_trial_reason": semantic_trial_reason,
            "semantic_trial_candidates": semantic_trial_candidates,
            "shared_primitive_trial_candidates": shared_primitive_trial_candidates,
            "semantic_trial_limit": 1 if semantic_trial_mode == "encourage_bounded_trial" else 0,
            "route_stage": route_stage,
            "route_family_mode": route_family_mode,
            "route_family_candidates": route_family_candidates,
            "exact_positive_match_mode": exact_positive_match_mode,
            "exact_positive_match_operator_ids": exact_positive_match_operator_ids,
            "exact_positive_match_route_families": exact_positive_match_route_families,
        }

    @staticmethod
    def _request_surface_metadata(
        *,
        candidate_operator_ids: Sequence[str],
        original_candidate_operator_ids: Sequence[str],
        guardrail: Mapping[str, Any] | None,
        metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        decision_axes = metadata.get("decision_axes")
        if not isinstance(decision_axes, Mapping):
            decision_axes = {}
        guardrail_payload = {} if guardrail is None else dict(guardrail)
        effective_candidate_operator_ids = [
            str(operator_id)
            for operator_id in guardrail_payload.get("effective_candidate_operator_ids", candidate_operator_ids)
        ]
        filtered_operator_ids = [
            str(operator_id)
            for operator_id in guardrail_payload.get("filtered_operator_ids", [])
        ]
        original_route_families = sorted(
            {
                operator_route_family(operator_id)
                for operator_id in original_candidate_operator_ids
                if operator_route_family(operator_id)
            }
        )
        visible_route_families = sorted(
            {
                operator_route_family(operator_id)
                for operator_id in effective_candidate_operator_ids
                if operator_route_family(operator_id)
            }
        )
        filtered_route_families = sorted(
            {
                operator_route_family(operator_id)
                for operator_id in filtered_operator_ids
                if operator_route_family(operator_id)
            }
        )
        prompt_panels = metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            prompt_panels = {}
        regime_panel = prompt_panels.get("regime_panel")
        if not isinstance(regime_panel, Mapping):
            regime_panel = {}
        retrieval_panel = prompt_panels.get("retrieval_panel")
        if not isinstance(retrieval_panel, Mapping):
            retrieval_panel = {}
        visibility_floor_families = [
            str(route_family)
            for route_family in retrieval_panel.get("visibility_floor_families", [])
            if str(route_family).strip()
        ]
        recover_release_evidence_active = bool(regime_panel.get("recover_release_ready", False))
        if not recover_release_evidence_active:
            recover_release_evidence_active = (
                str(regime_panel.get("preservation_pressure", "low")).strip() == "high"
                and bool({str(route_family).strip() for route_family in visibility_floor_families} & STABLE_ROUTE_FAMILIES)
            )
        guardrail_reason_codes = [
            str(reason_code)
            for reason_code in guardrail_payload.get("reason_codes", [])
            if str(reason_code).strip()
        ]
        suppressed_route_family_reasons = {
            route_family: list(guardrail_reason_codes)
            for route_family in filtered_route_families
        }
        return {
            "original_candidate_pool_size": int(len(tuple(original_candidate_operator_ids))),
            "effective_candidate_pool_size": int(len(tuple(effective_candidate_operator_ids))),
            "original_route_families": original_route_families,
            "visible_route_families": visible_route_families,
            "effective_route_families": visible_route_families,
            "filtered_route_families": filtered_route_families,
            "suppressed_route_families": filtered_route_families,
            "suppressed_route_family_reasons": suppressed_route_family_reasons,
            "route_family_mode": str(decision_axes.get("route_family_mode", "none")),
            "route_family_candidates": [
                str(route_family) for route_family in decision_axes.get("route_family_candidates", [])
            ],
            "exact_positive_match_mode": str(decision_axes.get("exact_positive_match_mode", "none")),
            "exact_positive_match_operator_ids": [
                str(operator_id) for operator_id in decision_axes.get("exact_positive_match_operator_ids", [])
            ],
            "exact_positive_match_route_families": [
                str(route_family) for route_family in decision_axes.get("exact_positive_match_route_families", [])
            ],
            "route_stage": str(decision_axes.get("route_stage", "direct_operator")),
            "semantic_trial_mode": str(decision_axes.get("semantic_trial_mode", "none")),
            "semantic_trial_reason": str(decision_axes.get("semantic_trial_reason", "")),
            "semantic_trial_candidates": [
                str(operator_id) for operator_id in decision_axes.get("semantic_trial_candidates", [])
            ],
            "shared_primitive_trial_candidates": [
                str(operator_id) for operator_id in decision_axes.get("shared_primitive_trial_candidates", [])
            ],
            "stable_local_handoff_active": bool(retrieval_panel.get("stable_local_handoff_active", False)),
            "positive_match_families": [
                str(route_family)
                for route_family in retrieval_panel.get("positive_match_families", [])
                if str(route_family).strip()
            ],
            "visibility_floor_families": visibility_floor_families,
            "objective_balance_pressure": str(decision_axes.get("objective_balance_pressure", "low")),
            "preferred_effect": str(decision_axes.get("preferred_effect", "")),
            "recover_exit_ready": bool(regime_panel.get("recover_exit_ready", False)),
            "recover_release_ready": bool(regime_panel.get("recover_release_ready", False)),
            "recover_release_evidence_active": bool(recover_release_evidence_active),
            "recover_reentry_pressure": str(regime_panel.get("recover_reentry_pressure", "low")),
            "diversity_deficit_level": str(regime_panel.get("diversity_deficit_level", "low")),
        }

    @staticmethod
    def _build_semantic_trial_candidates(operator_panel: dict[str, Any]) -> list[str]:
        candidates: list[str] = []
        rows = operator_panel.items() if isinstance(operator_panel, dict) else ()
        for operator_id, row in rows:
            normalized_operator_id = str(operator_id)
            if normalized_operator_id in _STABLE_PROMPT_OPERATOR_IDS or not isinstance(row, dict):
                continue
            expected_feasibility_risk = str(
                row.get("expected_feasibility_risk", row.get("recent_regression_risk", "medium"))
            )
            if expected_feasibility_risk == "high":
                continue
            if LLMOperatorController._low_post_feasible_success_trial(row):
                continue
            applicability = str(row.get("applicability", "low"))
            medium_gradient_smoothing = (
                normalized_operator_id == "gradient_band_smooth"
                and applicability == "medium"
                and str(row.get("expected_gradient_effect", "")) == "improve"
            )
            if applicability != "high" and not medium_gradient_smoothing:
                continue
            candidates.append(normalized_operator_id)
        return candidates

    @staticmethod
    def _build_shared_primitive_trial_candidates(
        operator_panel: Mapping[str, Any],
        *,
        preferred_effect: str,
        frontier_score: int,
    ) -> list[str]:
        candidates: list[str] = []
        if not isinstance(operator_panel, Mapping):
            return candidates
        preferred_effect = str(preferred_effect or "")
        if preferred_effect == "gradient_improve":
            ordered_operator_ids = ("component_subspace_sbx", "component_block_translate_2_4")
        else:
            ordered_operator_ids = ("component_block_translate_2_4", "component_subspace_sbx")
        for operator_id in ordered_operator_ids:
            row = operator_panel.get(operator_id)
            if not isinstance(row, Mapping):
                continue
            applicability = str(row.get("applicability", "low"))
            if applicability not in {"medium", "high"}:
                continue
            risk = str(row.get("expected_feasibility_risk", row.get("recent_regression_risk", "medium")))
            if risk == "high":
                continue
            if LLMOperatorController._low_post_feasible_success_trial(dict(row)):
                continue
            if operator_id not in candidates:
                candidates.append(operator_id)
        return candidates

    @staticmethod
    def _prioritize_shared_primitive_trial_candidates(
        candidate_operator_ids: Sequence[str],
        operator_panel: Mapping[str, Any],
        shared_primitive_trial_candidates: Sequence[str],
        *,
        preferred_effect: str,
        frontier_score: int,
    ) -> list[str]:
        if not shared_primitive_trial_candidates:
            return []
        candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
        preferred_effect = str(preferred_effect or "")
        prioritized: list[str] = []
        for operator_id in shared_primitive_trial_candidates:
            normalized_operator_id = str(operator_id)
            if normalized_operator_id not in candidate_set:
                continue
            operator_row = operator_panel.get(normalized_operator_id)
            if not isinstance(operator_row, Mapping):
                continue
            applicability = str(operator_row.get("applicability", "low"))
            if applicability not in {"medium", "high"}:
                continue
            if preferred_effect == "peak_improve" and str(operator_row.get("expected_peak_effect", "")) == "improve":
                prioritized.append(normalized_operator_id)
                continue
            if preferred_effect == "gradient_improve" and str(operator_row.get("expected_gradient_effect", "")) == "improve":
                prioritized.append(normalized_operator_id)
                continue
            if frontier_score >= 3:
                prioritized.append(normalized_operator_id)
                continue
            prioritized.append(normalized_operator_id)
        if not prioritized:
            return []
        return list(dict.fromkeys(prioritized))


    @staticmethod
    def _low_post_feasible_success_trial(row: dict[str, Any]) -> bool:
        selection_count = int(row.get("post_feasible_selection_count", 0))
        if selection_count < 4:
            return False
        success_rate = row.get("post_feasible_success_rate")
        if success_rate is None:
            success_rate = float(row.get("post_feasible_success_count", 0)) / float(selection_count)
        if float(success_rate) >= 0.35:
            return False
        return str(row.get("frontier_evidence", "limited")) != "positive"

    @staticmethod
    def _build_route_family_candidates(
        operator_panel: dict[str, Any],
        *,
        semantic_trial_candidates: Sequence[str],
    ) -> list[str]:
        ordered_operator_ids: list[str] = []
        for operator_id in semantic_trial_candidates:
            normalized_operator_id = str(operator_id)
            if normalized_operator_id not in ordered_operator_ids:
                ordered_operator_ids.append(normalized_operator_id)
        for operator_id in operator_panel.keys() if isinstance(operator_panel, dict) else ():
            normalized_operator_id = str(operator_id)
            if normalized_operator_id not in ordered_operator_ids:
                row = operator_panel.get(normalized_operator_id)
                if isinstance(row, Mapping) and LLMOperatorController._positive_route_trial_candidate(row):
                    ordered_operator_ids.append(normalized_operator_id)

        route_family_candidates: list[str] = []
        for operator_id in ordered_operator_ids:
            route_family = ROUTE_FAMILY_BY_OPERATOR.get(operator_id)
            if route_family is None or route_family in STABLE_ROUTE_FAMILIES:
                continue
            if route_family not in route_family_candidates:
                route_family_candidates.append(route_family)
        return route_family_candidates

    @staticmethod
    def _positive_route_trial_candidate(row: Mapping[str, Any]) -> bool:
        feasibility_risk = str(
            row.get("expected_feasibility_risk", row.get("recent_regression_risk", "medium"))
        ).strip()
        if feasibility_risk == "high":
            return False
        if LLMOperatorController._low_post_feasible_success_trial(dict(row)):
            return False
        return (
            str(row.get("frontier_evidence", "")).strip() == "positive"
            or int(row.get("recent_expand_frontier_credit", 0)) > 0
            or int(row.get("recent_expand_preserve_credit", 0)) > 0
        )

    @staticmethod
    def _build_exact_positive_match_operator_ids(
        retrieval_panel: Mapping[str, Any],
        *,
        operator_panel: Mapping[str, Any],
    ) -> list[str]:
        operator_panel_ids = {str(operator_id) for operator_id in operator_panel.keys()}
        exact_positive_match_operator_ids: list[str] = []
        all_matches_stable = True
        for match in retrieval_panel.get("positive_matches", []):
            if not isinstance(match, Mapping):
                continue
            route_family = str(match.get("route_family", "")).strip()
            if route_family and route_family not in STABLE_ROUTE_FAMILIES:
                all_matches_stable = False
                break
        for match in retrieval_panel.get("positive_matches", []):
            if not isinstance(match, Mapping):
                continue
            operator_id = str(match.get("operator_id", "")).strip()
            route_family = str(match.get("route_family", "")).strip()
            if (
                not operator_id
                or operator_id not in operator_panel_ids
                or not route_family
                or (route_family in STABLE_ROUTE_FAMILIES and not all_matches_stable)
            ):
                continue
            operator_row = operator_panel.get(operator_id)
            if not isinstance(operator_row, Mapping):
                continue
            applicability = str(operator_row.get("applicability", "low")).strip()
            feasibility_risk = str(
                operator_row.get("expected_feasibility_risk", operator_row.get("recent_regression_risk", "medium"))
            ).strip()
            if applicability not in {"medium", "high"} or feasibility_risk == "high":
                continue
            if operator_id not in exact_positive_match_operator_ids:
                exact_positive_match_operator_ids.append(operator_id)
        return exact_positive_match_operator_ids

    @staticmethod
    def _build_exact_positive_match_route_families(
        retrieval_panel: Mapping[str, Any],
        *,
        exact_positive_match_operator_ids: Sequence[str],
    ) -> list[str]:
        exact_positive_match_operator_id_set = {str(operator_id) for operator_id in exact_positive_match_operator_ids}
        exact_positive_match_route_families: list[str] = []
        all_matches_stable = True
        for match in retrieval_panel.get("positive_matches", []):
            if not isinstance(match, Mapping):
                continue
            route_family = str(match.get("route_family", "")).strip()
            if route_family and route_family not in STABLE_ROUTE_FAMILIES:
                all_matches_stable = False
                break
        for match in retrieval_panel.get("positive_matches", []):
            if not isinstance(match, Mapping):
                continue
            operator_id = str(match.get("operator_id", "")).strip()
            route_family = str(match.get("route_family", "")).strip()
            if (
                not operator_id
                or operator_id not in exact_positive_match_operator_id_set
                or not route_family
                or (route_family in STABLE_ROUTE_FAMILIES and not all_matches_stable)
            ):
                continue
            if route_family not in exact_positive_match_route_families:
                exact_positive_match_route_families.append(route_family)
        return exact_positive_match_route_families

    @staticmethod
    def _prioritize_ordered_values(
        prioritized_values: Sequence[str],
        existing_values: Sequence[str],
    ) -> list[str]:
        ordered_values: list[str] = []
        for value in (*prioritized_values, *existing_values):
            normalized_value = str(value).strip()
            if normalized_value and normalized_value not in ordered_values:
                ordered_values.append(normalized_value)
        return ordered_values

    @staticmethod
    def _prioritize_exact_positive_candidate_operator_ids(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> tuple[str, ...]:
        prompt_panels = state.metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            return tuple(str(operator_id) for operator_id in candidate_operator_ids)
        decision_axes = LLMOperatorController._build_decision_axes({"prompt_panels": dict(prompt_panels)})
        if str(decision_axes.get("exact_positive_match_mode", "none")).strip() != "prefer_exact_match":
            return tuple(str(operator_id) for operator_id in candidate_operator_ids)
        candidate_operator_id_set = {str(operator_id) for operator_id in candidate_operator_ids}
        prioritized_operator_ids = [
            str(operator_id)
            for operator_id in decision_axes.get("exact_positive_match_operator_ids", [])
            if str(operator_id) in candidate_operator_id_set
        ]
        if not prioritized_operator_ids:
            return tuple(str(operator_id) for operator_id in candidate_operator_ids)
        return tuple(
            LLMOperatorController._prioritize_ordered_values(
                prioritized_operator_ids,
                candidate_operator_ids,
            )
        )

    @staticmethod
    def _apply_prefeasible_convert_exact_positive_contract(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
        *,
        policy_snapshot: PolicySnapshot,
    ) -> tuple[str, ...]:
        normalized_candidate_operator_ids = tuple(str(operator_id) for operator_id in candidate_operator_ids)
        if policy_snapshot.phase != "prefeasible_convert":
            return normalized_candidate_operator_ids
        prompt_panels = state.metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            return normalized_candidate_operator_ids
        regime_panel = prompt_panels.get("regime_panel")
        if not isinstance(regime_panel, Mapping):
            return normalized_candidate_operator_ids
        if str(regime_panel.get("entry_pressure", "low")).strip() != "high":
            return normalized_candidate_operator_ids
        retrieval_panel = prompt_panels.get("retrieval_panel")
        if not isinstance(retrieval_panel, Mapping):
            retrieval_panel = {}
        decision_axes = LLMOperatorController._build_decision_axes({"prompt_panels": dict(prompt_panels)})
        if str(decision_axes.get("exact_positive_match_mode", "none")).strip() != "prefer_exact_match":
            return normalized_candidate_operator_ids
        candidate_operator_id_set = set(normalized_candidate_operator_ids)
        exact_positive_operator_ids = [
            str(operator_id)
            for operator_id in decision_axes.get("exact_positive_match_operator_ids", [])
            if str(operator_id) in candidate_operator_id_set
        ]
        if not exact_positive_operator_ids:
            return normalized_candidate_operator_ids
        dominant_violation_family = str(regime_panel.get("dominant_violation_family", "")).strip()
        visibility_floor_families = {
            str(route_family).strip()
            for route_family in retrieval_panel.get("visibility_floor_families", [])
            if str(route_family).strip()
        }
        protected_nonstable_visibility_floor_operator_ids = {
            operator_id
            for operator_id in normalized_candidate_operator_ids
            if (
                operator_route_family(operator_id) == "budget_guard"
                and dominant_violation_family == "sink_budget"
                and operator_route_family(operator_id) in visibility_floor_families
            )
        }
        contracted_candidate_operator_ids: list[str] = []
        for operator_id in normalized_candidate_operator_ids:
            route_family = operator_route_family(operator_id)
            if operator_id in exact_positive_operator_ids:
                contracted_candidate_operator_ids.append(operator_id)
                continue
            if operator_id in protected_nonstable_visibility_floor_operator_ids:
                contracted_candidate_operator_ids.append(operator_id)
                continue
            if route_family == "budget_guard" and dominant_violation_family != "sink_budget":
                continue
            if route_family in STABLE_ROUTE_FAMILIES:
                continue
            entry_evidence_level = str(
                policy_snapshot.candidate_annotations.get(operator_id, {}).get("entry_evidence_level", "")
            ).strip()
            if entry_evidence_level in {"supported", "trusted"}:
                contracted_candidate_operator_ids.append(operator_id)
        if not contracted_candidate_operator_ids:
            return normalized_candidate_operator_ids
        return tuple(contracted_candidate_operator_ids)

    @staticmethod
    def _is_before_first_feasible(state: ControllerState) -> bool:
        run_state = state.metadata.get("run_state")
        if not isinstance(run_state, dict):
            return False
        return run_state.get("first_feasible_eval") is None

    @staticmethod
    def _recent_llm_valid_operator_counter(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> Counter[str]:
        recent_operator_counts = state.metadata.get("recent_operator_counts")
        if isinstance(recent_operator_counts, dict) and recent_operator_counts:
            return Counter(
                {
                    str(operator_id): int(
                        dict(summary).get("recent_llm_valid_selection_count", 0)
                    )
                    for operator_id, summary in recent_operator_counts.items()
                    if str(operator_id) in candidate_operator_ids
                    and int(dict(summary).get("recent_llm_valid_selection_count", 0)) > 0
                }
            )
        recent_decisions = state.metadata.get("recent_decisions", [])
        selected_operator_ids: list[str] = []
        for row in recent_decisions:
            operator_id = str(row.get("selected_operator_id", "")).strip()
            if operator_id not in candidate_operator_ids:
                continue
            if row.get("llm_valid") is True:
                selected_operator_ids.append(operator_id)
                continue
            if row.get("fallback_used") is True:
                continue
            selected_operator_ids.append(operator_id)
        return Counter(selected_operator_ids)

    @staticmethod
    def _recent_llm_valid_operator_sequence(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> tuple[str, ...]:
        recent_decisions = state.metadata.get("recent_decisions", [])
        selected_operator_ids: list[str] = []
        for row in recent_decisions:
            operator_id = str(row.get("selected_operator_id", "")).strip()
            if operator_id not in candidate_operator_ids:
                continue
            if row.get("llm_valid") is True:
                selected_operator_ids.append(operator_id)
                continue
            if row.get("fallback_used") is True:
                continue
            selected_operator_ids.append(operator_id)
        return tuple(selected_operator_ids)

    @staticmethod
    def _apply_recent_dominance_guardrail(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> tuple[tuple[str, ...], dict[str, Any] | None]:
        if len(candidate_operator_ids) <= 1:
            return tuple(candidate_operator_ids), None
        counter = LLMOperatorController._recent_llm_valid_operator_counter(state, candidate_operator_ids)
        recent_llm_valid_count = sum(counter.values())
        dominant_operator_id, dominant_count = ("", 0)
        dominant_share = 0.0
        if recent_llm_valid_count > 0:
            dominant_operator_id, dominant_count = counter.most_common(1)[0]
            dominant_share = dominant_count / float(recent_llm_valid_count)
        min_window = _RECENT_DOMINANCE_MIN_WINDOW
        min_count = _RECENT_DOMINANCE_MIN_COUNT
        min_share = _RECENT_DOMINANCE_MIN_SHARE
        threshold_profile = "default"
        if LLMOperatorController._is_before_first_feasible(state):
            recent_sequence = LLMOperatorController._recent_llm_valid_operator_sequence(state, candidate_operator_ids)
            recent_window = recent_sequence[-_PREFEASIBLE_CUSTOM_DOMINANCE_MIN_WINDOW:]
            window_counter = Counter(recent_window)
            if window_counter:
                window_count = sum(window_counter.values())
                window_operator_id, window_operator_count = window_counter.most_common(1)[0]
                window_share = window_operator_count / float(window_count)
                if (
                    window_operator_id not in _NATIVE_BASELINE_OPERATOR_IDS
                    and LLMOperatorController._operator_has_no_feasible_credit(state, window_operator_id)
                ):
                    counter = window_counter
                    recent_llm_valid_count = window_count
                    dominant_operator_id = window_operator_id
                    dominant_count = window_operator_count
                    dominant_share = window_share
                    min_window = _PREFEASIBLE_CUSTOM_DOMINANCE_MIN_WINDOW
                    min_count = _PREFEASIBLE_CUSTOM_DOMINANCE_MIN_COUNT
                    min_share = _PREFEASIBLE_CUSTOM_DOMINANCE_MIN_SHARE
                    threshold_profile = "prefeasible_zero_credit_custom"
        if recent_llm_valid_count < min_window:
            return tuple(candidate_operator_ids), None
        if dominant_count < min_count or dominant_share < min_share:
            return tuple(candidate_operator_ids), None
        protected_operator_ids = set(
            LLMOperatorController._recent_dominance_visibility_floor_protected_operator_ids(
                state,
                candidate_operator_ids,
            )
        )
        if dominant_operator_id in protected_operator_ids:
            return tuple(candidate_operator_ids), None
        advised_candidate_operator_ids = tuple(
            operator_id for operator_id in candidate_operator_ids if operator_id != dominant_operator_id
        )
        if not advised_candidate_operator_ids:
            return tuple(candidate_operator_ids), None
        return tuple(candidate_operator_ids), {
            "applied": True,
            "reason": "recent_operator_dominance",
            "recent_window_size": int(recent_llm_valid_count),
            "dominant_operator_id": dominant_operator_id,
            "dominant_operator_count": dominant_count,
            "dominant_operator_share": dominant_share,
            "threshold_profile": threshold_profile,
            "recent_counts": {
                operator_id: int(counter[operator_id])
                for operator_id in candidate_operator_ids
                if counter.get(operator_id, 0) > 0
            },
            "discouraged_operator_ids": [dominant_operator_id],
            "filtered_operator_ids": [],
            "original_candidate_operator_ids": list(candidate_operator_ids),
            "effective_candidate_operator_ids": list(candidate_operator_ids),
            "advised_alternative_operator_ids": list(advised_candidate_operator_ids),
        }

    @staticmethod
    def _recent_dominance_visibility_floor_protected_operator_ids(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> tuple[str, ...]:
        prompt_panels = state.metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            return ()
        retrieval_panel = prompt_panels.get("retrieval_panel")
        if not isinstance(retrieval_panel, Mapping):
            return ()
        visibility_floor_families = [
            str(route_family).strip()
            for route_family in retrieval_panel.get("visibility_floor_families", [])
            if str(route_family).strip()
        ]
        if not visibility_floor_families:
            return ()

        positive_match_operator_ids_by_family: dict[str, list[str]] = {}
        for match in retrieval_panel.get("positive_matches", []):
            if not isinstance(match, Mapping):
                continue
            operator_id = str(match.get("operator_id", "")).strip()
            route_family = str(match.get("route_family", "")).strip()
            if not operator_id or not route_family:
                continue
            family_matches = positive_match_operator_ids_by_family.setdefault(route_family, [])
            if operator_id not in family_matches:
                family_matches.append(operator_id)

        protected_operator_ids: list[str] = []
        for route_family in visibility_floor_families:
            family_candidate_operator_ids = [
                str(operator_id)
                for operator_id in candidate_operator_ids
                if operator_route_family(str(operator_id)) == route_family
            ]
            if len(family_candidate_operator_ids) != 1:
                continue
            positive_match_operator_ids = positive_match_operator_ids_by_family.get(route_family, [])
            protected_operator_id = next(
                (
                    operator_id
                    for operator_id in positive_match_operator_ids
                    if operator_id in family_candidate_operator_ids
                ),
                family_candidate_operator_ids[0],
            )
            if protected_operator_id not in protected_operator_ids:
                protected_operator_ids.append(protected_operator_id)
        return tuple(protected_operator_ids)

    @staticmethod
    def _apply_generation_local_dominance_guardrail(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> tuple[tuple[str, ...], dict[str, Any] | None]:
        if len(candidate_operator_ids) <= 1:
            return tuple(candidate_operator_ids), None
        progress_state = state.metadata.get("progress_state")
        phase = str(state.metadata.get("search_phase", "")).strip()
        if isinstance(progress_state, Mapping):
            phase = str(progress_state.get("phase") or state.metadata.get("search_phase", "")).strip()
            post_feasible_mode = str(progress_state.get("post_feasible_mode", "")).strip()
            if phase.startswith("post_feasible") and post_feasible_mode:
                phase = f"post_feasible_{post_feasible_mode}"
        if phase not in _GENERATION_LOCAL_DOMINANCE_PHASES:
            return tuple(candidate_operator_ids), None
        generation_local_memory = state.metadata.get("generation_local_memory")
        if not isinstance(generation_local_memory, Mapping):
            return tuple(candidate_operator_ids), None
        accepted_count = int(generation_local_memory.get("accepted_count", 0))
        dominant_operator_id = str(generation_local_memory.get("dominant_operator_id", "")).strip()
        dominant_operator_count = int(generation_local_memory.get("dominant_operator_count", 0))
        dominant_share = float(generation_local_memory.get("dominant_operator_share", 0.0))
        if accepted_count <= 0 or dominant_operator_id not in candidate_operator_ids:
            return tuple(candidate_operator_ids), None
        thresholds = _GENERATION_LOCAL_DOMINANCE_THRESHOLDS.get(
            phase,
            _GENERATION_LOCAL_DOMINANCE_THRESHOLDS["post_feasible_expand"],
        )
        min_window = int(thresholds["min_window"])
        min_count = int(thresholds["min_count"])
        min_share = float(thresholds["min_share"])
        if accepted_count < min_window or dominant_operator_count < min_count or dominant_share < min_share:
            return tuple(candidate_operator_ids), None
        protected_operator_ids = set(
            LLMOperatorController._recent_dominance_visibility_floor_protected_operator_ids(
                state,
                candidate_operator_ids,
            )
        )
        if dominant_operator_id in protected_operator_ids:
            return tuple(candidate_operator_ids), None
        viable_alternatives = LLMOperatorController._generation_local_viable_alternative_candidate_ids(
            state,
            candidate_operator_ids,
            excluded_operator_id=dominant_operator_id,
        )
        if not viable_alternatives:
            return tuple(candidate_operator_ids), None
        advised_candidate_operator_ids = tuple(
            operator_id for operator_id in candidate_operator_ids if operator_id != dominant_operator_id
        )
        if not advised_candidate_operator_ids:
            return tuple(candidate_operator_ids), None
        operator_counts = generation_local_memory.get("operator_counts")
        if not isinstance(operator_counts, Mapping):
            operator_counts = {}
        return tuple(candidate_operator_ids), {
            "applied": True,
            "reason": "generation_local_operator_dominance",
            "recent_window_size": int(accepted_count),
            "dominant_operator_id": dominant_operator_id,
            "dominant_operator_count": int(dominant_operator_count),
            "dominant_operator_share": float(dominant_share),
            "threshold_profile": f"generation_local_{phase}",
            "recent_counts": {
                str(operator_id): int(dict(summary).get("accepted_count", 0))
                for operator_id, summary in operator_counts.items()
                if isinstance(summary, Mapping) and int(dict(summary).get("accepted_count", 0)) > 0
            },
            "discouraged_operator_ids": [dominant_operator_id],
            "filtered_operator_ids": [],
            "original_candidate_operator_ids": list(candidate_operator_ids),
            "effective_candidate_operator_ids": list(candidate_operator_ids),
            "advised_alternative_operator_ids": list(advised_candidate_operator_ids),
            "viable_alternative_operator_ids": list(viable_alternatives),
        }

    @staticmethod
    def _apply_generation_local_strategy_group_guardrail(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> tuple[tuple[str, ...], dict[str, Any] | None]:
        if len(candidate_operator_ids) <= 1:
            return tuple(candidate_operator_ids), None
        progress_state = state.metadata.get("progress_state")
        phase = str(state.metadata.get("search_phase", "")).strip()
        if isinstance(progress_state, Mapping):
            phase = str(progress_state.get("phase") or state.metadata.get("search_phase", "")).strip()
            post_feasible_mode = str(progress_state.get("post_feasible_mode", "")).strip()
            if phase.startswith("post_feasible") and post_feasible_mode:
                phase = f"post_feasible_{post_feasible_mode}"
        if phase not in _GENERATION_LOCAL_DOMINANCE_PHASES:
            return tuple(candidate_operator_ids), None
        generation_local_memory = state.metadata.get("generation_local_memory")
        if not isinstance(generation_local_memory, Mapping):
            return tuple(candidate_operator_ids), None
        accepted_count = int(generation_local_memory.get("accepted_count", 0))
        operator_counts = generation_local_memory.get("operator_counts")
        if not isinstance(operator_counts, Mapping) or accepted_count <= 0:
            return tuple(candidate_operator_ids), None
        strategy_group_counter: Counter[str] = Counter()
        for operator_id, summary in operator_counts.items():
            if not isinstance(summary, Mapping):
                continue
            strategy_group_counter[LLMOperatorController._operator_strategy_group(str(operator_id))] += int(
                dict(summary).get("accepted_count", 0)
            )
        if not strategy_group_counter:
            return tuple(candidate_operator_ids), None
        dominant_group_id, dominant_group_count = strategy_group_counter.most_common(1)[0]
        dominant_group_share = float(dominant_group_count) / float(max(1, accepted_count))
        thresholds = _GENERATION_LOCAL_STRATEGY_GROUP_THRESHOLDS.get(
            phase,
            _GENERATION_LOCAL_STRATEGY_GROUP_THRESHOLDS["post_feasible_expand"],
        )
        min_window = int(thresholds["min_window"])
        min_count = int(thresholds["min_count"])
        min_share = float(thresholds["min_share"])
        if accepted_count < min_window or dominant_group_count < min_count or dominant_group_share < min_share:
            return tuple(candidate_operator_ids), None
        dominant_group_operator_ids = [
            str(operator_id)
            for operator_id in candidate_operator_ids
            if LLMOperatorController._operator_strategy_group(str(operator_id)) == dominant_group_id
        ]
        if not dominant_group_operator_ids or len(dominant_group_operator_ids) == len(candidate_operator_ids):
            return tuple(candidate_operator_ids), None
        viable_alternatives = LLMOperatorController._generation_local_viable_alternative_candidate_ids(
            state,
            candidate_operator_ids,
            excluded_operator_id=dominant_group_operator_ids[0],
            excluded_strategy_groups=[dominant_group_id],
        )
        if not viable_alternatives:
            return tuple(candidate_operator_ids), None
        protected_operator_ids = set(
            LLMOperatorController._generation_local_visibility_floor_protected_operator_ids(
                state,
                candidate_operator_ids,
                dominant_group_id=dominant_group_id,
            )
        )
        advised_candidate_operator_ids = tuple(
            operator_id
            for operator_id in candidate_operator_ids
            if (
                LLMOperatorController._operator_strategy_group(str(operator_id)) != dominant_group_id
                or operator_id in protected_operator_ids
            )
        )
        if not advised_candidate_operator_ids:
            return tuple(candidate_operator_ids), None
        discouraged_operator_ids = [
            operator_id
            for operator_id in dominant_group_operator_ids
            if operator_id not in protected_operator_ids
        ]
        if not discouraged_operator_ids:
            return tuple(candidate_operator_ids), None
        return tuple(candidate_operator_ids), {
            "applied": True,
            "reason": "generation_local_strategy_group_dominance",
            "recent_window_size": int(accepted_count),
            "dominant_operator_id": dominant_group_operator_ids[0],
            "dominant_operator_share": float(dominant_group_share),
            "threshold_profile": f"generation_local_strategy_group_{phase}",
            "recent_counts": {
                str(group_id): int(count)
                for group_id, count in strategy_group_counter.items()
                if int(count) > 0
            },
            "discouraged_operator_ids": discouraged_operator_ids,
            "filtered_operator_ids": [],
            "original_candidate_operator_ids": list(candidate_operator_ids),
            "effective_candidate_operator_ids": list(candidate_operator_ids),
            "advised_alternative_operator_ids": list(advised_candidate_operator_ids),
            "viable_alternative_operator_ids": list(viable_alternatives),
        }

    @staticmethod
    def _decision_guardrail_metadata(guardrail: dict[str, Any] | None) -> dict[str, Any]:
        if guardrail is None:
            return {}
        return {
            "guardrail_applied": bool(guardrail.get("applied", False)),
            "guardrail_reason": str(guardrail.get("reason", "")),
            "guardrail_reason_codes": list(guardrail.get("reason_codes", [])),
            "guardrail_threshold_profile": str(guardrail.get("threshold_profile", "")),
            "guardrail_filtered_operator_ids": list(guardrail.get("filtered_operator_ids", [])),
            "guardrail_discouraged_operator_ids": list(guardrail.get("discouraged_operator_ids", [])),
            "guardrail_soft_advice_operator_ids": list(guardrail.get("soft_advice_operator_ids", [])),
            "guardrail_viable_alternative_operator_ids": list(
                guardrail.get("viable_alternative_operator_ids", [])
            ),
            "guardrail_dominant_operator_id": str(guardrail.get("dominant_operator_id", "")),
            "guardrail_dominant_operator_share": float(guardrail.get("dominant_operator_share", 0.0)),
            "guardrail_recent_window_size": int(guardrail.get("recent_window_size", 0)),
            "guardrail_policy_phase": str(guardrail.get("policy_phase", "")),
            "guardrail_policy_reset_active": bool(guardrail.get("policy_reset_active", False)),
        }

    @staticmethod
    def _decision_phase_metadata(
        *,
        policy_phase: str,
        model_phase: str,
        model_rationale_present: bool,
    ) -> dict[str, Any]:
        return {
            "policy_phase": str(policy_phase),
            "phase_source": "policy_kernel",
            "model_phase": str(model_phase),
            "model_rationale_present": bool(model_rationale_present),
        }

    @staticmethod
    def _operator_has_no_feasible_credit(state: ControllerState, operator_id: str) -> bool:
        operator_summary = state.metadata.get("operator_summary")
        if not isinstance(operator_summary, dict):
            return True
        summary = operator_summary.get(operator_id)
        if not isinstance(summary, dict):
            return True
        return int(summary.get("feasible_entry_count", 0)) <= 0 and int(
            summary.get("feasible_preservation_count", 0)
        ) <= 0

    @staticmethod
    def _build_phase_policy_guidance(policy_snapshot: PolicySnapshot) -> str:
        guidance: list[str] = []
        if policy_snapshot.phase == "cold_start":
            guidance.append(
                "Cold-start policy: bootstrap with stable operator families before speculative custom exploration."
            )
        elif policy_snapshot.phase == "prefeasible_convert":
            guidance.append(
                "Prefeasible convert policy: keep first feasible conversion before frontier growth or Pareto novelty. "
                "Then protect stable near-feasible progress as the second objective. "
                "Favor operators with supported entry evidence that can relieve the dominant violation family."
            )
        elif policy_snapshot.phase.startswith("prefeasible"):
            guidance.append(
                "Prefeasible policy: prioritize trusted evidence and stable operator roles before speculative custom families."
            )
        elif policy_snapshot.phase == "post_feasible_expand":
            guidance.append(
                "Post-feasible expand policy: preserve feasibility first, then use trusted frontier evidence to restore Pareto growth without inviting avoidable regression. "
                "When hotspot geometry is already sink-aligned, a hotspot-spread move can be a bounded semantic trial rather than a speculative detour."
            )
        elif policy_snapshot.phase == "post_feasible_preserve":
            guidance.append(
                "Post-feasible preserve policy: preserve feasibility first, reduce regression pressure second, and only accept frontier gains that do not destabilize the feasible set."
            )
        elif policy_snapshot.phase == "post_feasible_recover":
            guidance.append(
                "Post-feasible recover policy: protect the feasible set first, then narrow choices toward trusted preserve families until regression pressure falls."
            )
        elif policy_snapshot.phase.startswith("post_feasible"):
            guidance.append(
                "Post-feasible policy: keep feasibility stable before prioritizing Pareto improvements."
            )
        if "prefeasible_speculative_family_collapse" in policy_snapshot.reason_codes:
            guidance.append(
                "A family-level policy filter removed speculative custom families that lack trusted evidence."
            )
        if "post_feasible_recover_preserve_bias" in policy_snapshot.reason_codes:
            guidance.append(
                "A recovery filter removed risky expansion families that lack preservation evidence."
            )
        if "post_feasible_expand_frontier_bias" in policy_snapshot.reason_codes:
            guidance.append(
                "A frontier-growth filter removed high-regression families without positive frontier evidence."
            )
        if "post_feasible_expand_semantic_budget" in policy_snapshot.reason_codes:
            guidance.append(
                "A recent expand-budget filter suppressed semantic route families that recently regressed feasibility without frontier return."
            )
        if "post_feasible_stable_low_success_cooldown" in policy_snapshot.reason_codes:
            guidance.append(
                "A stable-operator success advisory cooled routes with repeated post-feasible failures and no frontier credit."
            )
        if any(str(code).endswith("_plateau_cooldown") for code in policy_snapshot.reason_codes):
            guidance.append(
                "A preserve-plateau advisory cooled repeated sink-only preserve moves because objective progress has stalled and viable alternatives remain."
            )
        if "post_feasible_expand_gradient_polish_handoff" in policy_snapshot.reason_codes:
            guidance.append(
                "A gradient-polish handoff cooled uncredited broad moves while keeping broad operators that already earned frontier or objective credit visible as controlled escapes."
            )
        if "post_feasible_expand_saturation_demotion" in policy_snapshot.reason_codes:
            guidance.append(
                "An expand saturation governor demoted this decision from expand to preserve because the frontier "
                "has not improved after a sustained expand window. Prioritize feasibility preservation and avoid "
                "speculative expansion until the next frontier gain resets the saturation counter."
            )
        if policy_snapshot.reset_active:
            guidance.append(
                "A progress-reset window is active, so use trusted evidence to recover from a no-progress streak while preserving stable role diversity across baseline, global exploration, and local cleanup."
            )
        return " ".join(guidance)

    @staticmethod
    def _operator_strategy_group(operator_id: str) -> str:
        return _OPERATOR_STRATEGY_GROUPS.get(str(operator_id), str(operator_id))

    @staticmethod
    def _generation_local_viable_alternative_candidate_ids(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
        *,
        excluded_operator_id: str,
        excluded_strategy_groups: Sequence[str] = (),
    ) -> tuple[str, ...]:
        prompt_panels = state.metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            return ()
        operator_panel = prompt_panels.get("operator_panel")
        if not isinstance(operator_panel, Mapping):
            return ()
        regime_panel = prompt_panels.get("regime_panel")
        if not isinstance(regime_panel, Mapping):
            regime_panel = {}
        objective_balance = regime_panel.get("objective_balance")
        if not isinstance(objective_balance, Mapping):
            objective_balance = {}
        preferred_effect = str(objective_balance.get("preferred_effect") or "")
        excluded_strategy_group_set = {str(group_id) for group_id in excluded_strategy_groups}
        dominant_strategy_group = LLMOperatorController._operator_strategy_group(excluded_operator_id)
        if dominant_strategy_group:
            excluded_strategy_group_set.add(dominant_strategy_group)
        prioritized_operator_ids: list[str] = []
        fallback_operator_ids: list[str] = []
        cross_strategy_operator_ids: list[str] = []
        cross_strategy_fallback_operator_ids: list[str] = []
        for operator_id in candidate_operator_ids:
            normalized_operator_id = str(operator_id)
            if normalized_operator_id == excluded_operator_id:
                continue
            operator_row = operator_panel.get(normalized_operator_id)
            if not isinstance(operator_row, Mapping):
                continue
            applicability = str(operator_row.get("applicability", "low"))
            if applicability not in {"medium", "high"}:
                continue
            alternative_strategy_group = LLMOperatorController._operator_strategy_group(normalized_operator_id)
            fallback_operator_ids.append(normalized_operator_id)
            if alternative_strategy_group not in excluded_strategy_group_set:
                cross_strategy_fallback_operator_ids.append(normalized_operator_id)
            if preferred_effect == "peak_improve" and str(operator_row.get("expected_peak_effect", "")) == "improve":
                prioritized_operator_ids.append(normalized_operator_id)
                if alternative_strategy_group not in excluded_strategy_group_set:
                    cross_strategy_operator_ids.append(normalized_operator_id)
            elif (
                preferred_effect == "gradient_improve"
                and str(operator_row.get("expected_gradient_effect", "")) == "improve"
            ):
                prioritized_operator_ids.append(normalized_operator_id)
                if alternative_strategy_group not in excluded_strategy_group_set:
                    cross_strategy_operator_ids.append(normalized_operator_id)
            elif preferred_effect in {"balanced", ""}:
                prioritized_operator_ids.append(normalized_operator_id)
                if alternative_strategy_group not in excluded_strategy_group_set:
                    cross_strategy_operator_ids.append(normalized_operator_id)
        if cross_strategy_operator_ids:
            return tuple(cross_strategy_operator_ids)
        if prioritized_operator_ids:
            return tuple(prioritized_operator_ids)
        if cross_strategy_fallback_operator_ids:
            return tuple(cross_strategy_fallback_operator_ids)
        return tuple(fallback_operator_ids)

    @staticmethod
    def _generation_local_visibility_floor_protected_operator_ids(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
        *,
        dominant_group_id: str,
    ) -> tuple[str, ...]:
        prompt_panels = state.metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            return ()
        retrieval_panel = prompt_panels.get("retrieval_panel")
        if not isinstance(retrieval_panel, Mapping):
            return ()
        visibility_floor_families = [
            str(route_family).strip()
            for route_family in retrieval_panel.get("visibility_floor_families", [])
            if str(route_family).strip()
        ]
        if not visibility_floor_families:
            return ()

        positive_match_operator_ids_by_family: dict[str, list[str]] = {}
        for match in retrieval_panel.get("positive_matches", []):
            if not isinstance(match, Mapping):
                continue
            operator_id = str(match.get("operator_id", "")).strip()
            route_family = str(match.get("route_family", "")).strip()
            if not operator_id or not route_family:
                continue
            family_matches = positive_match_operator_ids_by_family.setdefault(route_family, [])
            if operator_id not in family_matches:
                family_matches.append(operator_id)

        protected_operator_ids: list[str] = []
        for route_family in visibility_floor_families:
            family_candidate_operator_ids = [
                str(operator_id)
                for operator_id in candidate_operator_ids
                if operator_route_family(str(operator_id)) == route_family
            ]
            if not family_candidate_operator_ids:
                continue
            if any(
                LLMOperatorController._operator_strategy_group(operator_id) != dominant_group_id
                for operator_id in family_candidate_operator_ids
            ):
                continue
            positive_match_operator_ids = positive_match_operator_ids_by_family.get(route_family, [])
            protected_operator_id = next(
                (
                    operator_id
                    for operator_id in positive_match_operator_ids
                    if operator_id in family_candidate_operator_ids
                ),
                family_candidate_operator_ids[0],
            )
            if protected_operator_id not in protected_operator_ids:
                protected_operator_ids.append(protected_operator_id)
        return tuple(protected_operator_ids)

    @staticmethod
    def _build_generation_local_guidance(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        generation_local_memory = state.metadata.get("generation_local_memory")
        if not isinstance(generation_local_memory, Mapping):
            return ""
        accepted_count = int(generation_local_memory.get("accepted_count", 0))
        dominant_operator_id = str(generation_local_memory.get("dominant_operator_id", "")).strip()
        dominant_share = float(generation_local_memory.get("dominant_operator_share", 0.0))
        if accepted_count < 3 or not dominant_operator_id or dominant_operator_id not in candidate_operator_ids:
            return ""
        viable_alternatives = LLMOperatorController._generation_local_viable_alternative_candidate_ids(
            state,
            candidate_operator_ids,
            excluded_operator_id=dominant_operator_id,
        )
        if not viable_alternatives:
            return ""
        dominant_strategy_group = LLMOperatorController._operator_strategy_group(dominant_operator_id)
        return (
            "Current-generation mix alert: "
            f"{dominant_operator_id} already accounts for {dominant_share:.0%} of the {accepted_count} accepted "
            "offspring in this generation. "
            f"Prefer viable alternatives across strategy groups such as {', '.join(viable_alternatives)} instead of copying "
            f"the current {dominant_strategy_group or 'dominant'} strategy again unless it is uniquely required. "
            "If the dominant operator is native_baseline, require clearly stronger frontier evidence before repeating it; "
            "if it is a sink adjustment, repeat it only when sink span, sink budget, or sink alignment remains the active bottleneck."
        )

    @staticmethod
    def _build_objective_balance_guidance(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        prompt_panels = state.metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            return ""
        regime_panel = prompt_panels.get("regime_panel")
        if not isinstance(regime_panel, Mapping):
            return ""
        objective_balance = regime_panel.get("objective_balance")
        if not isinstance(objective_balance, Mapping):
            return ""
        pressure = str(objective_balance.get("balance_pressure", "low"))
        if pressure not in {"high", "medium"}:
            return ""

        preferred_effect = str(objective_balance.get("preferred_effect") or "")
        stagnant_objectives = [str(item) for item in objective_balance.get("stagnant_objectives", [])]
        improving_objectives = [str(item) for item in objective_balance.get("improving_objectives", [])]
        operator_panel = prompt_panels.get("operator_panel")
        if not isinstance(operator_panel, Mapping):
            operator_panel = {}

        effect_key = ""
        if preferred_effect == "peak_improve":
            effect_key = "expected_peak_effect"
        elif preferred_effect == "gradient_improve":
            effect_key = "expected_gradient_effect"
        candidates = [
            str(operator_id)
            for operator_id in candidate_operator_ids
            if isinstance(operator_panel.get(operator_id), Mapping)
            and str(dict(operator_panel[operator_id]).get(effect_key, "")) == "improve"
            and str(dict(operator_panel[operator_id]).get("applicability", "low")) in {"medium", "high"}
            and not LLMOperatorController._low_post_feasible_success_trial(dict(operator_panel[operator_id]))
            and str(
                dict(operator_panel[operator_id]).get(
                    "expected_feasibility_risk",
                    dict(operator_panel[operator_id]).get("recent_regression_risk", "medium"),
                )
            )
            != "high"
        ]
        candidate_text = f" especially {', '.join(candidates)}" if candidates else ""
        stagnant_text = ", ".join(stagnant_objectives) if stagnant_objectives else "one objective"
        improving_text = ", ".join(improving_objectives) if improving_objectives else "the other objective"

        if preferred_effect == "peak_improve":
            return (
                "Objective balance alert: "
                f"{stagnant_text} has stagnated while {improving_text} continues improving. "
                f"Prefer operators with expected_peak_effect=improve and usable applicability{candidate_text} "
                "over operators that only improve gradient. "
                "A bounded temperature_max-focused trial is justified if it preserves feasibility."
            )
        if preferred_effect == "gradient_improve":
            return (
                "Objective balance alert: "
                f"{stagnant_text} has stagnated while {improving_text} continues improving. "
                f"Prefer operators with expected_gradient_effect=improve and usable applicability{candidate_text} "
                "over operators that only improve peak temperature."
            )
        if preferred_effect == "balanced":
            return (
                "Objective balance alert: both objectives look stagnant. "
                "Diversify toward operators with credible applicability to break the current basin."
            )
        return ""

    @staticmethod
    def _build_route_family_guidance(
        candidate_operator_ids: Sequence[str],
        *,
        policy_snapshot: PolicySnapshot,
    ) -> str:
        if policy_snapshot.phase not in {"prefeasible_convert", "post_feasible_expand"}:
            return ""
        route_families: list[str] = []
        for operator_id in candidate_operator_ids:
            route_family = ROUTE_FAMILY_BY_OPERATOR.get(str(operator_id))
            if route_family is None or route_family in STABLE_ROUTE_FAMILIES:
                continue
            if route_family not in route_families:
                route_families.append(route_family)
        if len(route_families) < 2:
            return ""
        if policy_snapshot.phase == "prefeasible_convert":
            return (
                "Convert family mix is active. Choose a route family before choosing the final operator. "
                f"Available route families: {route_families}. "
                "Prefer bounded entry moves that directly relieve the current bottleneck and keep the path to first feasible short."
            )
        return (
            "Bounded expand mix is active. Choose a route family before choosing the final operator. "
            f"Available route families: {route_families}. "
            "Prefer underused route families when they have comparable local evidence, and avoid reusing a cooled-down route family unless it is uniquely justified by the current spatial state."
        )

    @staticmethod
    def _entry_convert_metadata(
        *,
        state: ControllerState,
        policy_snapshot: PolicySnapshot,
        candidate_operator_ids: Sequence[str],
    ) -> dict[str, Any]:
        if policy_snapshot.phase != "prefeasible_convert":
            return {}
        progress_state = state.metadata.get("progress_state")
        dominant_violation_family = ""
        dominant_violation_persistence_count = 0
        evaluations_since_near_feasible_improvement: int | None = None
        if isinstance(progress_state, dict):
            dominant_violation_family = str(progress_state.get("recent_dominant_violation_family", ""))
            dominant_violation_persistence_count = int(
                progress_state.get("recent_dominant_violation_persistence_count", 0)
            )
            if progress_state.get("evaluations_since_near_feasible_improvement") is not None:
                evaluations_since_near_feasible_improvement = int(
                    progress_state["evaluations_since_near_feasible_improvement"]
                )
        supported_entry_candidate_count = sum(
            1
            for operator_id in candidate_operator_ids
            if str(policy_snapshot.candidate_annotations.get(operator_id, {}).get("entry_evidence_level", ""))
            in {"supported", "trusted"}
        )
        return {
            "entry_convert_active": True,
            "dominant_violation_family": dominant_violation_family,
            "dominant_violation_persistence_count": dominant_violation_persistence_count,
            "evaluations_since_near_feasible_improvement": evaluations_since_near_feasible_improvement,
            "supported_entry_candidate_count": int(supported_entry_candidate_count),
            "supported_entry_candidate_share": (
                0.0
                if not candidate_operator_ids
                else float(supported_entry_candidate_count) / float(len(candidate_operator_ids))
            ),
        }

    @staticmethod
    def _selected_entry_metadata(
        policy_snapshot: PolicySnapshot,
        selected_operator_id: str,
    ) -> dict[str, Any]:
        annotation = policy_snapshot.candidate_annotations.get(str(selected_operator_id), {})
        if not isinstance(annotation, dict):
            return {}
        dominant_violation_relief_count = int(annotation.get("dominant_violation_relief_count", 0))
        near_feasible_improvement_count = int(annotation.get("near_feasible_improvement_count", 0))
        return {
            "selected_entry_evidence_level": str(annotation.get("entry_evidence_level", "")),
            "near_feasible_relief": (
                dominant_violation_relief_count > 0 or near_feasible_improvement_count > 0
            ),
        }

    @staticmethod
    def _merge_guardrail_metadata(
        *,
        original_candidate_operator_ids: Sequence[str],
        effective_candidate_operator_ids: Sequence[str],
        policy_snapshot: PolicySnapshot,
        dominance_guardrails: Sequence[dict[str, Any] | None],
    ) -> dict[str, Any] | None:
        active_dominance_guardrails = [guardrail for guardrail in dominance_guardrails if guardrail is not None]
        filtered_operator_ids = list(policy_snapshot.suppressed_operator_ids)
        discouraged_operator_ids: list[str] = []
        for dominance_guardrail in active_dominance_guardrails:
            for operator_id in dominance_guardrail.get("filtered_operator_ids", []):
                normalized = str(operator_id)
                if normalized not in filtered_operator_ids:
                    filtered_operator_ids.append(normalized)
            for operator_id in dominance_guardrail.get("discouraged_operator_ids", []):
                normalized = str(operator_id)
                if normalized not in discouraged_operator_ids:
                    discouraged_operator_ids.append(normalized)
        reason_codes = list(policy_snapshot.reason_codes)
        for dominance_guardrail in active_dominance_guardrails:
            if dominance_guardrail.get("reason"):
                reason_codes.append(str(dominance_guardrail["reason"]))
        primary_dominance_guardrail = (
            None
            if not active_dominance_guardrails
            else active_dominance_guardrails[-1]
        )
        applied = bool(filtered_operator_ids or discouraged_operator_ids or policy_snapshot.reset_active or active_dominance_guardrails)
        if not applied:
            return None
        return {
            "applied": True,
            "reason": (
                str(primary_dominance_guardrail.get("reason", ""))
                if primary_dominance_guardrail is not None
                else ("phase_policy" if reason_codes else "")
            ),
            "reason_codes": reason_codes,
            "threshold_profile": (
                str(primary_dominance_guardrail.get("threshold_profile", ""))
                if primary_dominance_guardrail is not None
                else "policy_kernel"
            ),
            "filtered_operator_ids": filtered_operator_ids,
            "discouraged_operator_ids": discouraged_operator_ids,
            "soft_advice_operator_ids": discouraged_operator_ids,
            "dominance_advice_active": bool(discouraged_operator_ids),
            "dominant_operator_id": (
                str(primary_dominance_guardrail.get("dominant_operator_id", ""))
                if primary_dominance_guardrail is not None
                else ""
            ),
            "dominant_operator_share": (
                float(primary_dominance_guardrail.get("dominant_operator_share", 0.0))
                if primary_dominance_guardrail is not None
                else 0.0
            ),
            "recent_window_size": (
                int(primary_dominance_guardrail.get("recent_window_size", 0))
                if primary_dominance_guardrail is not None
                else 0
            ),
            "policy_phase": policy_snapshot.phase,
            "policy_reset_active": policy_snapshot.reset_active,
            "original_candidate_operator_ids": list(original_candidate_operator_ids),
            "effective_candidate_operator_ids": list(effective_candidate_operator_ids),
            "recent_counts": (
                {
                    str(operator_id): int(count)
                    for operator_id, count in dict(primary_dominance_guardrail.get("recent_counts", {})).items()
                }
                if primary_dominance_guardrail is not None
                else {}
            ),
            "viable_alternative_operator_ids": (
                [str(operator_id) for operator_id in primary_dominance_guardrail.get("viable_alternative_operator_ids", [])]
                if primary_dominance_guardrail is not None
                else []
            ),
        }
