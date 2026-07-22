# optmem — 学習メモリ/オプティマイザ状態プランナ

ai-project-loop **Cycle 13** の成果物(2026-07-23)。

## 概要

モデル仕様(JSON)から、学習時メモリ(**重み+勾配+オプティマイザ状態**)を方式別に計算し、
パラメータ種別ごとに状態表現を変える**Tiered State Allocation**の削減効果を出すプランナ。
Python 3 標準ライブラリのみ・決定論的。GB = 10^9 バイト。

状態バイト/パラメータ: `adamw_fp32`=8(m4+v4) / `adamw_bf16`=4 / `adamw_8bit`=2 / `sgd_momentum`=4。

## 着想元(11_AI Archive)

- [[2026-07-23-where-should-optimizer-state-live-tiered-state-allocation-fo-b4ba]] —
  MoE学習でオプティマイザ状態がメモリ最大項になること(bf16重み12.6GBのAdamW更新に
  モーメント約50.6GB)を示し、密バックボーン/エキスパート/ルータで状態表現を変える
  **SkewAdam / Tiered State Allocation** を提案した論文。本ツールはその見積りを再現・一般化する。
- 関連: ローカルLLMのVRAM制約 [[ai-agent-lab-project]] のメモリ計画にも使える。

## 使い方

```bash
python optmem.py sample/moe.json
```

- spec: `weight_dtype_bytes` / `grad_dtype_bytes` / `groups[{name,params}]` / `tier{group:scheme}`
- `--json` で機械可読出力

## 動作確認結果(2026-07-23)

論文の例(6.3B MoE, bf16重み12.6GB)を再現:

```
          scheme  state(GB)  total(GB)
      adamw_fp32       50.4       75.6      ← 論文の「約50.6GB」を再現
      adamw_8bit       12.6       37.8
tiered(SkewAdam風)      24.9       50.1  ★
  - backbone 1.9B  adamw_fp32 → 15.2GB
  - experts 4.25B  adamw_8bit →  8.5GB   ← 多数・疎な更新は低精度状態で十分
  - router  0.15B  adamw_fp32 →  1.2GB
-- tiered は adamw_fp32 比で 25.5GB 削減 (33.7%)
```

AdamW全fp32の50.4GB状態を、種別ごとの割当で24.9GBへ圧縮できることを定量化。

## 制限事項

- 状態バイト数は代表的実装の近似(実際は8bit最適化のブロック単位スケール等で微増)
- アクティベーション・一時バッファ・並列化(ZeRO/シャーディング)は含まない(状態項に限定)
- パラメータ群の分割は spec 入力に依存(モデル構造の自動解析はしない)
