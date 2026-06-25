"""Aggregate CatBench results into parity plots and an Excel report.

After one or more calculators have been benchmarked on a dataset, this produces
the comparison artefacts CatBench generates (MAE, anomaly classification, parity
plots, Excel workbook). We point CatBench at the per-benchmark directory and
pass the calculator names explicitly so only our result folders are analysed.
"""

from __future__ import annotations

import os
from pathlib import Path

from catbench.adsorption import AdsorptionAnalysis

from .calculators import resolve_calculator_names


def _discover_calculators(bench_dir: Path) -> list[str]:
    """Return calculator names that have a results file under ``bench_dir``."""

    found: list[str] = []
    for child in sorted(bench_dir.iterdir()):
        if child.is_dir() and (child / f"{child.name}_result.json").exists():
            found.append(child.name)
    return found


def analyze(
    benchmark: str,
    *,
    result_dir: str | os.PathLike,
    calculators: str | list[str] | None = None,
    benchmarking_name: str | None = None,
    plot_enabled: bool = True,
) -> Path:
    """Run CatBench analysis for one benchmark; return its output directory.

    ``calculators`` may be ``"all"``, a comma-separated string, or a list. When
    omitted, every calculator folder found under ``result/<benchmark>/`` is used.
    """

    result_dir = Path(result_dir).resolve()
    bench_dir = result_dir / benchmark
    if not bench_dir.is_dir():
        raise FileNotFoundError(f"No results found for benchmark at {bench_dir}")

    if calculators is None:
        mlip_list = _discover_calculators(bench_dir)
    elif isinstance(calculators, str):
        mlip_list = resolve_calculator_names(calculators)
    else:
        mlip_list = list(calculators)

    if not mlip_list:
        raise RuntimeError(f"No calculator results to analyse under {bench_dir}")

    previous_cwd = Path.cwd()
    try:
        os.chdir(bench_dir)
        AdsorptionAnalysis(
            mlip_list=mlip_list,
            calculating_path=str(bench_dir),
            benchmarking_name=benchmarking_name or benchmark,
            plot_enabled=plot_enabled,
        ).analysis()
    finally:
        os.chdir(previous_cwd)

    return bench_dir
