from optimizers.benchmark_runner.igd import empirical_reference_front, igd_2d


def test_empirical_reference_front_keeps_nondominated_points() -> None:
    points = [(1.0, 5.0), (2.0, 4.0), (3.0, 7.0), (1.5, 4.5)]

    front = empirical_reference_front(points)

    assert front == [(1.0, 5.0), (1.5, 4.5), (2.0, 4.0)]


def test_igd_2d_is_zero_when_candidate_matches_reference() -> None:
    reference = [(1.0, 5.0), (2.0, 4.0)]

    assert igd_2d(reference, reference) == 0.0


def test_igd_2d_is_average_nearest_reference_distance_after_normalization() -> None:
    reference = [(0.0, 0.0), (10.0, 0.0)]
    candidate = [(0.0, 0.0)]

    value = igd_2d(candidate, reference)

    assert value == 0.5
