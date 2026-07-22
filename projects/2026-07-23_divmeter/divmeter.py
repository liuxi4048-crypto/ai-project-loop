#!/usr/bin/env python3
"""divmeter: モデル回答集合の多様性を測り、条件間(自由形式 vs 構造化出力)の崩壊を定量化する。

「JSONのみで返答」といった形式指定は、モデルが選ぶ回答を偏らせ、回答の多様性を潰す
ことが知られている(最頻答のシェアが上がり、異なり回答数が減る)。本ツールは、同じ
プロンプト群への回答集合を条件ごとに受け取り、最頻答シェア・異なり数・正規化エントロピー・
Simpson多様性を算出して条件間の差(崩壊)を可視化する。Python 3 標準ライブラリのみ・決定論的。

入力(JSON): {"conditions": {"free-form": ["dog","cat",...], "json-mode": [...]}}
使い方:
    python divmeter.py <data.json> [--json]
"""
import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def metrics(answers: list) -> dict:
    n = len(answers)
    c = Counter(a.strip().lower() for a in answers)
    distinct = len(c)
    mode_count = c.most_common(1)[0][1] if c else 0
    mode_share = mode_count / n if n else 0.0
    probs = [v / n for v in c.values()] if n else []
    H = -sum(p * math.log2(p) for p in probs) if probs else 0.0
    norm_H = H / math.log2(distinct) if distinct > 1 else 0.0     # 0..1(1=一様)
    simpson = 1 - sum(p * p for p in probs) if probs else 0.0     # Gini-Simpson 0..1
    return {"n": n, "distinct": distinct, "mode_answer": c.most_common(1)[0][0] if c else None,
            "mode_share": round(mode_share, 3), "norm_entropy": round(norm_H, 3),
            "simpson_diversity": round(simpson, 3)}


def main() -> int:
    ap = argparse.ArgumentParser(description="answer diversity meter across conditions")
    ap.add_argument("data", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    data = json.loads(args.data.read_text(encoding="utf-8"))
    conds = data["conditions"]
    results = {name: metrics(ans) for name, ans in conds.items()}

    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"{args.data.name}  条件 {len(results)}\n")
        print(f"{'condition':>14} {'n':>4} {'distinct':>8} {'mode_share':>10} "
              f"{'norm_H':>7} {'simpson':>8}")
        for name, r in results.items():
            print(f"{name:>14} {r['n']:>4} {r['distinct']:>8} {r['mode_share']:>10} "
                  f"{r['norm_entropy']:>7} {r['simpson_diversity']:>8}")
        # 2条件なら崩壊量を表示(1つ目=基準, 2つ目=対象)
        names = list(results)
        if len(names) >= 2:
            a, b = results[names[0]], results[names[1]]
            d_distinct = b["distinct"] - a["distinct"]
            d_mode = b["mode_share"] - a["mode_share"]
            d_simp = b["simpson_diversity"] - a["simpson_diversity"]
            print(f"\n-- {names[1]} は {names[0]} 比: 異なり {d_distinct:+d} / "
                  f"最頻答シェア {d_mode:+.1%} / Simpson {d_simp:+.3f}"
                  f"{'  → 多様性が崩壊' if d_distinct < 0 or d_mode > 0 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
