from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


ModeId = Literal["raw", "union", "llm"]


@dataclass(frozen=True, slots=True)
class ResourceCap:
    evaluation_workers: int
    concurrent_runs: int

    @property
    def estimated_workers(self) -> int:
        return int(self.evaluation_workers) * int(self.concurrent_runs)


@dataclass(frozen=True, slots=True)
class MatrixLeaf:
    matrix_id: str
    block_id: str
    scenario_id: str
    method_id: str
    algorithm_family: str
    algorithm_backbone: str
    mode: ModeId
    llm_profile: str | None
    replicate_seed: int
    benchmark_seed: int
    algorithm_seed: int
    population_size: int
    num_generations: int
    base_spec_path: Path

    @property
    def nominal_budget(self) -> int:
        return int(self.population_size) * int(self.num_generations)


@dataclass(frozen=True, slots=True)
class MatrixConfig:
    matrix_id: str
    scenarios: tuple[str, ...]
    replicate_seeds: tuple[int, ...]
    algorithm_seed_offset: int
    population_size: int
    num_generations: int
    llm_profiles: tuple[str, ...]
    resource_caps: dict[str, ResourceCap]

    def expand_leaves(self) -> list[MatrixLeaf]:
        leaves: list[MatrixLeaf] = []
        for scenario_id in self.scenarios:
            for backbone, family in (("nsga2", "genetic"), ("spea2", "genetic"), ("moead", "decomposition")):
                for replicate_seed in self.replicate_seeds:
                    leaves.append(
                        MatrixLeaf(
                            matrix_id=self.matrix_id,
                            block_id="M1_raw_backbone_512eval",
                            scenario_id=scenario_id,
                            method_id=f"{backbone}_raw",
                            algorithm_family=family,
                            algorithm_backbone=backbone,
                            mode="raw",
                            llm_profile=None,
                            replicate_seed=replicate_seed,
                            benchmark_seed=replicate_seed,
                            algorithm_seed=replicate_seed + self.algorithm_seed_offset,
                            population_size=self.population_size,
                            num_generations=self.num_generations,
                            base_spec_path=Path(
                                f"scenarios/optimization/{scenario_id}_raw.yaml"
                                if backbone == "nsga2"
                                else f"scenarios/optimization/{scenario_id}_{backbone}_raw.yaml"
                            ),
                        )
                    )
            for replicate_seed in self.replicate_seeds:
                leaves.append(
                    MatrixLeaf(
                        matrix_id=self.matrix_id,
                        block_id="M2_nsga2_union_512eval",
                        scenario_id=scenario_id,
                        method_id="nsga2_union",
                        algorithm_family="genetic",
                        algorithm_backbone="nsga2",
                        mode="union",
                        llm_profile=None,
                        replicate_seed=replicate_seed,
                        benchmark_seed=replicate_seed,
                        algorithm_seed=replicate_seed + self.algorithm_seed_offset,
                        population_size=self.population_size,
                        num_generations=self.num_generations,
                        base_spec_path=Path(f"scenarios/optimization/{scenario_id}_union.yaml"),
                    )
                )
            for profile_index, llm_profile in enumerate(self.llm_profiles):
                block_letter = chr(ord("a") + profile_index)
                block_id = f"M3{block_letter}_llm_{llm_profile}_512eval"
                for replicate_seed in self.replicate_seeds:
                    leaves.append(
                        MatrixLeaf(
                            matrix_id=self.matrix_id,
                            block_id=block_id,
                            scenario_id=scenario_id,
                            method_id=f"nsga2_llm_{llm_profile}",
                            algorithm_family="genetic",
                            algorithm_backbone="nsga2",
                            mode="llm",
                            llm_profile=llm_profile,
                            replicate_seed=replicate_seed,
                            benchmark_seed=replicate_seed,
                            algorithm_seed=replicate_seed + self.algorithm_seed_offset,
                            population_size=self.population_size,
                            num_generations=self.num_generations,
                            base_spec_path=Path(f"scenarios/optimization/{scenario_id}_llm.yaml"),
                        )
                    )
        return leaves
