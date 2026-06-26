#!/usr/bin/env python3
"""Visualize an adsorption-energy benchmark, catbench.org-style.

Reads the per-model summary CSV produced by ``cli/analyze.py`` and renders:

1. A **metric heatmap-table** (one row per model, one column per metric). Each
   column is colored independently with the *viridis* colormap so brighter =
   better; the raw value is printed in every cell.
2. **Pareto scatter plots** of accuracy / robustness versus cost:
   - Accuracy-Efficiency : Time per step (s) vs Normal MAE (eV)
   - Robustness-Efficiency: Time per step (s) vs Normal rate (%)

Both static figures (matplotlib, PNG) and an interactive HTML dashboard
(plotly) are written.

Run ``python -m mlip_adsorption_energy_benchmark.cli.analyze --benchmark <name>``
first so the summary CSV exists.

Example
-------
    python -m mlip_adsorption_energy_benchmark.cli.visualize --benchmark ComerGeneralized2024

(If the package is not installed, prefix with ``PYTHONPATH=src``.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm
from matplotlib.colors import Normalize

from .. import KNOWN_BENCHMARKS
from ..analysis import summary_csv_path

# Repo root: .../src/mlip_adsorption_energy_benchmark/cli/visualize.py -> parents[3].
REPO_ROOT = Path(__file__).resolve().parents[3]
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

    # Bigger cells so labels/annotations have room to be larger and legible.
    fig_w = max(11.0, 1.5 * n_cols + 4.0)
    fig_h = max(4.0, 0.62 * n_rows + 2.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="#dddddd")
    im = ax.imshow(np.ma.masked_invalid(norm), cmap=cmap, aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels([m[1] for m in metrics], rotation=40, ha="right", fontsize=12)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(models, fontsize=11)
    ax.set_title("Benchmark metrics (viridis: bright = better, per column)", fontsize=14)

    sm = cm.ScalarMappable(norm=Normalize(0, 1), cmap=cmap)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("per-column score (1 = best)", fontsize=11)
    cbar.ax.tick_params(labelsize=10)

    for i in range(n_rows):
        for j in range(n_cols):
            val = raw[i, j]
            if not np.isfinite(val):
                continue
            txt = f"{val:.3f}" if abs(val) < 100 else f"{val:.1f}"
            shade = norm[i, j]
            color = "white" if (np.isfinite(shade) and shade < 0.55) else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=9, color=color)

    fig.tight_layout()
    fig.savefig(out_base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


# Single-metric bar charts (sorted best-first, viridis colorbar). All three of
# these metrics are "lower is better", so bars are sorted ascending and colored
# with reversed viridis (bright = lower = better).
BAR_METRICS: list[tuple[str, str]] = [
    ("MAE_total (eV)", "MAE total (eV)"),
    ("MAE_normal (eV)", "MAE normal (eV)"),
    ("Time_per_step (s)", "Time per step (s)"),
]


def bars_matplotlib(df: pd.DataFrame, out_png: Path) -> None:
    """One horizontal bar chart per metric, sorted best-first, with a colorbar."""

    metrics = [(c, l) for c, l in BAR_METRICS if c in df.columns and df[c].notna().any()]
    if not metrics:
        return
    n = len(df)
    fig, axes = plt.subplots(
        len(metrics), 1, figsize=(11.0, max(5.0, 0.42 * n + 1.4) * len(metrics))
    )
    if len(metrics) == 1:
        axes = [axes]

    cmap = plt.get_cmap("viridis_r")  # bright = low value = better
    for ax, (col, label) in zip(axes, metrics):
        sub = df[["MLIP_name", col]].dropna(subset=[col]).copy()
        sub = sub.sort_values(col, ascending=True)            # best (lowest) first
        names = sub["MLIP_name"].astype(str).tolist()
        vals = sub[col].to_numpy(dtype=float)
        y = np.arange(len(vals))[::-1]                        # best on top

        vmin, vmax = float(vals.min()), float(vals.max())
        norm = Normalize(vmin, vmax)
        colors = cmap(norm(vals))
        ax.barh(y, vals, color=colors, edgecolor="black", linewidth=0.3)

        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=10)
        ax.set_xlabel(label, fontsize=12)
        ax.set_title(f"{label} — sorted best→worst", fontsize=13)
        ax.tick_params(axis="x", labelsize=10)
        ax.margins(x=0.12)
        span = (vmax - vmin) or 1.0
        for yi, v in zip(y, vals):
            ax.text(v + 0.01 * span, yi, f"{v:.3f}", va="center", ha="left", fontsize=8)

        sm = cm.ScalarMappable(norm=norm, cmap=cmap)
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label(f"{label} (bright = better)", fontsize=10)
        cbar.ax.tick_params(labelsize=9)

    fig.tight_layout()
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _scatter_panels(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Build the list of (ycol, ylabel, title) scatter panels that have data."""

    panels: list[tuple[str, str, str]] = []
    if "MAE_total (eV)" in df.columns and df["MAE_total (eV)"].notna().any():
        panels.append(("MAE_total (eV)", "MAE total (eV)", "Accuracy (total)-Efficiency"))
    if "MAE_normal (eV)" in df.columns and df["MAE_normal (eV)"].notna().any():
        panels.append(("MAE_normal (eV)", "MAE normal (eV)", "Accuracy (normal)-Efficiency"))
    if "Normal rate (%)" in df.columns and df["Normal rate (%)"].notna().any():
        panels.append(("Normal rate (%)", "Normal rate (%)", "Robustness-Efficiency"))
    return panels


def _color_column(df: pd.DataFrame) -> str:
    """Metric used to color scatter points (MAE_total preferred, else accuracy)."""

    if "MAE_total (eV)" in df.columns and df["MAE_total (eV)"].notna().any():
        return "MAE_total (eV)"
    return _accuracy_column(df)


def _scatter_ax(ax, df, xcol, ycol, color_col, title, ylabel):
    x = df[xcol].to_numpy(dtype=float)
    y = df[ycol].to_numpy(dtype=float)
    c = df[color_col].to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)

    # Color by MAE with reversed viridis so that lower MAE (better) is brighter.
    sc = ax.scatter(
        x[mask], y[mask],
        c=np.where(np.isfinite(c[mask]), c[mask], np.nan),
        cmap="viridis_r", s=90, edgecolor="black", linewidth=0.5, zorder=3,
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
    time_col = "Time_per_step (s)"
    if time_col not in df.columns:
        print(f"  (skip scatter: '{time_col}' not in summary)")
        return

    panels = _scatter_panels(df)
    if not panels:
        print("  (skip scatter: no MAE / Normal-rate columns)")
        return

    color_col = _color_column(df)
    fig, axes = plt.subplots(1, len(panels), figsize=(6.0 * len(panels), 5.2))
    if len(panels) == 1:
        axes = [axes]
    last = None
    for ax, (ycol, ylabel, title) in zip(axes, panels):
        last = _scatter_ax(ax, df, time_col, ycol, color_col, title, ylabel)
    if last is not None:
        cbar = fig.colorbar(last, ax=axes, fraction=0.04, pad=0.02)
        cbar.set_label(f"{color_col}  (bright = better)")
    fig.suptitle("Pareto: accuracy / robustness vs cost", fontsize=11)
    fig.savefig(out_base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Interactive (plotly) output
# ---------------------------------------------------------------------------
def interactive_html(df: pd.DataFrame, metrics, out_html: Path, title: str) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    models = df["MLIP_name"].astype(str).tolist()
    time_col = "Time_per_step (s)"
    color_col = _color_column(df)

    # Heatmap matrix (rows reversed so the best/first model is on top).
    z, text = [], []
    for col, _, hib in metrics:
        z.append(_normalize_good(df[col].to_numpy(dtype=float), hib))
        text.append([f"{v:.3f}" if np.isfinite(v) else "" for v in df[col]])
    z = np.array(z).T
    text = np.array(text).T

    panels = _scatter_panels(df) if time_col in df.columns else []
    n_rows = 1 + len(panels)
    specs = [[{"type": "heatmap"}]] + [[{"type": "scatter"}] for _ in panels]
    titles = ["Metrics (viridis: bright = better, per column)"] + [
        f"{title}: time/step vs {ylabel}" for _, ylabel, title in panels
    ]
    row_heights = [0.5] + [0.5 / len(panels)] * len(panels) if panels else [1.0]

    fig = make_subplots(
        rows=n_rows, cols=1, specs=specs, subplot_titles=titles,
        vertical_spacing=0.06, row_heights=row_heights,
    )

    fig.add_trace(
        go.Heatmap(
            z=z[::-1], x=[m[1] for m in metrics], y=models[::-1],
            text=text[::-1], texttemplate="%{text}", textfont={"size": 9},
            colorscale="Viridis", zmin=0, zmax=1,
            colorbar=dict(title="score (1=best)", len=0.45, y=0.78),
        ),
        row=1, col=1,
    )

    for idx, (ycol, ylabel, _title) in enumerate(panels):
        row = idx + 2
        fig.add_trace(
            go.Scatter(
                x=df[time_col], y=df[ycol], mode="markers+text",
                text=models, textposition="top center", textfont={"size": 8},
                marker=dict(
                    # reversescale -> lower MAE (better) is brighter
                    size=12, color=df[color_col], colorscale="Viridis",
                    reversescale=True,
                    showscale=(idx == 0), line=dict(width=0.7, color="black"),
                    colorbar=dict(
                        title=f"{color_col} (bright=better)", len=0.4, y=0.25
                    ) if idx == 0 else None,
                ),
                hovertext=models, name=ylabel,
            ),
            row=row, col=1,
        )
        fig.update_xaxes(title_text="Time per step (s)", row=row, col=1)
        fig.update_yaxes(title_text=ylabel, row=row, col=1)

    fig.update_layout(
        title=title, showlegend=False,
        height=520 + 320 * len(panels) + 14 * len(models),
        width=max(900, 70 * len(metrics) + 300),
        template="plotly_white",
    )
    fig.write_html(str(out_html), include_plotlyjs="cdn")


# ---------------------------------------------------------------------------
# Per-calculator parity plots (MLIP vs DFT), Total + Normal, colored by adsorbate
# ---------------------------------------------------------------------------
def _parse_adsorbate(reaction_key: str) -> str:
    """Extract the adsorbate label from a CatBench reaction key.

    e.g. 'Ag8O16_H2O(g) - H2(g) + * -> O*'      -> 'O'
         'W12_H2O(g) - H2(g) + * -> SH*_3'        -> 'SH'
         '... -> 2.0OH*'                           -> 'OH'
    """

    product = reaction_key.split("->")[-1].strip()
    product = product.split("_")[0]              # drop trailing _<index>
    product = re.sub(r"^[0-9.]+", "", product)   # drop leading coefficient
    return product.replace("*", "").strip() or "?"


def _classify_reactions(mlip_result: dict, label: str) -> dict[str, str]:
    """Per-reaction Normal/anomaly classification, reusing CatBench's classifier.

    We call CatBench's own ``_anomaly_detection`` (the single source of truth for
    its leaderboard numbers) so our Normal/Total split matches CatBench exactly.
    Falls back to treating everything as 'normal' if the internal API changes.
    """

    try:
        from catbench.adsorption import AdsorptionAnalysis

        analyzer = AdsorptionAnalysis(mlip_list=[label], plot_enabled=False)
        n_crit = int(mlip_result.get("calculation_settings", {}).get("n_crit_relax", 999))
        _, anomaly_summary = analyzer._anomaly_detection(mlip_result, label, n_crit)
        return {r: v.get("classification", "normal") for r, v in anomaly_summary.items()}
    except Exception as exc:  # noqa: BLE001
        print(f"  (warning: classification failed for {label}: {exc}; treating all as normal)")
        return {}


def parity_dataframe(result_json: Path) -> pd.DataFrame:
    """Build a tidy parity table (DFT vs MLIP per reaction) from a result.json."""

    data = json.loads(result_json.read_text())
    classes = _classify_reactions(data, result_json.parent.name)
    rows = []
    for reaction, v in data.items():
        if reaction == "calculation_settings" or not isinstance(v, dict):
            continue
        try:
            dft = float(v["reference"]["ads_eng"])
            mlip = float(v["final"]["ads_eng_median"])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append({
            "reaction": reaction,
            "adsorbate": _parse_adsorbate(reaction),
            "DFT": dft,
            "MLIP": mlip,
            "classification": classes.get(reaction, "normal"),
        })
    return pd.DataFrame(rows)


def _adsorbate_color_map(adsorbates: list[str]) -> dict[str, tuple]:
    base = plt.get_cmap("tab10" if len(adsorbates) <= 10 else "tab20")
    return {a: base(i % base.N) for i, a in enumerate(adsorbates)}


def _parity_panel(ax, sub: pd.DataFrame, adsorbates, color_map, title, ylabel):
    if len(sub):
        lo = float(min(sub["DFT"].min(), sub["MLIP"].min()))
        hi = float(max(sub["DFT"].max(), sub["MLIP"].max()))
        pad = 0.05 * (hi - lo + 1e-9)
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], "k--", lw=1, zorder=1)
        for a in adsorbates:
            s = sub[sub["adsorbate"] == a]
            if len(s):
                ax.scatter(s["DFT"], s["MLIP"], s=35, color=[color_map[a]],
                           label=f"{a} (n={len(s)})", edgecolor="black",
                           linewidth=0.3, alpha=0.85, zorder=3)
        mae = (sub["MLIP"] - sub["DFT"]).abs().mean()
        ax.text(0.04, 0.96, f"MAE = {mae:.3f} eV\nN = {len(sub)}",
                transform=ax.transAxes, va="top", ha="left", fontsize=11,
                bbox=dict(boxstyle="round", fc="white", alpha=0.7))
        ax.legend(fontsize=10, loc="lower right")
    else:
        ax.text(0.5, 0.5, "(no reactions)", transform=ax.transAxes, ha="center")
    ax.set_xlabel("DFT adsorption energy (eV)", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.3)


def parity_matplotlib(df: pd.DataFrame, label: str, out_png: Path) -> None:
    adsorbates = sorted(df["adsorbate"].unique())
    color_map = _adsorbate_color_map(adsorbates)
    normal = df[df["classification"] == "normal"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 6.2))
    _parity_panel(axes[0], df, adsorbates, color_map,
                  "Total (all reactions)", f"{label} adsorption energy (eV)")
    _parity_panel(axes[1], normal, adsorbates, color_map,
                  "Normal (anomalies & migration excluded)",
                  f"{label} adsorption energy (eV)")
    fig.suptitle(f"{label} — parity (MLIP vs DFT), colored by adsorbate", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def parity_plotly(df: pd.DataFrame, label: str, out_html: Path) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    adsorbates = sorted(df["adsorbate"].unique())
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
               "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    color_of = {a: palette[i % len(palette)] for i, a in enumerate(adsorbates)}
    panels = [("Total (all reactions)", df),
              ("Normal (anomalies & migration excluded)",
               df[df["classification"] == "normal"])]

    fig = make_subplots(rows=1, cols=2, subplot_titles=[p[0] for p in panels],
                        horizontal_spacing=0.08)
    for col, (_title, sub) in enumerate(panels, start=1):
        if len(sub):
            lo = float(min(sub["DFT"].min(), sub["MLIP"].min()))
            hi = float(max(sub["DFT"].max(), sub["MLIP"].max()))
            fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines",
                                     line=dict(color="black", dash="dash"),
                                     showlegend=False, hoverinfo="skip"),
                          row=1, col=col)
            for a in adsorbates:
                s = sub[sub["adsorbate"] == a]
                if not len(s):
                    continue
                fig.add_trace(go.Scatter(
                    x=s["DFT"], y=s["MLIP"], mode="markers", name=a,
                    legendgroup=a, showlegend=(col == 1),
                    marker=dict(color=color_of[a], size=7,
                                line=dict(width=0.4, color="black")),
                    text=s["reaction"],
                    hovertemplate="%{text}<br>DFT=%{x:.3f}<br>MLIP=%{y:.3f}<extra>" + a + "</extra>",
                ), row=1, col=col)
            mae = (sub["MLIP"] - sub["DFT"]).abs().mean()
            suffix = "" if col == 1 else str(col)
            fig.add_annotation(text=f"MAE={mae:.3f} eV  N={len(sub)}",
                               xref=f"x{suffix} domain", yref=f"y{suffix} domain",
                               x=0.04, y=0.96, showarrow=False, align="left")
        fig.update_xaxes(title_text="DFT adsorption energy (eV)", row=1, col=col)
        fig.update_yaxes(title_text=f"{label} (eV)",
                         scaleanchor=f"x{'' if col == 1 else col}",
                         scaleratio=1, row=1, col=col)

    fig.update_layout(title=f"{label} — parity (MLIP vs DFT), by adsorbate",
                      template="plotly_white", height=620, width=1200)
    fig.write_html(str(out_html), include_plotlyjs="cdn")


def export_adsorbate_breakdown(bench_dir: Path, benchmark: str, label: str,
                               out_csv: Path) -> None:
    """Save CatBench's per-adsorbate breakdown sheet for one MLIP to CSV."""

    xlsx = bench_dir / f"{benchmark}_Benchmarking_Analysis.xlsx"
    if not xlsx.exists():
        return
    try:
        raw = pd.read_excel(xlsx, sheet_name=label)
    except Exception:  # noqa: BLE001
        return
    if "Adsorbate_name" in raw.columns:
        raw = raw[raw["Adsorbate_name"].notna()]
    raw.to_csv(out_csv, index=False)


def render_per_calculator(df_summary: pd.DataFrame, bench_dir: Path, benchmark: str,
                          outdir: Path, static: bool, html: bool) -> int:
    """Build per-calculator parity outputs for every model in the summary."""

    pc_dir = outdir / "per_calculator"
    pc_dir.mkdir(parents=True, exist_ok=True)
    made = 0
    for label in df_summary["MLIP_name"].astype(str):
        result_json = bench_dir / label / f"{label}_result.json"
        if not result_json.exists():
            continue
        pdf = parity_dataframe(result_json)
        if pdf.empty:
            continue
        pdf.to_csv(pc_dir / f"{label}_parity.csv", index=False)
        export_adsorbate_breakdown(bench_dir, benchmark, label,
                                   pc_dir / f"{label}_adsorbate_breakdown.csv")
        if static:
            parity_matplotlib(pdf, label, pc_dir / f"{label}_parity.png")
        if html:
            parity_plotly(pdf, label, pc_dir / f"{label}_parity.html")
        made += 1
    return made


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
    parser.add_argument("--no-static", action="store_true", help="Skip PNG output.")
    parser.add_argument("--no-html", action="store_true", help="Skip interactive HTML.")
    parser.add_argument(
        "--no-per-calculator",
        action="store_true",
        help="Skip the per-calculator parity (MLIP vs DFT) plots.",
    )
    parser.add_argument(
        "--exclude-bars-scatter",
        default=None,
        help=(
            "Comma-separated MLIP_name(s) to drop from the bar chart and Pareto "
            "scatter ONLY (e.g. a gross outlier that flattens the shared axes). "
            "They are kept in the heatmap, dashboard, per-calculator plots, and "
            "the summary CSV/table."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bench_dir = Path(args.result_dir).resolve() / args.benchmark
    csv_path = Path(args.csv) if args.csv else summary_csv_path(bench_dir, args.benchmark)
    if not csv_path.exists():
        print(
            f"Summary CSV not found: {csv_path}\n"
            f"Run: python -m mlip_adsorption_energy_benchmark.cli.analyze --benchmark {args.benchmark}",
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

    # Optionally drop gross outliers from the bar chart / scatter only (they
    # otherwise flatten the shared axes). Kept everywhere else.
    excluded = {
        n.strip() for n in (args.exclude_bars_scatter or "").split(",") if n.strip()
    }
    bs_df = df[~df["MLIP_name"].astype(str).isin(excluded)] if excluded else df
    if excluded:
        kept = sorted(excluded & set(df["MLIP_name"].astype(str)))
        print(f"Excluding from bars/scatter only: {', '.join(kept) or '(none matched)'}")

    if not args.no_static:
        heatmap_matplotlib(df, metrics, outdir / f"{args.benchmark}_heatmap")
        bars_matplotlib(bs_df, outdir / f"{args.benchmark}_bars.png")
        scatter_matplotlib(bs_df, outdir / f"{args.benchmark}_scatter")
        print("  static : heatmap.png, bars.png, scatter.png")

    if not args.no_html:
        interactive_html(
            df, metrics, outdir / f"{args.benchmark}_dashboard.html",
            title=f"{args.benchmark} — MLIP adsorption-energy benchmark",
        )
        print("  html   : dashboard.html")

    if not args.no_per_calculator:
        made = render_per_calculator(
            df, bench_dir, args.benchmark, outdir,
            static=not args.no_static, html=not args.no_html,
        )
        print(f"  per-calc: {made} calculator(s) -> parity .png/.html/.csv "
              f"+ adsorbate_breakdown.csv under {outdir / 'per_calculator'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
