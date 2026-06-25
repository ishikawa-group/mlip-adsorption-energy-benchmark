#!/usr/bin/env python3
"""Visualize an adsorption-energy benchmark, catbench.org-style.

Reads the per-model summary CSV produced by ``code/analyze.py`` and renders:

1. A **metric heatmap-table** (one row per model, one column per metric). Each
   column is colored independently with the *viridis* colormap so brighter =
   better; the raw value is printed in every cell.
2. **Pareto scatter plots** of accuracy / robustness versus cost:
   - Accuracy-Efficiency : Time per step (s) vs Normal MAE (eV)
   - Robustness-Efficiency: Time per step (s) vs Normal rate (%)

Both static figures (matplotlib, PNG + PDF) and an interactive HTML dashboard
(plotly) are written.

Run ``code/analyze.py --benchmark <name>`` first so the summary CSV exists.

Example
-------
    python code/visualize.py --benchmark ComerGeneralized2024
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm
from matplotlib.colors import Normalize

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from mlip_adsorption_energy_benchmark import KNOWN_BENCHMARKS  # noqa: E402
from mlip_adsorption_energy_benchmark.analysis import summary_csv_path  # noqa: E402

DEFAULT_RESULT_DIR = REPO_ROOT / "result"

# ---------------------------------------------------------------------------
# Metric definitions (catbench.org-style). "higher_is_better" controls the
# viridis direction so that bright always means "good".
# ---------------------------------------------------------------------------
# (column name in the summary CSV, short display label, higher_is_better)
METRIC_SPECS: list[tuple[str, str, bool]] = [
    ("MAE_total (eV)", "MAE total (eV)", False),
    ("MAE_normal (eV)", "MAE normal (eV)", False),
    ("MAE_single (eV)", "MAE single (eV)", False),
    ("Normal rate (%)", "Normal (%)", True),
    ("Adsorbate migration rate (%)", "Migration (%)", False),
    ("Anomaly rate (%)", "Anomaly (%)", False),
    ("Anomaly rate - reproduction failure (%)", "Reprod. fail (%)", False),
    ("Anomaly rate - unphysical relaxation (%)", "Unphys. relax (%)", False),
    ("Anomaly rate - energy anomaly (%)", "Energy anom. (%)", False),
    ("ADwT (%)", "ADwT (%)", True),
    ("AMDwT (%)", "AMDwT (%)", True),
    ("Time_per_step (s)", "Time/step (s)", False),
]


def load_summary(csv_path: Path) -> pd.DataFrame:
    """Load the summary CSV and coerce metric columns to numbers."""

    df = pd.read_csv(csv_path)
    if "MLIP_name" not in df.columns:
        raise ValueError(f"{csv_path} has no 'MLIP_name' column.")
    for col, _, _ in METRIC_SPECS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _accuracy_column(df: pd.DataFrame) -> str:
    """Prefer MAE_normal for ranking/plots; fall back to MAE_total."""

    if "MAE_normal (eV)" in df.columns and df["MAE_normal (eV)"].notna().any():
        return "MAE_normal (eV)"
    return "MAE_total (eV)"


def _present_metrics(df: pd.DataFrame) -> list[tuple[str, str, bool]]:
    """Metric specs whose column exists and has at least one value."""

    out = []
    for col, label, hib in METRIC_SPECS:
        if col in df.columns and df[col].notna().any():
            out.append((col, label, hib))
    return out


def _normalize_good(values: np.ndarray, higher_is_better: bool) -> np.ndarray:
    """Map a column to [0, 1] where 1 = best (for viridis brightness)."""

    v = values.astype(float)
    finite = v[np.isfinite(v)]
    if finite.size == 0:
        return np.full_like(v, np.nan)
    lo, hi = float(np.min(finite)), float(np.max(finite))
    if hi == lo:
        norm = np.where(np.isfinite(v), 0.5, np.nan)
    else:
        norm = (v - lo) / (hi - lo)
    if not higher_is_better:
        norm = 1.0 - norm
    return norm


# ---------------------------------------------------------------------------
# Static (matplotlib) outputs
# ---------------------------------------------------------------------------
def heatmap_matplotlib(df: pd.DataFrame, metrics, out_base: Path) -> None:
    models = df["MLIP_name"].astype(str).tolist()
    n_rows, n_cols = len(models), len(metrics)

    norm = np.full((n_rows, n_cols), np.nan)
    raw = np.full((n_rows, n_cols), np.nan)
    for j, (col, _, hib) in enumerate(metrics):
        raw[:, j] = df[col].to_numpy(dtype=float)
        norm[:, j] = _normalize_good(raw[:, j], hib)

    fig_w = max(8.0, 1.05 * n_cols + 3.0)
    fig_h = max(3.0, 0.5 * n_rows + 2.0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="#dddddd")
    im = ax.imshow(np.ma.masked_invalid(norm), cmap=cmap, aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels([m[1] for m in metrics], rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(models, fontsize=8)
    ax.set_title("Benchmark metrics (viridis: bright = better, per column)", fontsize=10)

    sm = cm.ScalarMappable(norm=Normalize(0, 1), cmap=cmap)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("per-column score (1 = best)", fontsize=8)

    for i in range(n_rows):
        for j in range(n_cols):
            val = raw[i, j]
            if not np.isfinite(val):
                continue
            txt = f"{val:.3f}" if abs(val) < 100 else f"{val:.1f}"
            shade = norm[i, j]
            color = "white" if (np.isfinite(shade) and shade < 0.55) else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7, color=color)

    fig.tight_layout()
    fig.savefig(out_base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def _scatter_ax(ax, df, xcol, ycol, color_col, title, ylabel):
    x = df[xcol].to_numpy(dtype=float)
    y = df[ycol].to_numpy(dtype=float)
    c = df[color_col].to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)

    sc = ax.scatter(
        x[mask], y[mask],
        c=np.where(np.isfinite(c[mask]), c[mask], np.nan),
        cmap="viridis", s=90, edgecolor="black", linewidth=0.5, zorder=3,
    )
    for xi, yi, name in zip(x[mask], y[mask], df["MLIP_name"].astype(str)[mask]):
        ax.annotate(name, (xi, yi), fontsize=6.5, xytext=(4, 3),
                    textcoords="offset points")
    ax.set_xlabel("Time per step (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.3, zorder=0)
    return sc


def scatter_matplotlib(df: pd.DataFrame, out_base: Path) -> None:
    acc = _accuracy_column(df)
    time_col = "Time_per_step (s)"
    if time_col not in df.columns:
        print(f"  (skip scatter: '{time_col}' not in summary)")
        return

    panels = [(acc, acc.replace(" (eV)", "") + " (eV)", "Accuracy-Efficiency")]
    if "Normal rate (%)" in df.columns:
        panels.append(("Normal rate (%)", "Normal rate (%)", "Robustness-Efficiency"))

    fig, axes = plt.subplots(1, len(panels), figsize=(6.5 * len(panels), 5.2))
    if len(panels) == 1:
        axes = [axes]
    last = None
    for ax, (ycol, ylabel, title) in zip(axes, panels):
        last = _scatter_ax(ax, df, time_col, ycol, acc, title, ylabel)
    if last is not None:
        cbar = fig.colorbar(last, ax=axes, fraction=0.04, pad=0.02)
        cbar.set_label(acc)
    fig.suptitle("Pareto: accuracy / robustness vs cost", fontsize=11)
    fig.savefig(out_base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Interactive (plotly) output
# ---------------------------------------------------------------------------
def interactive_html(df: pd.DataFrame, metrics, out_html: Path, title: str) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    models = df["MLIP_name"].astype(str).tolist()
    acc = _accuracy_column(df)
    time_col = "Time_per_step (s)"

    # Heatmap matrix (rows reversed so the best/first model is on top).
    z, text = [], []
    for col, _, hib in metrics:
        z.append(_normalize_good(df[col].to_numpy(dtype=float), hib))
        text.append([f"{v:.3f}" if np.isfinite(v) else "" for v in df[col]])
    z = np.array(z).T
    text = np.array(text).T

    has_scatter = time_col in df.columns
    specs = [[{"type": "heatmap"}]]
    titles = ["Metrics (viridis: bright = better, per column)"]
    if has_scatter:
        specs = [[{"type": "heatmap"}], [{"type": "scatter"}], [{"type": "scatter"}]]
        titles = [
            "Metrics (viridis: bright = better, per column)",
            "Accuracy-Efficiency: time/step vs MAE",
            "Robustness-Efficiency: time/step vs Normal rate",
        ]
    fig = make_subplots(
        rows=len(specs), cols=1, specs=specs, subplot_titles=titles,
        vertical_spacing=0.07,
        row_heights=[0.5] + [0.25] * (len(specs) - 1) if has_scatter else [1.0],
    )

    fig.add_trace(
        go.Heatmap(
            z=z[::-1], x=[m[1] for m in metrics], y=models[::-1],
            text=text[::-1], texttemplate="%{text}", textfont={"size": 9},
            colorscale="Viridis", zmin=0, zmax=1,
            colorbar=dict(title="score (1=best)", len=0.5, y=0.8),
        ),
        row=1, col=1,
    )

    if has_scatter:
        def _scatter(ycol, row, ytitle):
            fig.add_trace(
                go.Scatter(
                    x=df[time_col], y=df[ycol], mode="markers+text",
                    text=models, textposition="top center", textfont={"size": 8},
                    marker=dict(
                        size=12, color=df[acc], colorscale="Viridis",
                        showscale=(row == 2), line=dict(width=0.7, color="black"),
                        colorbar=dict(title=acc, len=0.25, y=0.28) if row == 2 else None,
                    ),
                    hovertext=models, name=ytitle,
                ),
                row=row, col=1,
            )
            fig.update_xaxes(title_text="Time per step (s)", row=row, col=1)
            fig.update_yaxes(title_text=ytitle, row=row, col=1)

        _scatter(acc, 2, acc)
        if "Normal rate (%)" in df.columns:
            _scatter("Normal rate (%)", 3, "Normal rate (%)")

    fig.update_layout(
        title=title, showlegend=False,
        height=520 + (420 if has_scatter else 0) + 14 * len(models),
        width=max(900, 70 * len(metrics) + 300),
        template="plotly_white",
    )
    fig.write_html(str(out_html), include_plotlyjs="cdn")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize an adsorption-energy benchmark (catbench.org-style).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--benchmark", required=True,
        help="Dataset name. Known: " + ", ".join(KNOWN_BENCHMARKS),
    )
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    parser.add_argument(
        "--csv", default=None,
        help="Explicit summary CSV path (default: result/<benchmark>/<benchmark>_summary.csv).",
    )
    parser.add_argument(
        "--outdir", default=None,
        help="Output directory (default: result/<benchmark>/viz).",
    )
    parser.add_argument("--no-static", action="store_true", help="Skip PNG/PDF output.")
    parser.add_argument("--no-html", action="store_true", help="Skip interactive HTML.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bench_dir = Path(args.result_dir).resolve() / args.benchmark
    csv_path = Path(args.csv) if args.csv else summary_csv_path(bench_dir, args.benchmark)
    if not csv_path.exists():
        print(
            f"Summary CSV not found: {csv_path}\n"
            f"Run: python code/analyze.py --benchmark {args.benchmark}",
            file=sys.stderr,
        )
        return 1

    df = load_summary(csv_path)
    acc = _accuracy_column(df)
    df = df.sort_values(acc, na_position="last").reset_index(drop=True)
    metrics = _present_metrics(df)
    if not metrics:
        print("No plottable metrics found in the summary CSV.", file=sys.stderr)
        return 1

    outdir = Path(args.outdir) if args.outdir else bench_dir / "viz"
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Models   : {len(df)}  | Metrics: {len(metrics)}  | sorted by {acc}")
    print(f"Out dir  : {outdir}")

    if not args.no_static:
        heatmap_matplotlib(df, metrics, outdir / f"{args.benchmark}_heatmap")
        scatter_matplotlib(df, outdir / f"{args.benchmark}_scatter")
        print("  static : heatmap.{png,pdf}, scatter.{png,pdf}")

    if not args.no_html:
        interactive_html(
            df, metrics, outdir / f"{args.benchmark}_dashboard.html",
            title=f"{args.benchmark} — MLIP adsorption-energy benchmark",
        )
        print("  html   : dashboard.html")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
