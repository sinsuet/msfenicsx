# msfenicsx Rules

Scope: active rules for the current clean-rebuild `msfenicsx` repository on `main`.

## 1. Path and Edit Safety

- Use explicit repository-relative paths with forward slashes (`/`) whenever practical.
- Read the exact source before editing and preserve precise edit context.
- Ensure parent directories exist before writing new files.
- If a write looks risky because of locking, permissions, or unclear ownership, stop and notify first.

## 2. Python and Environment

- This repository's canonical execution environment is WSL2 Ubuntu, not native Windows.
- Treat `/home/hymn/msfenicsx` as the canonical workspace path even when the editor opens the repo via `\\wsl$\Ubuntu\home\hymn\msfenicsx`.
- Run Python, CLI, and test commands in the `msfenicsx` conda environment.
- Prefer reproducible command forms such as `conda run -n msfenicsx ...`.
- Run Python, CLI, tests, and verification inside WSL with Linux paths.
- Prefer `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...` when shell initialization is uncertain.
- Do not use Windows-side `conda`, `python`, or `pytest` for repository verification unless the user explicitly asks for a Windows-specific check.
- If a command must be launched from a Windows host shell, invoke WSL explicitly, for example:
  `wsl.exe -d Ubuntu bash -lc "cd /home/hymn/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx <command>"`
- Do not assume system `python` or system `pytest`.

## 3. Secrets and Configuration

- Never hardcode API keys, tokens, or private credentials.
- Load secrets from environment variables or explicit local configuration.
- Do not silently change important runtime or solver defaults without documenting the change.

## 4. Encoding and Text I/O

- Repository text files default to UTF-8 encoding without BOM.
- Python file reads and writes for repository artifacts, docs, YAML, JSON, and reports should explicitly use `encoding="utf-8"` unless a stronger reason exists.
- Do not introduce locale-dependent encodings such as GBK or ANSI into active repository workflows.
- Treat terminal-side mojibake from the host or WSL bridge as environment noise unless the same corruption is present in the saved repository artifact itself.

## 5. Root-Cause First

- Do not use fake passes, temporary bypasses, or scientifically invalid shortcuts for core generation, validation, or solver behavior.
- Fix root causes with physically and architecturally defensible changes.

## 6. Canonical Model Stability

- Active canonical objects are `scenario_template`, `thermal_case`, and `thermal_solution`.
- New work should extend these contracts instead of inventing parallel active schemas without explicit approval.

## 7. Architecture Boundaries

- Keep repository boundaries visible at the root:
  - `core/`
  - `evaluation/`
  - `optimizers/`
  - `llm/`
  - `visualization/`
  - `scenarios/`
  - `tests/`
  - `docs/`
- `core/` owns schema, geometry, generator, solver, artifact I/O, contracts, and CLI.
- `core/` must not depend on `evaluation/`, `optimizers/`, `llm/`, or `visualization/`.
- `scenarios/` contains data, not business logic.
- The active implemented paper-facing classical optimizer baseline is plain `pymoo` `NSGA-II`.
- Do not quietly promote heuristic hybrid controllers or operator-pool experiments to the active mainline without an explicit approved plan.
- Future operator-pool or controller work should follow the algorithm-agnostic multi-backbone matrix direction rather than creating a new single-backbone hybrid path.

## 8. Legacy Cutover Protection

- Do not reintroduce the old demo stack as active runtime architecture.
- Legacy folders such as `src/`, `radiation_gen/`, `examples/`, and `states/` must not come back as active code paths without explicit approval.
- Reuse legacy ideas only by rewriting them into the new architecture.

## 9. Documentation Sync

- For major architecture, workflow, or contract changes, update in the same change set:
  - `README.md`
  - relevant files under `docs/`
  - `RULES.md` and `AGENTS.md` when repository guidance changes
- Do not leave contradictions between code, `README.md`, and active documentation.
- Active status sections in docs must reflect current truth, not stale plans.

## 10. Repository Hygiene and Generated Artifacts

- Remove temporary scripts, debug files, caches, and one-off intermediate outputs after validation when they are not part of the intended repository state.
- Human-authored source and docs stay in source and docs paths.
- Machine-generated runtime outputs belong in `scenario_runs/` or another explicitly designated output location, not in source folders.
- The canonical runtime root for active workflows is `scenario_runs/`.
- Prefer organizing generated inputs, solved case bundles, evaluation reports, and optimization bundles under `scenario_runs/` instead of scattering them across ad hoc top-level folders.
- Update `.gitignore` when new generated artifact classes appear.
- Do not manually edit generated artifacts to change conclusions; rerun instead.

## 11. Testing and Verification

- Maintained automated tests live under `tests/`.
- New features and bug fixes should add or update targeted tests with the implementation.
- Before claiming completion, run fresh relevant verification commands in the `msfenicsx` conda environment.

## 12. Evidence and Reproducibility

- Scientific or performance claims must identify the relevant template, case, solver profile, seed, and runtime path or artifact bundle.
- For multicase optimization claims, identify the operating cases and whether the evidence comes from one representative Pareto point or the Pareto set as a whole.
- If comparing future controller methods, keep the operator pool, repair, benchmark seeds, evaluation spec, and simulation budget matched unless the comparison is explicitly framed as a different experiment class.
- If comparing future backbone methods, keep benchmark source, evaluation spec, design-variable encoding, repair, and total expensive-evaluation budget matched unless the comparison is explicitly framed as a different experiment class.
- If something is not validated yet, label it as a hypothesis rather than a confirmed result.
- Comparative claims should use more than one seed unless the work is explicitly exploratory.

## 13. Negative Results and Failures

- Keep infeasible cases, failed solves, regressions, and anomalies visible in analysis instead of hiding them.
- Failure reasons and dominant violations are valid evidence and should be retained in reports or run artifacts when relevant.
