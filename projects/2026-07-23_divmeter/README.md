# divmeter — 回答多様性メーター(構造化出力の多様性崩壊を定量化)

ai-project-loop **Cycle 17** の成果物(2026-07-23)。

## 概要

同じプロンプト群への回答集合を条件ごと(自由形式 vs 構造化出力など)に受け取り、
**最頻答シェア・異なり数・正規化エントロピー・Simpson多様性**を算出して条件間の
多様性崩壊を可視化するCLI。Python 3 標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- [[2026-07-23-structured-output-collapses-answer-diversity-across-44-langu-bb8d]] —
  「JSONのみで返答」という形式指定がモデルの選ぶ回答を偏らせ、44モデル横断で
  **最頻答シェアが41%→64%、異なり回答が52→36へ低下**したと報告した論文。本ツールはその
  多様性崩壊を測る指標を実装。

## 使い方

```bash
python divmeter.py sample/census.json
```

- 入力: `{"conditions": {"free-form": [...], "json-mode": [...]}}` / `--json` で機械可読出力
- 指標: mode_share(最頻答の割合)/ distinct / norm_entropy(0..1, 1=一様)/ simpson(Gini-Simpson)

## 動作確認結果(2026-07-23)

「動物を1つ挙げよ」への回答(各25件)で、自由形式→JSON形式の崩壊を再現:

```
     condition    n distinct mode_share  norm_H  simpson
     free-form   25        9       0.40   0.814    0.771
     json-mode   25        5       0.64   0.663    0.541
-- json-mode は free-form 比: 異なり -4 / 最頻答シェア +24.0% / Simpson -0.230 → 多様性が崩壊
```

最頻答シェア 0.40→0.64 は**論文の 41%→64% とほぼ一致**、異なり数の減少(9→5)も
論文の 52→36 と同方向。エントロピー・Simpson もそろって低下し、崩壊を定量化できている。

## 制限事項

- 回答は文字列完全一致で集計(casefold のみ)。言い換え・表記ゆれは別回答扱い
- サンプルは小規模の再現デモ(論文は31プロンプト×44モデルの大規模実測)
- 多様性の「良し悪し」は用途次第(創作は高多様性が良いが、抽出タスクは一貫性が良い)
