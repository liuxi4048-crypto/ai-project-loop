# groundcheck — 生成回答の根拠づけ(幻覚)検証

ai-project-loop **Cycle 34** の成果物(2026-07-23)。

## 概要

生成回答の各主張(文)が提供ソースに根拠づけられているかを事後検証するCLI。各主張の内容語が
いずれかのソースにどれだけ**被覆(containment)**されるかを測り、閾値未満の主張を「根拠なし=
幻覚候補」として検出、全体の根拠率とゲート判定を出す。標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- [[2026-07-21-zero-hallucination-by-construction-hallucination-aware-layer-2f2b]] —
  LLMが本質的に非根拠テキスト(幻覚)を生成しうる前提で、**事後検証と信頼確保の階層的監視**で
  根拠性を担保するフレームワーク。本ツールはその要である「主張のソース根拠づけ検証」を実装。
- 系譜: 内部整合を見る [[2026-07-23-reasoning-error-from-known-fact-step-level-self-consistency-484d|stepcheck]] と異なり、こちらは**回答のソース被覆(RAG忠実性/attribution)**が対象。

## 使い方

```bash
python groundcheck.py sample/qa.json
```

- 入力: `{sources:[{id,text}], answer, threshold}` / `--json` で機械可読出力
- 終了コード: 全主張が根拠あり=0・根拠なしあり=1

## 動作確認結果(2026-07-23)

2ソースに対し、2つは正しく根拠づけられ、1つは捏造(アルキメデスが自作)の回答:

```
  ✓ [s1 cov 1.0] … ancient Greek device to predict astronomical positions …
  ✓ [s2 cov 1.0] … discovered in 1901 in a shipwreck and contains thirty bronze gears
  ✗ 根拠なし(幻覚候補, cov 0.2) … personally built by the mathematician Archimedes
-- 根拠率 2/3 = 67%  → ✗ 1件の根拠なし主張(不合格)
```

ソースに無い「アルキメデスが自作」主張を幻覚候補として検出し、根拠づけられた主張は通過。
事後検証による幻覚検出とゲートを正しく行えている。

## 制限事項

- 語彙被覆ベース(軽い語幹化のみ)。言い換え・含意・数値の含意関係は判定しない(埋め込み/NLIが必要)
- 文単位の主張分割。1文に複数主張が混在すると粒度が粗い
- 高被覆でも意味的に誤り(同じ語で逆の主張)を捉えない ― あくまで一次スクリーニング
