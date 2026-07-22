# ireval — BM25検索 + 情報検索評価(recall@k / MRR / nDCG@k)

ai-project-loop **Cycle 16** の成果物(2026-07-23)。

## 概要

文書集合に **BM25** 索引を張り、関連判定付きクエリ集合に対して **recall@k / MRR / nDCG@k** を
算出する自己完結の検索評価ハーネス。法律QAなど検索拡張(retrieval)型システムの「関連文書を
上位に出せるか」を測る。Python 3 標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- [[2026-07-23-ailqa-evaluating-ai-driven-legal-question-answering-systems-15e7]] —
  埋め込み・検索を用いた法律QAシステムの評価基盤を構築する AILQA の論文。本ツールはその
  「検索精度を関連判定付きで評価する」部分を、BM25 と標準IR指標でモデル不要に実装。
- 系譜: 評価の落とし穴を扱う [[2026-07-23-benchmarking-generalization-in-financial-statement-fraud-det-c3d9|splitaudit]] と同じ「評価」テーマだが、こちらは**検索ランキングの品質**が対象。

## 使い方

```bash
python ireval.py sample/legal.json --k 3
```

- 入力: `{"documents":[{id,text}], "queries":[{text,relevant:[id]}]}` / `--json` で機械可読出力
- BM25パラメータ k1=1.5, b=0.75。同点は id 昇順で決定論的に順位付け

## 動作確認結果(2026-07-23)

法律6文書・7クエリ(うち2件は関連文書2つ)で、k を変えて指標が正しく振る舞う:

```
k=1:  平均 recall@1=0.857  MRR=1.0  nDCG@1=1.0
        （複数関連クエリは top1 に1件しか入らず recall@1=0.5）
k=2:  平均 recall@2=1.0    MRR=1.0  nDCG@2=1.0
        （2件目の関連文書も top2 に surface）
```

BM25 は全クエリで関連文書を1位に検索(MRR=1.0)。複数関連クエリで recall@k が
k とともに 0.857→1.0 へ増える、標準的なIR指標の挙動を再現できている。

## 制限事項

- 語彙一致ベースの BM25(意味的類似・言い換えは埋め込み検索に劣る)。同義語展開は未実装
- 関連判定は二値(段階的関連度 graded relevance には未対応、nDCG は 0/1 ゲイン)
- トークン化は英数字の単純分割。ストップワード除去・ステミングはしない
