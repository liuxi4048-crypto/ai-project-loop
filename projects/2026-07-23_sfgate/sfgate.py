#!/usr/bin/env python3
"""sfgate: 統計優先ゲート ― 信頼区間が十分なら確定、不十分ならエスカレートする。

品質(有用性など)をノイズ入りの安価な計測で推定するとき、少数・ばらつきの大きい標本で
早まった判断をするのは危険。統計優先ゲーティングは、平均の95%信頼区間(CI)を求め、
CIが閾値を明確に上回れば受理、明確に下回れば却下、閾値をまたぐ/標本不足/CIが広すぎる場合は
「審議へエスカレート」する。本ツールはその判定を実装する。標準ライブラリのみ・決定論的。

入力(JSON): {"threshold":0.7,"min_samples":4,"max_ci_halfwidth":0.1,
             "candidates":[{"id","measurements":[...]}...]}
使い方:
    python sfgate.py <data.json> [--json]
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

Z = 1.96  # 95% 正規近似


def ci(xs):
    n = len(xs)
    if n == 0:
        return 0.0, float("inf")
    mean = sum(xs) / n
    if n < 2:
        return mean, float("inf")
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    hw = Z * math.sqrt(var) / math.sqrt(n)
    return mean, hw


def gate(xs, thr, min_n, max_hw):
    n = len(xs)
    mean, hw = ci(xs)
    lo, hi = mean - hw, mean + hw
    if n < min_n:
        return "ESCALATE", f"標本不足(n={n}<{min_n})", mean, hw
    if hw > max_hw:
        return "ESCALATE", f"CIが広すぎる(±{hw:.3f}>{max_hw})", mean, hw
    if lo > thr:
        return "ACCEPT", f"CI下限 {lo:.3f} > 閾値 {thr}", mean, hw
    if hi < thr:
        return "REJECT", f"CI上限 {hi:.3f} < 閾値 {thr}", mean, hw
    return "ESCALATE", f"CIが閾値をまたぐ [{lo:.3f}, {hi:.3f}]", mean, hw


def main() -> int:
    ap = argparse.ArgumentParser(description="statistics-first gating with adjudicative escalation")
    ap.add_argument("data", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    d = json.loads(args.data.read_text(encoding="utf-8"))
    thr = float(d.get("threshold", 0.7))
    min_n = int(d.get("min_samples", 4))
    max_hw = float(d.get("max_ci_halfwidth", 0.1))

    rows = []
    for c in d["candidates"]:
        dec, why, mean, hw = gate(c["measurements"], thr, min_n, max_hw)
        rows.append({"id": c["id"], "n": len(c["measurements"]),
                     "mean": round(mean, 3), "ci_halfwidth": round(hw, 3) if hw != float("inf") else None,
                     "decision": dec, "reason": why})

    counts = {}
    for r in rows:
        counts[r["decision"]] = counts.get(r["decision"], 0) + 1

    if args.json:
        print(json.dumps({"threshold": thr, "min_samples": min_n,
                          "max_ci_halfwidth": max_hw, "results": rows,
                          "summary": counts}, ensure_ascii=False, indent=2))
    else:
        mark = {"ACCEPT": "✓ 受理", "REJECT": "✗ 却下", "ESCALATE": "→ 審議へ"}
        print(f"閾値 {thr}  最小標本 {min_n}  CI半幅上限 {max_hw}\n")
        print(f"{'id':>8} {'n':>3} {'mean':>6} {'CI半幅':>7}  判定")
        for r in rows:
            hw = f"±{r['ci_halfwidth']}" if r["ci_halfwidth"] is not None else "±∞"
            print(f"{r['id']:>8} {r['n']:>3} {r['mean']:>6} {hw:>7}  [{mark[r['decision']]}] {r['reason']}")
        summary = " / ".join(f"{mark[k]} {v}" for k, v in sorted(counts.items()))
        print(f"\n-- {summary}(統計優先: 確信できる時だけ確定し、曖昧な時は審議へ回す)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
