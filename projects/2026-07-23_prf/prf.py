#!/usr/bin/env python3
"""prf: 擬似関連性フィードバック(PRF)で検索クエリを拡張し、語彙不一致の関連文書を浮上させる。

PRF は「一次検索の上位k件は関連しているとみなし、そこから抽出した語でクエリを拡張して
再検索する」手法。クエリと語彙がずれた関連文書(例: 「car」と書かず「vehicle/engine」と
書く文書)を surface できる。本ツールは BM25 の一次検索→上位から拡張語抽出→二次検索を行い、
関連文書の順位と recall の改善を可視化する。標準ライブラリのみ・決定論的。

入力(JSON): {"query":"...", "relevant":["d2",...], "documents":[{"id","text"}...],
             "top_k":2, "expansion_terms":3}
使い方:
    python prf.py <data.json> [--json]
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
_TOK = re.compile(r"[a-z']+")
STOP = {"a", "an", "the", "of", "and", "on", "in", "into", "has", "have", "is",
        "for", "to", "s", "with", "delivers"}


def tok(t):
    return [w for w in _TOK.findall(t.lower()) if w not in STOP]


class BM25:
    def __init__(self, docs):
        self.ids = [d["id"] for d in docs]
        self.toks = [tok(d["text"]) for d in docs]
        self.lens = [len(t) for t in self.toks]
        self.avgdl = sum(self.lens) / len(self.lens)
        self.tf = [Counter(t) for t in self.toks]
        self.N = len(docs)
        df = Counter()
        for t in self.toks:
            for w in set(t):
                df[w] += 1
        self.df = df
        self.idf = {w: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for w, n in df.items()}

    def rank(self, qterms):
        scores = []
        for i in range(self.N):
            s = 0.0
            for w in qterms:
                if w in self.tf[i]:
                    f = self.tf[i][w]
                    s += self.idf.get(w, 0) * (f * (K1 + 1)) / (f + K1 * (1 - B + B * self.lens[i] / self.avgdl))
            scores.append((self.ids[i], s))
        return sorted(scores, key=lambda x: (-x[1], x[0]))


def recall_at(ranked, relevant, k):
    top = {d for d, _ in ranked[:k]}
    return len(top & relevant) / len(relevant) if relevant else 0.0


def rank_of(ranked, doc_id):
    for i, (d, _) in enumerate(ranked, 1):
        if d == doc_id:
            return i
    return None


def expand(bm25, ranked, qterms, top_k, m):
    """PRF拡張: 擬似関連の上位 top_k 文書に「跨って」現れる語を優先(freq×idfを補助)。"""
    doc_count, wscore = Counter(), Counter()
    for did, _ in ranked[:top_k]:
        i = bm25.ids.index(did)
        for w in set(bm25.tf[i]):
            if w not in qterms:
                doc_count[w] += 1
        for w, f in bm25.tf[i].items():
            if w not in qterms:
                wscore[w] += f * bm25.idf.get(w, 0)
    cand = sorted(doc_count, key=lambda w: (-doc_count[w], -wscore[w], w))
    return cand[:m]


def main() -> int:
    ap = argparse.ArgumentParser(description="pseudo-relevance feedback query expansion")
    ap.add_argument("data", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    data = json.loads(args.data.read_text(encoding="utf-8"))
    bm25 = BM25(data["documents"])
    relevant = set(data["relevant"])
    top_k = int(data.get("top_k", 2))
    m = int(data.get("expansion_terms", 3))
    k_eval = int(data.get("recall_k", 3))

    q0 = tok(data["query"])
    r1 = bm25.rank(q0)
    exp = expand(bm25, r1, set(q0), top_k, m)
    r2 = bm25.rank(q0 + exp)

    rec1, rec2 = recall_at(r1, relevant, k_eval), recall_at(r2, relevant, k_eval)
    rank_moves = {d: (rank_of(r1, d), rank_of(r2, d)) for d in sorted(relevant)}

    if args.json:
        print(json.dumps({"query": data["query"], "expansion": exp,
                          "recall_before": round(rec1, 3), "recall_after": round(rec2, 3),
                          "rank_before_after": rank_moves}, ensure_ascii=False, indent=2))
    else:
        print(f"query: '{data['query']}'   文書 {bm25.N}   PRF上位{top_k}件から拡張語{m}個\n")
        print(f"  一次検索 top{k_eval}: {[d for d, _ in r1[:k_eval]]}  recall@{k_eval}={rec1:.2f}")
        print(f"  拡張語: {exp}")
        print(f"  二次検索 top{k_eval}: {[d for d, _ in r2[:k_eval]]}  recall@{k_eval}={rec2:.2f}\n")
        print("  関連文書の順位(PRF前→後):")
        for d, (b, a) in rank_moves.items():
            mark = " ↑改善" if a and b and a < b else ""
            print(f"    {d}: {b} → {a}{mark}")
        print(f"\n-- PRFで recall@{k_eval} {rec1:.2f}→{rec2:.2f}"
              "(語彙のずれた関連文書を上位に引き上げ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
