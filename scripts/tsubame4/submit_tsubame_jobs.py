#!/usr/bin/env python3
"""Submit TSUBAME4 jobs for MLIP adsorption-energy benchmarks.

One SGE job is submitted per (benchmark, calculator) pair, so all calculators
run in parallel on separate GPUs.

Example (the intended workflow)::

    python scripts/tsubame4/submit_tsubame_jobs.py \
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
    resolve_calculator_specs,
    spec_to_string,
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
        "--calculator-factory",
        default=None,
        metavar="MODULE:CALLABLE",
        help="Arbitrary ASE Calculator factory; mutually exclusive with --calculator.",
    )
    parser.add_argument(
        "--factory-kwargs-json",
        default=None,
        help="Factory keyword arguments as a JSON object or @path/to/file.json.",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Result/job label required with --calculator-factory.",
    )
    parser.add_argument(
        "--calculator",
        default=None,
        help=(
            "'all' or comma-separated calculator specs "
            "'<preset>[:key=value;...]' (key in model/task/modal). "
            "Each spec becomes its own job and result folder, e.g. "
            "'sevennet:modal=omat24,uma:task=oc22'."
        ),
    )
    parser.add_argument("--device", default="cuda", choices=["auto", "cpu", "cuda", "mps"])
    parser.add_argument("--n-seeds", type=int, default=1)
    parser.add_argument("--mode", default="basic")
    parser.add_argument("--model", default=None, help="Override preset model name.")
    parser.add_argument("--task", default=None, help="Override UMA/fairchem task.")
    parser.add_argument("--modal", default=None, help="Override SevenNet modal.")
    parser.add_argument("--dispersion", action="store_true")
    parser.add_argument(
        "--cueq",
        action="store_true",
        help=(
            "Enable CuEquivariance (SevenNet only). Results are saved under a "
            "separate '<label>-cueq' folder and the jobs are named accordingly, "
            "so they never overwrite the non-cueq runs."
        ),
    )
    parser.add_argument(
        "--save-files",
        action="store_true",
        help=(
            "Write per-structure log/traj files. OFF by default: on large "
            "datasets these create tens of thousands of files per job and can "
            "exhaust the group-shared inode quota on Lustre."
        ),
    )
    parser.add_argument(
        "--rerun-completed",
        action="store_true",
        help=(
            "Also (re)submit calculators whose final <label>_result.json already "
            "exists. Default: skip them, so a re-submission only resumes the jobs "
            "that timed out (CatBench auto-resumes from structure_cache.json)."
        ),
    )
    parser.add_argument("--group", default=TSUBAME_GROUP, help="TSUBAME4 group (-g).")
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--dry-run", action="store_true", help="Print qsub commands only.")
    args = parser.parse_args()
    if args.calculator_factory and args.calculator:
        parser.error("--calculator-factory and --calculator are mutually exclusive")
    if args.calculator_factory and not args.label:
        parser.error("--label is required with --calculator-factory")
    if args.calculator_factory and any(
        (args.model, args.task, args.modal, args.dispersion, args.cueq)
    ):
        parser.error(
            "preset overrides/--dispersion/--cueq are not valid with "
            "--calculator-factory; use --factory-kwargs-json"
        )
    if not args.calculator_factory and args.factory_kwargs_json:
        parser.error("--factory-kwargs-json requires --calculator-factory")
    if not args.calculator_factory and args.label:
        parser.error("--label is only valid with --calculator-factory")
    if not args.calculator_factory and args.calculator is None:
        args.calculator = "all"
    return args


def main() -> int:
    args = parse_args()
    if not os.path.exists(RUN_SCRIPT):
        print(f"Error: run script not found: {RUN_SCRIPT}", file=sys.stderr)
        return 1

    benchmarks = _parse_benchmarks(args.benchmark)
    jobs = (
        [None]
        if args.calculator_factory
        else list(resolve_calculator_specs(args.calculator))
    )
    result_dir = Path(args.result_dir).resolve()
    data_dir = Path(args.data_dir).resolve()

    print(f"Project     : {PROJECT_DIR}")
    print(f"Run script  : {RUN_SCRIPT}")
    print(f"Benchmarks  : {', '.join(benchmarks)}")
    if args.calculator_factory:
        print(f"Factory     : {args.calculator_factory}")
        print(f"Label       : {args.label}")
    else:
        print(f"Calculators : {', '.join(j.label for j in jobs if j is not None)}")
    print(f"Device      : {args.device}")
    print(f"CuEquivar.  : {bool(args.cueq)} (label suffix '-cueq')")
    print(f"Dispersion  : {bool(args.dispersion)} (D3, label suffix '-d3')")
    print(f"Save files  : {bool(args.save_files)} (per-structure log/traj)")
    print(f"Group       : {args.group}")
    print(f"Result dir  : {result_dir}")
    print(f"Data dir    : {data_dir}")
    print(f"Total jobs  : {len(benchmarks) * len(jobs)}")
    print(f"Skip done   : {not args.rerun_completed}")
    print()

    submitted = 0
    skipped = 0
    for benchmark in benchmarks:
        for job in jobs:
            # One job per (benchmark, calculator variant). The spec string is
            # passed through CALCULATOR so the run script reproduces this exact
            # variant; the label keys the job name and result folder.
            spec = spec_to_string(job) if job is not None else ""
            # Distinct identity per variant: '-cueq' (CuEquivariance) and/or
            # '-d3' (dispersion) suffixes so these never clash with plain runs.
            label = (
                args.label
                if job is None
                else job.label
                + ("-cueq" if args.cueq else "")
                + ("-d3" if args.dispersion else "")
            )
            assert label is not None

            # Resume safety: a finished run has been relocated to
            # result/<benchmark>/<label>/<label>_result.json. Skip it so a
            # re-submission only resumes/finishes the jobs that timed out
            # (CatBench auto-resumes those from their structure_cache.json).
            final_result = result_dir / benchmark / label / f"{label}_result.json"
            if final_result.exists() and not args.rerun_completed:
                print(f"Skipping (already completed): {benchmark} / {label}")
                skipped += 1
                continue

            job_name = f"mlipads_{benchmark}_{label}"[:120]
            log_dir = result_dir / benchmark / "log" / "tsubame_jobs" / label
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
            if args.calculator_factory:
                env["CALCULATOR_FACTORY"] = str(args.calculator_factory)
                env["FACTORY_KWARGS_JSON"] = str(args.factory_kwargs_json or "")
                env["LABEL"] = label
                env.pop("CALCULATOR", None)
            else:
                env["CALCULATOR"] = spec
                env.pop("CALCULATOR_FACTORY", None)
                env.pop("FACTORY_KWARGS_JSON", None)
                env.pop("LABEL", None)
            env["DEVICE"] = str(args.device)
            env["N_SEEDS"] = str(int(args.n_seeds))
            env["MODE"] = str(args.mode)
            env["DISPERSION"] = "true" if args.dispersion else "false"
            env["CUEQ"] = "true" if args.cueq else "false"
            env["SAVE_FILES"] = "true" if args.save_files else "false"
            env["RESULT_DIR"] = str(result_dir)
            env["DATA_DIR"] = str(data_dir)
            # Global overrides only used as a fallback when the spec sets none.
            for key, val in (("MODEL", args.model), ("TASK", args.task), ("MODAL", args.modal)):
                if val:
                    env[key] = str(val)
                else:
                    env.pop(key, None)

            identity = args.calculator_factory or spec
            print(f"Submitting: {benchmark} / {identity} (job={job_name})")
            if args.dry_run:
                print("  Command:", " ".join(cmd))
                print(
                    "  Env    : PROJECT_DIR, BENCHMARK, CALCULATOR or "
                    "CALCULATOR_FACTORY+LABEL, DEVICE, N_SEEDS, "
                    "MODE, [MODEL], [TASK], [MODAL], DISPERSION, CUEQ, SAVE_FILES, "
                    "RESULT_DIR, DATA_DIR"
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

    print(f"\nSubmitted jobs: {submitted}  (skipped completed: {skipped})")
    if args.dry_run:
        print("(dry-run mode; no jobs actually submitted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
