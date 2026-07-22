# biaslens — ニュース文のバイアス検出+中立化

ai-project-loop **Cycle 11** の成果物(2026-07-23)。

## 概要

テキスト中の扇情的・主観的な語(loaded language)を語彙ベースで検出し、中立な言い換え
(または削除)を提案して**中立化テキストを生成**するCLI。編集的断定・扇情的な動詞/形容詞・
レッテル的な名詞を分類して指摘する。Python 3 標準ライブラリのみ・決定論的。

検出カテゴリ: `editorializing`(clearly/obviously/everyone knows…)、`loaded_verb`
(slammed/boasted/admitted…)、`loaded_adj`(disastrous/reckless…)、`labeling`
(regime/propaganda/so-called…)。

## 着想元(11_AI Archive)

- [[2026-07-23-autojourn-multi-perspective-summarisation-bias-detection-and-8dfa]] —
  自動ジャーナリズムで生成ニュースの**バイアス検出と中立化(neutralisation)**、多視点保持を
  行う AutoJourn の論文。本ツールはその「検出→中立化」を、モデル不要の語彙ベースで実装。
- 系譜: 事実照合の [[2026-07-23-reasoning-error-from-known-fact-step-level-self-consistency-484d|stepcheck]] とは異なり、**主観・偏向語**を対象に検出だけでなく書き換えまで行う。

## 使い方

```bash
python biaslens.py sample/article.txt
```

- `--json` で機械可読出力 / `--rewrite-only` で中立化テキストのみ / 終了コード: 検出=1・なし=0

## 動作確認結果(2026-07-23)

偏向を多数含むサンプル記事(bias score 32.04 /100語, 14件検出):

原文(抜粋): *"The regime's new policy is clearly a disastrous mistake. Everyone knows that the so-called reform will fail. … critics slammed the reckless spending."*

中立化後:

> The government's new policy is a significant mistake. The reform will fail. Officials said about the significant plan, but critics criticized the contested spending. The government said the rollout was serious, and the minister did not answer questions about the messaging campaign.

編集的断定の削除・扇情語の言い換え・文頭の再大文字化まで一貫して処理できている。

## 制限事項

- 語彙ベース(固定辞書)。辞書外の偏向・皮肉・文脈依存のバイアスは検出しない
- 語単位の置換のため、文法的に不自然な結果が残ることがある(例: "said about")
- 英語のみ。中立化は「無難化」であり、事実性や多視点性そのものは保証しない
