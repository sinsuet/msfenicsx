"""Family-specific adapters for controller-guided proposal execution."""

from optimizers.adapters.decomposition_family import build_decomposition_union_algorithm
from optimizers.adapters.genetic_family import build_genetic_union_algorithm
from optimizers.adapters.swarm_family import build_swarm_union_algorithm

__all__ = [
    "build_decomposition_union_algorithm",
    "build_genetic_union_algorithm",
    "build_swarm_union_algorithm",
]
