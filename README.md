# mlip-adsorption-energy-benchmark

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

## ディレクトリ構成

```
mlip-adsorption-energy-benchmark/
├── src/mlip_adsorption_energy_benchmark/  # ベンチマーク用の関数群
│   ├── calculators.py   # calculator preset 定義 + build_calculator()
│   ├── benchmarks.py     # データセット定義 + ダウンロードキャッシュ
│   ├── runner.py         # CatBench 実行ラッパ（出力レイアウト制御）
│   └── analysis.py       # 解析ラッパ（parity plot / Excel）
├── code/                 # 実行用 CLI
│   ├── run_benchmark.py  # ベンチマーク実行
│   └── analyze.py        # 結果解析
├── result/               # 出力: result/<benchmark>/<calculator>/（git 管理外）
├── data/                 # データセットのダウンロードキャッシュ（git 管理外）
└── script/tsubame4/      # TSUBAME4 ジョブ投入
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

```bash
# 1 calculator を 1 データセットで（動作確認は小さい BM_dataset を CPU で）
python code/run_benchmark.py --benchmark BM_dataset --calculator chgnet --device cpu

# 全 calculator を逐次実行（GPU 推奨）
python code/run_benchmark.py --benchmark MamunHighT2019 --calculator all --device cuda

# 解析（parity plot + Excel レポート）
python code/analyze.py --benchmark MamunHighT2019
```

出力は `result/<benchmark>/<calculator>/` に格納されます。

## TSUBAME4 でのジョブ投入

`(benchmark × calculator)` ごとに 1 ジョブを投入し、各 calculator を別 GPU で並列実行します。

```bash
# clone 後、計算ノードで仮想環境を作成（前述のインストール手順）

# MamunHighT2019 と ComerGeneralized2024 を全 calculator 分まとめて投入
python script/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 \
    --calculator all

# 投入せずコマンドだけ確認
python script/tsubame4/submit_tsubame_jobs.py \
    --benchmark MamunHighT2019,ComerGeneralized2024 --calculator all --dry-run
```

- ジョブ設定: `-g tga-ishikawalab`、`gpu_h=1`、`h_rt=24:00:00`、`module load cuda`
- デバイス既定は `cuda`
- ログは `result/<benchmark>/log/tsubame_jobs/<calculator>/` に出力

主な引数: `--device`, `--n-seeds`, `--mode`, `--model/--task/--modal`（preset 上書き）,
`--group`, `--dry-run`。

## 英語版

[README_en.md](README_en.md) を参照してください。
