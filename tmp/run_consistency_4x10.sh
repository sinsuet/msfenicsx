set -euo pipefail
source /home/hymn/miniconda3/etc/profile.d/conda.sh
conda activate msfenicsx
cd /home/hymn/msfenicsx
root=demo_runs/consistency_4x10_20260326
mkdir -p "$root"
for i in 1 2 3 4; do
  group=$(printf "group_%02d" "$i")
  echo "=== START ${group} ==="
  python examples/03_optimize_multicomponent_case.py \
    --state-path states/baseline_multicomponent.yaml \
    --runs-root "$root/$group" \
    --real-llm \
    --max-iters 10 \
    --continue-when-feasible
  echo "=== END ${group} ==="
done