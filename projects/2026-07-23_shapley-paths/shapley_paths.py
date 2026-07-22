#!/usr/bin/env python3
"""shapley-paths: 並列推論パスの貢献度をShapley値で厳密に帰属する。

LLMの並列推論(複数の推論パスを生成し多数決等で最終回答を出す)では、
結果レベルの報酬が全パスに一律に割り当てられるため、冗長・誤誘導なパス
(フリーライダー)にも同じ報酬が付き、学習信号が曖昧になる。
本ツールは、各パスの答えと正解(gold)から、アンサンブル成功への各パスの
Shapley値(限界貢献の全順序平均)を厳密計算し、貢献者とフリーライダー/
誤誘導パスを識別する。Python 3 標準ライブラリのみ。

協力ゲーム: 提携 S(パスの部分集合)の価値 v(S) = S の多数決が gold と一致なら 1、
             それ以外(不一致・同数・空)は 0。
Shapley値: φ_i = Σ_{S⊆N\\{i}} |S|!(n-|S|-1)!/n! · (v(S∪{i}) - v(S))
効率性: Σ_i φ_i = v(N)(全体提携の価値)を満たす → 検算に使える。

使い方:
    python shapley_paths.py <config.json> [--json]

config:
    {"gold": "B", "answers": ["B","B","B","A","C"]}
    または {"gold":"B","paths":[{"id":"p1","answer":"B"}, ...]}
"""
import argparse
import json
import sys
from collections import Counter
from itertools import combinations
from math import factorial
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def majority(answers) -> str:
    """一意な最多得票を返す。空・同数は None(=棄権/不正解扱い)。"""
    if not answers:
        return None
    tally = Counter(answers)
    top = tally.most_common()
    if len(top) >= 2 and top[0][1] == top[1][1]:
        return None
    return top[0][0]


def coalition_value(indices, ans, gold) -> int:
    return 1 if majority([ans[i] for i in indices]) == gold else 0


def shapley(ans, gold) -> list:
    n = len(ans)
    phi = [0.0] * n
    others = list(range(n))
    for i in range(n):
        rest = [j for j in others if j != i]
        for size in range(len(rest) + 1):
            w = factorial(size) * factorial(n - size - 1) / factorial(n)
            for S in combinations(rest, size):
                marg = coalition_value(S + (i,), ans, gold) - coalition_value(S, ans, gold)
                if marg:
                    phi[i] += w * marg
    return phi


def main() -> int:
    ap = argparse.ArgumentParser(description="Shapley reward attribution for parallel reasoning paths")
    ap.add_argument("config", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.config.is_file():
        print(f"error: no such file: {args.config}", file=sys.stderr)
        return 2

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    gold = cfg["gold"]
    if "paths" in cfg:
        ids = [p.get("id", f"p{i+1}") for i, p in enumerate(cfg["paths"])]
        ans = [p["answer"] for p in cfg["paths"]]
    else:
        ans = cfg["answers"]
        ids = [f"p{i+1}" for i in range(len(ans))]

    n = len(ans)
    if n == 0:
        print("error: no paths", file=sys.stderr)
        return 2
    if n > 18:
        print(f"warning: n={n} → 2^n 提携の厳密計算は重い(近似未実装)", file=sys.stderr)

    phi = shapley(ans, gold)
    grand = coalition_value(tuple(range(n)), ans, gold)
    final = majority(ans)

    rows = sorted(zip(ids, ans, phi), key=lambda r: -r[2])

    if args.json:
        print(json.dumps({
            "gold": gold, "final_answer": final, "ensemble_correct": bool(grand),
            "attribution": [{"id": i, "answer": a, "shapley": round(s, 6),
                             "role": role(s, a, gold)} for i, a, s in rows],
            "shapley_sum": round(sum(phi), 6),
        }, ensure_ascii=False, indent=2))
    else:
        print(f"gold={gold}  最終回答(多数決)={final}  "
              f"アンサンブル{'正解' if grand else '不正解'}\n")
        print(f"{'path':>6} {'answer':>8} {'shapley':>10}  役割")
        for i, a, s in rows:
            print(f"{i:>6} {a:>8} {s:>10.4f}  {role(s, a, gold)}")
        print(f"\nΣφ = {sum(phi):.4f}  (= v(N) = {grand}; 効率性の検算)")
        contributors = sum(1 for _, _, s in rows if s > 1e-9)
        freeriders = sum(1 for _, _, s in rows if abs(s) <= 1e-9)
        misleaders = sum(1 for _, _, s in rows if s < -1e-9)
        print(f"-- 貢献者 {contributors} / フリーライダー {freeriders} / 誤誘導 {misleaders}")

    return 0


def role(s: float, a: str, gold: str) -> str:
    if s < -1e-9:
        return "✗ 誤誘導(限界貢献が負)"
    if abs(s) <= 1e-9:
        return "· フリーライダー(貢献ゼロ)"
    return "✓ 貢献者"


if __name__ == "__main__":
    sys.exit(main())
