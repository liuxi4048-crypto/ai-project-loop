#!/usr/bin/env python3
"""eventdedup: 同一事件を報じるほぼ重複の報道をクラスタリングして集約する。

ニュースアーカイブには、同じ出来事を複数媒体が別の言い回しで報じた「ほぼ重複」の記事が
たまる(例: 1つのセキュリティ事件に8本の記事)。本ツールは、記事テキストを単語シングル
(k-gram)に分解し Jaccard 類似度で近似重複を検出、単連結クラスタリング(Union-Find)で
「N 報道 → 1 事件」に集約する。標準ライブラリのみ・決定論的。

入力(JSON): {"threshold":0.25, "documents":[{"id","title","text"}...]}
使い方:
    python eventdedup.py <data.json> [--json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "is", "its", "with",
        "by", "at", "as", "it", "was", "after", "over", "s"}


def shingles(text, k=3):
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)} if len(words) >= k else set(words)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def main() -> int:
    ap = argparse.ArgumentParser(description="near-duplicate news/event clustering")
    ap.add_argument("data", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    data = json.loads(args.data.read_text(encoding="utf-8"))
    docs = data["documents"]
    thr = float(data.get("threshold", 0.25))
    k = int(data.get("shingle_k", 2))     # 1=語集合(言い換えに強い) / 2以上=語順も見る
    n = len(docs)
    sh = [shingles(f"{d.get('title','')} {d.get('text','')}", k) for d in docs]

    uf = UF(n)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            s = jaccard(sh[i], sh[j])
            if s >= thr:
                uf.union(i, j)
                pairs.append((docs[i]["id"], docs[j]["id"], round(s, 3)))

    clusters = {}
    for i in range(n):
        clusters.setdefault(uf.find(i), []).append(i)
    groups = sorted(clusters.values(), key=lambda g: -len(g))

    events = len(groups)
    dupes = n - events

    if args.json:
        out = [{"size": len(g), "members": [docs[i]["id"] for i in g],
                "representative": docs[g[0]]["id"]} for g in groups]
        print(json.dumps({"documents": n, "events": events, "duplicates_removed": dupes,
                          "clusters": out, "linked_pairs": pairs}, ensure_ascii=False, indent=2))
    else:
        print(f"報道 {n}件  → 事件 {events}件(重複 {dupes}件を集約)  Jaccard閾値 {thr}\n")
        for gi, g in enumerate(groups, 1):
            tag = f"事件{gi}({len(g)}報道)" if len(g) > 1 else f"単独{gi}"
            print(f"  [{tag}] 代表: {docs[g[0]]['title'][:60]}")
            for i in g[1:]:
                print(f"      + {docs[i]['id']}: {docs[i]['title'][:56]}")
        print(f"\n-- 冗長度 {dupes}/{n} = {dupes/n:.0%} の報道が既存事件の重複"
              "(1事件に複数媒体が別表現で報じたもの)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
