# rubric-score — 宣言的ルーブリックのエッセイ採点+フィードバック生成

ai-project-loop **Cycle 10** の成果物(2026-07-23)。

## 概要

重み付き評価基準を書いたルーブリック(JSON)に対しエッセイを採点し、**基準ごとのサブスコアと
具体的な改善フィードバック**を返す透明・決定論的なスコアラ。点数だけでなく「なぜその点か・
どう直すか」を出す。Python 3 標準ライブラリのみ。

基準タイプ:

| type | 内容 |
|------|------|
| `metric` | 表層特徴(段落数/語数/平均文長/接続詞数/語彙多様性)を `ideal` 範囲と比較し、`hard` 境界へ線形減衰 |
| `keywords` | 内容カバレッジ(`all`: 全必須 / `any`: いずれか必須) |

## 着想元(11_AI Archive)

- [[2026-07-23-beyond-score-prediction-llm-based-essay-scoring-and-feedback-3126]] —
  自動エッセイ採点を「スコア予測」に留めず、**ルーブリック報酬**と**ルーブリックベースの
  フィードバック評価(RFE)**でフィードバック品質まで改善する RLAES の論文。本ツールはその核心
  (ルーブリックに基づく採点+構造化フィードバック)を、RL・モデル不要の透明な形で実装。

## 使い方

```bash
python rubric_score.py sample/rubric.json sample/essay_strong.txt
```

- `--json` で機械可読出力

## 動作確認結果(2026-07-23)

同一ルーブリック(structure/development/clarity/cohesion/lexical/content の6基準)で、
強い作文と弱い作文を明確に分離:

```
essay_strong.txt   総合 100.0 / 100   （全基準を満たす）
essay_weak.txt     総合  32.9 / 100
  - [structure]        paragraph_count=1  → 段落を増やす
  - [development]      word_count=56      → 展開を増やす
  - [sentence_clarity] avg_sentence_len=56 → 一文を短く
  - [cohesion]         connective_count=2  → 接続表現を増やす
  - [content]          benefit/advantage/culture/career のいずれかが必要
```

弱い作文(1段落・56語の一文・キーワード欠落)の各弱点を基準別に指摘できている。

## 制限事項

- 採点は表層特徴とキーワードのヒューリスティック(意味理解・論証の妥当性は判定しない)
- 高度な言い換えで基準を満たす/満たさないケースは取りこぼし得る(語彙多様性など)
- ルーブリックの設計品質がそのまま採点品質を決める(基準・範囲・重みは要調整)
