# fundflow — AI投資・資金調達のディールフロー分析

ai-project-loop **Cycle 39** の成果物(2026-07-23)。

## 概要

AI分野の投資・資金調達イベント(日付・投資家・調達先・金額)を集計し、**総額・調達先/投資家
ランキング・ディールサイズ分布・調達先の資本集中度(HHI)・最大ディール**を算出する
ディールフロー分析ツール。標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- 本サイクル時点のアーカイブは、AI投資・資金調達ニュースのクラスタが目立っていた:
  [[2026-07-23-amd-commits-up-to-5-billion-to-anthropic-ad3e]] /
  [[2026-07-22-samsung-deepens-its-ai-empire-with-a-potential-billion-euro-88f9]] /
  [[2026-07-23-travis-kalanick-s-robotics-company-raises-1-7b-led-by-a16z-9002]] など。
  この横断テーマ(資本流入の波)を切り口に、資本の流れを定量化する分析器を実装。

## 使い方

```bash
python fundflow.py sample/deals.json
```

- 入力: `{events:[{date,investor,recipient,amount_usd}]}` / `--json` で機械可読出力

## 動作確認結果(2026-07-23)

アーカイブの投資クラスタから編纂した6件(金額は概算):

```
投資イベント 6件  総額 $8.9B
調達先ランキング: Anthropic $5.75B(65%) / Kalanick Robotics $1.70B / Mistral $1.10B …
ディールサイズ: >=$1B 3件 / $100M-1B 2件 / <$100M 1件
最大ディール: AMD → Anthropic $5.00B
-- 調達先集中度HHI 0.474（高集中：資本が少数の研究所へ）
```

総額の65%が Anthropic に集まり、HHI 0.474 で高集中。アーカイブが示す「AI資本が少数の
フロンティア研究所へ集中する」構図を定量化できている。

## 制限事項

- サンプルはアーカイブの投資ニュースから編纂した**概算値**(公式財務データではない)
- 為替は単純に USD 換算(€→$ の概算)。ラウンド種別・バリュエーションは扱わない
- capex(自社インフラ投資)と外部投資を区別しない ― 明確な「投資→調達先」イベントのみを対象
