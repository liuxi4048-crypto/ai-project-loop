# prf — 擬似関連性フィードバック(PRF)によるクエリ拡張

ai-project-loop **Cycle 26** の成果物(2026-07-23)。

## 概要

BM25 の一次検索の上位 k 件を「関連」とみなし、そこに**跨って現れる語**でクエリを拡張して
再検索する擬似関連性フィードバック(PRF)。クエリと語彙のずれた関連文書(例: 「car」と
書かず「vehicle/engine」と書く文書)を上位に引き上げる。標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- [[2026-07-23-plaid-prf-pseudo-relevance-feedback-with-centroid-like-token-74e6]] —
  ColBERT系マルチベクトル検索 PLAID に PRF を適用し、**上位検索結果に基づきクエリを再構成**する
  PLAID-PRF。本ツールはその中核「上位結果からクエリを拡張して再検索する」を BM25 上で実装。
- 系譜: 検索評価 [[2026-07-23-ailqa-evaluating-ai-driven-legal-question-answering-systems-15e7|ireval]] と同じ BM25 基盤だが、こちらは**クエリ拡張という検索手法**そのもの。

## 使い方

```bash
python prf.py sample/cars.json
```

- 入力: `{query, relevant:[id], documents:[{id,text}], top_k, expansion_terms, recall_k}`
- `--json` で機械可読出力

## 動作確認結果(2026-07-23)

クエリ「fast car」。関連文書 veh は "vehicle engine acceleration…" でクエリ語を一切含まない:

```
  一次検索 top3: [c1, c2, n1]  recall@3=0.67   ← veh は6位(語彙不一致で埋もれる)
  拡張語: [acceleration, engine]                ← 擬似関連上位2件に跨って出る語
  二次検索 top3: [c1, c2, veh]  recall@3=1.00   ← veh が3位へ
  veh: 6 → 3 ↑改善
```

「fast car」と一語も共有しない veh を、上位結果由来の拡張語で surface し、recall@3 を
0.67→1.00 に改善。PRF が語彙ミスマッチを橋渡しする効果を再現できている。

## 制限事項

- 拡張語は「擬似関連上位に跨って出る語」を優先(RM3 的)。上位が実際は無関連だと拡張が逆効果(query drift)
- BM25 の語彙一致ベース。真の意味的橋渡し(埋め込み/ColBERT)には及ばない
- 拡張語数・top_k は固定入力。適応的な重み付け(Rocchio 係数の調整)は未実装
