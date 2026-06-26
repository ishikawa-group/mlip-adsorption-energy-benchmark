#!/usr/bin/env python3
"""Generate parity plots and the Excel report for a benchmarked dataset.

Run after one or more calculators have completed::

    python -m mlip_adsorption_energy_benchmark.cli.analyze --benchmark MamunHighT2019

(If the package is not installed, prefix with ``PYTHONPATH=src``.)

By default every calculator found under ``result/<benchmark>/`` is included.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import KNOWN_BENCHMARKS, analyze

# Repo root: .../src/mlip_adsorption_energy_benchmark/cli/analyze.py -> parents[3].
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESULT_DIR = REPO_ROOT / "result"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyse MLIP adsorption-energy benchmark results.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--benchmark",
        required=True,
        help="CatBench dataset name. Known: " + ", ".join(KNOWN_BENCHMARKS),
    )
    parser.add_argument(
        "--calculator",
        default=None,
        help="'all', comma-separated list, or omit to auto-detect.",
    )
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip parity-plot generation (Excel report only).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = analyze(
        args.benchmark,
        result_dir=args.result_dir,
        calculators=args.calculator,
        plot_enabled=not args.no_plot,
    )
    print(f"Analysis written under: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
