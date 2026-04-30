# S1 Typical Desktop-Safe Parallel Benchmark Execution Design

> Status: historical S1 execution design; current active paper-facing debugging has moved to `s5_aggressive15` in the S5-S7 family.
>
> This design adds conservative parallel execution to the active `raw` and `union` optimizer paths so single-run latency and batch throughput improve while desktop responsiveness, benchmark integrity, and controller trace semantics remain stable.

## 1. Goal

Improve execution efficiency for the active `s1_typical` benchmark while preserving the current scientific contract from `AGENTS.md`.

Required invariants:

- At the time of this design, `s1_typical` remained the only active paper-facing benchmark
- one operating case only
- fifteen named components
- all fifteen optimize `x/y` only
- no optimized rotation
- `32D` decision vector
- paper-facing objectives remain:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- paper-facing hard constraints remain unchanged
- `raw` and `union` remain directly comparable
- benchmark integrity metrics and artifact semantics must not drift under parallel execution

This is an execution-architecture upgrade, not a benchmark redesign.

## 2. Problem Statement

The current optimizer path underutilizes available machine resources because the expensive evaluation pipeline is serialized even though many candidate solves are independent.

For the active paper-facing `s1_typical` specs:

- `population_size = 32`
- `num_generations = 16`
- one run therefore executes approximately:
  - one baseline evaluation
  - `32 * 16 = 512` optimizer evaluations

The dominant runtime cost is the expensive per-candidate path:

1. repair
2. cheap constraints
3. PDE solve
4. evaluation

The current structure serializes work at two important layers:

- `optimizers/run_suite.py` iterates modes and seeds serially
- `optimizers/problem.py` evaluates candidates one at a time

At the same time, the user requirement is explicitly conservative:

- improve both single-run latency and batch throughput
- avoid saturating the machine
- avoid multi-seed development runs that can consume an hour or more
- keep the desktop usable during optimization

## 3. Constraints And Non-Goals

### 3.1 Hard Constraints

The following must remain unchanged:

- no new paper-facing objectives
- no new paper-facing constraints
- no benchmark-specific physics changes
- no multi-`benchmark_seed` interpretation for `s1_typical`
- no corruption of `first_feasible_eval`, `optimizer_feasible_rate`, Pareto summaries, or representative artifacts
- no `union` controller-history semantic drift

### 3.2 Non-Goals

This phase does not attempt:

- solver-internal MPI redesign
- aggressive machine saturation
- asynchronous multi-mode default scheduling
- concurrent multi-seed paper-facing runs
- `llm` execution optimization
- changes to benchmark physics or evaluation definitions

## 4. Current Runtime Structure

### 4.1 Outer Orchestration

`optimizers/run_suite.py` currently executes:

- selected mode order serially
- benchmark seeds serially within each mode
- summary and rendering after each mode finishes

This is simple and safe, but it does not shorten a single `raw` or `union` run.

### 4.2 Inner Evaluation Path

`optimizers/problem.py` currently implements a fully serial elementwise evaluation flow:

1. assign `evaluation_index`
2. decode vector and build decision payload
3. repair candidate
4. run cheap constraints
5. if cheap-constraint-feasible:
   - build `ThermalCase`
   - solve PDE
   - evaluate solution
   - store artifacts
6. append record to `history`

This means the expensive solve/evaluate segment cannot overlap across candidates even though those solves are independent once the candidate case is fixed.

### 4.3 Union Semantics

`optimizers/adapters/genetic_family.py` constructs union controller decisions sequentially and uses:

- `problem.history`
- predicted `evaluation_index`
- recent controller and operator traces

Therefore the controller decision stage is semantically order-sensitive even if later expensive solves are not.

## 5. Rejected Approaches

### 5.1 Outer-Only Run Parallelism

One option is to parallelize only independent outer jobs such as:

- `raw` and `union` side by side
- independent seeds side by side
- page/report rendering side by side

Pros:

- low implementation risk
- easy to reason about

Cons:

- weak improvement to single-run latency
- increased risk of desktop contention when multiple full optimizers run at once
- encourages multi-seed usage, which is explicitly undesirable during development

Decision: reject as the primary solution.

### 5.2 Full Optimizer-Wide Concurrent Execution

Another option is to parallelize proposal generation, controller decisions, evaluation, and artifact writing broadly across the optimizer loop.

Pros:

- highest theoretical speedup

Cons:

- high risk to `union` controller semantics
- higher risk of nondeterministic `history` ordering
- harder debugging and failure recovery
- more likely to overload the desktop

Decision: reject.

### 5.3 Solver-Internal Parallelism First

Another option is to redesign the PDE solve itself around MPI or more aggressive solver-level parallelism.

Pros:

- could eventually accelerate each candidate solve

Cons:

- much higher implementation cost
- greater numerical and environment risk
- unnecessary before exploiting the simpler cross-candidate parallelism already available

Decision: reject for this phase.

## 6. Selected Design

### 6.1 Conservative Hybrid Execution

Adopt a conservative hybrid model:

- keep optimizer control flow and controller decisions on the main process
- parallelize only the expensive candidate solve/evaluate segment
- keep submission and artifact recording deterministic
- default to a small, desktop-safe worker count

This design improves both:

- single-run latency, because multiple expensive candidate solves can overlap
- batch throughput, because each run finishes faster even when outer orchestration stays conservative

### 6.2 Parallel Boundary

The parallel boundary should sit between:

- main-process candidate preparation
- worker-process expensive evaluation

Selected split:

Main process responsibilities:

- generation progression
- raw offspring generation
- union controller decision selection
- operator proposal generation
- `repair`
- cheap constraints
- `evaluation_index` allocation
- `history` and trace submission
- artifact persistence and summary building

Worker responsibilities:

- build candidate `ThermalCase` from already repaired payload
- execute `solve_case_artifacts`
- execute `evaluate_case_solution`
- return success payload or structured failure payload

This keeps the order-sensitive logic serial and pushes only the dominant cost to workers.

## 7. Execution Model

### 7.1 Main-Thread Submission

Each candidate should be handled in this order:

1. assign stable `evaluation_index`
2. repair proposal
3. run cheap constraints
4. if cheap constraints fail:
   - record penalty immediately on the main thread
   - do not consume worker capacity
5. if cheap constraints pass:
   - submit a solve/evaluate task to the worker pool

### 7.2 Worker Completion

Workers may finish out of order.

However, completion order must not define repository semantics.

The main process should maintain a pending-result buffer keyed by `evaluation_index` and commit results only in evaluation order.

### 7.3 Ordered Commit Rule

The ordered commit rule is mandatory:

- `history` append order must remain `evaluation_index` order
- `artifacts_by_index` population must reflect the same order
- `first_feasible_eval` must continue to refer to the earliest optimizer evaluation index that is feasible
- controller and operator traces must remain aligned with the planned candidate index, not worker finish order

This preserves paper-facing comparability between serial and parallel runs.

## 8. Resource Governance

### 8.1 Default Profile

The default runtime profile should be `desktop-safe`.

Selected behavior:

- one mode run at a time
- one `benchmark_seed` only
- small bounded candidate worker pool
- no default outer parallel mode scheduling

### 8.2 Worker Count Policy

The first implementation should use explicit bounded worker counts, not complex dynamic auto-scaling.

Recommended default:

- default `evaluation_workers = 2` when the machine has enough headroom
- degrade to `1` when available CPU budget is small

The system should preserve a safety reserve for the desktop instead of allocating all available logical cores.

### 8.3 Configuration Surface

Expose only a small configuration surface, for example:

- execution profile name such as `desktop-safe`
- explicit `evaluation_workers`

Do not expose many tuning knobs in the first phase.

### 8.4 Memory Posture

The first phase should use a simple conservative memory posture:

- no long-lived large caches in workers
- one candidate solve per worker at a time
- no aggressive concurrent report rendering in the background

The aim is predictable machine behavior, not maximum throughput.

## 9. Raw And Union Compatibility

### 9.1 Raw

`raw` can adopt this execution model directly.

It has no controller-history dependency beyond the ordinary ordered evaluation stream, so once ordered commit is preserved, result semantics remain stable.

### 9.2 Union

`union` must preserve its sequential controller semantics.

Selected rule:

- controller decisions remain sequential and generation-local
- a full batch of event records may be prepared in order
- expensive solve/evaluate work for cheap-constraint-feasible candidates may then execute in parallel
- result commit remains ordered

This preserves:

- `problem.history` meaning
- predicted `evaluation_index` meaning
- `controller_trace` and `operator_trace` alignment

### 9.3 LLM

`llm` is explicitly out of scope for this implementation phase.

The design should avoid making future `llm` support harder, but no `llm` execution changes are required now.

When `llm` is brought onto this execution path later, it should reuse the same bounded execution surface:

- single `benchmark_seed`
- the same `--evaluation-workers` control
- the same desktop-safe default posture used by `raw` and `union`

## 10. Failure Handling

Parallel execution must preserve current failure visibility.

Required behavior:

- cheap-constraint failures still produce immediate local penalty records
- worker exceptions must be reported back to the main process
- the main process converts worker exceptions into the same penalty-style optimizer record shape used today
- failure reason strings remain visible in history and diagnostics
- failed solves must not disappear because of retry loops or silent worker drops

This keeps anomalies visible in artifacts and comparisons.

## 11. Artifact And Summary Integrity

Parallel execution must not change the meaning of repository outputs.

The following outputs must remain semantically stable:

- optimizer `history`
- `aggregate_metrics`
- representative candidate selection
- representative case/solution/evaluation bundles
- `generation_summary.jsonl`
- `controller_trace.json`
- `operator_trace.json`
- mode summaries
- comparison summaries

The implementation should therefore keep:

- artifact writing in the main process
- summary construction after ordered record commit
- no concurrent writes to the same run directory from multiple workers

## 12. Module Impact

Primary implementation areas are expected to include:

- `optimizers/problem.py`
- `optimizers/drivers/raw_driver.py`
- `optimizers/drivers/union_driver.py`
- `optimizers/run_suite.py`
- `optimizers/cli.py`
- possibly a new helper module for parallel candidate evaluation
- targeted tests under `tests/optimizers/`

Documentation likely impacted:

- `README.md`
- docs describing optimizer execution and validation guidance

`AGENTS.md` should only change if repository-wide guidance itself changes.

## 13. Validation Strategy

### 13.1 Focused Tests First

Before any expensive reruns, add focused tests covering:

- stable `evaluation_index` assignment under parallel execution
- ordered `history` commit even when worker completion is out of order
- cheap-constraint failures not entering the worker pool
- worker exception conversion into visible penalty records
- raw aggregate metrics stability
- union trace and controller-state stability

### 13.2 Low-Cost Smoke Validation

Use low-cost smoke configurations for development validation:

- small population
- one or two generations
- single `benchmark_seed`

These smoke runs should validate pipeline behavior without requiring long paper-facing reruns.

### 13.3 Serial-Equivalent Validation

The first strong regression gate should be:

- parallel architecture with `evaluation_workers = 1`

Acceptance intent:

- matches serial semantics closely enough that summaries, ordering, and artifacts remain unchanged in meaning

### 13.4 Bounded Parallel Validation

The next regression gate should be:

- same setup with `evaluation_workers = 2`

Acceptance checks:

- ordered records remain stable
- `first_feasible_eval` remains meaningful
- `optimizer_feasible_rate` remains meaningful
- Pareto size and representative selection remain coherent
- trace alignment remains correct

### 13.5 Final Real Validation

Only after focused tests and smoke validation pass:

- run one real single-seed `raw` validation
- run one real single-seed `union` validation

Do not introduce multi-seed validation in this phase.

## 14. Rollout Order

Implementation should proceed in this order:

1. Extract the expensive candidate solve/evaluate path into a worker-safe task boundary.
2. Add ordered-result commit infrastructure in the optimizer problem layer.
3. Integrate bounded parallel evaluation into `raw`.
4. Add focused tests for ordering, failures, and metrics.
5. Validate low-cost smoke runs and serial-equivalent behavior.
6. Integrate the same evaluation model into `union` while preserving sequential controller decisions.
7. Add focused union trace and controller-state tests.
8. Run final single-seed real `raw` and `union` validation with conservative worker settings.
9. Only then consider enabling `desktop-safe` concurrency by default.

## 15. Final Recommendation

Proceed with a desktop-safe hybrid execution upgrade for `s1_typical` `raw` and `union`.

This is the smallest credible performance design that:

- improves single-run wall-clock time
- improves overall batch throughput
- avoids aggressive machine saturation
- preserves benchmark integrity
- preserves `union` controller semantics
- respects the user's preference for conservative daytime execution

It is the right intermediate step before considering any broader runtime acceleration work.
