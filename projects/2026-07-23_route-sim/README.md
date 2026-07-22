# route-sim — 予算校正リカバリールーティングのシミュレータ

ai-project-loop **Cycle 9** の成果物(2026-07-23)。

## 概要

コーディングエージェントの失敗回復で、「安モデル→高モデル」への機械的エスカレートと、
実行フィードバックで校正した回復配分を、**同一の乱数実現・固定予算**で比較するシミュレータ。
Python 3 標準ライブラリのみ・シード固定で再現可能。

モデル: まず全タスクに安モデルを1回試す(必須, コスト N)。残予算 `R = budget - N` を回復に配分。

| 方策 | 回復の使い方 |
|------|------|
| `cheap-only` | 回復なし(安1回のみ) |
| `always-escalate` | 失敗タスクを出現順に高モデルへ、Rが尽きるまで(従来) |
| `budget-calibrated` | フィードバック d̂ から各失敗タスクの「1コストあたり期待回復利得」を見積り、価値の高い回復(安で再試行 or 高モデル)を優先配分 |

## 着想元(11_AI Archive)

- [[2026-07-23-coderescue-budget-calibrated-recovery-routing-for-coding-age-411e]] —
  従来は安→高へ機械的エスカレートしていた回復を、**実行フィードバックで予算校正**し
  安モデルでの回復を最大化する CodeRescue の着想。本ツールはその効果を制御実験で可視化する。
- 系譜: Cycle 2 [[2026-07-22-validating-distributed-llm-serving-benchmarks-with-nvidia-sr-f347|pareto-sweep]] はコスト/品質の静的探索、本ツールは**動的なルーティング方策**の比較(別軸)。

## 使い方

```bash
python route_sim.py --tasks 300 --budget 400 --cost-exp 5 --seed 0
```

- `--json` で機械可読出力

## 動作確認結果(2026-07-23)

```
tasks=300  budget=400  cost(cheap=1, exp=5)  seed=0
            policy  solved   spent  solved/100cost
        cheap-only     134     300           44.67
   always-escalate     150     400           37.50
 budget-calibrated     184     400           46.00  ★
-- budget-calibrated は always-escalate 比で解決数 +22.7%(同一予算 400)
```

複数シードで budget-calibrated が常に解決数最多。`seed=7` では**高モデル乱用を避け、
より少ない予算(625 < 700)でより多く解決**(216 vs 207)。予算が潤沢になるほど両者の差は
縮む(どちらも全失敗をエスカレートできるため)——現実的な挙動。

## 制限事項

- 成功確率・コスト・フィードバック雑音は簡略な合成モデル(実エージェントのlog校正ではない)
- 回復は1タスク1アクション(安再試行→さらに高モデル、の多段回復は未モデル化)
- calibrated の配分は d̂ ベースの貪欲(厳密な予算付きナップサック最適化ではない)
