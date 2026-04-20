"""Decomposition-family union adapter for controller-guided offspring proposals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

import numpy as np
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
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow
from optimizers.raw_backbones.moead import ConstrainedMOEAD, build_algorithm_kwargs
from optimizers.repair import repair_case_from_vector
from optimizers.traces.correlation import format_decision_id


@dataclass(slots=True)
class DecompositionUnionAdapterArtifacts:
    algorithm: Any
    controller_trace: list[ControllerTraceRow]
    operator_trace: list[OperatorTraceRow]
    llm_request_trace: list[dict[str, Any]] | None = None
    llm_response_trace: list[dict[str, Any]] | None = None
    llm_reflection_trace: list[dict[str, Any]] | None = None
    llm_metrics: dict[str, Any] | None = None


class UnionConstrainedMOEAD(ConstrainedMOEAD):
    def __init__(
        self,
        *,
        operator_ids: list[str],
        controller_id: str,
        variable_layout: VariableLayout,
        repair_reference_case: Any,
        optimization_spec: dict[str, Any],
        ref_dirs: np.ndarray,
        n_neighbors: int,
        reference_direction_parameters: dict[str, Any],
        radiator_span_max: float | None = None,
        controller_parameters: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ref_dirs=ref_dirs, n_neighbors=n_neighbors)
        self.reference_direction_parameters = reference_direction_parameters
        self.union_controller = build_controller(controller_id, controller_parameters)
        self.operator_ids = list(operator_ids)
        self.variable_layout = variable_layout
        self.repair_reference_case = repair_reference_case
        self.optimization_spec = optimization_spec
        self.radiator_span_max = radiator_span_max
        self.design_variable_ids = [str(item["variable_id"]) for item in self.optimization_spec.get("design_variables", [])]
        self.native_operator_id = native_operator_id_for_backbone("decomposition", "moead")
        self.controller_trace: list[ControllerTraceRow] = []
        self.operator_trace: list[OperatorTraceRow] = []

    def _next(self):
        pop = self.pop
        n_parents = self.mating.crossover.n_parents
        for neighbor_index in self.random_state.permutation(len(pop)):
            parent_indices = self.selection.do(
                self.problem,
                pop,
                1,
                n_parents,
                neighbors=[self.neighbors[neighbor_index]],
                to_pop=False,
                random_state=self.random_state,
            )
            row = np.asarray(parent_indices, dtype=np.int64).reshape(-1)
            parents = ParentBundle.from_vectors(*(np.asarray(pop[index].X, dtype=np.float64) for index in row))
            evaluation_index = int(self.problem._next_evaluation_index)
            state = build_controller_state(
                parents,
                family="decomposition",
                backbone="moead",
                generation_index=max(0, int(getattr(self, "n_iter", 0))),
                evaluation_index=evaluation_index,
                candidate_operator_ids=self.operator_ids,
                metadata={
                    "neighbor_index": int(neighbor_index),
                    "parent_indices": row.tolist(),
                    "design_variable_ids": list(self.design_variable_ids),
                    "radiator_span_max": self.radiator_span_max,
                },
                controller_trace=self.controller_trace,
                operator_trace=self.operator_trace,
                history=self.problem.history,
                recent_window=32,
            )
            decision = select_controller_decision(self.union_controller, state, self.operator_ids, self.random_state)
            decision_index = 0
            decision_id = format_decision_id(int(state.generation_index), int(state.evaluation_index), int(decision_index))
            start = time.perf_counter()
            operator_id = decision.selected_operator_id
            if operator_id == self.native_operator_id:
                raw_proposal = self._native_moead_proposal(pop, row)
                proposal_kind = "native"
            else:
                native_proposal = self._native_moead_proposal(pop, row)
                custom_proposal = get_operator_definition(operator_id).propose(
                    parents=parents,
                    state=state,
                    variable_layout=self.variable_layout,
                    rng=self.random_state,
                )
                # MOEA/D depends strongly on neighborhood-native offspring geometry.
                # Inject only a small custom displacement on top of the native proposal.
                raw_proposal = 0.98 * native_proposal + 0.02 * np.asarray(custom_proposal, dtype=np.float64)
                proposal_kind = "custom"
            operator_wall_ms = float((time.perf_counter() - start) * 1000.0)
            repaired_proposal = self._repair_vector(raw_proposal)
            self.controller_trace.append(
                ControllerTraceRow(
                    generation_index=state.generation_index,
                    evaluation_index=state.evaluation_index,
                    family="decomposition",
                    backbone="moead",
                    controller_id=self.union_controller.controller_id,
                    candidate_operator_ids=tuple(self.operator_ids),
                    selected_operator_id=operator_id,
                    phase=str(decision.metadata.get("model_phase") or decision.phase),
                    rationale=decision.rationale,
                    metadata={
                        "decision_id": decision_id,
                        "decision_index": int(decision_index),
                        "neighbor_index": int(neighbor_index),
                        "parent_indices": row.tolist(),
                        "proposal_kind": proposal_kind,
                        **dict(decision.metadata),
                    },
                )
            )
            self.operator_trace.append(
                OperatorTraceRow(
                    generation_index=state.generation_index,
                    evaluation_index=state.evaluation_index,
                    operator_id=operator_id,
                    parent_count=parents.num_parents,
                    parent_vectors=tuple(tuple(float(value) for value in vector.tolist()) for vector in parents.vectors),
                    proposal_vector=tuple(float(value) for value in raw_proposal.tolist()),
                    metadata={
                        "decision_id": decision_id,
                        "decision_index": int(decision_index),
                        "decision_evaluation_index": int(state.evaluation_index),
                        "neighbor_index": int(neighbor_index),
                        "parent_indices": row.tolist(),
                        "proposal_kind": proposal_kind,
                        "wall_ms": float(operator_wall_ms),
                        "repaired_vector": repaired_proposal.tolist(),
                    },
                )
            )
            offspring = Population.new(X=np.asarray([repaired_proposal], dtype=np.float64))[0]
            offspring = yield offspring
            self.ideal = np.min(np.vstack([self.ideal, offspring.F]), axis=0)
            self._replace(neighbor_index, offspring)

    def _native_moead_proposal(self, pop: Population, parent_indices: np.ndarray) -> np.ndarray:
        native_offspring = self.mating.crossover(
            self.problem,
            pop,
            parents=np.asarray([parent_indices], dtype=np.int64),
            random_state=self.random_state,
        )
        native_offspring = self.mating.mutation(
            self.problem,
            native_offspring,
            random_state=self.random_state,
        )
        chosen = self.random_state.choice(native_offspring)
        return np.asarray(chosen.X, dtype=np.float64)

    def _repair_vector(self, vector: np.ndarray) -> np.ndarray:
        repaired_case = repair_case_from_vector(
            self.repair_reference_case,
            self.optimization_spec,
            np.asarray(vector, dtype=np.float64),
            radiator_span_max=self.radiator_span_max,
        )
        return extract_decision_vector(repaired_case, self.optimization_spec)


def build_decomposition_union_algorithm(
    problem: Any,
    optimization_spec: Any,
    algorithm_config: dict[str, Any],
    *,
    trace_output_root: str | Path | None = None,
) -> DecompositionUnionAdapterArtifacts:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    if algorithm_config["mode"] != "union":
        raise ValueError(f"Decomposition union adapter requires algorithm.mode='union', got {algorithm_config['mode']!r}.")
    if algorithm_config["family"] != "decomposition" or algorithm_config["backbone"] != "moead":
        raise ValueError(
            "Decomposition union adapter supports only family='decomposition', backbone='moead'. "
            f"Received family={algorithm_config['family']!r}, backbone={algorithm_config['backbone']!r}."
        )

    kwargs = build_algorithm_kwargs(problem, algorithm_config)
    algorithm = UnionConstrainedMOEAD(
        operator_ids=list(spec_payload["operator_control"]["operator_pool"]),
        controller_id=str(spec_payload["operator_control"]["controller"]),
        variable_layout=VariableLayout.from_optimization_spec(spec_payload),
        repair_reference_case=problem.base_case,
        optimization_spec=spec_payload,
        ref_dirs=kwargs["ref_dirs"],
        n_neighbors=kwargs["n_neighbors"],
        reference_direction_parameters=kwargs["reference_direction_parameters"],
        radiator_span_max=getattr(problem, "radiator_span_max", None),
        controller_parameters=spec_payload["operator_control"].get("controller_parameters"),
    )
    configure_controller_trace_outputs(algorithm.union_controller, output_root=trace_output_root)
    return DecompositionUnionAdapterArtifacts(
        algorithm=algorithm,
        controller_trace=algorithm.controller_trace,
        operator_trace=algorithm.operator_trace,
        llm_request_trace=getattr(algorithm.union_controller, "request_trace", None),
        llm_response_trace=getattr(algorithm.union_controller, "response_trace", None),
        llm_reflection_trace=getattr(algorithm.union_controller, "reflection_trace", None),
        llm_metrics=getattr(algorithm.union_controller, "metrics", None),
    )
