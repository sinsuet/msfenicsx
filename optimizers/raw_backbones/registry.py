"""Registry for raw optimizer backbone wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from optimizers.raw_backbones import ctaea, cmopso, moead, nsga2, nsga3, rvea, spea2


RawAlgorithmBuilder = Callable[[Any, dict[str, Any]], Any]


@dataclass(frozen=True, slots=True)
class RawBackboneDefinition:
    family: str
    backbone: str
    build_algorithm: RawAlgorithmBuilder


_REGISTERED_RAW_BACKBONES = {
    (definition.family, definition.backbone): definition
    for definition in (
        RawBackboneDefinition(nsga2.FAMILY, nsga2.BACKBONE, nsga2.build_algorithm),
        RawBackboneDefinition(nsga3.FAMILY, nsga3.BACKBONE, nsga3.build_algorithm),
        RawBackboneDefinition(ctaea.FAMILY, ctaea.BACKBONE, ctaea.build_algorithm),
        RawBackboneDefinition(rvea.FAMILY, rvea.BACKBONE, rvea.build_algorithm),
        RawBackboneDefinition(spea2.FAMILY, spea2.BACKBONE, spea2.build_algorithm),
        RawBackboneDefinition(moead.FAMILY, moead.BACKBONE, moead.build_algorithm),
        RawBackboneDefinition(cmopso.FAMILY, cmopso.BACKBONE, cmopso.build_algorithm),
    )
}


def list_registered_backbones() -> list[str]:
    return sorted({definition.backbone for definition in _REGISTERED_RAW_BACKBONES.values()})


def get_raw_backbone_definition(family: str, backbone: str) -> RawBackboneDefinition:
    key = (family, backbone)
    if key not in _REGISTERED_RAW_BACKBONES:
        raise KeyError(f"Unsupported raw backbone family={family!r}, backbone={backbone!r}.")
    return _REGISTERED_RAW_BACKBONES[key]


def build_raw_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> Any:
    if algorithm_config["mode"] != "raw":
        raise ValueError(f"Raw backbone registry only supports algorithm.mode='raw', got {algorithm_config['mode']!r}.")
    definition = get_raw_backbone_definition(
        family=str(algorithm_config["family"]),
        backbone=str(algorithm_config["backbone"]),
    )
    return definition.build_algorithm(problem, algorithm_config)
