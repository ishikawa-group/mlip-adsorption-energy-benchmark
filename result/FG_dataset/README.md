# FG_dataset — MLIP Adsorption-Energy Benchmark Results (with D3 dispersion)

**English** | [日本語](README_jp.md)

## Benchmark overview

**FG_dataset** is a dataset of DFT reference adsorption energies for **functional-group
organic molecules** adsorbed on various metal surfaces, for **2,651 reactions** in total
(reaction key examples: `group4_au_4821`, `amidines_os_4aZc` = `<functional-group family>_<metal>_<id>`;
source: [CatBench](https://catbench.org/?dataset=FG_dataset) / Zenodo).
The adsorbing molecules span **11 functional-group families**: besides **aromatics
(`aromatics` / `aromatics2`)**, they include amides (`amides`), amidines (`amidines`),
carbamate (`carbamate`), oximes (`oximes`), and `group2` / `group2b` / `group3N` /
`group3S` / `group4`. Compared with the small-molecule (O\*/OH\*) adsorption of
ComerGeneralized2024, these molecules are **larger and more diverse, with aromatic rings
and heteroatoms**, so **van der Waals (dispersion) interactions contribute significantly**.

For this reason the results here are evaluated with **Grimme-D3(BJ) dispersion** added to
every calculator (**18 calculator/variants** compared).

- Calculators compared: UMA (fairchem), SevenNet (7net-omni, each modal), MatterSim, CHGNet, NequIP-OAM
- A trailing **`-d3`** means **D3(BJ) dispersion is on** (the xc functional is selected
  automatically per model/modal/task from ase-calculator-kit's policy table: e.g. OC20=RPBE,
  most are PBE, r2SCAN family = r2scan)
- SevenNet is run as **`-cueq-d3`** (CuEquivariance acceleration + D3)
- Only **`uma-oc25`** has no D3 (this model already includes dispersion during training,
  so the correction is refused to avoid double counting = left as-is)
- Settings: `mode=basic` (structure relaxation, LBFGS), `n_seeds=1`, `f_crit_relax=0.05`, `n_crit_relax=999`

### Meaning of the metrics

| Metric | Description |
|---|---|
| MAE_total (eV) | Mean absolute error of predicted vs DFT adsorption energy over all reactions |
| MAE_normal (eV) | MAE over normal reactions only (anomalies and adsorbate migration excluded) |
| Normal rate (%) | Fraction of reactions classified as normal (higher = more robust) |
| Anomaly rate (%) | Fraction with energy anomaly / unphysical relaxation / reproduction failure (lower = better) |
| ADwT / AMDwT (%) | Fraction of predictions within threshold (higher = better) |
| Time per step (s) | Compute time per optimization step (lower = faster) |

## Overall comparison

### Metric heatmap table

Each column is normalized independently with viridis so that **brighter (yellow) =
higher performance** (metrics where smaller is better, such as MAE and time, are
inverted). Each cell shows the raw value.

![metric heatmap](analysis/FG_dataset_heatmap.png)

### Single-metric ranking (bar charts)

Horizontal bars for MAE_total / MAE_normal / Time per step, **sorted best-first
(smaller = higher)**. The viridis colorbar means **brighter = higher performance
(lower value)**.

> In the bar charts and the scatter below, the outlier **`uma-oc22-d3`
> (MAE_total = 6.511 eV) is excluded** to keep the shared axes from being flattened and
> hard to read (it is still included in the heatmap, summary table, and each calculator's
> parity plot).

![single-metric bars](analysis/FG_dataset_bars.png)

### Pareto scatter (accuracy / robustness vs compute cost)

From left: "Time/step vs MAE_total", "Time/step vs MAE_normal", "Time/step vs
Normal rate". **Lower-left (low cost, low MAE)** means better accuracy-efficiency;
for Normal rate, **upper-left** is more robust and faster. Point color is MAE_total
(brighter = lower MAE = better).

![pareto scatter](analysis/FG_dataset_scatter.png)

### Summary table (ascending MAE_normal)

| # | MLIP | MAE_total (eV) | MAE_normal (eV) | Normal (%) | ADwT (%) | AMDwT (%) | Time/step (s) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sevennet-matpes_r2scan-cueq-d3 | 0.250 | 0.245 | 85.138 | 78.601 | 85.472 | 0.165 |
| 2 | sevennet-omat24-cueq-d3 | 0.296 | 0.284 | 84.157 | 81.138 | 85.895 | 0.160 |
| 3 | uma-oc25 | 0.295 | 0.287 | 88.306 | 86.726 | 88.499 | 0.065 |
| 4 | uma-omat-d3 | 0.302 | 0.289 | 78.235 | 77.663 | 80.776 | 0.177 |
| 5 | sevennet-mpa-cueq-d3 | 0.325 | 0.314 | 84.195 | 82.241 | 86.564 | 0.158 |
| 6 | sevennet-matpes_pbe-cueq-d3 | 0.351 | 0.344 | 87.627 | 82.916 | 87.401 | 0.163 |
| 7 | sevennet-oc22-cueq-d3 | 0.367 | 0.347 | 82.007 | 73.931 | 82.107 | 0.166 |
| 8 | mattersim-1M-d3 | 0.520 | 0.361 | 36.100 | 69.633 | 67.503 | 0.155 |
| 9 | nequip-XL-d3 | 0.546 | 0.523 | 80.158 | 79.845 | 82.546 | 0.238 |
| 10 | nequip-l-d3 | 0.566 | 0.539 | 78.536 | 78.700 | 81.604 | 0.197 |
| 11 | chgnet-r2scan-d3 | 0.880 | 0.610 | 37.231 | 56.174 | 63.165 | 0.175 |
| 12 | mattersim-5M-d3 | 0.958 | 0.640 | 43.644 | 71.073 | 68.915 | 0.145 |
| 13 | nequip-m-d3 | 0.812 | 0.742 | 67.974 | 76.867 | 76.785 | 0.171 |
| 14 | chgnet-0.3.0-d3 | 1.054 | 0.767 | 37.269 | 64.122 | 65.476 | 0.176 |
| 15 | uma-oc20-d3 | 0.885 | 0.853 | 37.910 | 31.304 | 55.478 | 0.168 |
| 16 | nequip-s-d3 | 1.148 | 0.867 | 27.876 | 64.539 | 62.950 | 0.122 |
| 17 | sevennet-oc20-cueq-d3 | 0.975 | 0.992 | 31.384 | 30.765 | 54.047 | 0.173 |
| 18 | uma-oc22-d3 | 6.511 | 1.504 | 1.924 | 69.578 | 77.157 | 0.181 |

### Key findings

- **Best accuracy**: `sevennet-matpes_r2scan-cueq-d3` (MAE_normal = 0.245 eV,
  MAE_total = 0.250 eV), followed by `sevennet-omat24-cueq-d3` (0.284 eV),
  `uma-oc25` (0.287 eV), and `uma-omat-d3` (0.289 eV).
- **Worst accuracy**: `uma-oc22-d3` (MAE_normal = 1.504 eV; MAE_total is a large 6.511 eV
  with heavy outliers, and Normal rate is only 1.9% — most reactions are flagged as
  anomalies). The OC22 task does not fit this molecular-adsorption system.
- **Fastest**: `uma-oc25` (0.065 s/step). It is both top-accuracy (3rd) and fastest, so
  it has the best balance on this dataset. The others are roughly 0.12–0.24 s/step.
- **Robustness (Normal rate)**: the top SevenNet modals (cueq-d3) and `uma-oc25` /
  `nequip-XL/l-d3` are high at 78–88%, whereas `mattersim`, `chgnet`, `uma-oc20/oc22-d3`,
  `sevennet-oc20-cueq-d3`, and `nequip-s-d3` drop to around 30–44%. For large molecules
  such as aromatics, unphysical relaxation and energy anomalies tend to increase.
- **modal/task dependence**: even within SevenNet, `matpes_r2scan` / `omat24` / `mpa` /
  `matpes_pbe` are good (MAE_normal 0.24–0.34 eV), but `oc20` degrades badly (0.992 eV).
  UMA is likewise good on `omat`/`oc25` and poor on `oc20`/`oc22`. This suggests that
  **modals/tasks trained on diverse (OMat/MPtrj-type) data also generalize better to
  functional-group molecule adsorption**.
- This is a comparison with D3 dispersion added to every calculator, reflecting that
  for large adsorbing molecules with aromatic rings and heteroatoms the dispersion
  contribution is not negligible.

## Per-calculator parity plots (prediction vs DFT)

Left = Total (all reactions), right = Normal (anomalies/migration excluded). Points
are colored by **functional-group family**; the dashed line is y=x. The Normal/anomaly
classification follows CatBench's own classifier. (Ascending MAE_normal.)

### 1. sevennet-matpes_r2scan-cueq-d3

MAE_total = 0.250 eV / MAE_normal = 0.245 eV / Normal = 85.138 %

![sevennet-matpes_r2scan-cueq-d3 parity](analysis/per_calculator/sevennet-matpes_r2scan-cueq-d3_parity.png)

### 2. sevennet-omat24-cueq-d3

MAE_total = 0.296 eV / MAE_normal = 0.284 eV / Normal = 84.157 %

![sevennet-omat24-cueq-d3 parity](analysis/per_calculator/sevennet-omat24-cueq-d3_parity.png)

### 3. uma-oc25

MAE_total = 0.295 eV / MAE_normal = 0.287 eV / Normal = 88.306 %

![uma-oc25 parity](analysis/per_calculator/uma-oc25_parity.png)

### 4. uma-omat-d3

MAE_total = 0.302 eV / MAE_normal = 0.289 eV / Normal = 78.235 %

![uma-omat-d3 parity](analysis/per_calculator/uma-omat-d3_parity.png)

### 5. sevennet-mpa-cueq-d3

MAE_total = 0.325 eV / MAE_normal = 0.314 eV / Normal = 84.195 %

![sevennet-mpa-cueq-d3 parity](analysis/per_calculator/sevennet-mpa-cueq-d3_parity.png)

### 6. sevennet-matpes_pbe-cueq-d3

MAE_total = 0.351 eV / MAE_normal = 0.344 eV / Normal = 87.627 %

![sevennet-matpes_pbe-cueq-d3 parity](analysis/per_calculator/sevennet-matpes_pbe-cueq-d3_parity.png)

### 7. sevennet-oc22-cueq-d3

MAE_total = 0.367 eV / MAE_normal = 0.347 eV / Normal = 82.007 %

![sevennet-oc22-cueq-d3 parity](analysis/per_calculator/sevennet-oc22-cueq-d3_parity.png)

### 8. mattersim-1M-d3

MAE_total = 0.520 eV / MAE_normal = 0.361 eV / Normal = 36.100 %

![mattersim-1M-d3 parity](analysis/per_calculator/mattersim-1M-d3_parity.png)

### 9. nequip-XL-d3

MAE_total = 0.546 eV / MAE_normal = 0.523 eV / Normal = 80.158 %

![nequip-XL-d3 parity](analysis/per_calculator/nequip-XL-d3_parity.png)

### 10. nequip-l-d3

MAE_total = 0.566 eV / MAE_normal = 0.539 eV / Normal = 78.536 %

![nequip-l-d3 parity](analysis/per_calculator/nequip-l-d3_parity.png)

### 11. chgnet-r2scan-d3

MAE_total = 0.880 eV / MAE_normal = 0.610 eV / Normal = 37.231 %

![chgnet-r2scan-d3 parity](analysis/per_calculator/chgnet-r2scan-d3_parity.png)

### 12. mattersim-5M-d3

MAE_total = 0.958 eV / MAE_normal = 0.640 eV / Normal = 43.644 %

![mattersim-5M-d3 parity](analysis/per_calculator/mattersim-5M-d3_parity.png)

### 13. nequip-m-d3

MAE_total = 0.812 eV / MAE_normal = 0.742 eV / Normal = 67.974 %

![nequip-m-d3 parity](analysis/per_calculator/nequip-m-d3_parity.png)

### 14. chgnet-0.3.0-d3

MAE_total = 1.054 eV / MAE_normal = 0.767 eV / Normal = 37.269 %

![chgnet-0.3.0-d3 parity](analysis/per_calculator/chgnet-0.3.0-d3_parity.png)

### 15. uma-oc20-d3

MAE_total = 0.885 eV / MAE_normal = 0.853 eV / Normal = 37.910 %

![uma-oc20-d3 parity](analysis/per_calculator/uma-oc20-d3_parity.png)

### 16. nequip-s-d3

MAE_total = 1.148 eV / MAE_normal = 0.867 eV / Normal = 27.876 %

![nequip-s-d3 parity](analysis/per_calculator/nequip-s-d3_parity.png)

### 17. sevennet-oc20-cueq-d3

MAE_total = 0.975 eV / MAE_normal = 0.992 eV / Normal = 31.384 %

![sevennet-oc20-cueq-d3 parity](analysis/per_calculator/sevennet-oc20-cueq-d3_parity.png)

### 18. uma-oc22-d3

MAE_total = 6.511 eV / MAE_normal = 1.504 eV / Normal = 1.924 %

![uma-oc22-d3 parity](analysis/per_calculator/uma-oc22-d3_parity.png)
