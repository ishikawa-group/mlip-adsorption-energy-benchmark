# mlip-adsorption-energy-benchmark

A thin workflow layer for benchmarking the **adsorption-energy accuracy** of
machine-learning interatomic potentials (MLIPs) against DFT references.

- Benchmark engine (datasets, relaxations, analysis/reporting):
  [CatBench](https://github.com/JinukMoon/catbench)
- MLIP calculator factory (UMA / SevenNet / MatterSim / CHGNet / NequIP behind one API):
  [ase-calculator-kit](https://github.com/ishikawa-group/ase-calculator-kit)

This repository glues the two together so a single command runs a benchmark
locally or submits jobs on TSUBAME4.

> **Naming**: Python package names cannot contain hyphens, so the importable
> package under `src/` is `mlip_adsorption_energy_benchmark` (underscores), and
> the config file is the conventional `pyproject.toml`.

## Layout

```
mlip-adsorption-energy-benchmark/
├── src/mlip_adsorption_energy_benchmark/  # package (functions + CLIs)
│   ├── calculators.py   # calculator presets + build_calculator()
│   ├── benchmarks.py     # dataset definitions + download cache
│   ├── runner.py         # CatBench run wrapper (output-layout control)
│   ├── analysis.py       # analysis wrapper (parity plots / Excel / summary CSV)
│   └── cli/              # executable CLIs (run via python -m ...cli.<name>)
│       ├── run.py        # run a benchmark
│       ├── analyze.py    # analyse results
│       └── visualize.py  # visualize results
├── result/               # output: result/<benchmark>/<calculator>/ (git-ignored)
├── data/                 # dataset download cache (git-ignored)
└── scripts/tsubame4/     # TSUBAME4 job submission
    ├── run_tsubame_benchmark.sh
    └── submit_tsubame_jobs.py
```

## Supported calculators (presets)

Pass `all` or a comma-separated list of preset names to `--calculator`. Defaults
are tuned for adsorption energies (overridable on the CLI).

| preset      | backend   | defaults                          | notes |
|-------------|-----------|-----------------------------------|-------|
| `uma`       | uma       | `model=uma-s-1p2`, `task=oc20`    | catalysis/adsorption task |
| `sevennet`  | sevennet  | `model=7net-omni`, `modal=mpa`    | multi-fidelity (PBE+U) |
| `mattersim` | mattersim | `model=5M`                        | general purpose |
| `chgnet`    | chgnet    | (bundled default)                 | lightweight, general |
| `nequip`    | nequip    | `model=L`                         | OAM (MPS unsupported) |

### Sweeping variants of one calculator

Each `--calculator` item may be a `preset:key=value` spec (key in model/task/modal),
giving every variant its **own folder and job** (comma-separate multiple specs):

```
uma:task=oc22            -> result/<benchmark>/uma-oc22/
sevennet:modal=omat24    -> result/<benchmark>/sevennet-omat24/
nequip:model=m           -> result/<benchmark>/nequip-m/
chgnet:model=0.3.0       -> result/<benchmark>/chgnet-0.3.0/
```

A bare preset name (or `all`) keeps its preset-name label and default settings.

## Supported benchmarks (datasets)

Names are passed straight to CatBench (fetched from Zenodo). Common ones:

- `MamunHighT2019` — ~45k small-molecule adsorptions on 2,035 bimetallic alloys
- `ComerGeneralized2024` — 325 adsorptions on metal oxides
- `BM_dataset` — 32 large molecules (small; good for smoke tests)
- also `OC20-Dense`, `GameNetOx_oxide`, `FG_dataset`

## Installation

Python `>=3.12,<3.14` (ase-calculator-kit constraint). CUDA recommended.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

CatBench and ase-calculator-kit are installed from GitHub. `.venv` is git-ignored.

## Local usage

CLIs are run as package submodules via `python -m` (works directly after
`pip install -e .`; otherwise prefix with `PYTHONPATH=src`).

```bash
# one calculator on one dataset (smoke test: small BM_dataset on CPU)
python -m mlip_adsorption_energy_benchmark.cli.run --benchmark BM_dataset --calculator chgnet --device cpu

# all calculators, sequentially (GPU recommended)
python -m mlip_adsorption_energy_benchmark.cli.run --benchmark MamunHighT2019 --calculator all --device cuda

# analysis (parity plots + Excel report + summary CSV)
python -m mlip_adsorption_energy_benchmark.cli.analyze --benchmark MamunHighT2019

# visualization (catbench.org-style: metric heatmap-table + Pareto scatter)
python -m mlip_adsorption_energy_benchmark.cli.visualize --benchmark MamunHighT2019
```

### Visualization (`cli/visualize.py`)

Reads the **`result/<benchmark>/<benchmark>_summary.csv`** written by `analyze.py`
and renders [catbench.org](https://catbench.org)-style figures into
`result/<benchmark>/viz/`:

- **Metric heatmap-table**: one row per model, one column per metric (MAE /
  Normal% / anomaly breakdown / ADwT / AMDwT / Time/step ...). Each column is
  colored independently with **viridis** (bright = better), the raw value is
  printed in each cell, with a colorbar.
- **Single-metric bar charts**: MAE_total / MAE_normal / Time/step as horizontal
  bars **sorted best-first** (three metrics stacked in one figure, viridis
  colorbar = brighter is better).
- **Pareto scatter**: Time/step vs Total MAE, Time/step vs Normal MAE
  (Accuracy-Efficiency), and Time/step vs Normal rate % (Robustness-Efficiency),
  points colored by MAE (bright = better).
- **Per-calculator parity plots** (`viz/per_calculator/`): predicted vs DFT for
  each calculator, in **Total** and **Normal (anomalies & migration excluded)**
  panels, points **colored by adsorbate**. The Normal/anomaly split reuses
  CatBench's own classifier (`_anomaly_detection`) so it matches the official
  numbers. Also writes `<label>_parity.csv` and CatBench's per-adsorbate
  `<label>_adsorbate_breakdown.csv`. Disable with `--no-per-calculator`.
- Outputs: static `*_heatmap.png` / `*_scatter.png` / (per-calc) `<label>_parity.png`
  and interactive `*_dashboard.html` / (per-calc) `<label>_parity.html` (plotly).

> Run `analyze.py` first so the summary CSV exists.

Output is written to `result/<benchmark>/<calculator>/`.

## TSUBAME4 job submission

Submits one job per `(benchmark, calculator)` pair so each calculator runs on a
separate GPU in parallel.

```bash
# after cloning, create the venv on a compute node (see Installation)

# submit MamunHighT2019 and ComerGeneralized2024 for all calculators
python scripts/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 \
    --calculator all

# preview qsub commands without submitting
python scripts/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 --calculator all --dry-run
```

- Job settings: `-g tga-ishikawalab`, `gpu_h=1`, `h_rt=24:00:00`, `module load cuda`
- Default device is `cuda`
- Logs go to `result/<benchmark>/log/tsubame_jobs/<calculator>/`

Key flags: `--device`, `--n-seeds`, `--mode`, `--model/--task/--modal` (preset
overrides), `--group`, `--save-files`, `--cueq`, `--dry-run`.

`--cueq` enables SevenNet's CuEquivariance acceleration (needs cuequivariance
installed). Its results are saved under a separate **`<label>-cueq`** folder
(e.g. `sevennet-mpa-cueq`) and separate jobs, so they never overwrite the
non-cueq runs.

> **Note on inodes (file count)**
> With `save_files=True`, CatBench creates per-structure `log/<key>/` and
> `traj/<key>/` directories. On large datasets (e.g. MamunHighT2019 with ~45k
> adsorptions) this reaches tens of thousands of files per job and can exhaust
> the shared filesystem's **inode quota** (`OSError: [Errno 122] Disk quota
> exceeded`, even when free space remains). TSUBAME submission therefore
> **omits per-structure files by default** (passes `--no-save-files`). Only the
> small `*_result.json` files are written, which is enough for MAE/parity
> analysis. Pass `--save-files` only when you need trajectories.

### Resuming jobs that hit the walltime

Large datasets (e.g. MamunHighT2019, ~45k adsorptions) may not finish within a
single 24h job. CatBench **auto-resumes** from `*_structure_cache.json` (already
done structures are `Skipping already calculated`), so **just re-submitting the
same command continues from where it stopped** — no work is wasted.

```bash
# e.g. after 24h, re-submit; only unfinished jobs resume
python scripts/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 --device cuda \
    --calculator "<same spec as the first run>"
```

- Calculators already **completed** (a `result/<benchmark>/<label>/<label>_result.json`
  exists) are skipped by default; only timed-out ones resume.
- **Important**: do not delete the in-progress `result/<benchmark>/result/<label>/`
  (it holds the cache).
- Use `--rerun-completed` to recompute everything from scratch.
- Resume only works if the relaxation settings (`--f-crit-relax` / `--n-crit-relax`
  / `--mode`) match the first run; changing them invalidates the cache.
