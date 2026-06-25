#!/usr/bin/env python3
"""Submit TSUBAME4 jobs for MLIP adsorption-energy benchmarks.

One SGE job is submitted per (benchmark, calculator) pair, so all calculators
run in parallel on separate GPUs.

Example (the intended workflow)::

    python script/tsubame4/submit_tsubame_jobs.py \
        --benchmark MamunHighT2019,ComerGeneralized2024 \
        --calculator all

Add ``--dry-run`` to print the qsub commands without submitting.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RUN_SCRIPT = str((SCRIPT_DIR / "run_tsubame_benchmark.sh").resolve())
PROJECT_DIR = SCRIPT_DIR.parent.parent.resolve()

sys.path.insert(0, str(PROJECT_DIR / "src"))
from mlip_adsorption_energy_benchmark import (  # noqa: E402
    KNOWN_BENCHMARKS,
    resolve_calculator_names,
)

DEFAULT_RESULT_DIR = (PROJECT_DIR / "result").resolve()
DEFAULT_DATA_DIR = (PROJECT_DIR / "data").resolve()

# TSUBAME4 group (matches the lab's other submission scripts).
TSUBAME_GROUP = "tga-ishikawalab"


def _parse_benchmarks(value: str) -> list[str]:
    raw = str(value).strip()
    if not raw or raw.lower() == "all":
        return list(KNOWN_BENCHMARKS)
    out: list[str] = []
    for part in raw.split(","):
        name = part.strip()
        if name and name not in out:
            out.append(name)
    if not out:
        raise argparse.ArgumentTypeError("--benchmark must be 'all' or a comma list.")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit per-(benchmark, calculator) TSUBAME4 jobs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--benchmark",
        default="all",
        help="'all' or comma-separated dataset names: " + ", ".join(KNOWN_BENCHMARKS),
    )
    parser.add_argument(
        "--calculator",
        default="all",
        help="'all' or comma-separated calculator presets.",
    )
    parser.add_argument("--device", default="cuda", choices=["auto", "cpu", "cuda", "mps"])
    parser.add_argument("--n-seeds", type=int, default=3)
    parser.add_argument("--mode", default="basic")
    parser.add_argument("--model", default=None, help="Override preset model name.")
    parser.add_argument("--task", default=None, help="Override UMA/fairchem task.")
    parser.add_argument("--modal", default=None, help="Override SevenNet modal.")
    parser.add_argument("--dispersion", action="store_true")
    parser.add_argument("--group", default=TSUBAME_GROUP, help="TSUBAME4 group (-g).")
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--dry-run", action="store_true", help="Print qsub commands only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not os.path.exists(RUN_SCRIPT):
        print(f"Error: run script not found: {RUN_SCRIPT}", file=sys.stderr)
        return 1

    benchmarks = _parse_benchmarks(args.benchmark)
    calculators = resolve_calculator_names(args.calculator)
    result_dir = Path(args.result_dir).resolve()
    data_dir = Path(args.data_dir).resolve()

    print(f"Project     : {PROJECT_DIR}")
    print(f"Run script  : {RUN_SCRIPT}")
    print(f"Benchmarks  : {', '.join(benchmarks)}")
    print(f"Calculators : {', '.join(calculators)}")
    print(f"Device      : {args.device}")
    print(f"Group       : {args.group}")
    print(f"Result dir  : {result_dir}")
    print(f"Data dir    : {data_dir}")
    print(f"Total jobs  : {len(benchmarks) * len(calculators)}")
    print()

    submitted = 0
    for benchmark in benchmarks:
        for calculator in calculators:
            job_name = f"mlipads_{benchmark}_{calculator}"[:120]
            log_dir = result_dir / benchmark / "log" / "tsubame_jobs" / calculator
            stdout_log = log_dir / f"{job_name}_stdout.log"
            stderr_log = log_dir / f"{job_name}_stderr.log"
            if not args.dry_run:
                log_dir.mkdir(parents=True, exist_ok=True)

            cmd = [
                "qsub",
                "-V",
                "-g",
                args.group,
                "-o",
                str(stdout_log),
                "-e",
                str(stderr_log),
                "-N",
                job_name,
                RUN_SCRIPT,
            ]

            env = os.environ.copy()
            env["PROJECT_DIR"] = str(PROJECT_DIR)
            env["BENCHMARK"] = benchmark
            env["CALCULATOR"] = calculator
            env["DEVICE"] = str(args.device)
            env["N_SEEDS"] = str(int(args.n_seeds))
            env["MODE"] = str(args.mode)
            env["DISPERSION"] = "true" if args.dispersion else "false"
            env["RESULT_DIR"] = str(result_dir)
            env["DATA_DIR"] = str(data_dir)
            for key, val in (("MODEL", args.model), ("TASK", args.task), ("MODAL", args.modal)):
                if val:
                    env[key] = str(val)
                else:
                    env.pop(key, None)

            print(f"Submitting: {benchmark} / {calculator} (job={job_name})")
            if args.dry_run:
                print("  Command:", " ".join(cmd))
                print(
                    "  Env    : PROJECT_DIR, BENCHMARK, CALCULATOR, DEVICE, N_SEEDS, "
                    "MODE, [MODEL], [TASK], [MODAL], DISPERSION, RESULT_DIR, DATA_DIR"
                )
                submitted += 1
                continue

            try:
                res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            except Exception as exc:  # noqa: BLE001
                print(f"  -> Exception while submitting: {exc}", file=sys.stderr)
                continue

            if res.returncode == 0:
                print(f"  -> submitted: {res.stdout.strip()}")
                submitted += 1
            else:
                print(f"  -> submit failed: {res.stderr.strip()}", file=sys.stderr)

    print(f"\nSubmitted jobs: {submitted}")
    if args.dry_run:
        print("(dry-run mode; no jobs actually submitted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
