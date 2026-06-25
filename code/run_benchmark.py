#!/usr/bin/env python3
"""Run an MLIP adsorption-energy benchmark.

Examples
--------
Run a single calculator on one dataset (CPU)::

    python code/run_benchmark.py --benchmark BM_dataset --calculator chgnet --device cpu

Run every calculator on a dataset (sequential; mainly for local use --
on a cluster prefer one job per calculator via script/tsubame4/)::

    python code/run_benchmark.py --benchmark MamunHighT2019 --calculator all --device cuda

Output is written to ``result/<benchmark>/<calculator>/``.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# Make ``src/`` importable when run directly (no install needed).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from mlip_adsorption_energy_benchmark import (  # noqa: E402
    KNOWN_BENCHMARKS,
    resolve_calculator_specs,
    run_adsorption_benchmark,
)

DEFAULT_RESULT_DIR = REPO_ROOT / "result"
DEFAULT_DATA_DIR = REPO_ROOT / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark MLIP calculators on adsorption-energy datasets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--benchmark",
        required=True,
        help="CatBench dataset name. Known: " + ", ".join(KNOWN_BENCHMARKS),
    )
    parser.add_argument(
        "--calculator",
        default="all",
        help=(
            "'all' or a comma-separated list of calculator specs "
            "'<preset>[:key=value;...]' where key is model/task/modal "
            "(e.g. 'uma:task=oc22,sevennet:modal=omat24')."
        ),
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="Compute device passed to the MLIP backend.",
    )
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=1,
        help="Reproducibility seeds (1 = ~3x faster; use >1 to measure run-to-run spread).",
    )
    parser.add_argument("--model", default=None, help="Override preset model name.")
    parser.add_argument("--task", default=None, help="Override UMA/fairchem task.")
    parser.add_argument("--modal", default=None, help="Override SevenNet modal.")
    parser.add_argument(
        "--dispersion",
        action="store_true",
        help="Enable D3 dispersion (for backends that support it).",
    )
    parser.add_argument(
        "--cueq",
        action="store_true",
        help=(
            "Enable CuEquivariance acceleration (SevenNet only). Results are "
            "saved under a separate '<label>-cueq' folder so they do not clash "
            "with the non-cueq runs."
        ),
    )
    parser.add_argument("--f-crit-relax", type=float, default=0.05, help="Force crit (eV/A).")
    parser.add_argument("--n-crit-relax", type=int, default=999, help="Max relax steps.")
    parser.add_argument(
        "--mode",
        default="basic",
        help="CatBench mode: 'basic' (relaxation) or 'oc20' (direct energy).",
    )
    parser.add_argument(
        "--no-save-files",
        action="store_true",
        help="Do not write trajectory/log files (saves disk).",
    )
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    jobs = resolve_calculator_specs(args.calculator)

    print("==== MLIP adsorption-energy benchmark ====")
    print(f"Benchmark   : {args.benchmark}")
    print(f"Calculators : {', '.join(j.label for j in jobs)}")
    print(f"Device      : {args.device}")
    print(f"Seeds       : {args.n_seeds}")
    print(f"Mode        : {args.mode}")
    print(f"Result dir  : {args.result_dir}")
    print(f"Data dir    : {args.data_dir}")
    print()

    failures = 0
    for job in jobs:
        # Spec overrides take precedence; fall back to global CLI overrides.
        model = job.overrides.get("model", args.model)
        task = job.overrides.get("task", args.task)
        modal = job.overrides.get("modal", args.modal)
        # Distinct output folder per variant: '-cueq' and/or '-d3' suffixes so
        # CuEquivariance and dispersion-corrected runs never clash with plain runs.
        label = job.label + ("-cueq" if args.cueq else "") + ("-d3" if args.dispersion else "")
        print(f"---- Running: {args.benchmark} / {label} ----", flush=True)
        try:
            out = run_adsorption_benchmark(
                args.benchmark,
                job.preset,
                label=label,
                device=args.device,
                n_seeds=args.n_seeds,
                result_dir=args.result_dir,
                data_dir=args.data_dir,
                model=model,
                task=task,
                modal=modal,
                dispersion=args.dispersion,
                enable_cueq=args.cueq,
                f_crit_relax=args.f_crit_relax,
                n_crit_relax=args.n_crit_relax,
                mode=args.mode,
                save_files=not args.no_save_files,
            )
            print(f"  -> done: {out}", flush=True)
        except Exception:  # keep going for the remaining calculators
            failures += 1
            print(f"  -> FAILED for calculator {label!r}:", file=sys.stderr)
            traceback.print_exc()

    if failures:
        print(f"\nCompleted with {failures} failure(s).", file=sys.stderr)
        return 1
    print("\nAll requested calculations finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
