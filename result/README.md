# MLIP Adsorption-Energy Benchmark — Overview of the Three Datasets

**English** | [日本語](README_jp.md)

This page summarizes how machine-learning interatomic potentials (MLIPs) predict
**adsorption energies**, evaluated on three CatBench datasets with deliberately
different character. For the full results of each dataset (heatmap over all
calculators, bar charts, Pareto scatter, per-calculator parity plots, numeric
tables), see the sub-README of that dataset.

| Dataset | System (surface × adsorbate) | Reactions | Variants | Dispersion | Details |
|---|---|---:|---:|:---:|---|
| **ComerGeneralized2024** | metal **oxide** surfaces × O\* / OH\* | 325 | 23 | none | [README](ComerGeneralized2024/README.md) |
| **MamunHighT2019** | **binary-alloy** surfaces × small-molecule fragments (CH\*/O\*/H\* …) | 45,130 | 21\* | none | [README](MamunHighT2019/README.md) |
| **FG_dataset** | pure **metal** surfaces × **functional-group organic molecules** (aromatics, amides, …) | 2,651 | 18 | **D3(BJ)** | [README](FG_dataset/README.md) |

\* MamunHighT2019 currently has 21 completed variants (`nequip-l` / `nequip-XL`
are still computing).

> The three datasets are intentionally **complementary**: Comer is "simple O/OH on
> oxides", Mamun is "small molecules on alloys, at large scale", and FG is "large
> organic molecules on metals (where dispersion matters)". Because the surface
> type, adsorbate size, and importance of dispersion all differ, the strengths and
> weaknesses of MLIPs show up in three dimensions.

---

## 1. Accuracy summary

`MAE_normal` is the mean absolute error over normal reactions only (anomalies and
migration excluded); it measures a **model's local energy-prediction ability**.
`MAE_total` is the error over all reactions including anomalies; it is closer to
**robustness when used as-is in large-scale automated relaxation / screening**.
We therefore interpret "best MAE_normal" and "recommended for production" separately.

| Dataset | Best MAE_normal | MAE_normal | its MAE_total | Recommended for production | Reason |
|---|---|---:|---:|---|---|
| ComerGeneralized2024 | `uma-omat` | **0.130 eV** | 0.248 eV | `uma-omat` / `sevennet-omat24(-cueq)` / `sevennet-mpa(-cueq)` | For O/OH on oxides, OMat/MPtrj-based models and UMA-OMat are strong. |
| MamunHighT2019 | `sevennet-mpa`(-cueq) | **0.190 eV** | 0.672–0.673 eV | `sevennet-matpes_pbe(-cueq)` / `sevennet-oc20(-cueq)` | `mpa` is best on normal reactions, but its total degrades on metal-surface O\* anomalies. MatPES/OC20 keep O\* total and anomalies stable. |
| FG_dataset (D3) | `sevennet-matpes_r2scan-cueq-d3` | **0.245 eV** | 0.250 eV | `sevennet-matpes_r2scan-cueq-d3` / `sevennet-omat24-cueq-d3` / `uma-oc25` | For organic-molecule adsorption evaluated with D3(BJ), MatPES-r2SCAN is best. |

**Overall trends**

- **MAE_normal (normal reactions) and MAE_total (including anomalous structures)
  must be read separately.** SevenNet `mpa`/`omat24` are highly accurate on Mamun
  if you look at normal structures only, but on metal-surface O\* the number of
  anomalies grows and MAE_total can degrade badly. For large-scale automated
  relaxation / screening, prioritize MAE_total and the per-adsorbate breakdown.
- **For O/OH on oxides, OMat/MPtrj-based models and UMA-OMat are strong.** On Comer,
  `uma-omat` is the most accurate, and SevenNet `mpa`/`omat24` also give good normal
  accuracy on O\* / OH\*.
- **When metal / alloy-surface O\* is involved, prefer MatPES / OC20 models.** On
  Mamun's O\*, `sevennet-matpes_pbe(-cueq)` and `sevennet-oc20(-cueq)` greatly
  suppress the O\* MAE_total and anomalies, whereas the `mpa`/`omat24` family can
  break down due to a PES inconsistency inherited from PBE+U training data.
- **Treat `uma-oc25` as an empirical candidate.** It is relatively stable on Mamun
  (including O\*), but OC25 itself is a dataset aimed at **solid-liquid interfaces**
  with explicit solvent, so its justification for general gas-phase adsorption on
  metals is less direct than OC20 or MatPES-PBE. We therefore treat its good Mamun
  result as an empirical outcome on this benchmark.
- **CuEquivariance (`-cueq`)** speeds up inference by about 1.4–1.5× while keeping
  accuracy (the model is identical). The effect is larger on the large Mamun set.
- **Difficulty (best MAE_normal) increases as Comer < Mamun < FG.** Within this
  benchmark, atom-like O/OH on oxides is easiest to predict, and large organic
  molecules on metals are hardest.

---

## 2. Which surfaces and molecules ended in anomalies?

Here an **anomaly (abnormal termination)** means the CatBench classifier labeled the
relaxation as something other than `normal`: **unphysical_relaxation** (a physically
unreasonable relaxation) / **adsorbate_migration** (the adsorbate moved or desorbed) /
**reproduction_failure** / **energy_anomaly**. The rates below are aggregated
**across all calculators** for each dataset, so they represent the **intrinsic
difficulty of that surface / molecule**, not the quirk of a single model.

### 2-1. ComerGeneralized2024 (oxides × O/OH) — overall anomaly rate 21.9%

- **Adsorbates**: O\* (21.3%) and OH\* (22.4%) are almost equal, and the **main cause
  is `unphysical_relaxation` (52%)**. Rather than the adsorbate itself, what matters is
  that **the oxide slab collapses structurally during relaxation**.
- **Surfaces prone to anomalies (oxide cations)**:
  **Tl (75%) > Cd (55%) > In (53%) > Hg (41%) > Fe (40%) > Cu (39%)**.
  → Oxides of **post-transition / main-group metals (Tl/Cd/In/Hg) and easily reduced
  late-3d metals (Fe/Cu/Mn/Zn)** are overwhelmingly the hardest, because their oxide
  surfaces are unstable, take many polymorphs, and reconstruct strongly on relaxation.
- **Well-reproduced surfaces**: **Ir (1.1%) / Rh (1.7%) / Nb (5.7%) / Ru (6.5%) /
  Os (6.9%)**. → Oxides of **platinum-group and refractory transition metals** have
  stable structures, which MLIPs follow easily.

### 2-2. MamunHighT2019 (binary alloys × small molecules) — overall anomaly rate 17.7% (lowest of the three)

- **Adsorbates prone to anomalies**:
  **H2O (33.7%) > SH (28.6%) > O (26.7%) > CH2 (23.9%)**.
  → **Weakly physisorbed H2O tends to move / desorb (migration) during relaxation**;
  SH/CH2 are similarly mobile. In contrast, **O\* is dominated by
  `unphysical_relaxation`**, appearing as embedding into the surface, going
  subsurface, or a local-oxidation-like reconstruction.
- **O\* is extremely model-dependent.** For example, `sevennet-mpa-cueq` gives an O\*
  MAE_total of 2.86 eV, with PES-collapse anomalies (unphysical_relaxation 1209 +
  energy_anomaly 1183 + reproduction_failure 14 = 2406, excluding adsorbate_migration)
  at 2406/7369 (the full non-normal count including migration 476 is 2882/7369 = 39%),
  yet its MAE_normal is only ~0.24 eV — **so for normal structures the energy is not
  far off**. The main problem is not the energy regression itself, but the inability
  to keep the correct adsorption site / surface structure during O\* relaxation.
- **MatPES / OC20 models strongly suppress the O\* collapse.** For
  `sevennet-matpes_pbe-cueq` and `sevennet-oc20-cueq`, the O\* MAE_total drops to
  ~0.30 eV and the anomaly count is far smaller. For screening that includes O\* on
  metals / alloys, always check the O\* adsorbate breakdown, not just the MAE_normal
  of `mpa`/`omat24`.
- **Do not read `uma-oc25` as "good because OC25 directly targets gas-phase adsorption
  on metals".** OC25 mainly targets solid-liquid interfaces with explicit solvent, a
  different domain from Mamun's gas-phase small-molecule adsorption. We therefore treat
  its relatively good Mamun result as an **empirical outcome on this benchmark**, and
  place the first-principles justification for metal O\* on the MatPES-PBE / OC20 family.
- **Correspondence with the SevenNet-Omni paper**: Kim et al., *Optimizing Cross-Domain
  Transfer for Universal Machine Learning Interatomic Potentials* (arXiv:2510.11241)
  reports that when partially filled 3d metals such as Co/Ni coexist with oxygen,
  PBE+U-type data like MPtrj/OMat24 learn a PES that includes the Hubbard correction,
  so uMLIPs that rely heavily on such data **can show anomalous PES for oxygen-containing
  adsorption on metal surfaces**. In that paper's PES of an O atom approaching Co(111) /
  Cu(111), most models show anomalous curves on Co, whereas `7net-Omni.matpes` — a
  channel derived from Hubbard-free MatPES — keeps a physically reasonable PES.
- **Correspondence with the "Better without U" paper**: Warford, Thiemann, Csányi,
  *Better without U: Impact of Selective Hubbard U Correction on Foundational MLIPs*
  (arXiv:2601.21056) frames this as a more general **selective Hubbard U pathology**.
  It notes that in Materials Project data (MPtrj / Alexandria / OMat24), Hubbard U is
  applied to transition metals such as V/W/Fe/Ni/Co/Cr/Mo/Mn **only when O or F is
  present in the cell**. As a result the training data mixes **two incompatible PES,
  GGA(PBE) and GGA+U**, and the MLIP is forced to interpolate between them. This causes
  systematic underbinding — and sometimes spurious repulsion — between U-corrected
  metals and O/F-containing species. Datasets without +U, such as MatPES or MP-ALOE,
  avoid this pathology more easily.
- **Oxide-surface O\* and metal-surface O\* are different domains.** On Comer's oxide
  surfaces the surface already has an M–O bonding network, so the PBE+U-like oxide
  environment is close to the intended domain of `mpa`/`omat24`/`oc22`. In contrast,
  Mamun's metal-surface O\* is an intermediate state that begins to locally oxidize the
  metal surface, requiring metallic bonding, the local alloy environment, M–O bonding,
  and surface reconstruction to be handled simultaneously. Hence a model that does not
  collapse on oxide O\* can still break down on metal O\*.
- **Well-reproduced adsorbates**: **S / N / H (12–13%)** and similar **atomic adsorbates
  that chemisorb strongly and do not move**.
- **Surfaces prone to anomalies (alloy constituents)**:
  **Mn (29%) / Cr (29%) / Fe (28%) / Bi (27%) / Mo (25%) / Sn (25%) / W (24%)**.
  → Alloys containing **magnetic 3d metals (Mn/Cr/Fe), p-block elements (Bi/Sn/Pb/Tl),
  or refractory metals with complex bonding** are hard. Especially when O\* is present,
  the "mixed PBE/PBE+U PES for 3d-metal–O interactions" pointed out by the SevenNet-Omni
  and "Better without U" papers can amplify both anomalies and MAE_total degradation.
- **Well-reproduced surfaces**: **Ti / Hf / Zr / Sc / Ta / Tc (11–13%)**.
  → **Early transition metals** bind strongly and clearly, and stay stable even in alloys.

### 2-3. FG_dataset (metals × functional-group molecules, D3) — overall anomaly rate 40.6% (highest of the three)

- **The main cause is `adsorbate_migration` (69%)**. Because **large, floppy molecules
  change their orientation and adsorption site during relaxation**, the essence is not
  "the energy is off" but that **the geometry moves away from the initial site and is
  flagged as an anomaly**.
- **Molecules prone to anomalies**:
  **aromatics (55%) > group2b (48%) > carbamate (47%) > group2 (46%) > amides (45%) >
  oximes (45%)**. → **Aromatics are hardest**: the planar π system slides and rotates
  easily on the surface, and larger, more polyfunctional molecules move more.
- **Relatively easy molecules**: **group3N (27%) / group3S (31%) / aromatics2 (32%)**
  (anchored strongly to the surface via N/S, or smaller molecules).
- **Surfaces prone to anomalies (pure metals)**:
  **Ni (51%) > Cd (51%) > Rh (46%) > Zn (43%) > Pd (42%) > Ru/Pt (41%)**.
  → The **more reactive late transition metals** pull molecules in more strongly, causing
  reorientation and dissociation.
- **Relatively stable surfaces**: **Ag (30%) / Cu (33%) / Os (34%)**.

---

## 3. Cross-benchmark synthesis

- **The "mode" of anomaly differs qualitatively by dataset**:
  - Oxides (Comer) → **the surface collapses** (unphysical_relaxation). Difficulty is set
    by the **oxide stability of the cation**.
  - Alloys × small molecules (Mamun) → dominated by **migration of weakly bound species**
    and **local oxidation / PBE-PBE+U PES inconsistency for metal-surface O\***. For O\*
    in particular, `mpa`/`omat24` channels — strongly pulled by PBE+U inorganic-crystal
    data — can output a PES unsuitable for adsorption on metal surfaces.
  - Metals × large molecules (FG) → dominated by **molecular reorientation (migration)**.
    Difficulty is set by **molecular size and aromaticity**.
- **Common weaknesses**: post-transition / main-group metals (Cd, Tl, In, Hg, Bi, Sn) and
  magnetic 3d metals (Mn, Cr, Fe) are hard for MLIPs both as surfaces and in alloys.
  Conversely, **platinum-group and early transition metals are predicted stably**.
- **The problem adsorbates are "the ones that move" and "the ones that trigger local
  oxidation".** Physisorbed H2O and aromatic molecules that slide on the surface tend to
  become anomalies because they **move away from the initial structure during relaxation**,
  before energy even matters. In addition, metal-surface O\* may look like an immobile,
  strongly bound species, yet it pulls surface atoms in and causes local oxidation,
  going subsurface, and PBE/PBE+U PES inconsistency, which can badly break MAE_total.
- **Practical implications for model choice**:
  - Oxide-surface O/OH: `uma-omat`, `sevennet-omat24(-cueq)`, `sevennet-mpa(-cueq)`,
    `sevennet-matpes_r2scan(-cueq)` are candidates.
  - Systems including metal / alloy-surface O\*: make `sevennet-matpes_pbe(-cueq)` and
    `sevennet-oc20(-cueq)` the first choice. `uma-oc25` is good on Mamun, but since OC25
    comes from solid-liquid interfaces, treat it as an empirical candidate on this
    benchmark rather than a general recommendation for gas-phase adsorption on metals.
    `mpa`/`omat24` can have good MAE_normal yet a broken MAE_total from O\* anomalies.
  - Large organic molecules on metals: assuming evaluation with D3(BJ), compare
    `sevennet-matpes_r2scan-cueq-d3`, `sevennet-omat24-cueq-d3`, `uma-oc25`, etc.
- **When using MLIPs for catalyst screening**, systems that include **(i) easily reduced /
  magnetic metals, (ii) metal-surface O\*, or (iii) large, floppy (aromatic) molecules**
  warrant extra care: check relaxation convergence, inspect the per-adsorbate breakdown,
  visualize the O\* structures, and validate against DFT.

> **Method note**: Anomaly rates are aggregated over all calculators from each dataset's
> `analysis/per_calculator/<label>_parity.csv` (the CatBench classifier's `classification`
> column). Surface elements are extracted from the slab formula in the reaction key
> (cation for oxides, constituent elements for alloys); FG metals are taken from the metal
> token in the key. Reaction counts, best accuracies, and other numbers follow each
> sub-README / `*_summary.csv`.
> The discussion of the SevenNet-Omni paper is based on Kim et al., *Optimizing
> Cross-Domain Transfer for Universal Machine Learning Interatomic Potentials*,
> arXiv:2510.11241, in particular its metallic-surfaces section on the PBE+U-derived
> anomalous PES for Co/Ni + O.
> The discussion of the general PES inconsistency from selective Hubbard U is based on
> Warford, Thiemann, Csányi, *Better without U: Impact of Selective Hubbard U Correction
> on Foundational MLIPs*, arXiv:2601.21056.
> The positioning of OC25 follows Sahoo et al., *The Open Catalyst 2025 Dataset and Models
> for Solid-Liquid Interfaces*, arXiv:2509.17862, interpreting it as a model derived from
> solid-liquid interfaces.
