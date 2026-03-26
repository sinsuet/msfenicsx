#!/usr/bin/env bash
set -euo pipefail

# Compile from the repository root so the relative image paths inside
# slides/demo_workflow_beamer.tex keep working, while all build outputs stay in
# slides/.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEXLIVE_BIN="/home/hymn/latex/texlive/bin/x86_64-linux"
MAIN_TEX="slides/demo_workflow_beamer.tex"

if [[ ! -x "${TEXLIVE_BIN}/latexmk" ]]; then
  echo "latexmk not found in ${TEXLIVE_BIN}" >&2
  exit 1
fi

export PATH="${TEXLIVE_BIN}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "${ROOT_DIR}"
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=slides "${MAIN_TEX}"
