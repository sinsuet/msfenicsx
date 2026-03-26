set -euo pipefail
source /home/hymn/miniconda3/etc/profile.d/conda.sh
conda activate msfenicsx
cd /home/hymn/msfenicsx
root=demo_runs/consistency_10x15_fullwindow_20260326
rm -rf "$root"
mkdir -p "$root"
for i in $(seq 1 10); do
  group=$(printf "group_%02d" "$i")
  echo "=== START ${group} ==="
  python examples/03_optimize_multicomponent_case.py \
    --state-path states/baseline_multicomponent.yaml \
    --runs-root "$root/$group" \
    --real-llm \
    --max-iters 15 \
    --max-invalid-proposals 15 \
    --continue-when-feasible
  echo "=== END ${group} ==="
done