"""Genetic-family union adapter for controller-guided offspring proposals."""

from __future__ import annotations

from copy import deepcopy
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from pymoo.core.infill import InfillCriterion
from pymoo.core.population import Population

from optimizers.codec import extract_decision_vector
from optimizers.operator_pool.controllers import build_controller, select_controller_decision
from optimizers.operator_pool.layout import VariableLayout
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.operators import get_operator_definition, native_operator_id_for_backbone
from optimizers.operator_pool.state_builder import build_controller_state
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow
from optimizers.raw_backbones.registry import get_raw_backbone_definition
from optimizers.repair import repair_case_from_vector


@dataclass(slots=True)
class GeneticUnionAdapterArtifacts:
    algorithm: Any
    controller_trace: list[ControllerTraceRow]
    operator_trace: list[OperatorTraceRow]
    llm_request_trace: list[dict[str, Any]] | None = None
    llm_response_trace: list[dict[str, Any]] | None = None
    llm_reflection_trace: list[dict[str, Any]] | None = None
    llm_metrics: dict[str, Any] | None = None


class GeneticFamilyUnionMating(InfillCriterion):
    def __init__(
        self,
        *,
        operator_ids: list[str],
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
        self.operator_ids = list(operator_ids)
        self.controller = build_controller(controller_id, controller_parameters)
        self.variable_layout = variable_layout
        self.repair_reference_case = repair_reference_case
        self.optimization_spec = optimization_spec
        self.family = family
        self.backbone = backbone
        self.selection = selection
        self.raw_mating = raw_mating
        self.radiator_span_max = radiator_span_max
        memory_cfg = controller_parameters.get("memory", {}) if isinstance(controller_parameters, dict) else {}
        self.recent_window = max(1, int(memory_cfg.get("recent_window", 32)))
        self.design_variable_ids = [
            str(item["variable_id"]) for item in self.optimization_spec.get("design_variables", [])
        ]
        algorithm_settings = self.optimization_spec.get("algorithm", {})
        population_size = int(algorithm_settings.get("population_size", 0))
        num_generations = int(algorithm_settings.get("num_generations", 0))
        self.total_evaluation_budget = max(0, 1 + population_size * num_generations)
        self.native_parameters = deepcopy(native_parameters)
        self.native_operator_id = native_operator_id_for_backbone(family, backbone)
        self.controller_trace: list[ControllerTraceRow] = []
        self.operator_trace: list[OperatorTraceRow] = []
        self._next_decision_index = 0

    def _do(
        self,
        problem: Any,
        pop: Population,
        n_offsprings: int,
        random_state=None,
        algorithm=None,
        parents=None,
        **kwargs,
    ) -> Population:
        if algorithm is None:
            raise ValueError("GeneticFamilyUnionMating requires the calling pymoo algorithm context.")
        rng = random_state if random_state is not None else getattr(algorithm, "random_state", None)
        if rng is None:
            rng = np.random.default_rng()
        children_per_native_event = int(self.raw_mating.crossover.n_offsprings)
        generation_index = max(0, int(getattr(algorithm, "n_iter", 0)))
        base_event_count = math.ceil(n_offsprings / children_per_native_event)
        initial_rows = (
            np.asarray(parents, dtype=np.int64)
            if parents is not None
            else self._select_parent_rows(problem, pop, base_event_count, rng, algorithm=algorithm, **kwargs)
        )
        event_records = [
            self._build_event_record(
                pop,
                row,
                generation_index=generation_index,
                event_index=event_index,
                rng=rng,
                problem=problem,
            )
            for event_index, row in enumerate(initial_rows.tolist())
        ]

        proposal_vectors: list[np.ndarray] = []
        if event_records and all(record["operator_id"] == self.native_operator_id for record in event_records):
            native_offspring = self._native_offspring_population(
                problem,
                pop,
                initial_rows,
                rng,
                algorithm=algorithm,
                **kwargs,
            )
            native_vectors = np.asarray(native_offspring.get("X"), dtype=np.float64)
            for event_index, record in enumerate(event_records):
                start = event_index * children_per_native_event
                end = start + children_per_native_event
                self._append_trace_rows(
                    record=record,
                    proposal_vectors=[np.asarray(vector, dtype=np.float64) for vector in native_vectors[start:end]],
                    problem=problem,
                    generation_index=generation_index,
                    children_per_event=children_per_native_event,
                    proposal_vectors_out=proposal_vectors,
                )
            return Population.new("X", np.asarray(proposal_vectors, dtype=np.float64))

        for record in event_records:
            self._append_trace_rows(
                record=record,
                proposal_vectors=self._event_proposals(
                    problem,
                    pop,
                    record,
                    rng,
                    algorithm=algorithm,
                    **kwargs,
                ),
                problem=problem,
                generation_index=generation_index,
                children_per_event=1,
                proposal_vectors_out=proposal_vectors,
            )

        while len(proposal_vectors) < n_offsprings:
            extra_row = self._select_parent_rows(problem, pop, 1, rng, algorithm=algorithm, **kwargs)[0]
            record = self._build_event_record(
                pop,
                extra_row.tolist(),
                generation_index=generation_index,
                event_index=len(event_records),
                rng=rng,
                problem=problem,
            )
            event_records.append(record)
            self._append_trace_rows(
                record=record,
                proposal_vectors=self._event_proposals(
                    problem,
                    pop,
                    record,
                    rng,
                    algorithm=algorithm,
                    **kwargs,
                ),
                problem=problem,
                generation_index=generation_index,
                children_per_event=1,
                proposal_vectors_out=proposal_vectors,
            )

        return Population.new("X", np.asarray(proposal_vectors, dtype=np.float64))

    def _select_parent_rows(
        self,
        problem: Any,
        pop: Population,
        n_select: int,
        rng: np.random.Generator,
        *,
        algorithm: Any,
        **kwargs,
    ) -> np.ndarray:
        return np.asarray(
            self.selection.do(
                problem,
                pop,
                n_select,
                n_parents=self.raw_mating.crossover.n_parents,
                to_pop=False,
                random_state=rng,
                algorithm=algorithm,
                **kwargs,
            ),
            dtype=np.int64,
        )

    def _build_event_record(
        self,
        pop: Population,
        row: list[int],
        *,
        generation_index: int,
        event_index: int,
        rng: np.random.Generator,
        problem: Any,
    ) -> dict[str, Any]:
        parent_vectors = [np.asarray(pop[index].X, dtype=np.float64) for index in row]
        parents = ParentBundle.from_vectors(*parent_vectors)
        decision_index = self._next_decision_index
        self._next_decision_index += 1
        state = build_controller_state(
            parents,
            family=self.family,
            backbone=self.backbone,
            generation_index=generation_index,
            evaluation_index=int(problem._next_evaluation_index + event_index),
            candidate_operator_ids=self.operator_ids,
            metadata={
                "parent_indices": row,
                "native_parameters": deepcopy(self.native_parameters),
                "decision_index": decision_index,
                "design_variable_ids": list(self.design_variable_ids),
                "total_evaluation_budget": int(self.total_evaluation_budget),
                "radiator_span_max": self.radiator_span_max,
            },
            controller_trace=self.controller_trace,
            operator_trace=self.operator_trace,
            history=problem.history,
            recent_window=self.recent_window,
        )
        decision = select_controller_decision(self.controller, state, self.operator_ids, rng)
        return {
            "decision_index": decision_index,
            "row": list(row),
            "parents": parents,
            "state": state,
            "decision": decision,
            "operator_id": decision.selected_operator_id,
        }

    def _event_proposals(
        self,
        problem: Any,
        pop: Population,
        record: dict[str, Any],
        rng: np.random.Generator,
        *,
        algorithm: Any,
        **kwargs,
    ) -> list[np.ndarray]:
        del problem, pop, algorithm, kwargs
        proposal = get_operator_definition(record["operator_id"]).propose(
            parents=record["parents"],
            state=record["state"],
            variable_layout=self.variable_layout,
            rng=rng,
        )
        if record["operator_id"] != self.native_operator_id and self.backbone == "rvea":
            # RVEA degrades when custom actions fully replace the reference-vector offspring;
            # keep custom actions as a local perturbation around the selected parent.
            raw_proposal = 0.8 * np.asarray(record["parents"].primary, dtype=np.float64) + 0.2 * np.asarray(
                proposal,
                dtype=np.float64,
            )
        else:
            raw_proposal = np.asarray(proposal, dtype=np.float64)
        return [np.asarray(raw_proposal, dtype=np.float64)]

    def _append_trace_rows(
        self,
        *,
        record: dict[str, Any],
        proposal_vectors: list[np.ndarray],
        problem: Any,
        generation_index: int,
        children_per_event: int,
        proposal_vectors_out: list[np.ndarray],
    ) -> None:
        proposal_kind = "native" if record["operator_id"] == self.native_operator_id else "custom"
        for sibling_index, proposal_vector in enumerate(proposal_vectors):
            evaluation_index = int(problem._next_evaluation_index + len(proposal_vectors_out))
            repaired_vector = self._repair_vector(proposal_vector)
            self.controller_trace.append(
                ControllerTraceRow(
                    generation_index=generation_index,
                    evaluation_index=evaluation_index,
                    family=self.family,
                    backbone=self.backbone,
                    controller_id=self.controller.controller_id,
                    candidate_operator_ids=tuple(self.operator_ids),
                    selected_operator_id=str(record["operator_id"]),
                    phase=str(record["decision"].metadata.get("model_phase") or record["decision"].phase),
                    rationale=str(record["decision"].rationale),
                    metadata={
                        "decision_index": int(record["decision_index"]),
                        "parent_indices": list(record["row"]),
                        "proposal_kind": proposal_kind,
                        "sibling_index": int(sibling_index),
                        "children_per_event": int(children_per_event),
                        **dict(record["decision"].metadata),
                    },
                )
            )
            self.operator_trace.append(
                OperatorTraceRow(
                    generation_index=generation_index,
                    evaluation_index=evaluation_index,
                    operator_id=str(record["operator_id"]),
                    parent_count=record["parents"].num_parents,
                    parent_vectors=tuple(
                        tuple(float(value) for value in vector.tolist()) for vector in record["parents"].vectors
                    ),
                    proposal_vector=tuple(float(value) for value in proposal_vector.tolist()),
                    metadata={
                        "decision_index": int(record["decision_index"]),
                        "proposal_kind": proposal_kind,
                        "sibling_index": int(sibling_index),
                        "children_per_event": int(children_per_event),
                        "repaired_vector": repaired_vector.tolist(),
                    },
                )
            )
            proposal_vectors_out.append(np.asarray(proposal_vector, dtype=np.float64))

    def _native_offspring_population(
        self,
        problem: Any,
        pop: Population,
        parent_indices: np.ndarray,
        rng: np.random.Generator,
        *,
        algorithm: Any,
        **kwargs,
    ) -> Population:
        native_offspring = self.raw_mating.crossover(
            problem,
            pop,
            parents=np.asarray(parent_indices, dtype=np.int64),
            random_state=rng,
            algorithm=algorithm,
            **kwargs,
        )
        return self.raw_mating.mutation(
            problem,
            native_offspring,
            random_state=rng,
            algorithm=algorithm,
            **kwargs,
        )

    def _repair_vector(
        self,
        vector: np.ndarray,
    ) -> np.ndarray:
        repaired_case = repair_case_from_vector(
            self.repair_reference_case,
            self.optimization_spec,
            np.asarray(vector, dtype=np.float64),
            radiator_span_max=self.radiator_span_max,
        )
        return extract_decision_vector(repaired_case, self.optimization_spec)


def build_genetic_union_algorithm(problem: Any, optimization_spec: Any, algorithm_config: dict[str, Any]) -> GeneticUnionAdapterArtifacts:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    if algorithm_config["mode"] != "union":
        raise ValueError(f"Genetic union adapter requires algorithm.mode='union', got {algorithm_config['mode']!r}.")
    if algorithm_config["family"] != "genetic":
        raise ValueError(f"Genetic union adapter supports only family='genetic', got {algorithm_config['family']!r}.")

    raw_algorithm_config = dict(algorithm_config)
    raw_algorithm_config["mode"] = "raw"
    definition = get_raw_backbone_definition(
        family=str(algorithm_config["family"]),
        backbone=str(algorithm_config["backbone"]),
    )
    algorithm = definition.build_algorithm(problem, raw_algorithm_config)
    raw_mating = algorithm.mating
    operator_control = spec_payload["operator_control"]
    mating = GeneticFamilyUnionMating(
        operator_ids=list(operator_control["operator_pool"]),
        controller_id=str(operator_control["controller"]),
        controller_parameters=deepcopy(operator_control.get("controller_parameters")),
        variable_layout=VariableLayout.from_optimization_spec(spec_payload),
        repair_reference_case=problem.base_case,
        optimization_spec=spec_payload,
        family=str(algorithm_config["family"]),
        backbone=str(algorithm_config["backbone"]),
        selection=raw_mating.selection,
        raw_mating=raw_mating,
        native_parameters={
            "crossover": deepcopy(algorithm_config.get("parameters", {}).get("crossover", {})),
            "mutation": deepcopy(algorithm_config.get("parameters", {}).get("mutation", {})),
        },
        radiator_span_max=getattr(problem, "radiator_span_max", None),
    )
    algorithm.mating = mating
    return GeneticUnionAdapterArtifacts(
        algorithm=algorithm,
        controller_trace=mating.controller_trace,
        operator_trace=mating.operator_trace,
        llm_request_trace=getattr(mating.controller, "request_trace", None),
        llm_response_trace=getattr(mating.controller, "response_trace", None),
        llm_reflection_trace=getattr(mating.controller, "reflection_trace", None),
        llm_metrics=getattr(mating.controller, "metrics", None),
    )
