"""Aggregate CatBench results into parity plots and an Excel report.

After one or more calculators have been benchmarked on a dataset, this produces
the comparison artefacts CatBench generates (MAE, anomaly classification, parity
plots, Excel workbook). We point CatBench at the per-benchmark directory and
pass the calculator names explicitly so only our result folders are analysed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from catbench.adsorption import AdsorptionAnalysis

from .calculators import resolve_calculator_specs


def _discover_calculators(bench_dir: Path) -> list[str]:
    """Return calculator labels that have a results file under ``bench_dir``."""

    found: list[str] = []
    for child in sorted(bench_dir.iterdir()):
        if child.is_dir() and (child / f"{child.name}_result.json").exists():
            found.append(child.name)
    return found


def summary_csv_path(bench_dir: Path, name: str) -> Path:
    """Path of the flat per-model summary CSV (consumed by visualize.py)."""

    return bench_dir / f"{name}_summary.csv"


def export_summary_csv(bench_dir: Path, name: str) -> Path | None:
    """Flatten CatBench's ``MLIP_Data`` Excel sheet into a tidy summary CSV.

    CatBench writes its cross-model comparison to ``MLIP_Data`` in the xlsx
    report, but with a two-row header (the anomaly-rate breakdown columns are
    labelled on the first data row). We promote that sub-header into proper
    column names, drop the helper row, and save a flat CSV that downstream
    tools (``cli/visualize.py``) can read directly.
    """

    xlsx = bench_dir / f"{name}_Benchmarking_Analysis.xlsx"
    if not xlsx.exists():
        return None

    raw = pd.read_excel(xlsx, sheet_name="MLIP_Data")
    if raw.empty:
        return None

    # Row 0 names the anomaly-rate breakdown columns pandas saw as 'Unnamed: N'.
    sub_header = raw.iloc[0]
    renames: dict[str, str] = {}
    for col in raw.columns:
        if str(col).startswith("Unnamed"):
            label = str(sub_header[col]).strip()
            if label and label.lower() != "nan":
                renames[col] = f"Anomaly rate - {label} (%)"

    df = raw.drop(index=0).rename(columns=renames).reset_index(drop=True)
    df = df[df["MLIP_name"].notna()].reset_index(drop=True)

    # Convenience: time per step in seconds (matches catbench.org axis units).
    if "Time_per_step (ms)" in df.columns:
        df["Time_per_step (s)"] = pd.to_numeric(
            df["Time_per_step (ms)"], errors="coerce"
        ) / 1000.0

    out = summary_csv_path(bench_dir, name)
    df.to_csv(out, index=False)
    return out


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
        # Accept variant specs (e.g. "uma:task=oc22") and map them to labels.
        mlip_list = [job.label for job in resolve_calculator_specs(calculators)]
    else:
        mlip_list = list(calculators)

    if not mlip_list:
        raise RuntimeError(f"No calculator results to analyse under {bench_dir}")

    name = benchmarking_name or benchmark
    previous_cwd = Path.cwd()
    try:
        os.chdir(bench_dir)
        AdsorptionAnalysis(
            mlip_list=mlip_list,
            calculating_path=str(bench_dir),
            benchmarking_name=name,
            plot_enabled=plot_enabled,
        ).analysis()
    finally:
        os.chdir(previous_cwd)

    # Also emit a tidy CSV summary for downstream visualization.
    csv_path = export_summary_csv(bench_dir, name)
    if csv_path is not None:
        print(f"Summary CSV written: {csv_path}")

    return bench_dir
