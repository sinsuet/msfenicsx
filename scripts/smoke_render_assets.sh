#!/usr/bin/env bash
# Smoke test: run raw/union/llm at 10×5 and verify outputs.
set -euo pipefail

SCENARIO_ROOT="./scenario_runs/s1_typical/smoke"
MODES=("raw" "union" "llm")

rm -rf "$SCENARIO_ROOT"

for mode in "${MODES[@]}"; do
    echo "=== smoke: $mode ==="
    conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
        --optimization-spec "scenarios/optimization/s1_typical_${mode}.yaml" \
        --output-root "${SCENARIO_ROOT}-${mode}" \
        --population-size 10 --num-generations 5 \
        --evaluation-workers 2
done

echo "=== verifying outputs ==="
for mode in "${MODES[@]}"; do
    run_dir="${SCENARIO_ROOT}-${mode}"
    for required in \
        "traces/evaluation_events.jsonl" \
        "traces/operator_trace.jsonl" \
        "analytics/hypervolume.csv" \
        "figures/hypervolume_progress.png" \
        "figures/hypervolume_progress.pdf" \
        "figures/operator_phase_heatmap.png" \
        "run.yaml"
    do
        if [[ ! -f "${run_dir}/${required}" ]]; then
            echo "MISSING: ${run_dir}/${required}"
            exit 1
        fi
    done
    echo "ok: ${mode}"
done

echo "=== all smokes passed ==="
