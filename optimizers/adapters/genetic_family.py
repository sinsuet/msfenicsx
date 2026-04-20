"""Genetic-family union adapter for controller-guided offspring proposals."""

from __future__ import annotations

from copy import deepcopy
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from pymoo.core.infill import InfillCriterion
from pymoo.core.population import Population

from optimizers.codec import extract_decision_vector
from optimizers.operator_pool.controllers import (
    build_controller,
    configure_controller_trace_outputs,
    select_controller_decision,
)
from optimizers.operator_pool.layout import VariableLayout
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.operators import get_operator_definition, native_operator_id_for_backbone
from optimizers.operator_pool.state_builder import build_controller_state
from optimizers.operator_pool.trace import (
    ControllerAttemptTraceRow,
    ControllerTraceRow,
    OperatorAttemptTraceRow,
    OperatorTraceRow,
)
from optimizers.raw_backbones.registry import get_raw_backbone_definition
from optimizers.repair import repair_case_from_vector
from optimizers.traces.correlation import format_decision_id


@dataclass(slots=True)
class GeneticUnionAdapterArtifacts:
    algorithm: Any
    controller_trace: list[ControllerTraceRow]
    operator_trace: list[OperatorTraceRow]
    controller_attempt_trace: list[ControllerAttemptTraceRow]
    operator_attempt_trace: list[OperatorAttemptTraceRow]
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
        self.controller_attempt_trace: list[ControllerAttemptTraceRow] = []
        self.operator_attempt_trace: list[OperatorAttemptTraceRow] = []
        self._next_decision_index = 0
        self._next_attempt_index = 0

    def do(self, problem, pop, n_offsprings, random_state=None, n_max_iterations=None, **kwargs):
        if n_max_iterations is None:
            n_max_iterations = self.n_max_iterations

        algorithm = kwargs.pop("algorithm", None)
        if algorithm is None:
            raise ValueError("GeneticFamilyUnionMating requires the calling pymoo algorithm context.")
        parents = kwargs.pop("parents", None)
        rng = random_state if random_state is not None else getattr(algorithm, "random_state", None)
        if rng is None:
            rng = np.random.default_rng()
        if self.controller.controller_id != "llm":
            return self._legacy_batched_do(
                problem,
                pop,
                n_offsprings,
                rng=rng,
                n_max_iterations=n_max_iterations,
                algorithm=algorithm,
                parents=parents,
                **kwargs,
            )

        off = Population.create()
        n_attempted_events = 0
        decision_indices_seen: set[int] = set()
        generation_controller_trace: list[ControllerTraceRow] = []
        generation_operator_trace: list[OperatorTraceRow] = []
        next_provisional_evaluation_index = int(problem._next_evaluation_index)
        children_per_native_event = int(self.raw_mating.crossover.n_offsprings)
        base_event_count = max(1, math.ceil(n_offsprings / max(1, children_per_native_event)))
        if parents is None:
            parent_row_queue = [
                [int(value) for value in row]
                for row in self._select_parent_rows(
                    problem,
                    pop,
                    base_event_count,
                    rng,
                    algorithm=algorithm,
                    **kwargs,
                ).tolist()
            ]
        else:
            parent_row_queue = [
                [int(value) for value in row]
                for row in np.asarray(parents, dtype=np.int64).tolist()
            ]

        while len(off) < n_offsprings and n_attempted_events < n_max_iterations:
            if parent_row_queue:
                parent_row = parent_row_queue.pop(0)
            else:
                parent_row = self._select_parent_rows(
                    problem,
                    pop,
                    1,
                    rng,
                    algorithm=algorithm,
                    **kwargs,
                )[0].tolist()
            record = self._build_event_record(
                pop,
                parent_row,
                generation_index=max(0, int(getattr(algorithm, "n_iter", 0))),
                event_index=n_attempted_events,
                rng=rng,
                problem=problem,
                local_controller_trace=generation_controller_trace,
                local_operator_trace=generation_operator_trace,
                generation_target_offsprings=int(n_offsprings),
            )
            decision_indices_seen.add(int(record["decision_index"]))
            proposal_population, next_provisional_evaluation_index = self._proposal_population_for_record(
                problem,
                pop,
                record,
                rng,
                algorithm=algorithm,
                provisional_evaluation_start=next_provisional_evaluation_index,
                **kwargs,
            )
            if len(proposal_population) > 0:
                proposal_population = self.repair(problem, proposal_population, random_state=rng, **kwargs)
            self._refresh_repaired_payloads(proposal_population)
            proposal_population = self._filter_raw_duplicates(proposal_population, pop, off)
            proposal_population = self._filter_repaired_duplicates(proposal_population, pop, off)

            if len(off) + len(proposal_population) > n_offsprings:
                n_keep = n_offsprings - len(off)
                self._mark_population_rejected(
                    proposal_population[n_keep:],
                    rejection_reason="batch_truncation",
                )
                proposal_population = proposal_population[:n_keep]

            self._append_accepted_trace_rows(
                proposal_population,
                evaluation_start_index=int(problem._next_evaluation_index + len(off)),
                controller_trace_out=generation_controller_trace,
                operator_trace_out=generation_operator_trace,
            )
            off = Population.merge(off, proposal_population)
            n_attempted_events += 1

        self.controller_trace.extend(generation_controller_trace)
        self.operator_trace.extend(generation_operator_trace)
        self._sync_llm_decision_statuses(decision_indices_seen)
        return off

    def _legacy_batched_do(
        self,
        problem: Any,
        pop: Population,
        n_offsprings: int,
        *,
        rng: np.random.Generator,
        n_max_iterations: int,
        algorithm: Any,
        parents: Any | None,
        **kwargs,
    ) -> Population:
        off = Population.create()
        n_infills = 0
        decision_indices_seen: set[int] = set()

        while len(off) < n_offsprings:
            n_remaining = n_offsprings - len(off)
            proposal_population = self._batched_proposal_population(
                problem,
                pop,
                n_remaining,
                rng=rng,
                algorithm=algorithm,
                parents=parents,
                **kwargs,
            )
            parents = None
            if len(proposal_population) > 0:
                decision_indices_seen.update(
                    int(payload["decision_index"])
                    for payload in proposal_population.get("trace_payload", to_numpy=False)
                    if isinstance(payload, dict)
                )
            proposal_population = self.repair(problem, proposal_population, random_state=rng, **kwargs)
            self._refresh_repaired_payloads(proposal_population)
            proposal_population = self._filter_raw_duplicates(proposal_population, pop, off)
            proposal_population = self._filter_repaired_duplicates(proposal_population, pop, off)

            if len(off) + len(proposal_population) > n_offsprings:
                n_keep = n_offsprings - len(off)
                self._mark_population_rejected(
                    proposal_population[n_keep:],
                    rejection_reason="batch_truncation",
                )
                proposal_population = proposal_population[:n_keep]

            self._append_accepted_trace_rows(
                proposal_population,
                evaluation_start_index=int(problem._next_evaluation_index + len(off)),
                controller_trace_out=self.controller_trace,
                operator_trace_out=self.operator_trace,
            )
            off = Population.merge(off, proposal_population)
            n_infills += 1
            if n_infills >= n_max_iterations:
                break

        self._sync_llm_decision_statuses(decision_indices_seen)
        return off

    def _batched_proposal_population(
        self,
        problem: Any,
        pop: Population,
        n_offsprings: int,
        *,
        rng: np.random.Generator,
        algorithm: Any,
        parents: Any | None,
        **kwargs,
    ) -> Population:
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
        proposal_payloads: list[dict[str, Any]] = []
        if event_records and all(record["operator_id"] == self.native_operator_id for record in event_records):
            start = time.perf_counter()
            native_offspring = self._native_offspring_population(
                problem,
                pop,
                initial_rows,
                rng,
                algorithm=algorithm,
                **kwargs,
            )
            operator_wall_ms = float((time.perf_counter() - start) * 1000.0)
            native_vectors = np.asarray(native_offspring.get("X"), dtype=np.float64)
            for event_index, record in enumerate(event_records):
                start = event_index * children_per_native_event
                end = start + children_per_native_event
                self._append_attempt_payloads(
                    record=record,
                    proposal_vectors=[np.asarray(vector, dtype=np.float64) for vector in native_vectors[start:end]],
                    generation_index=generation_index,
                    provisional_evaluation_start=int(problem._next_evaluation_index),
                    children_per_event=children_per_native_event,
                    operator_wall_ms=operator_wall_ms,
                    proposal_payloads_out=proposal_payloads,
                    proposal_vectors_out=proposal_vectors,
                )
            return self._proposal_population(proposal_vectors, proposal_payloads)

        for record in event_records:
            start = time.perf_counter()
            proposal_vectors_for_record = self._event_proposals(
                problem,
                pop,
                record,
                rng,
                algorithm=algorithm,
                **kwargs,
            )
            operator_wall_ms = float((time.perf_counter() - start) * 1000.0)
            self._append_attempt_payloads(
                record=record,
                proposal_vectors=proposal_vectors_for_record,
                generation_index=generation_index,
                provisional_evaluation_start=int(problem._next_evaluation_index),
                children_per_event=1,
                operator_wall_ms=operator_wall_ms,
                proposal_payloads_out=proposal_payloads,
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
            start = time.perf_counter()
            proposal_vectors_for_record = self._event_proposals(
                problem,
                pop,
                record,
                rng,
                algorithm=algorithm,
                **kwargs,
            )
            operator_wall_ms = float((time.perf_counter() - start) * 1000.0)
            self._append_attempt_payloads(
                record=record,
                proposal_vectors=proposal_vectors_for_record,
                generation_index=generation_index,
                provisional_evaluation_start=int(problem._next_evaluation_index),
                children_per_event=1,
                operator_wall_ms=operator_wall_ms,
                proposal_payloads_out=proposal_payloads,
                proposal_vectors_out=proposal_vectors,
            )

        return self._proposal_population(proposal_vectors, proposal_payloads)

    def _proposal_population_for_record(
        self,
        problem: Any,
        pop: Population,
        record: dict[str, Any],
        rng: np.random.Generator,
        *,
        algorithm: Any,
        provisional_evaluation_start: int,
        **kwargs,
    ) -> tuple[Population, int]:
        generation_index = int(record.get("generation_index", 0))
        proposal_vectors: list[np.ndarray] = []
        proposal_payloads: list[dict[str, Any]] = []
        if record["operator_id"] == self.native_operator_id:
            start = time.perf_counter()
            native_offspring = self._native_offspring_population(
                problem,
                pop,
                np.asarray([record["row"]], dtype=np.int64),
                rng,
                algorithm=algorithm,
                **kwargs,
            )
            native_vectors = [
                np.asarray(vector, dtype=np.float64)
                for vector in np.asarray(native_offspring.get("X"), dtype=np.float64)
            ]
            operator_wall_ms = float((time.perf_counter() - start) * 1000.0)
            self._append_attempt_payloads(
                record=record,
                proposal_vectors=native_vectors,
                generation_index=generation_index,
                provisional_evaluation_start=provisional_evaluation_start,
                children_per_event=int(self.raw_mating.crossover.n_offsprings),
                operator_wall_ms=operator_wall_ms,
                proposal_payloads_out=proposal_payloads,
                proposal_vectors_out=proposal_vectors,
            )
        else:
            start = time.perf_counter()
            proposal_vectors_for_record = self._event_proposals(
                problem,
                pop,
                record,
                rng,
                algorithm=algorithm,
                **kwargs,
            )
            operator_wall_ms = float((time.perf_counter() - start) * 1000.0)
            self._append_attempt_payloads(
                record=record,
                proposal_vectors=proposal_vectors_for_record,
                generation_index=generation_index,
                provisional_evaluation_start=provisional_evaluation_start,
                children_per_event=1,
                operator_wall_ms=operator_wall_ms,
                proposal_payloads_out=proposal_payloads,
                proposal_vectors_out=proposal_vectors,
            )
        return (
            self._proposal_population(proposal_vectors, proposal_payloads),
            int(provisional_evaluation_start + len(proposal_vectors)),
        )

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
        local_controller_trace: list[ControllerTraceRow] | None = None,
        local_operator_trace: list[OperatorTraceRow] | None = None,
        generation_target_offsprings: int | None = None,
    ) -> dict[str, Any]:
        parent_vectors = [np.asarray(pop[index].X, dtype=np.float64) for index in row]
        parents = ParentBundle.from_vectors(*parent_vectors)
        decision_index = self._next_decision_index
        self._next_decision_index += 1
        evaluation_index = int(problem._next_evaluation_index + len(local_controller_trace or []))
        state = build_controller_state(
            parents,
            family=self.family,
            backbone=self.backbone,
            generation_index=generation_index,
            evaluation_index=evaluation_index,
            candidate_operator_ids=self.operator_ids,
            metadata={
                "parent_indices": row,
                "native_parameters": deepcopy(self.native_parameters),
                "decision_index": decision_index,
                "design_variable_ids": list(self.design_variable_ids),
                "total_evaluation_budget": int(self.total_evaluation_budget),
                "radiator_span_max": self.radiator_span_max,
                "generation_target_offsprings": generation_target_offsprings,
            },
            controller_trace=self.controller_trace,
            operator_trace=self.operator_trace,
            local_controller_trace=local_controller_trace,
            local_operator_trace=local_operator_trace,
            history=problem.history,
            recent_window=self.recent_window,
        )
        decision = select_controller_decision(self.controller, state, self.operator_ids, rng)
        decision_id = format_decision_id(
            int(generation_index),
            int(evaluation_index),
            int(decision_index),
        )
        return {
            "decision_index": decision_index,
            "decision_id": decision_id,
            "evaluation_index": int(evaluation_index),
            "generation_index": int(generation_index),
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

    def _append_attempt_payloads(
        self,
        *,
        record: dict[str, Any],
        proposal_vectors: list[np.ndarray],
        generation_index: int,
        provisional_evaluation_start: int,
        children_per_event: int,
        operator_wall_ms: float,
        proposal_payloads_out: list[dict[str, Any]],
        proposal_vectors_out: list[np.ndarray],
    ) -> None:
        proposal_kind = "native" if record["operator_id"] == self.native_operator_id else "custom"
        for sibling_index, proposal_vector in enumerate(proposal_vectors):
            provisional_evaluation_index = int(provisional_evaluation_start + len(proposal_vectors_out))
            repaired_vector = self._repair_vector(proposal_vector)
            attempt_index = self._next_attempt_index
            self._next_attempt_index += 1
            decision_metadata = {
                "decision_index": int(record["decision_index"]),
                "decision_id": str(record["decision_id"]),
                "decision_evaluation_index": int(record["evaluation_index"]),
                "parent_indices": list(record["row"]),
                "proposal_kind": proposal_kind,
                "sibling_index": int(sibling_index),
                "children_per_event": int(children_per_event),
                **dict(record["decision"].metadata),
            }
            operator_metadata = {
                "decision_index": int(record["decision_index"]),
                "decision_id": str(record["decision_id"]),
                "decision_evaluation_index": int(record["evaluation_index"]),
                "parent_indices": list(record["row"]),
                "proposal_kind": proposal_kind,
                "sibling_index": int(sibling_index),
                "children_per_event": int(children_per_event),
                "wall_ms": float(operator_wall_ms),
            }
            controller_attempt_row = ControllerAttemptTraceRow(
                generation_index=generation_index,
                provisional_evaluation_index=provisional_evaluation_index,
                decision_index=int(record["decision_index"]),
                attempt_index=attempt_index,
                family=self.family,
                backbone=self.backbone,
                controller_id=self.controller.controller_id,
                candidate_operator_ids=tuple(self.operator_ids),
                selected_operator_id=str(record["operator_id"]),
                phase=str(record["decision"].metadata.get("model_phase") or record["decision"].phase),
                rationale=str(record["decision"].rationale),
                metadata=decision_metadata,
            )
            operator_attempt_row = OperatorAttemptTraceRow(
                generation_index=generation_index,
                provisional_evaluation_index=provisional_evaluation_index,
                decision_index=int(record["decision_index"]),
                attempt_index=attempt_index,
                operator_id=str(record["operator_id"]),
                parent_count=record["parents"].num_parents,
                parent_vectors=tuple(
                    tuple(float(value) for value in vector.tolist()) for vector in record["parents"].vectors
                ),
                proposal_vector=tuple(float(value) for value in proposal_vector.tolist()),
                repaired_vector=tuple(float(value) for value in repaired_vector.tolist()),
                metadata=operator_metadata,
            )
            self.controller_attempt_trace.append(controller_attempt_row)
            self.operator_attempt_trace.append(operator_attempt_row)
            proposal_payloads_out.append(
                {
                    "decision_index": int(record["decision_index"]),
                    "attempt_index": int(attempt_index),
                    "generation_index": int(generation_index),
                    "parent_indices": list(record["row"]),
                    "proposal_kind": proposal_kind,
                    "sibling_index": int(sibling_index),
                    "children_per_event": int(children_per_event),
                    "selected_operator_id": str(record["operator_id"]),
                    "phase": str(record["decision"].metadata.get("model_phase") or record["decision"].phase),
                    "rationale": str(record["decision"].rationale),
                    "candidate_operator_ids": tuple(self.operator_ids),
                    "parent_count": int(record["parents"].num_parents),
                    "parent_vectors": tuple(
                        tuple(float(value) for value in vector.tolist()) for vector in record["parents"].vectors
                    ),
                    "proposal_vector": np.asarray(proposal_vector, dtype=np.float64),
                    "repaired_vector": np.asarray(repaired_vector, dtype=np.float64),
                    "repaired_key": self._vector_key(repaired_vector),
                    "decision_metadata": decision_metadata,
                    "operator_metadata": operator_metadata,
                    "controller_attempt_row": controller_attempt_row,
                    "operator_attempt_row": operator_attempt_row,
                }
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

    @staticmethod
    def _proposal_population(
        proposal_vectors: list[np.ndarray],
        proposal_payloads: list[dict[str, Any]],
    ) -> Population:
        if not proposal_vectors:
            return Population.create()
        return Population.new(
            "X",
            np.asarray(proposal_vectors, dtype=np.float64),
            "trace_payload",
            proposal_payloads,
        )

    @staticmethod
    def _trace_payload(individual: Any) -> dict[str, Any]:
        payload = individual.get("trace_payload")
        if not isinstance(payload, dict):
            raise ValueError("Expected union-mating trace_payload metadata on offspring individual.")
        return payload

    def _refresh_repaired_payloads(self, population: Population) -> None:
        for individual in population:
            payload = self._trace_payload(individual)
            repaired_vector = self._repair_vector(np.asarray(individual.X, dtype=np.float64))
            payload["repaired_vector"] = np.asarray(repaired_vector, dtype=np.float64)
            payload["repaired_key"] = self._vector_key(repaired_vector)
            operator_attempt_row = payload["operator_attempt_row"]
            operator_attempt_row.repaired_vector = tuple(float(value) for value in repaired_vector.tolist())

    def _filter_raw_duplicates(self, population: Population, pop: Population, off: Population) -> Population:
        deduped_population, kept_indices, duplicate_indices = self.eliminate_duplicates.do(
            population,
            return_indices=True,
        )
        for duplicate_index in duplicate_indices:
            self._mark_attempt_status(
                self._trace_payload(population[int(duplicate_index)]),
                rejection_reason="duplicate_within_batch",
                duplicate_within_batch=True,
            )
        kept_population = population[kept_indices]
        deduped_population, kept_reference_indices, duplicate_reference_indices = self.eliminate_duplicates.do(
            kept_population,
            pop,
            off,
            return_indices=True,
            to_itself=False,
        )
        for duplicate_index in duplicate_reference_indices:
            self._mark_attempt_status(
                self._trace_payload(kept_population[int(duplicate_index)]),
                rejection_reason="duplicate_with_population",
                duplicate_with_population=True,
            )
        return deduped_population

    def _filter_repaired_duplicates(self, population: Population, pop: Population, off: Population) -> Population:
        if len(population) == 0:
            return population
        reference_keys = self._reference_repaired_keys(pop)
        reference_keys.update(self._reference_repaired_keys(off))
        kept_indices: list[int] = []
        batch_keys: set[tuple[float, ...]] = set()
        for index, individual in enumerate(population):
            payload = self._trace_payload(individual)
            repaired_key = payload["repaired_key"]
            duplicate_with_population = repaired_key in reference_keys
            duplicate_within_batch = repaired_key in batch_keys
            if duplicate_with_population or duplicate_within_batch:
                self._mark_attempt_status(
                    payload,
                    rejection_reason="repair_collapsed_duplicate",
                    duplicate_with_population=duplicate_with_population,
                    duplicate_within_batch=duplicate_within_batch,
                    repair_collapsed_duplicate=True,
                )
                continue
            batch_keys.add(repaired_key)
            kept_indices.append(index)
        return population[kept_indices]

    def _reference_repaired_keys(self, population: Population) -> set[tuple[float, ...]]:
        return {
            self._vector_key(self._repair_vector(np.asarray(individual.X, dtype=np.float64)))
            for individual in population
        }

    def _mark_population_rejected(
        self,
        population: Population,
        *,
        rejection_reason: str,
    ) -> None:
        for individual in population:
            self._mark_attempt_status(
                self._trace_payload(individual),
                rejection_reason=rejection_reason,
            )

    def _mark_attempt_status(
        self,
        payload: dict[str, Any],
        *,
        accepted_for_evaluation: bool | None = None,
        accepted_evaluation_index: int | None = None,
        rejection_reason: str | None = None,
        duplicate_with_population: bool = False,
        duplicate_within_batch: bool = False,
        repair_collapsed_duplicate: bool = False,
    ) -> None:
        controller_attempt_row = payload["controller_attempt_row"]
        operator_attempt_row = payload["operator_attempt_row"]
        if duplicate_with_population:
            controller_attempt_row.duplicate_with_population = True
            operator_attempt_row.duplicate_with_population = True
        if duplicate_within_batch:
            controller_attempt_row.duplicate_within_batch = True
            operator_attempt_row.duplicate_within_batch = True
        if repair_collapsed_duplicate:
            controller_attempt_row.repair_collapsed_duplicate = True
            operator_attempt_row.repair_collapsed_duplicate = True
        if accepted_for_evaluation is True:
            controller_attempt_row.accepted_for_evaluation = True
            operator_attempt_row.accepted_for_evaluation = True
            if accepted_evaluation_index is not None:
                if accepted_evaluation_index not in controller_attempt_row.accepted_evaluation_indices:
                    controller_attempt_row.accepted_evaluation_indices.append(int(accepted_evaluation_index))
                if accepted_evaluation_index not in operator_attempt_row.accepted_evaluation_indices:
                    operator_attempt_row.accepted_evaluation_indices.append(int(accepted_evaluation_index))
            controller_attempt_row.rejection_reason = ""
            operator_attempt_row.rejection_reason = ""
            return
        if accepted_for_evaluation is False:
            controller_attempt_row.accepted_for_evaluation = False
            operator_attempt_row.accepted_for_evaluation = False
        if rejection_reason:
            if not controller_attempt_row.rejection_reason:
                controller_attempt_row.rejection_reason = str(rejection_reason)
            if not operator_attempt_row.rejection_reason:
                operator_attempt_row.rejection_reason = str(rejection_reason)

    def _append_accepted_trace_rows(
        self,
        population: Population,
        *,
        evaluation_start_index: int,
        controller_trace_out: list[ControllerTraceRow],
        operator_trace_out: list[OperatorTraceRow],
    ) -> None:
        evaluation_index = int(evaluation_start_index)
        for individual in population:
            payload = self._trace_payload(individual)
            self._mark_attempt_status(
                payload,
                accepted_for_evaluation=True,
                accepted_evaluation_index=evaluation_index,
            )
            controller_trace_out.append(
                ControllerTraceRow(
                    generation_index=int(payload["generation_index"]),
                    evaluation_index=evaluation_index,
                    family=self.family,
                    backbone=self.backbone,
                    controller_id=self.controller.controller_id,
                    candidate_operator_ids=tuple(str(value) for value in payload["candidate_operator_ids"]),
                    selected_operator_id=str(payload["selected_operator_id"]),
                    phase=str(payload["phase"]),
                    rationale=str(payload["rationale"]),
                    metadata={
                        **dict(payload["decision_metadata"]),
                        "attempt_index": int(payload["attempt_index"]),
                    },
                )
            )
            operator_trace_out.append(
                OperatorTraceRow(
                    generation_index=int(payload["generation_index"]),
                    evaluation_index=evaluation_index,
                    operator_id=str(payload["selected_operator_id"]),
                    parent_count=int(payload["parent_count"]),
                    parent_vectors=tuple(payload["parent_vectors"]),
                    proposal_vector=tuple(float(value) for value in payload["proposal_vector"].tolist()),
                    metadata={
                        **dict(payload["operator_metadata"]),
                        "attempt_index": int(payload["attempt_index"]),
                        "repaired_vector": payload["repaired_vector"].tolist(),
                    },
                )
            )
            evaluation_index += 1

    def _sync_llm_decision_statuses(self, decision_indices: set[int]) -> None:
        if not decision_indices:
            return
        for decision_index in decision_indices:
            attempt_rows = [
                row for row in self.controller_attempt_trace if int(row.decision_index) == int(decision_index)
            ]
            if not attempt_rows:
                continue
            accepted_indices = sorted(
                {
                    int(accepted_index)
                    for row in attempt_rows
                    for accepted_index in row.accepted_evaluation_indices
                }
            )
            accepted_for_evaluation = bool(accepted_indices)
            rejection_reason = "" if accepted_for_evaluation else next(
                (str(row.rejection_reason) for row in attempt_rows if str(row.rejection_reason).strip()),
                "",
            )
            duplicate_with_population = any(bool(row.duplicate_with_population) for row in attempt_rows)
            duplicate_within_batch = any(bool(row.duplicate_within_batch) for row in attempt_rows)
            repair_collapsed_duplicate = any(bool(row.repair_collapsed_duplicate) for row in attempt_rows)
            self._update_llm_trace_entries(
                getattr(self.controller, "request_trace", None),
                decision_index=decision_index,
                accepted_for_evaluation=accepted_for_evaluation,
                accepted_evaluation_indices=accepted_indices,
                rejection_reason=rejection_reason,
                duplicate_with_population=duplicate_with_population,
                duplicate_within_batch=duplicate_within_batch,
                repair_collapsed_duplicate=repair_collapsed_duplicate,
            )
            self._update_llm_trace_entries(
                getattr(self.controller, "response_trace", None),
                decision_index=decision_index,
                accepted_for_evaluation=accepted_for_evaluation,
                accepted_evaluation_indices=accepted_indices,
                rejection_reason=rejection_reason,
                duplicate_with_population=duplicate_with_population,
                duplicate_within_batch=duplicate_within_batch,
                repair_collapsed_duplicate=repair_collapsed_duplicate,
            )

    @staticmethod
    def _update_llm_trace_entries(
        rows: list[dict[str, Any]] | None,
        *,
        decision_index: int,
        accepted_for_evaluation: bool,
        accepted_evaluation_indices: list[int],
        rejection_reason: str,
        duplicate_with_population: bool,
        duplicate_within_batch: bool,
        repair_collapsed_duplicate: bool,
    ) -> None:
        if rows is None:
            return
        for row in reversed(rows):
            if row.get("decision_index") != int(decision_index):
                continue
            row["accepted_for_evaluation"] = bool(accepted_for_evaluation)
            row["accepted_evaluation_indices"] = list(accepted_evaluation_indices)
            row["accepted_evaluation_index"] = (
                None if not accepted_evaluation_indices else int(accepted_evaluation_indices[0])
            )
            row["rejection_reason"] = "" if accepted_for_evaluation else str(rejection_reason)
            row["duplicate_with_population"] = bool(duplicate_with_population)
            row["duplicate_within_batch"] = bool(duplicate_within_batch)
            row["repair_collapsed_duplicate"] = bool(repair_collapsed_duplicate)
            break

    @staticmethod
    def _vector_key(vector: np.ndarray) -> tuple[float, ...]:
        return tuple(round(float(value), 12) for value in np.asarray(vector, dtype=np.float64).tolist())


def build_genetic_union_algorithm(
    problem: Any,
    optimization_spec: Any,
    algorithm_config: dict[str, Any],
    *,
    trace_output_root: str | Path | None = None,
) -> GeneticUnionAdapterArtifacts:
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
    configure_controller_trace_outputs(mating.controller, output_root=trace_output_root)
    algorithm.mating = mating
    return GeneticUnionAdapterArtifacts(
        algorithm=algorithm,
        controller_trace=mating.controller_trace,
        operator_trace=mating.operator_trace,
        controller_attempt_trace=mating.controller_attempt_trace,
        operator_attempt_trace=mating.operator_attempt_trace,
        llm_request_trace=getattr(mating.controller, "request_trace", None),
        llm_response_trace=getattr(mating.controller, "response_trace", None),
        llm_reflection_trace=getattr(mating.controller, "reflection_trace", None),
        llm_metrics=getattr(mating.controller, "metrics", None),
    )
