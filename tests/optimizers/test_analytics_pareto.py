"""Pareto filtering and 2D hypervolume."""

from __future__ import annotations

import math


def test_pareto_minimization_filters_dominated_points() -> None:
    from optimizers.analytics.pareto import pareto_front_indices

    # Minimization in both objectives.
    objectives = [
        (1.0, 5.0),  # non-dominated
        (2.0, 4.0),  # non-dominated
        (3.0, 3.0),  # non-dominated
        (4.0, 6.0),  # dominated by (2,4)
        (5.0, 2.0),  # non-dominated
    ]
    idx = pareto_front_indices(objectives)
    assert idx == [0, 1, 2, 4]


def test_hypervolume_2d_against_reference_point() -> None:
    from optimizers.analytics.pareto import hypervolume_2d

    # Single point (3,3) with reference (5,5): HV = 2 x 2 = 4.
    hv = hypervolume_2d([(3.0, 3.0)], reference_point=(5.0, 5.0))
    assert math.isclose(hv, 4.0, rel_tol=1e-9)


def test_hypervolume_2d_multiple_points() -> None:
    from optimizers.analytics.pareto import hypervolume_2d

    # Points (1,4), (2,3), (4,1) vs ref (5,5).
    # Stepwise: (1,4)->(2,3)->(4,1) contributes
    #   (2-1)*(5-4) + (4-2)*(5-3) + (5-4)*(5-1) = 1 + 4 + 4 = 9
    hv = hypervolume_2d([(1.0, 4.0), (2.0, 3.0), (4.0, 1.0)], reference_point=(5.0, 5.0))
    assert math.isclose(hv, 9.0, rel_tol=1e-9)


def test_hypervolume_2d_ignores_dominated_points() -> None:
    from optimizers.analytics.pareto import hypervolume_2d

    points = [(1.0, 4.0), (2.0, 3.0), (4.0, 1.0), (3.0, 4.0)]  # (3,4) is dominated
    hv = hypervolume_2d(points, reference_point=(5.0, 5.0))
    assert math.isclose(hv, 9.0, rel_tol=1e-9)
