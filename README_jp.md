# mlip-adsorption-energy-benchmark

[English](README.md) | **日本語**

機械学習原子間ポテンシャル (MLIP) の **吸着エネルギー予測精度** を DFT 参照値に対して
ベンチマークするための薄いワークフロー層です。

- ベンチマーク本体（データセット・緩和計算・解析/レポート）:
  [CatBench](https://github.com/JinukMoon/catbench)
- MLIP calculator の生成（UMA / SevenNet / MatterSim / CHGNet / NequIP を統一 API で）:
  [ase-calculator-kit](https://github.com/ishikawa-group/ase-calculator-kit)

本リポジトリは上記 2 つを繋ぎ、コマンド 1 つでローカル実行・TSUBAME4 へのジョブ投入が
できるようにしたものです。

> **命名について**: Python のパッケージ名にハイフンは使えないため、`src/` 配下の
> import 名は `mlip_adsorption_energy_benchmark`（アンダースコア）です。
> 設定ファイルも慣習に従い `pyproject.toml` を使用しています。

## このリポジトリの目的（CatBench に加えて）

[CatBench](https://github.com/JinukMoon/catbench) がデータセット・緩和計算・解析を提供します。
本リポジトリはその上に薄い層を足し、**新しい MLIP（や新しい modal / task / 分散補正の variant）が
リリースされたときに、すぐ自分たちの環境で検証・比較できる**ことを狙いとしています。

- **統一 API でモデルを差し込む**。新しい calculator は
  [ase-calculator-kit](https://github.com/ishikawa-group/ase-calculator-kit) 経由で扱えるため、
  出たばかりのモデルの追加も通常は preset/spec の 1 行変更で済み、モデルごとの繋ぎコードが不要。
- **1 コマンドでローカルでもクラスタでも**。同じコマンドでローカル実行、または TSUBAME4 に
  （データセット × calculator）ごとにジョブ投入でき、全モデル・全データセットを並列に回せる。
- **自前のレポート**。サマリ表・ヒートマップ・Pareto 図・calculator ごとの parity 図で、
  横並び比較と anomaly 解析をすぐに行える。

要するに、CatBench が「ベンチマークのエンジン」、本リポジトリは最新 MLIP に追随して
モデル比較を再現可能に保つための「自分たち用のハーネス」です。

## ディレクトリ構成

```
mlip-adsorption-energy-benchmark/
├── src/mlip_adsorption_energy_benchmark/  # パッケージ本体（関数 + CLI）
│   ├── calculators.py   # calculator preset 定義 + build_calculator()
│   ├── benchmarks.py     # データセット定義 + ダウンロードキャッシュ
│   ├── runner.py         # CatBench 実行ラッパ（出力レイアウト制御）
│   ├── analysis.py       # 解析ラッパ（parity plot / Excel / summary CSV）
│   └── cli/              # 実行用 CLI（python -m ...cli.<name> で起動）
│       ├── run.py        # ベンチマーク実行
│       ├── analyze.py    # 結果解析
│       └── visualize.py  # 結果可視化
├── result/               # 出力: result/<benchmark>/<calculator>/（git 管理外）
├── data/                 # データセットのダウンロードキャッシュ（git 管理外）
└── scripts/tsubame4/     # TSUBAME4 ジョブ投入
    ├── run_tsubame_benchmark.sh
    └── submit_tsubame_jobs.py
```

## 対応 calculator（preset）

`--calculator` には `all` または以下のプリセット名（カンマ区切り）を指定します。
吸着エネルギー向けに task/modal のデフォルトを設定済みです（CLI で上書き可能）。

| preset      | backend   | デフォルト設定                    | 備考 |
|-------------|-----------|-----------------------------------|------|
| `uma`       | uma       | `model=uma-s-1p2`, `task=oc20`    | 触媒/吸着タスク |
| `sevennet`  | sevennet  | `model=7net-omni`, `modal=mpa`    | 多忠実度（PBE+U） |
| `mattersim` | mattersim | `model=5M`                        | 汎用 |
| `chgnet`    | chgnet    | （バンドル既定）                  | 軽量・汎用 |
| `nequip`    | nequip    | `model=L`                         | OAM（MPS 非対応） |

### variant（同じ計算機の別設定）を一度に流す

`--calculator` の各要素は `preset:key=value` 形式で model/task/modal を指定でき、
variant ごとに **別フォルダ・別ジョブ** になります（複数 variant はカンマ区切り）。

```
uma:task=oc22            -> result/<benchmark>/uma-oc22/
sevennet:modal=omat24    -> result/<benchmark>/sevennet-omat24/
nequip:model=m           -> result/<benchmark>/nequip-m/
chgnet:model=0.3.0       -> result/<benchmark>/chgnet-0.3.0/
```

preset 名のみ（または `all`）の場合はラベル＝preset 名（既定設定）になります。

## 対応 benchmark（データセット）

CatBench が Zenodo から取得するデータセット名をそのまま指定します。主なもの:

- `MamunHighT2019` — 2,035 二元合金上の小分子吸着（約 45k）
- `ComerGeneralized2024` — 金属酸化物上の吸着（325）
- `BM_dataset` — 大型分子 32 個（小さく動作確認向き）
- ほか `OC20-Dense`, `GameNetOx_oxide`, `FG_dataset`

## インストール

Python は `>=3.12,<3.14`（ase-calculator-kit の制約）。CUDA 環境推奨。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

依存（CatBench / ase-calculator-kit）は GitHub から取得します。`.venv` は git 管理外です。

## ローカル実行

CLI はパッケージのサブモジュールとして `python -m` で起動します
（`pip install -e .` 済みならそのまま、未インストールなら先頭に `PYTHONPATH=src` を付与）。

```bash
# 1 calculator を 1 データセットで（動作確認は小さい BM_dataset を CPU で）
python -m mlip_adsorption_energy_benchmark.cli.run --benchmark BM_dataset --calculator chgnet --device cpu

# 全 calculator を逐次実行（GPU 推奨）
python -m mlip_adsorption_energy_benchmark.cli.run --benchmark MamunHighT2019 --calculator all --device cuda

# 解析（parity plot + Excel レポート + サマリ CSV）
python -m mlip_adsorption_energy_benchmark.cli.analyze --benchmark MamunHighT2019

# 可視化（catbench.org 風: 指標ヒートマップ表 + Pareto 散布図）
python -m mlip_adsorption_energy_benchmark.cli.visualize --benchmark MamunHighT2019
```

出力は `result/<benchmark>/<calculator>/` に格納されます。

### 可視化（`cli/visualize.py`）

`analyze.py` が出力する **`result/<benchmark>/<benchmark>_summary.csv`** を読み、
[catbench.org](https://catbench.org) 風の図を `result/<benchmark>/viz/` に生成します。

- **指標ヒートマップ表**: 1 行 = 1 モデル、列 = 各指標（MAE / Normal% / anomaly 内訳 /
  ADwT / AMDwT / Time/step 等）。各列を **viridis** で独立に色付け（明るい = 良い）し、
  セルに実数値を表示、colorbar 付き。
- **単一指標の棒グラフ**: MAE_total / MAE_normal / Time/step を**良い順**に並べた横棒グラフ
  （3 指標を1枚に縦並び、viridis カラーバー付き＝明るいほど良い）。
- **Pareto 散布図**: Time/step vs Total MAE、Time/step vs Normal MAE
  （Accuracy-Efficiency）、Time/step vs Normal rate%（Robustness-Efficiency）。
  点は MAE で viridis 着色（明るい=良い）。
- **計算機ごとの詳細 parity 図**（`viz/per_calculator/`）: 各 calculator の予測 vs DFT を
  **Total** と **Normal（anomaly/migration 除外）**の2パネルで出力。点は**吸着種で色分け**。
  Normal/anomaly の分類は CatBench 本体の分類器（`_anomaly_detection`）を再利用するため
  公式数値と一致。あわせて `<label>_parity.csv` と CatBench の吸着種別ブレークダウン
  `<label>_adsorbate_breakdown.csv` も出力。`--no-per-calculator` で無効化可。
- 出力: 静的 `*_heatmap.png` / `*_scatter.png` /（per-calc）`<label>_parity.png` と
  インタラクティブ `*_dashboard.html` /（per-calc）`<label>_parity.html`（plotly）。

> `analyze.py` を先に実行してサマリ CSV を作成してください。

## TSUBAME4 でのジョブ投入

`(benchmark × calculator)` ごとに 1 ジョブを投入し、各 calculator を別 GPU で並列実行します。

```bash
# clone 後、計算ノードで仮想環境を作成（前述のインストール手順）

# MamunHighT2019 と ComerGeneralized2024 を全 calculator 分まとめて投入
python scripts/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 \
    --calculator all

# 投入せずコマンドだけ確認
python scripts/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 --calculator all --dry-run
```

- ジョブ設定: `-g tga-ishikawalab`、`gpu_h=1`、`h_rt=24:00:00`、`module load cuda`
- デバイス既定は `cuda`
- ログは `result/<benchmark>/log/tsubame_jobs/<calculator>/` に出力

主な引数: `--device`, `--n-seeds`, `--mode`, `--model/--task/--modal`（preset 上書き）,
`--group`, `--save-files`, `--cueq`, `--dry-run`。

`--dispersion` は Grimme-D3(BJ) 分散力補正を有効化します。汎函数(xc)は
ase-calculator-kit (>= v0.2.2) の方針表に従い model/modal/task ごとに自動選択され
（例: OC20=RPBE, それ以外の多くは PBE, r2SCAN系=r2scan）、訓練時に分散を含むモデル
（UMA `oc25` 等）は二重計上を避けるため拒否されます。結果は **`<label>-d3`** の別ディレクトリに保存。

`--cueq` は SevenNet の CuEquivariance を有効化します（cuequivariance 導入環境が必要）。
結果は **`<label>-cueq`**（例 `sevennet-mpa-cueq`）の別ディレクトリ・別ジョブに保存され、
非 cueq の結果を上書きしません（`--cueq --dispersion` 併用時は `<label>-cueq-d3`）。例:

```bash
python scripts/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 --device cuda --cueq \
    --calculator "sevennet:modal=mpa,sevennet:modal=omat24,sevennet:modal=matpes_pbe,sevennet:modal=oc20,sevennet:modal=oc22,sevennet:modal=matpes_r2scan"
```

> **inode（ファイル数）に関する注意**
> CatBench は `save_files=True` だと構造ごとに `log/<key>/`・`traj/<key>/` を作成し、
> 大規模データ（例: MamunHighT2019 は ~45k 吸着）では 1 ジョブあたり数万ファイルに達して
> 共有ファイルシステムの **inode クォータ**を使い切ります（`OSError: [Errno 122]
> Disk quota exceeded`。容量に余裕があっても起きます）。
> このため TSUBAME 投入は **既定で per-structure ファイルを出力しません**
> （`run_benchmark.py` に `--no-save-files` を渡す）。結果は `*_result.json` 等の小さな
> JSON のみで、MAE/parity 解析には十分です。trajectory が必要な場合のみ `--save-files` を付与。

### 再開（resume）— 大規模データが walltime で切れた場合

MamunHighT2019（~45k 吸着）のような大規模データは 1 ジョブの 24h walltime 内に
終わらないことがあります。CatBench は `*_structure_cache.json` から **自動で続きを再開**
（計算済み構造は `Skipping already calculated` でスキップ）するため、**同じコマンドで
再投入するだけで続きから完了**できます。計算は無駄になりません。

```bash
# 24h 後など、未完了ジョブだけを再投入（同じ --calculator / 設定で）
python scripts/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 --device cuda \
    --calculator "<初回と同じ spec>"
```

- 既定で **完了済み**（`result/<benchmark>/<label>/<label>_result.json` がある）calculator は
  自動スキップし、**未完了/時間切れのものだけ resume** します。
- **重要**: 途中経過 `result/<benchmark>/result/<label>/`（cache 含む）を消さないこと。
- 完了済みも含めて最初から再計算したい場合のみ `--rerun-completed` を付けます。
- 再開が確実に効く条件は「relaxation 設定（`--f-crit-relax` / `--n-crit-relax` / `--mode` 等）を
  初回と同一にすること」。変更するとキャッシュは破棄され再計算されます。

## 謝辞・引用

本リポジトリは 2 つのオープンソースツールの上に載せた薄いワークフロー層です。利用する
場合は以下を引用・クレジットしてください。

- **CatBench** — 本ベンチマークのフレームワーク・分類器・データセットの出典。
  Moon et al., "CatBench framework for benchmarking machine learning interatomic
  potentials in adsorption energy predictions for heterogeneous catalysis,"
  *Cell Reports Physical Science* (2025).
  - コード: <https://github.com/JinukMoon/CatBench>（DOI: 10.5281/zenodo.17172022）
  - データセット: <https://doi.org/10.5281/zenodo.17157086> ／ <https://catbench.org>
  - 本リポジトリのベンチマークデータセット（ComerGeneralized2024, MamunHighT2019,
    FG_dataset など）は CatBench 経由で Zenodo から取得しており、**DFT 吸着エネルギーの
    参照値はすべて CatBench のデータセット集に由来します。**
- **ase-calculator-kit** — MLIP calculator を統一生成する依存ツール:
  <https://github.com/ishikawa-group/ase-calculator-kit>

## English version

[README.md](README.md) を参照してください。
