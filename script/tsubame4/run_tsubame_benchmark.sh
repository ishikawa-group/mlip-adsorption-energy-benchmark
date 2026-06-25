#!/bin/bash
#$ -cwd
#$ -l gpu_h=1
#$ -l h_rt=24:00:00

# One TSUBAME4 job = one (benchmark, calculator) adsorption-energy run.
# Configuration is passed through environment variables (see submit script).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"

if [ -z "${BENCHMARK:-}" ]; then
  echo "Error: BENCHMARK is not set" >&2
  exit 1
fi
if [ -z "${CALCULATOR:-}" ]; then
  echo "Error: CALCULATOR is not set" >&2
  exit 1
fi

DEVICE="${DEVICE:-cuda}"
N_SEEDS="${N_SEEDS:-3}"
MODE="${MODE:-basic}"
F_CRIT_RELAX="${F_CRIT_RELAX:-0.05}"
N_CRIT_RELAX="${N_CRIT_RELAX:-999}"
MODEL="${MODEL:-}"
TASK="${TASK:-}"
MODAL="${MODAL:-}"
DISPERSION="${DISPERSION:-false}"
RESULT_DIR="${RESULT_DIR:-${PROJECT_DIR}/result}"
DATA_DIR="${DATA_DIR:-${PROJECT_DIR}/data}"

echo "==== MLIP adsorption-energy benchmark (TSUBAME4) ===="
echo "PROJECT_DIR : ${PROJECT_DIR}"
echo "BENCHMARK   : ${BENCHMARK}"
echo "CALCULATOR  : ${CALCULATOR}"
echo "DEVICE      : ${DEVICE}"
echo "N_SEEDS     : ${N_SEEDS}"
echo "MODE        : ${MODE}"
echo "MODEL       : ${MODEL:-(preset default)}"
echo "TASK        : ${TASK:-(preset default)}"
echo "MODAL       : ${MODAL:-(preset default)}"
echo "DISPERSION  : ${DISPERSION}"
echo "RESULT_DIR  : ${RESULT_DIR}"
echo "DATA_DIR    : ${DATA_DIR}"
echo "Start time  : $(date)"

if command -v module >/dev/null 2>&1; then
  module purge
  module load cuda || true
fi

if [ -f "${PROJECT_DIR}/.venv/bin/activate" ]; then
  source "${PROJECT_DIR}/.venv/bin/activate"
fi

export PYTHONPATH="${PROJECT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
export MPLBACKEND=Agg
unset DISPLAY || true

CMD=(python -u "${PROJECT_DIR}/code/run_benchmark.py"
  --benchmark "${BENCHMARK}"
  --calculator "${CALCULATOR}"
  --device "${DEVICE}"
  --n-seeds "${N_SEEDS}"
  --mode "${MODE}"
  --f-crit-relax "${F_CRIT_RELAX}"
  --n-crit-relax "${N_CRIT_RELAX}"
  --result-dir "${RESULT_DIR}"
  --data-dir "${DATA_DIR}"
)

if [ -n "${MODEL}" ]; then
  CMD+=(--model "${MODEL}")
fi
if [ -n "${TASK}" ]; then
  CMD+=(--task "${TASK}")
fi
if [ -n "${MODAL}" ]; then
  CMD+=(--modal "${MODAL}")
fi
if [ "${DISPERSION}" = "true" ] || [ "${DISPERSION}" = "1" ]; then
  CMD+=(--dispersion)
fi

echo "Command: ${CMD[*]}"
"${CMD[@]}"

echo "Done at $(date)"
