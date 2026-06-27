# MLIP 吸着エネルギーベンチマーク — 3 データセット総合まとめ

機械学習原子間ポテンシャル (MLIP) の **吸着エネルギー予測精度**を、性質の異なる 3 つの
CatBench データセットで評価した結果の総合ページです。各データセットの詳細（全 calculator の
ヒートマップ・棒グラフ・Pareto 散布図・calculator ごとの parity 図・数値表）は、それぞれの
サブ README を参照してください。

| データセット | 系（表面 × 吸着種） | 反応数 | 比較 variant | 分散補正 | 詳細 |
|---|---|---:|---:|:---:|---|
| **ComerGeneralized2024** | 金属**酸化物**表面 × O\* / OH\* | 325 | 23 | なし | [README](ComerGeneralized2024/README.md) |
| **MamunHighT2019** | **二元合金**表面 × 小分子フラグメント（CH\*/O\*/H\* …） | 45,130 | 21\* | なし | [README](MamunHighT2019/README.md) |
| **FG_dataset** | 純**金属**表面 × **官能基を持つ有機分子**（芳香族・アミド等） | 2,651 | 18 | **D3(BJ)** | [README](FG_dataset/README.md) |

\* MamunHighT2019 は現時点で完了済みの 21 variant（`nequip-l`/`nequip-XL` は計算継続中）。

> 3 つはあえて**相補的**に選んでいます。Comer は「酸化物上の単純な O/OH」、Mamun は「合金上の
> 小分子を大規模に」、FG は「金属上の大きな有機分子（分散力が効く）」。表面の種類・吸着種の
> サイズ・分散の重要性が異なるため、MLIP の得手不得手が立体的に見えます。

---

## 1. 精度の総括

各データセットでの **最高精度モデル**と代表値（MAE_normal = anomaly/migration を除いた正常反応の
平均絶対誤差）です。詳細な順位表は各サブ README にあります。

| データセット | 最高精度モデル | MAE_normal | 同 MAE_total | 最速モデル |
|---|---|---:|---:|---|
| ComerGeneralized2024 | `uma-omat` | **0.130 eV** | 0.248 eV | `nequip-s` (0.008 s/step) |
| MamunHighT2019 | `sevennet-mpa`(-cueq) | **0.190 eV** | 0.672 eV | `nequip-s` (0.008 s/step) |
| FG_dataset (D3) | `sevennet-matpes_r2scan-cueq-d3` | **0.245 eV** | 0.250 eV | `uma-oc25` (0.065 s/step) |

**全体傾向**

- **正常反応の MAE_normal と、異常構造を含む MAE_total は分けて見る必要がある**。SevenNet の
  `mpa`/`omat24` は正常構造だけなら Mamun でも高精度だが、金属上 O\* では anomaly が増えて
  MAE_total が大きく悪化することがある。大量自動緩和・スクリーニングでは MAE_total と
  adsorbate 別 breakdown を優先して評価する。
- **酸化物上 O/OH では OMat/MPtrj 系や UMA-OMat が強い**。Comer では `uma-omat` が最高精度で、
  SevenNet `mpa`/`omat24` も O\* / OH\* の normal 精度は良好。
- **金属・合金上の O\* を含む場合は MatPES / OC20 / OC25 系を優先**。Mamun の O\* では
  `sevennet-matpes_pbe(-cueq)` や `sevennet-oc20(-cueq)` が O\* の MAE_total と anomaly を大きく
  抑える一方、`mpa`/`omat24` 系は PBE+U 系データ由来の PES 不整合により崩れる場合がある。
- **CuEquivariance (`-cueq`)** は精度を保ったまま推論を約 1.4–1.5 倍高速化（モデルは同一）。
  大規模な Mamun ほど効果が大きい。
- **難易度（最高精度の MAE_normal）は Comer < Mamun < FG の順**。酸化物上の単原子的な O/OH が
  最も当てやすく、金属上の大きな有機分子が最も難しい。

---

## 2. 「どの表面・分子が異常終了したか」の考察

ここでの **anomaly（異常終了）** は、CatBench の分類器が緩和結果を
`normal` 以外（**unphysical_relaxation**＝非物理的な構造緩和 / **adsorbate_migration**＝吸着種の
移動・脱離 / **reproduction_failure**＝再現失敗 / **energy_anomaly**＝エネルギー異常）に分類したもの。
以下は各データセットで **全 calculator を横断して集計**した anomaly 率で、特定モデルの癖ではなく
**その表面・分子の“当てにくさ（固有の難しさ）”**を表します。

### 2-1. ComerGeneralized2024（酸化物 × O/OH）— 全体 anomaly 率 21.9%

- **吸着種**: O\* (21.3%) と OH\* (22.4%) でほぼ差がなく、**主因は `unphysical_relaxation`（52%）**。
  単純な吸着種そのものより、**酸化物スラブの構造が緩和中に崩れる**ことが効いている。
- **異常終了しやすい表面（酸化物のカチオン）**:
  **Tl (75%) > Cd (55%) > In (53%) > Hg (41%) > Fe (40%) > Cu (39%)**。
  → **ポスト遷移金属・典型金属（Tl/Cd/In/Hg）や還元されやすい後期 3d 金属（Fe/Cu/Mn/Zn）の酸化物**が
  圧倒的に苦手。これらは酸化物表面が不安定・多形を取りやすく、緩和で大きく再構成するため。
- **よく再現できる表面**: **Ir (1.1%) / Rh (1.7%) / Nb (5.7%) / Ru (6.5%) / Os (6.9%)**。
  → **白金族・耐熱性遷移金属**の酸化物は構造が安定で、MLIP も素直に追従できる。

### 2-2. MamunHighT2019（二元合金 × 小分子）— 全体 anomaly 率 17.7%（3 つで最低）

- **異常終了しやすい吸着種**:
  **H2O (33.7%) > SH (28.6%) > O (26.7%) > CH2 (23.9%)**。
  → **弱く物理吸着する H2O は緩和中に移動/脱離（migration）しやすい**。SH/CH2 も同様に動きやすい。
  一方 **O\* は `unphysical_relaxation` が主因**で、表面への埋め込み・サブサーフェス化・局所酸化的な
  再構成として現れやすい。
- **O\* はモデル依存性が非常に大きい**。例えば `sevennet-mpa-cueq` では O\* の MAE_total が 2.86 eV、
  anomaly count が 2406/7369 と大きく崩れる一方、MAE_normal は 0.24 eV 程度であり、
  **正常構造だけならエネルギーは大きく外れていない**。つまり主問題は energy regression そのものより、
  O\* 緩和中に正しい吸着サイト・表面構造を保持できないことにある。
- **MatPES / OC20 系では O\* 崩壊が大きく抑えられる**。`sevennet-matpes_pbe-cueq` や
  `sevennet-oc20-cueq` では O\* の MAE_total は約 0.30 eV まで下がり、anomaly count も大幅に少ない。
  金属・合金上 O\* を含むスクリーニングでは、`mpa`/`omat24` の MAE_normal だけでなく、O\* の
  adsorbate breakdown を必ず確認する。
- **SevenNet-Omni 論文との対応**: Kim et al., *Optimizing Cross-Domain Transfer for Universal Machine
  Learning Interatomic Potentials* (arXiv:2510.11241) では、Co/Ni などの部分充填 3d 金属と酸素が共存する場合、
  MPtrj/OMat24 のような PBE+U 系データでは Hubbard 補正を含む PES が学習されるため、
  それらに強く依存する uMLIP は **金属表面上の酸素含有吸着で異常な PES を示しうる**と報告されている。
  同論文では、O 原子を Co(111) / Cu(111) 表面へ近づけた PES で、Co では多くのモデルが異常な曲線を示すが、
  `7net-Omni.matpes` は Hubbard term を含まない MatPES 由来の channel のため物理的に妥当な PES を保つ、
  と議論されている。
- **酸化物上 O\* と金属上 O\* は別ドメイン**。Comer の酸化物表面では、表面がすでに M–O 結合ネットワークを
  持っており、PBE+U 的な酸化物環境は `mpa`/`omat24`/`oc22` 系の想定ドメインに近い。対して Mamun の
  金属上 O\* は、金属表面を局所酸化し始める途中状態であり、金属結合・合金局所環境・M–O 結合・表面再構成を
  同時に扱う必要がある。このため、酸化物上 O\* で崩壊しないモデルでも、金属上 O\* では崩れることがある。
- **よく再現できる吸着種**: **S / N / H（12–13%）** など、**強く化学吸着して動かない原子状吸着種**。
- **異常終了しやすい表面（合金構成元素）**:
  **Mn (29%) / Cr (29%) / Fe (28%) / Bi (27%) / Mo (25%) / Sn (25%) / W (24%)**。
  → **磁性を持つ 3d 金属（Mn/Cr/Fe）や p ブロック（Bi/Sn/Pb/Tl）・複雑結合の耐熱金属**を含む合金が苦手。
  とくに O\* を含む場合は、SevenNet-Omni 論文が指摘する「3d 金属–O 相互作用における PBE/PBE+U PES の混在」
  が anomaly と MAE_total 悪化を増幅しうる。
- **よく再現できる表面**: **Ti / Hf / Zr / Sc / Ta / Tc（11–13%）**。
  → **前期遷移金属**は吸着が強く明確で、合金でも安定。

### 2-3. FG_dataset（金属 × 官能基分子, D3）— 全体 anomaly 率 40.6%（3 つで最高）

- **主因は `adsorbate_migration`（69%）**。**大きく柔らかい分子が緩和中に向き・吸着位置を変える**ため、
  「エネルギーが外れる」というより**幾何構造が初期サイトから動いて anomaly 判定される**のが本質。
- **異常終了しやすい分子**:
  **aromatics（55%）> group2b（48%）> carbamate（47%）> group2（46%）> amides（45%）> oximes（45%）**。
  → **芳香族系が最難**。平面の π 系が表面上で滑り・回転しやすく、多官能で大きい分子ほど動く。
- **比較的当てやすい分子**: **group3N（27%）/ group3S（31%）/ aromatics2（32%）**
  （N/S で表面に強くアンカーされる、または小さめの分子）。
- **異常終了しやすい表面（純金属）**:
  **Ni (51%) > Cd (51%) > Rh (46%) > Zn (43%) > Pd (42%) > Ru/Pt (41%)**。
  → **反応性の高い後期遷移金属**ほど分子を強く引き込み、再配向・解離が起きやすい。
- **比較的安定な表面**: **Ag (30%) / Cu (33%) / Os (34%)**。

---

## 3. 横断的な考察（まとめ）

- **異常終了の“様式”はデータセットごとに質的に異なる**:
  - 酸化物（Comer）→ **表面が崩れる**（unphysical_relaxation）。難しさは**カチオンの酸化物安定性**で決まる。
  - 合金 × 小分子（Mamun）→ **弱吸着種の移動**と**金属上 O\* の局所酸化・PES 不整合**が支配的。
    とくに O\* では、PBE+U 系無機結晶データに強く引っ張られる `mpa`/`omat24` 系 channel が
    金属表面吸着に不適切な PES を出す場合がある。
  - 金属 × 大分子（FG）→ **分子の再配向（migration）**が支配的。難しさは**分子サイズ・芳香族性**で決まる。
- **共通する弱点**: ポスト遷移/典型金属（Cd, Tl, In, Hg, Bi, Sn）と磁性 3d 金属（Mn, Cr, Fe）は
  表面の形でも合金でも MLIP が苦手。逆に**白金族・前期遷移金属は安定して当たる**。
- **吸着種は「動くもの」と「局所酸化を引き起こすもの」が鬼門**。物理吸着の H2O や、表面上で滑る芳香族分子は、
  エネルギー以前に**緩和で初期構造から動いてしまう**ため anomaly になりやすい。加えて、金属上 O\* は
  動かない強吸着種に見えても、表面原子を引き込み、局所酸化・サブサーフェス化・PBE/PBE+U PES 不整合を起こすため、
  MAE_total が大きく壊れることがある。
- **モデル選択の実務的含意**:
  - 酸化物表面 O/OH: `uma-omat`, `sevennet-omat24(-cueq)`, `sevennet-mpa(-cueq)`, `sevennet-matpes_r2scan(-cueq)` が候補。
  - 金属・合金表面 O\* を含む系: `sevennet-matpes_pbe(-cueq)`, `sevennet-oc20(-cueq)`, `uma-oc25` を優先。
    `mpa`/`omat24` は MAE_normal が良くても O\* の anomaly で MAE_total が壊れる場合がある。
  - 金属上の大きな有機分子: D3(BJ) 付き評価を前提に、`sevennet-matpes_r2scan-cueq-d3`,
    `sevennet-omat24-cueq-d3`, `uma-oc25` などを比較する。
- **触媒スクリーニングで MLIP を使う場合**、**(i) 還元されやすい/磁性の金属、(ii) 金属上 O\*、
  (iii) 大きく柔らかい（芳香族）分子**を含む系では、緩和の収束チェック、adsorbate 別 breakdown、
  O\* の構造可視化、DFT 検証を手厚くすべき。

> **方法メモ**: anomaly 率は各データセットの `analysis/per_calculator/<label>_parity.csv`
> （CatBench 分類器の `classification` 列）を全 calculator 分集計したもの。表面元素は reaction key の
> スラブ式（酸化物はカチオン、合金は構成元素）から、FG の金属は key 中の金属トークンから抽出。
> 反応数・最高精度などの数値は各サブ README / `*_summary.csv` に基づく。
> SevenNet-Omni 論文に関する考察は Kim et al., *Optimizing Cross-Domain Transfer for Universal Machine
> Learning Interatomic Potentials*, arXiv:2510.11241 の metallic surfaces 節、とくに Co/Ni + O における
> PBE+U 由来の異常 PES の議論に基づく。
