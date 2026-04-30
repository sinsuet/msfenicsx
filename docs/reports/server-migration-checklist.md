# 共享服务器迁移 Checklist

本文档记录将 `msfenicsx` 迁移到共享服务器并运行 S5-S7 benchmark 矩阵前的推荐流程。目标是让代码、conda 环境、Git 身份、LLM credentials 和大型运行产物彼此隔离，避免误用共享服务器上的他人配置。

## 推荐原则

- 优先在服务器上 `git clone` 仓库，而不是直接复制整个本地工作目录。
- 在仓库内使用 repo-local Git config，避免依赖服务器全局 `~/.gitconfig`。
- 服务器上单独创建同名 conda 环境 `msfenicsx`。
- 服务器上手工创建 `.env`，不要通过 Git、公共目录或聊天记录传递密钥。
- 正式矩阵运行前先跑 focused tests 和 `M0_pilot_512eval`。
- 不把 `scenario_runs/`、`.env`、cache 和临时输出纳入 Git。

## 1. Clone 代码

```bash
mkdir -p /path/to/your/workspace
cd /path/to/your/workspace
git clone <your-repo-url> msfenicsx
cd msfenicsx
```

如果只能复制目录，必须包含 `.git/` 才能保留 Git 历史；复制后仍需执行下面的 Git 身份检查。

## 2. 设置 repo-local Git 身份

在服务器仓库目录内执行：

```bash
git config --local user.name "sinsuet"
git config --local user.email "759089797@qq.com"
```

检查配置来源：

```bash
git config --list --show-origin --show-scope | grep -E 'user.name|user.email'
```

期望看到 `local file:.git/config` 来源，而不是只看到 `global file:~/.gitconfig`。

## 3. 隔离 Git 凭据

如果服务器是多人共用同一个 Linux 用户，不要使用他人的全局 credential store。可以在本 repo 禁用 credential helper：

```bash
git config --local credential.helper ""
```

推荐使用自己的 SSH key，并把 key 限定在当前 repo：

```bash
git remote set-url origin git@github.com:<owner>/<repo>.git
git config --local core.sshCommand "ssh -i ~/.ssh/id_ed25519_msfenicsx -o IdentitiesOnly=yes"
```

检查：

```bash
git config --local --get core.sshCommand
git fetch origin
```

## 4. 创建或更新 conda 环境

### 已经有 `msfenicsx` 环境时

如果服务器上已经创建并激活了 `msfenicsx` 环境，推荐使用仓库内的分层 requirements 一键安装：

```bash
conda activate msfenicsx
conda install -c conda-forge --file requirements-conda.txt
yes | python -m pip install -r requirements-pip.txt
```

如果服务器有 `mamba`，优先用：

```bash
conda activate msfenicsx
mamba install -c conda-forge --file requirements-conda.txt
yes | python -m pip install -r requirements-pip.txt
```

`requirements-conda.txt` 放 FEniCSx/PETSc/MPI 和科学计算依赖；`requirements-pip.txt` 只放 pip-only 依赖，并使用 `-e . --no-deps` 安装本项目。这样可以避免 `pip install -e .` 读取 `pyproject.toml` 后尝试从 PyPI 编译 `petsc4py/PETSc`。不要把 `fenics-dolfinx`、`petsc4py`、`mpi4py` 这类包改成 pip-only 安装。

### 从零创建环境时

如果仓库中已有 `environment.yml`：

```bash
conda env create -f environment.yml
conda activate msfenicsx
```

如果环境已经存在：

```bash
conda env update -n msfenicsx -f environment.yml --prune
conda activate msfenicsx
```

如果服务器没有 `conda` 但有 `mamba`，优先使用：

```bash
mamba env create -f environment.yml
```

环境文件已经包含 editable install：

```yaml
- pip:
    - -e .
```

因此正常 `conda env create -f environment.yml` 后不需要重复执行 `python -m pip install -e .`。如果你临时手工创建环境、没有使用 `environment.yml`，再在仓库内执行：

```bash
python -m pip install -e .
```

## 5. 配置 `.env`

服务器上手工创建：

```bash
cp .env.example .env
chmod 600 .env
```

填入需要的 provider credentials：

```text
GPT_PROXY_API_KEY=...
GPT_PROXY_BASE_URL=...
QWEN_PROXY_API_KEY=...
QWEN_PROXY_BASE_URL=...
DEEPSEEK_PROXY_API_KEY=...
DEEPSEEK_PROXY_BASE_URL=...
GEMMA4_API_KEY=...
GEMMA4_BASE_URL=...
```

确认 `.env` 不会被 Git 跟踪：

```bash
git check-ignore -v .env
git status --short .env
```

## 6. 基础验证

先确认 Python package 可导入：

```bash
python - <<'PY'
import core
import evaluation
import optimizers
import llm
print('imports ok')
PY
```

运行聚焦测试。不要一开始就跑全仓测试；如果需要扩大验证范围，先确认服务器资源和时间预算。

```bash
pytest -v tests/optimizers/test_llm_client.py
```

如果 benchmark matrix 功能已经实现，运行对应的 matrix 聚焦测试：

```bash
pytest -v \
  tests/optimizers/test_matrix_specs.py \
  tests/optimizers/test_matrix_config.py \
  tests/optimizers/test_matrix_spec_snapshots.py \
  tests/optimizers/test_matrix_index.py \
  tests/optimizers/test_matrix_runner.py \
  tests/optimizers/test_matrix_aggregate.py \
  tests/optimizers/test_matrix_figures.py \
  tests/optimizers/test_matrix_representatives.py
```

## 7. M0 pilot

正式 S5-S7 512eval 矩阵前，先跑 `M0_pilot_512eval`。pilot 应检查：

- spec snapshots 是否正确写入 `replicate_seed`、`benchmark_source.seed` 和 `algorithm.seed`。
- profile resolution 是否正确，特别是 `gpt_5_4`、`default` 和 `gpt`。
- trace output、rendering 和 aggregation 是否完整。
- CPU utilization、memory、disk IO wait、wall time、timeout rate、PDE failures、LLM retry/fallback counts 和 render failures。
- Gemma4 本地服务 latency、timeout、fallback、显存/内存压力是否稳定。

## 8. 正式矩阵运行顺序

建议按 block 分批运行：

```text
M1_raw_backbone_512eval
M2_nsga2_union_512eval
M3a_llm_gpt_5_4_512eval
M3b_llm_qwen3_6_plus_512eval
M3c_llm_glm_5_512eval
M3d_llm_minimax_m2_5_512eval
M3e_llm_deepseek_v4_flash_512eval
M3f_llm_gemma4_512eval
M4_rerun_failed_512eval
M5_aggregate_visualize_512eval
```

不要同时运行多个高 worker blocks，除非确认全局 worker budget 仍在服务器安全范围内。

## 9. 迁移前后检查清单

迁移前本地检查：

```bash
git status --short
git log --oneline -5
git check-ignore -v .env scenario_runs
```

服务器上检查：

```bash
git status --short
git remote -v
git config --list --show-origin --show-scope | grep -E 'user.name|user.email|credential|core.sshCommand'
conda env list | grep msfenicsx
python -m pip show msfenicsx
```

正式运行前记录：

```bash
git rev-parse HEAD
git status --short
python --version
python -m pip freeze > scenario_runs/server_pip_freeze.txt
```

`scenario_runs/` 被 `.gitignore` 排除，环境记录文件用于运行现场留档，不应提交到仓库。
