# pareto-sweep — 宣言的パラメータ掃引 + Pareto分析ランナー

ai-project-loop **Cycle 2** の成果物(2026-07-22)。

## 概要

設定ファイル1つで、任意のコマンドをパラメータグリッド上に掃引し、各実行の stdout から
指標を抽出して **Pareto最適な設定** を割り出すCLI。Python 3 標準ライブラリのみ(依存ゼロ)。

「設定を変えて回し、速度と品質のトレードオフを見たい」対象なら、LLMサービングに限らず
何にでも使える(コンパイルフラグ、バッチサイズ、スレッド数、量子化ビット幅…)。

## 着想元(11_AI Archive)

- [[2026-07-22-validating-distributed-llm-serving-benchmarks-with-nvidia-sr-f347]] —
  NVIDIA srt-slurm の「宣言的YAML → 再現可能なベンチマーク → パラメータスイープ → Pareto分析」。
  本ツールはそのコアを、SLURMもクラスタも要らない **ローカル・依存ゼロ版** として再構成したもの
  (設定はYAMLの代わりに標準ライブラリのJSONで宣言)。

## 使い方

```bash
python sweep.py examples/serving.json --csv out.csv
```

設定(JSON):

```json
{
  "command": "python serving_bench.py --workers {workers} --batch {batch}",
  "grid": {"workers": [1,2,4,8], "batch": [8,16,32,64]},
  "metrics": {
    "throughput": {"pattern": "throughput=([0-9.]+)", "goal": "max"},
    "latency_ms": {"pattern": "latency_ms=([0-9.]+)", "goal": "min"}
  },
  "repeat": 1
}
```

- `command`: `{param}` プレースホルダを持つコマンドテンプレート
- `grid`: 各パラメータの候補値。直積で全組合せを掃引
- `metrics`: stdout から値を取る正規表現(第1グループを float 化)と最適化方向 `max`/`min`
- `repeat`: 各設定の実行回数(平均を取る)。`cwd`: コマンド実行ディレクトリ(既定=設定ファイルの場所)
- `--csv PATH` で結果をCSV出力、`--quiet` で進捗抑制

## 動作確認結果(2026-07-22)

`examples/serving.json`(待ち行列モデルで throughput/latency を決定論的に模擬する
`serving_bench.py` を対象)で 16 設定を掃引:

```
     workers  batch  throughput  latency_ms  pareto
           8      8      56.889      18.000   ★ PARETO
           8     16     102.400      24.000   ★ PARETO
           8     32     170.667      36.000   ★ PARETO
           8     64     256.000      60.000   ★ PARETO
-- 16 configs swept, 4 on the Pareto frontier
```

throughput最大・latency最小方向で Pareto 最適4点(いずれも workers=8。batch を上げて
スループットと遅延を交換する曲線)を正しく検出。指標が2つのときは ASCII 散布図も出力する。

## 制限事項

- 指標は stdout からの正規表現抽出のみ(構造化ログ/ファイル出力の対象は未対応)
- グリッド全数掃引(ベイズ最適化などの賢い探索はしない)。組合せ数に比例して時間がかかる
- ASCII散布図は指標がちょうど2つのときのみ
