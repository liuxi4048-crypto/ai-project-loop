#!/usr/bin/env python3
"""tpmatrix: 全正(TP)/全非負(TNN)行列の判定と、特性多項式の係数(主小行列式和)を計算する。

全正行列(totally positive)は「すべての小行列式が正」な行列。特性多項式
det(λI − M) = Σ_k (−1)^k e_k λ^{n−k} の係数 e_k は「位数 k のすべての主小行列式の和」で、
e_1=トレース、e_2=2×2主小行列式の和 … と続く(高次係数ほど低位数の主小行列式)。
本ツールは、行列の TP/TNN 判定(違反する小行列式を提示)と特性多項式係数の算出を行う。
標準ライブラリのみ・厳密(有理数)・決定論的。

使い方:
    python tpmatrix.py               # 組込み例(全正な Vandermonde と 非TP行列)
    python tpmatrix.py <matrix.json> # [[...],[...]] を判定
"""
import argparse
import json
import sys
from fractions import Fraction
from itertools import combinations
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def det(M):
    """小行列(有理数)の行列式。余因子展開(小サイズ向け)。"""
    n = len(M)
    if n == 0:
        return Fraction(1)
    if n == 1:
        return M[0][0]
    if n == 2:
        return M[0][0] * M[1][1] - M[0][1] * M[1][0]
    total = Fraction(0)
    for j in range(n):
        sub = [row[:j] + row[j + 1:] for row in M[1:]]
        total += ((-1) ** j) * M[0][j] * det(sub)
    return total


def minor(M, rows, cols):
    return det([[M[i][j] for j in cols] for i in rows])


def classify(M):
    """全ての小行列式を検査。最初の非正/負を witness として返す。"""
    n = len(M)
    tp, tnn = True, True
    witness_tp = witness_tnn = None
    for k in range(1, n + 1):
        for rows in combinations(range(n), k):
            for cols in combinations(range(n), k):
                v = minor(M, rows, cols)
                if v <= 0 and tp:
                    tp = False
                    witness_tp = (rows, cols, v)
                if v < 0 and tnn:
                    tnn = False
                    witness_tnn = (rows, cols, v)
    return tp, tnn, witness_tp, witness_tnn


def principal_minor_sums(M):
    """e_k = 位数 k の主小行列式(rows=cols)の和。e_0=1。"""
    n = len(M)
    e = [Fraction(1)]
    for k in range(1, n + 1):
        s = sum(minor(M, S, S) for S in combinations(range(n), k))
        e.append(s)
    return e


def char_poly(e, n):
    """係数リスト [1, -e1, e2, -e3, ...](λ^n から降順)。"""
    return [((-1) ** k) * e[k] for k in range(n + 1)]


def show(name, M):
    n = len(M)
    tp, tnn, wtp, wtnn = classify(M)
    e = principal_minor_sums(M)
    coeffs = char_poly(e, n)
    print(f"=== {name} ({n}x{n}) ===")
    for row in M:
        print("  [" + "  ".join(f"{str(x):>4}" for x in row) + "]")
    verdict = "全正(TP)" if tp else ("全非負(TNN)" if tnn else "TPでもTNNでもない")
    print(f"  判定: {verdict}")
    if not tp:
        r, c, v = wtp
        print(f"    TP違反の小行列式: rows{list(r)} cols{list(c)} = {v}")
    if not tnn:
        r, c, v = wtnn
        print(f"    負の小行列式: rows{list(r)} cols{list(c)} = {v}")
    terms = []
    for i, cf in enumerate(coeffs):
        p = n - i
        terms.append(f"{'+' if cf >= 0 else '-'}{abs(cf)}λ^{p}" if p else f"{'+' if cf >= 0 else '-'}{abs(cf)}")
    print(f"  特性多項式: " + " ".join(terms).lstrip("+"))
    print(f"  主小行列式和 e_k (高次係数の源): e1(trace)={e[1]}"
          + (f", e2={e[2]}" if n >= 2 else "")
          + (f", e3={e[3]}" if n >= 3 else ""))
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="totally positive/nonnegative test + char poly coefficients")
    ap.add_argument("matrix", type=Path, nargs="?")
    args = ap.parse_args()

    if args.matrix:
        if not args.matrix.is_file():
            print(f"error: no such file: {args.matrix}", file=sys.stderr)
            return 2
        raw = json.loads(args.matrix.read_text(encoding="utf-8"))
        M = [[Fraction(x) for x in row] for row in raw]
        show(args.matrix.name, M)
    else:
        # 全正な Vandermonde(節点 1,2,3): 全小行列式が正
        vander = [[Fraction((i + 1) ** j) for j in range(3)] for i in range(3)]
        show("Vandermonde nodes(1,2,3) — 全正の例", vander)
        # 非TP・非TNN: 負の小行列式を持つ
        show("非TP行列 [[1,2],[3,1]]", [[Fraction(1), Fraction(2)], [Fraction(3), Fraction(1)]])
        # 単位行列: 主小行列式は正だが0の小行列式があり TNN だが TP でない
        ident = [[Fraction(1 if i == j else 0) for j in range(3)] for i in range(3)]
        show("単位行列 I_3 — TNN だが TP でない", ident)
    return 0


if __name__ == "__main__":
    sys.exit(main())
