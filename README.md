# msfenicsx Clean Rebuild (Phase 1)

This repository is being rebuilt from a clean baseline for Phase 1. Legacy demo code can coexist during transition, but new work should align with the clean architecture boundaries below.

## Top-Level Module Boundaries

- `core/`: runtime kernel and CLI surface (`core/cli/`)
- `evaluation/`: metrics, scoring, and benchmark execution
- `optimizers/`: optimization strategies and orchestration
- `llm/`: LLM adapters, prompting, and model-facing workflows
- `visualization/`: plotting, rendering, and reporting surfaces

## Rebuild-Oriented Repository Structure

Phase 1 is organized around these top-level areas:

- `core/`
- `evaluation/`
- `optimizers/`
- `llm/`
- `visualization/`
- `scenarios/`
- `scenario_runs/`
- `tests/`
- `docs/`

`scenario_runs/` is intended for generated run outputs and is ignored by git.

