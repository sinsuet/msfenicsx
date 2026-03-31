"""LLM-guided controller for the hybrid-union operator registry."""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Sequence
from typing import Any

import numpy as np

from llm.openai_compatible import OpenAICompatibleClient, OpenAICompatibleConfig
from optimizers.operator_pool.decisions import ControllerDecision
from optimizers.operator_pool.policy_kernel import PolicySnapshot, build_policy_snapshot
from optimizers.operator_pool.random_controller import RandomUniformController
from optimizers.operator_pool.state import ControllerState


_OPERATOR_ROLE_SUMMARIES: dict[str, str] = {
    "native_sbx_pm": "native NSGA-II SBX plus polynomial mutation baseline proposal.",
    "sbx_pm_global": "more aggressive global SBX plus mutation exploration across the full vector.",
    "local_refine": "small local cleanup around the current layout, especially near the hot zone.",
    "hot_pair_to_sink": "move the processor and RF hot pair upward toward the sink boundary.",
    "hot_pair_separate": "increase spacing between the processor and RF hot pair.",
    "battery_to_warm_zone": "move the battery partway toward the warmer hot-pair region.",
    "radiator_align_hot_pair": "shift the radiator span to align better with the hot-pair center.",
    "radiator_expand": "expand radiator coverage outward to use more available span.",
    "radiator_contract": "contract radiator coverage inward to reduce span.",
}
_RECENT_DOMINANCE_MIN_WINDOW = 6
_RECENT_DOMINANCE_MIN_COUNT = 5
_RECENT_DOMINANCE_MIN_SHARE = 0.75
_PREFEASIBLE_MIN_SUPPORTED_SELECTIONS = 3
_PREFEASIBLE_CUSTOM_DOMINANCE_MIN_WINDOW = 4
_PREFEASIBLE_CUSTOM_DOMINANCE_MIN_COUNT = 4
_PREFEASIBLE_CUSTOM_DOMINANCE_MIN_SHARE = 0.75
_NATIVE_BASELINE_OPERATOR_IDS = frozenset({"native_sbx_pm"})


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
        self.metrics: dict[str, Any] = {
            "request_count": 0,
            "response_count": 0,
            "fallback_count": 0,
            "elapsed_seconds_total": 0.0,
            "elapsed_seconds_avg": 0.0,
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
        candidate_operator_ids, dominance_guardrail = self._apply_recent_dominance_guardrail(
            state,
            policy_snapshot.allowed_operator_ids,
        )
        guardrail = self._merge_guardrail_metadata(
            original_candidate_operator_ids=original_candidate_operator_ids,
            effective_candidate_operator_ids=candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            dominance_guardrail=dominance_guardrail,
        )

        system_prompt = self._build_system_prompt(
            state,
            candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            guardrail=guardrail,
        )
        user_prompt = self._build_user_prompt(
            state,
            candidate_operator_ids,
            original_candidate_operator_ids=original_candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            guardrail=guardrail,
        )
        self.request_trace.append(
            {
                "generation_index": state.generation_index,
                "evaluation_index": state.evaluation_index,
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
            }
        )
        self.metrics["request_count"] = int(self.metrics["request_count"]) + 1
        started_at = time.perf_counter()
        try:
            response = self.client.request_operator_decision(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=candidate_operator_ids,
            )
        except Exception as exc:
            elapsed_seconds = max(0.0, float(time.perf_counter() - started_at))
            self.metrics["fallback_count"] = int(self.metrics["fallback_count"]) + 1
            self._record_elapsed_seconds(elapsed_seconds)
            self.response_trace.append(
                {
                    "generation_index": state.generation_index,
                    "evaluation_index": state.evaluation_index,
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
                    "elapsed_seconds": elapsed_seconds,
                }
            )
            fallback_decision = self.fallback_controller.select_decision(state, candidate_operator_ids, rng)
            metadata = dict(fallback_decision.metadata)
            metadata.update(
                {
                    "fallback_used": True,
                    "fallback_controller": self.fallback_controller_id,
                    "fallback_reason": str(exc),
                    "elapsed_seconds": elapsed_seconds,
                    **self._decision_phase_metadata(
                        policy_phase=policy_snapshot.phase,
                        model_phase="",
                        model_rationale_present=False,
                    ),
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
        self._record_elapsed_seconds(elapsed_seconds)
        self.response_trace.append(
            {
                "generation_index": state.generation_index,
                "evaluation_index": state.evaluation_index,
                "provider": response.provider,
                "model": response.model,
                "capability_profile": response.capability_profile,
                "performance_profile": response.performance_profile,
                "selected_operator_id": response.selected_operator_id,
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
                "elapsed_seconds": elapsed_seconds,
            }
        )
        response_metadata = {
            "provider": response.provider,
            "model": response.model,
            "capability_profile": response.capability_profile,
            "performance_profile": response.performance_profile,
            "raw_payload": dict(response.raw_payload),
            "fallback_used": False,
            "elapsed_seconds": elapsed_seconds,
            **self._decision_phase_metadata(
                policy_phase=policy_snapshot.phase,
                model_phase=response.phase,
                model_rationale_present=bool(response.rationale.strip()),
            ),
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

    def _build_system_prompt(
        self,
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
        *,
        policy_snapshot: PolicySnapshot,
        guardrail: dict[str, Any] | None,
    ) -> str:
        operator_guidance = " ".join(
            f"{operator_id}: {_OPERATOR_ROLE_SUMMARIES.get(operator_id, 'specialized numeric proposal operator.')}"
            for operator_id in candidate_operator_ids
        )
        prompt = (
            "You are an operator-selection controller for constrained multiobjective thermal optimization. "
            "Select exactly one operator from the provided candidate_operator_ids. "
            "Do not emit raw design vectors. "
            "Treat recent_decisions and operator_summary as context, not as an instruction to copy the most recent "
            "dominant operator. Avoid repeatedly selecting the same operator when recent history is overly "
            "concentrated unless the current state makes that operator uniquely necessary. "
            f"Candidate operator semantics: {operator_guidance}"
        )
        phase_policy_guidance = self._build_phase_policy_guidance(policy_snapshot)
        if phase_policy_guidance:
            prompt = f"{prompt} {phase_policy_guidance}"
        if self._is_before_first_feasible(state):
            prompt = (
                f"{prompt} "
                "Before first feasible, prefer stable repeatable evidence over speculative one-off gains. "
                "Do not over-weight one-off large total-violation improvements from low-support operators."
            )
        if guardrail is None:
            return prompt
        dominant_operator_id = str(guardrail.get("dominant_operator_id", "")).strip()
        if not dominant_operator_id:
            return prompt
        dominant_share = float(guardrail.get("dominant_operator_share", 0.0))
        return (
            f"{prompt} "
            f"A recent-dominance guardrail removed {dominant_operator_id} from the current candidate set after "
            f"{dominant_share:.0%} recent concentration."
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
        metadata: dict[str, Any] = {
            "candidate_operator_ids": list(candidate_operator_ids),
        }
        if "search_phase" in state.metadata:
            metadata["search_phase"] = state.metadata["search_phase"]
        if "run_state" in state.metadata:
            metadata["run_state"] = dict(state.metadata["run_state"])
        if "parent_state" in state.metadata:
            metadata["parent_state"] = dict(state.metadata["parent_state"])
        if "archive_state" in state.metadata:
            metadata["archive_state"] = dict(state.metadata["archive_state"])
        if "domain_regime" in state.metadata:
            metadata["domain_regime"] = dict(state.metadata["domain_regime"])
        if "progress_state" in state.metadata:
            metadata["progress_state"] = dict(state.metadata["progress_state"])
        if "recent_decisions" in state.metadata:
            metadata["recent_decisions"] = list(state.metadata["recent_decisions"])
        if "recent_operator_counts" in state.metadata:
            metadata["recent_operator_counts"] = {
                str(operator_id): dict(summary)
                for operator_id, summary in dict(state.metadata["recent_operator_counts"]).items()
                if str(operator_id) in candidate_operator_ids
            }
        if "operator_summary" in state.metadata:
            metadata["operator_summary"] = LLMOperatorController._build_prompt_operator_summary(
                state,
                candidate_operator_ids,
            )
        metadata["phase_policy"] = {
            "phase": policy_snapshot.phase,
            "reset_active": policy_snapshot.reset_active,
            "reason_codes": list(policy_snapshot.reason_codes),
            "candidate_annotations": {
                operator_id: dict(annotation)
                for operator_id, annotation in policy_snapshot.candidate_annotations.items()
                if operator_id in candidate_operator_ids
            },
        }
        if tuple(original_candidate_operator_ids) != tuple(candidate_operator_ids):
            metadata["original_candidate_operator_ids"] = list(original_candidate_operator_ids)
        if guardrail is not None:
            metadata["decision_guardrail"] = dict(guardrail)
        return metadata

    @staticmethod
    def _is_before_first_feasible(state: ControllerState) -> bool:
        run_state = state.metadata.get("run_state")
        if not isinstance(run_state, dict):
            return False
        return run_state.get("first_feasible_eval") is None

    @staticmethod
    def _build_prompt_operator_summary(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> dict[str, dict[str, Any]]:
        raw_operator_summary = state.metadata.get("operator_summary", {})
        if not isinstance(raw_operator_summary, dict):
            return {}
        before_first_feasible = LLMOperatorController._is_before_first_feasible(state)
        prompt_operator_summary: dict[str, dict[str, Any]] = {}
        for operator_id, raw_summary in raw_operator_summary.items():
            if str(operator_id) not in candidate_operator_ids:
                continue
            summary = dict(raw_summary)
            if before_first_feasible:
                summary = LLMOperatorController._calibrate_prefeasible_operator_summary(summary)
            prompt_operator_summary[str(operator_id)] = summary
        return prompt_operator_summary

    @staticmethod
    def _calibrate_prefeasible_operator_summary(summary: dict[str, Any]) -> dict[str, Any]:
        calibrated_summary = dict(summary)
        selection_count = int(calibrated_summary.get("selection_count", 0))
        proposal_count = int(calibrated_summary.get("proposal_count", 0))
        recent_selection_count = int(calibrated_summary.get("recent_selection_count", 0))
        feasible_entry_count = int(calibrated_summary.get("feasible_entry_count", 0))
        feasible_preservation_count = int(calibrated_summary.get("feasible_preservation_count", 0))
        has_feasible_credit = feasible_entry_count > 0 or feasible_preservation_count > 0
        support_count = max(selection_count, proposal_count, recent_selection_count)
        evidence_level = (
            "feasible_credit"
            if has_feasible_credit
            else "supported"
            if support_count >= _PREFEASIBLE_MIN_SUPPORTED_SELECTIONS
            else "limited"
        )
        calibrated_summary["evidence_level"] = evidence_level
        if evidence_level == "limited":
            calibrated_summary.pop("avg_total_violation_delta", None)
            calibrated_summary.pop("recent_helpful_regimes", None)
            calibrated_summary.pop("recent_harmful_regimes", None)
        return calibrated_summary

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
        filtered_candidate_operator_ids = tuple(
            operator_id for operator_id in candidate_operator_ids if operator_id != dominant_operator_id
        )
        if not filtered_candidate_operator_ids:
            return tuple(candidate_operator_ids), None
        return filtered_candidate_operator_ids, {
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
            "filtered_operator_ids": [dominant_operator_id],
            "original_candidate_operator_ids": list(candidate_operator_ids),
            "effective_candidate_operator_ids": list(filtered_candidate_operator_ids),
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
        elif policy_snapshot.phase.startswith("prefeasible"):
            guidance.append(
                "Prefeasible policy: prioritize trusted evidence and stable operator families before speculative custom families."
            )
        elif policy_snapshot.phase.startswith("post_feasible"):
            guidance.append(
                "Post-feasible policy: preserve feasibility while expanding Pareto improvements."
            )
        if "prefeasible_speculative_family_collapse" in policy_snapshot.reason_codes:
            guidance.append(
                "A family-level policy filter removed speculative custom families that lack trusted evidence."
            )
        if policy_snapshot.reset_active:
            guidance.append(
                "A progress-reset window is active, so use trusted evidence to recover from a no-progress streak."
            )
        return " ".join(guidance)

    @staticmethod
    def _merge_guardrail_metadata(
        *,
        original_candidate_operator_ids: Sequence[str],
        effective_candidate_operator_ids: Sequence[str],
        policy_snapshot: PolicySnapshot,
        dominance_guardrail: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        filtered_operator_ids = list(policy_snapshot.suppressed_operator_ids)
        if dominance_guardrail is not None:
            for operator_id in dominance_guardrail.get("filtered_operator_ids", []):
                normalized = str(operator_id)
                if normalized not in filtered_operator_ids:
                    filtered_operator_ids.append(normalized)
        reason_codes = list(policy_snapshot.reason_codes)
        if dominance_guardrail is not None and dominance_guardrail.get("reason"):
            reason_codes.append(str(dominance_guardrail["reason"]))
        applied = bool(filtered_operator_ids or policy_snapshot.reset_active or dominance_guardrail)
        if not applied:
            return None
        return {
            "applied": True,
            "reason": (
                str(dominance_guardrail.get("reason", ""))
                if dominance_guardrail is not None
                else ("phase_policy" if reason_codes else "")
            ),
            "reason_codes": reason_codes,
            "threshold_profile": (
                str(dominance_guardrail.get("threshold_profile", ""))
                if dominance_guardrail is not None
                else "policy_kernel"
            ),
            "filtered_operator_ids": filtered_operator_ids,
            "dominant_operator_id": (
                str(dominance_guardrail.get("dominant_operator_id", ""))
                if dominance_guardrail is not None
                else ""
            ),
            "dominant_operator_share": (
                float(dominance_guardrail.get("dominant_operator_share", 0.0))
                if dominance_guardrail is not None
                else 0.0
            ),
            "recent_window_size": (
                int(dominance_guardrail.get("recent_window_size", 0))
                if dominance_guardrail is not None
                else 0
            ),
            "policy_phase": policy_snapshot.phase,
            "policy_reset_active": policy_snapshot.reset_active,
            "original_candidate_operator_ids": list(original_candidate_operator_ids),
            "effective_candidate_operator_ids": list(effective_candidate_operator_ids),
            "recent_counts": (
                {
                    str(operator_id): int(count)
                    for operator_id, count in dict(dominance_guardrail.get("recent_counts", {})).items()
                }
                if dominance_guardrail is not None
                else {}
            ),
        }
