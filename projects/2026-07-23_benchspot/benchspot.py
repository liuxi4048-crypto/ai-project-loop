#!/usr/bin/env python3
"""benchspot: ベンチマーク汚染(特定プロンプトへの過学習)を残差の外れ値として検出する。

有名な公開ベンチマークは各社がそれ向けに最適化しやすく、汎化指標として機能しなくなる
「ベンチマーク汚染」が起きる。行=題材A・列=題材Bのスコアグリッドに二元加法モデル
(スコア ≈ 全体平均 + 行効果 + 列効果)を当てると、ある1セルだけが加法的期待を大きく上回る
=特定の組合せへ突出して最適化された(汚染)兆候になる。本ツールはその残差外れ値を検出する。
標準ライブラリのみ・決定論的。

入力(JSON): {"rows":[...], "cols":[...], "scores":[[...]...], "z_threshold":2.5}
使い方:
    python benchspot.py <grid.json> [--json]
終了コード: 汚染疑いセルを検出=1 / なし=0
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="benchmark contamination / overfit detector")
    ap.add_argument("grid", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.grid.is_file():
        print(f"error: no such file: {args.grid}", file=sys.stderr)
        return 2

    d = json.loads(args.grid.read_text(encoding="utf-8"))
    rows, cols, S = d["rows"], d["cols"], d["scores"]
    thr = float(d.get("z_threshold", 2.5))
    R, C = len(rows), len(cols)

    grand = sum(sum(r) for r in S) / (R * C)
    row_eff = [sum(S[i]) / C - grand for i in range(R)]
    col_eff = [sum(S[i][j] for i in range(R)) / R - grand for j in range(C)]

    resid = [[S[i][j] - (grand + row_eff[i] + col_eff[j]) for j in range(C)] for i in range(R)]
    flat = [resid[i][j] for i in range(R) for j in range(C)]
    mean_r = sum(flat) / len(flat)
    std_r = (sum((x - mean_r) ** 2 for x in flat) / len(flat)) ** 0.5 or 1.0

    flagged = []
    for i in range(R):
        for j in range(C):
            z = (resid[i][j] - mean_r) / std_r
            if z > thr:
                flagged.append({"row": rows[i], "col": cols[j],
                                "score": round(S[i][j], 2),
                                "expected": round(grand + row_eff[i] + col_eff[j], 2),
                                "residual": round(resid[i][j], 2), "z": round(z, 2)})
    flagged.sort(key=lambda f: -f["z"])

    if args.json:
        print(json.dumps({"grand_mean": round(grand, 2), "z_threshold": thr,
                          "flagged": flagged}, ensure_ascii=False, indent=2))
    else:
        print(f"スコアグリッド {R}行×{C}列  全体平均 {grand:.2f}  残差z閾値 {thr}\n")
        if flagged:
            print("汚染疑い(加法期待を大きく上回るセル):")
            for f in flagged:
                print(f"  ⚠ {f['row']} × {f['col']}: 実測 {f['score']} vs 期待 {f['expected']} "
                      f"(残差 +{f['residual']}, z={f['z']})")
        else:
            print("  (加法モデルからの突出セルなし=特定組合せへの過学習の兆候なし)")
        print(f"\n-- 行効果(題材Aの一般的な上手さ)・列効果(題材B)を差し引いてなお突出するセルは、"
              "その特定の組合せへ最適化された(ベンチマーク汚染)疑い")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
