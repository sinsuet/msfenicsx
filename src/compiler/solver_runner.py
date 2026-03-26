from __future__ import annotations


def solve_steady_heat(problem):
    solution = problem.solve()
    solution.name = "temperature"
    return solution
