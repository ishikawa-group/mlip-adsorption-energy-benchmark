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
├── src/mlip_adsorption_energy_benchmark/  # benchmarking functions
│   ├── calculators.py   # calculator presets + build_calculator()
│   ├── benchmarks.py     # dataset definitions + download cache
│   ├── runner.py         # CatBench run wrapper (output-layout control)
│   └── analysis.py       # analysis wrapper (parity plots / Excel)
├── code/                 # executable CLIs
│   ├── run_benchmark.py  # run a benchmark
│   └── analyze.py        # analyse results
├── result/               # output: result/<benchmark>/<calculator>/ (git-ignored)
├── data/                 # dataset download cache (git-ignored)
└── script/tsubame4/      # TSUBAME4 job submission
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

```bash
# one calculator on one dataset (smoke test: small BM_dataset on CPU)
python code/run_benchmark.py --benchmark BM_dataset --calculator chgnet --device cpu

# all calculators, sequentially (GPU recommended)
python code/run_benchmark.py --benchmark MamunHighT2019 --calculator all --device cuda

# analysis (parity plots + Excel report)
python code/analyze.py --benchmark MamunHighT2019
```

Output is written to `result/<benchmark>/<calculator>/`.

## TSUBAME4 job submission

Submits one job per `(benchmark, calculator)` pair so each calculator runs on a
separate GPU in parallel.

```bash
# after cloning, create the venv on a compute node (see Installation)

# submit MamunHighT2019 and ComerGeneralized2024 for all calculators
python script/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 \
    --calculator all

# preview qsub commands without submitting
python script/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 --calculator all --dry-run
```

- Job settings: `-g tga-ishikawalab`, `gpu_h=1`, `h_rt=24:00:00`, `module load cuda`
- Default device is `cuda`
- Logs go to `result/<benchmark>/log/tsubame_jobs/<calculator>/`

Key flags: `--device`, `--n-seeds`, `--mode`, `--model/--task/--modal` (preset
overrides), `--group`, `--save-files`, `--dry-run`.

> **Note on inodes (file count)**
> With `save_files=True`, CatBench creates per-structure `log/<key>/` and
> `traj/<key>/` directories. On large datasets (e.g. MamunHighT2019 with ~45k
> adsorptions) this reaches tens of thousands of files per job and can exhaust
> the shared filesystem's **inode quota** (`OSError: [Errno 122] Disk quota
> exceeded`, even when free space remains). TSUBAME submission therefore
> **omits per-structure files by default** (passes `--no-save-files`). Only the
> small `*_result.json` files are written, which is enough for MAE/parity
> analysis. Pass `--save-files` only when you need trajectories.
