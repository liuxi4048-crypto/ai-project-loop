#!/usr/bin/env python3
"""ireval: BM25 検索器 + 情報検索の評価(recall@k / MRR / nDCG@k)。

法律QAなど検索拡張(retrieval)型システムの品質は「関連文書を上位に出せるか」で決まる。
本ツールは文書集合に BM25 索引を張り、関連判定付きのクエリ集合に対して
recall@k / MRR / nDCG@k を算出する自己完結の評価ハーネス。Python 3 標準ライブラリのみ・決定論的。

入力(JSON):
    {"documents": [{"id":"d1","text":"..."}, ...],
     "queries":   [{"text":"...","relevant":["d1","d3"]}, ...]}
使い方:
    python ireval.py <data.json> [--k 5] [--json]
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

K1, B = 1.5, 0.75
_TOK = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list:
    return _TOK.findall(text.lower())


class BM25:
    def __init__(self, docs):
        self.ids = [d["id"] for d in docs]
        self.toks = [tokenize(d["text"]) for d in docs]
        self.lens = [len(t) for t in self.toks]
        self.avgdl = sum(self.lens) / len(self.lens) if self.lens else 0
        self.tf = [Counter(t) for t in self.toks]
        self.N = len(docs)
        df = Counter()
        for t in self.toks:
            for term in set(t):
                df[term] += 1
        self.idf = {term: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
                    for term, n in df.items()}

    def score(self, query):
        q = tokenize(query)
        scores = []
        for i in range(self.N):
            s = 0.0
            for term in q:
                if term not in self.tf[i]:
                    continue
                f = self.tf[i][term]
                denom = f + K1 * (1 - B + B * self.lens[i] / self.avgdl)
                s += self.idf.get(term, 0.0) * (f * (K1 + 1)) / denom
            scores.append((self.ids[i], s))
        # スコア降順、同点はid昇順で決定論的に
        return sorted(scores, key=lambda x: (-x[1], x[0]))


def dcg(rels):
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(rels))


def evaluate(bm25, queries, k):
    per_q, rec_sum, rr_sum, ndcg_sum = [], 0.0, 0.0, 0.0
    for qi, q in enumerate(queries, 1):
        ranked = bm25.score(q["text"])
        rel = set(q["relevant"])
        topk = [doc_id for doc_id, _ in ranked[:k]]
        hit = sum(1 for d in topk if d in rel)
        recall = hit / len(rel) if rel else 0.0
        # MRR: 最初の関連文書の順位
        rr = 0.0
        for rank, (doc_id, _) in enumerate(ranked, 1):
            if doc_id in rel:
                rr = 1.0 / rank
                break
        # nDCG@k
        gains = [1.0 if d in rel else 0.0 for d in topk]
        ideal = [1.0] * min(len(rel), k)
        ndcg = dcg(gains) / dcg(ideal) if ideal else 0.0
        rec_sum += recall; rr_sum += rr; ndcg_sum += ndcg
        per_q.append({"query": q["text"], "topk": topk,
                      "recall_at_k": round(recall, 3),
                      "reciprocal_rank": round(rr, 3),
                      "ndcg_at_k": round(ndcg, 3)})
    n = len(queries)
    agg = {"recall_at_k": round(rec_sum / n, 3),
           "mrr": round(rr_sum / n, 3),
           "ndcg_at_k": round(ndcg_sum / n, 3)}
    return per_q, agg


def main() -> int:
    ap = argparse.ArgumentParser(description="BM25 retrieval + IR metrics")
    ap.add_argument("data", type=Path)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    data = json.loads(args.data.read_text(encoding="utf-8"))
    bm25 = BM25(data["documents"])
    per_q, agg = evaluate(bm25, data["queries"], args.k)

    if args.json:
        print(json.dumps({"k": args.k, "per_query": per_q, "aggregate": agg},
                         ensure_ascii=False, indent=2))
    else:
        print(f"{args.data.name}  文書 {bm25.N}  クエリ {len(per_q)}  k={args.k}\n")
        for r in per_q:
            print(f"  Q: {r['query'][:56]}")
            print(f"     top{args.k}={r['topk']}  recall={r['recall_at_k']} "
                  f"RR={r['reciprocal_rank']} nDCG={r['ndcg_at_k']}")
        print(f"\n-- 平均  recall@{args.k}={agg['recall_at_k']}  "
              f"MRR={agg['mrr']}  nDCG@{args.k}={agg['ndcg_at_k']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
