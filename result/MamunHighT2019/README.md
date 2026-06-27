# MamunHighT2019 — MLIP 吸着エネルギーベンチマーク結果

## ベンチマーク概要

**MamunHighT2019** は、**2,035 種の二元合金表面**上の **小分子吸着**に対する DFT 参照吸着
エネルギーのデータセットで、計 **45,130 反応**という大規模ベンチマークです
（reaction key 例: `Ag12_CH4(g) - H2(g) + * -> CH2*` = `<スラブ>_<気相反応> -> <吸着種>*`。
出典: [CatBench](https://catbench.org/?dataset=MamunHighT2019) / Zenodo）。
吸着種は **C / H / N / O / S 系の小分子フラグメント**（CH\*, CH2\*, CH3\*, NH\*, OH\*, SH\* など）です。
本ページは、機械学習原子間ポテンシャル (MLIP) が予測する吸着エネルギーを DFT と比較し、
精度・頑健性・計算コストを評価した結果です（**現時点で完了済みの 21 calculator/variant** を比較）。

- 比較した calculator: UMA(fairchem), SevenNet(7net-omni, 各 modal), MatterSim, CHGNet, NequIP-OAM
- 末尾 **`-cueq`** は SevenNet の **CuEquivariance** 高速化版（モデル自体は同一＝精度同等、推論が高速）
- 本ランは **分散力補正なし**（金属表面上の小分子吸着のため。`-d3` 付きの FG_dataset とは別軸）
- 計算条件: `mode=basic`（構造緩和, LBFGS）, `n_seeds=3`, `f_crit_relax=0.05`, `n_crit_relax=999`
- **`nequip-l` / `nequip-XL` は計算継続中**のため本集計には未収録（完了後に再生成予定）

### 指標の意味

| 指標 | 説明 |
|---|---|
| MAE_total (eV) | 全反応での予測 vs DFT 吸着エネルギーの平均絶対誤差 |
| MAE_normal (eV) | anomaly・吸着種 migration を除いた正常反応のみの MAE |
| Normal rate (%) | 正常に分類された反応の割合（高いほど頑健） |
| Anomaly rate (%) | エネルギー異常・非物理緩和・再現失敗の割合（低いほど良い） |
| ADwT / AMDwT (%) | しきい値内に収まる予測の割合（高いほど良い） |
| Time per step (s) | 1 最適化ステップあたりの計算時間（低いほど速い） |

## 全体比較

### 指標ヒートマップ表

各列を viridis で独立に正規化し、**明るい（黄色）ほど高性能**になるよう色付けしています
（MAE・時間など小さいほど良い指標は反転）。セル内は実数値です。

![metric heatmap](analysis/MamunHighT2019_heatmap.png)

### 単一指標ランキング（棒グラフ）

MAE_total / MAE_normal / Time per step を **良い順（小さいほど上）** に並べた横棒グラフです。
viridis カラーバーで、**明るいほど高性能（低い値）** を表します。
（本データセットは突出した外れ値が無いため、全 21 件を表示しています。）

![single-metric bars](analysis/MamunHighT2019_bars.png)

### Pareto 散布図（精度・頑健性 vs 計算コスト）

左から「Time/step vs MAE_total」「Time/step vs MAE_normal」「Time/step vs Normal rate」。
**左下（低コスト・低 MAE）** ほど精度効率が良く、Normal rate は **左上** ほど頑健かつ高速です。
点の色は MAE_total（明るいほど低 MAE＝良い）。

![pareto scatter](analysis/MamunHighT2019_scatter.png)

### サマリ表（MAE_normal 昇順）

| # | MLIP | MAE_total (eV) | MAE_normal (eV) | Normal (%) | ADwT (%) | AMDwT (%) | Time/step (s) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sevennet-mpa-cueq | 0.673 | 0.190 | 84.019 | 86.101 | 90.689 | 0.046 |
| 2 | sevennet-mpa | 0.672 | 0.190 | 84.086 | 86.125 | 90.722 | 0.068 |
| 3 | sevennet-omat24-cueq | 0.698 | 0.192 | 84.188 | 85.454 | 90.527 | 0.045 |
| 4 | sevennet-omat24 | 0.695 | 0.192 | 84.239 | 85.577 | 90.632 | 0.068 |
| 5 | sevennet-matpes_pbe | 0.249 | 0.194 | 90.312 | 87.088 | 91.982 | 0.067 |
| 6 | sevennet-matpes_pbe-cueq | 0.250 | 0.194 | 90.279 | 87.033 | 91.941 | 0.047 |
| 7 | sevennet-oc20 | 0.262 | 0.195 | 88.648 | 88.314 | 92.109 | 0.064 |
| 8 | sevennet-oc20-cueq | 0.263 | 0.195 | 88.628 | 88.193 | 92.030 | 0.044 |
| 9 | uma-oc20 | 0.288 | 0.211 | 87.006 | 89.119 | 92.507 | 0.058 |
| 10 | uma-oc25 | 0.331 | 0.222 | 83.472 | 85.169 | 89.992 | 0.058 |
| 11 | sevennet-oc22-cueq | 0.549 | 0.234 | 84.013 | 82.958 | 89.406 | 0.047 |
| 12 | sevennet-oc22 | 0.551 | 0.234 | 83.955 | 82.906 | 89.377 | 0.067 |
| 13 | uma-omat | 1.286 | 0.244 | 81.117 | 84.106 | 89.392 | 0.059 |
| 14 | sevennet-matpes_r2scan | 0.330 | 0.259 | 87.033 | 79.601 | 88.185 | 0.076 |
| 15 | sevennet-matpes_r2scan-cueq | 0.330 | 0.259 | 87.026 | 79.494 | 88.121 | 0.046 |
| 16 | nequip-m | 0.879 | 0.354 | 81.248 | 83.677 | 89.208 | 0.023 |
| 17 | mattersim-5M | 1.444 | 0.399 | 77.988 | 79.472 | 86.403 | 0.020 |
| 18 | chgnet-0.3.0 | 0.639 | 0.512 | 77.585 | 73.992 | 84.230 | 0.023 |
| 19 | chgnet-r2scan | 0.737 | 0.512 | 69.096 | 58.054 | 76.008 | 0.027 |
| 20 | nequip-s | 1.110 | 0.544 | 74.952 | 76.491 | 84.174 | 0.008 |
| 21 | uma-oc22 | 1.833 | 0.635 | 58.788 | 72.618 | 82.921 | 0.058 |

### 主な結果

- **最高精度（Normal）**: `sevennet-mpa`(-cueq)（MAE_normal = 0.190 eV）。上位は SevenNet の
  各 modal（mpa / omat24 / matpes_pbe / oc20）が 0.19–0.20 eV で拮抗し、`uma-oc20`（0.211 eV）が続く。
- **最高精度（Total）**: `sevennet-matpes_pbe`（MAE_total = 0.249 eV, Normal rate 90.3% も最高）。
  MAE_total では mpa/omat24 系（0.67–0.70 eV）より matpes_pbe / oc20 系の方が良く、
  **anomaly を含めた総合では matpes_pbe / oc20 modal が頑健**であることがわかる。
- **最低精度**: `uma-oc22`（MAE_normal = 0.635 eV, MAE_total = 1.833 eV, Normal rate 58.8%）。
  OC22 task はこの合金×小分子系には不適合。
- **最速**: `nequip-s`（0.008 s/step）、次いで `mattersim-5M`（0.020）/ `nequip-m`・`chgnet-0.3.0`（0.023）。
  ただし精度は中位以下で、**精度・速度のバランスでは `sevennet-*-cueq`（0.044–0.047 s/step で
  MAE_normal 0.19–0.26 eV）が優秀**。
- **CuEquivariance の効果**: 精度はほぼ同等のまま推論が高速化
  （例: `sevennet-mpa` 0.068s → `sevennet-mpa-cueq` 0.046s、`sevennet-oc20` 0.064s →
  `sevennet-oc20-cueq` 0.044s。MAE は一致）。大規模データほど効果が大きい。
- **modal/task 依存**: SevenNet は mpa/omat24/matpes_pbe/oc20 が良好、oc22 はやや劣化。
  UMA は oc20/oc25/omat が中上位だが oc22 が最下位。本データセット（合金上の小分子吸着）では
  OC20 系・MPtrj/OMat 系で学習した modal/task が良くフィットする。

## 各計算機の詳細 parity 図（予測 vs DFT）

左 = Total（全反応）, 右 = Normal（anomaly/migration 除外）。点は**吸着種**で色分け、
破線は y=x。Normal/anomaly の分類は CatBench 本体の分類器に準拠しています。
（MAE_normal 昇順）

### 1. sevennet-mpa-cueq

MAE_total = 0.673 eV / MAE_normal = 0.190 eV / Normal = 84.019 %

![sevennet-mpa-cueq parity](analysis/per_calculator/sevennet-mpa-cueq_parity.png)

### 2. sevennet-mpa

MAE_total = 0.672 eV / MAE_normal = 0.190 eV / Normal = 84.086 %

![sevennet-mpa parity](analysis/per_calculator/sevennet-mpa_parity.png)

### 3. sevennet-omat24-cueq

MAE_total = 0.698 eV / MAE_normal = 0.192 eV / Normal = 84.188 %

![sevennet-omat24-cueq parity](analysis/per_calculator/sevennet-omat24-cueq_parity.png)

### 4. sevennet-omat24

MAE_total = 0.695 eV / MAE_normal = 0.192 eV / Normal = 84.239 %

![sevennet-omat24 parity](analysis/per_calculator/sevennet-omat24_parity.png)

### 5. sevennet-matpes_pbe

MAE_total = 0.249 eV / MAE_normal = 0.194 eV / Normal = 90.312 %

![sevennet-matpes_pbe parity](analysis/per_calculator/sevennet-matpes_pbe_parity.png)

### 6. sevennet-matpes_pbe-cueq

MAE_total = 0.250 eV / MAE_normal = 0.194 eV / Normal = 90.279 %

![sevennet-matpes_pbe-cueq parity](analysis/per_calculator/sevennet-matpes_pbe-cueq_parity.png)

### 7. sevennet-oc20

MAE_total = 0.262 eV / MAE_normal = 0.195 eV / Normal = 88.648 %

![sevennet-oc20 parity](analysis/per_calculator/sevennet-oc20_parity.png)

### 8. sevennet-oc20-cueq

MAE_total = 0.263 eV / MAE_normal = 0.195 eV / Normal = 88.628 %

![sevennet-oc20-cueq parity](analysis/per_calculator/sevennet-oc20-cueq_parity.png)

### 9. uma-oc20

MAE_total = 0.288 eV / MAE_normal = 0.211 eV / Normal = 87.006 %

![uma-oc20 parity](analysis/per_calculator/uma-oc20_parity.png)

### 10. uma-oc25

MAE_total = 0.331 eV / MAE_normal = 0.222 eV / Normal = 83.472 %

![uma-oc25 parity](analysis/per_calculator/uma-oc25_parity.png)

### 11. sevennet-oc22-cueq

MAE_total = 0.549 eV / MAE_normal = 0.234 eV / Normal = 84.013 %

![sevennet-oc22-cueq parity](analysis/per_calculator/sevennet-oc22-cueq_parity.png)

### 12. sevennet-oc22

MAE_total = 0.551 eV / MAE_normal = 0.234 eV / Normal = 83.955 %

![sevennet-oc22 parity](analysis/per_calculator/sevennet-oc22_parity.png)

### 13. uma-omat

MAE_total = 1.286 eV / MAE_normal = 0.244 eV / Normal = 81.117 %

![uma-omat parity](analysis/per_calculator/uma-omat_parity.png)

### 14. sevennet-matpes_r2scan

MAE_total = 0.330 eV / MAE_normal = 0.259 eV / Normal = 87.033 %

![sevennet-matpes_r2scan parity](analysis/per_calculator/sevennet-matpes_r2scan_parity.png)

### 15. sevennet-matpes_r2scan-cueq

MAE_total = 0.330 eV / MAE_normal = 0.259 eV / Normal = 87.026 %

![sevennet-matpes_r2scan-cueq parity](analysis/per_calculator/sevennet-matpes_r2scan-cueq_parity.png)

### 16. nequip-m

MAE_total = 0.879 eV / MAE_normal = 0.354 eV / Normal = 81.248 %

![nequip-m parity](analysis/per_calculator/nequip-m_parity.png)

### 17. mattersim-5M

MAE_total = 1.444 eV / MAE_normal = 0.399 eV / Normal = 77.988 %

![mattersim-5M parity](analysis/per_calculator/mattersim-5M_parity.png)

### 18. chgnet-0.3.0

MAE_total = 0.639 eV / MAE_normal = 0.512 eV / Normal = 77.585 %

![chgnet-0.3.0 parity](analysis/per_calculator/chgnet-0.3.0_parity.png)

### 19. chgnet-r2scan

MAE_total = 0.737 eV / MAE_normal = 0.512 eV / Normal = 69.096 %

![chgnet-r2scan parity](analysis/per_calculator/chgnet-r2scan_parity.png)

### 20. nequip-s

MAE_total = 1.110 eV / MAE_normal = 0.544 eV / Normal = 74.952 %

![nequip-s parity](analysis/per_calculator/nequip-s_parity.png)

### 21. uma-oc22

MAE_total = 1.833 eV / MAE_normal = 0.635 eV / Normal = 58.788 %

![uma-oc22 parity](analysis/per_calculator/uma-oc22_parity.png)
