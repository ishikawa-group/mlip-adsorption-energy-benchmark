#!/usr/bin/env python3
"""Generate parity plots and the Excel report for a benchmarked dataset.

Run after one or more calculators have completed::

    python code/analyze.py --benchmark MamunHighT2019

By default every calculator found under ``result/<benchmark>/`` is included.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from mlip_adsorption_energy_benchmark import KNOWN_BENCHMARKS, analyze  # noqa: E402

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
