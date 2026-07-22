#!/usr/bin/env python3
"""subjfcast: 時系列予測で「集団モデル」と「被験者条件付けモデル」を比較する。

血糖予測などでは被験者ごとにベースラインや反応(例: 食事への感度)が異なる。集団レベルの
単一モデルは平均像しか捉えられず、個人差の大きい被験者で誤差が出る。被験者ごとに条件付け
(=被験者別に係数を推定)すると誤差が下がる。本ツールは合成多被験者データで両者の
一歩先予測 RMSE を比較する。標準ライブラリのみ・決定論的(乱数なし)。

使い方:
    python subjfcast.py [--subjects 8] [--length 40] [--json]
"""
import argparse
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")

AR = 0.6   # 共通の自己回帰係数


def make_data(S, T):
    """被験者ごとに異なるベースライン c0_s・食事感度 m_s を持つ系列を生成。"""
    subjects = []
    for s in range(S):
        c0 = 80.0 + 20.0 * ((s * 37) % 11) / 10.0 - 10.0   # 個体差の大きいベースライン
        m = 5.0 + 25.0 * ((s * 53) % 7) / 6.0              # 食事感度も個体差
        y = [c0]
        rows = []   # (y_prev, meal, y_next)
        for t in range(1, T):
            meal = 1.0 if (t + s) % 5 == 0 else 0.0
            struct = 2.0 * math.sin(0.5 * t)               # 決定論的な既約変動
            y_next = c0 * (1 - AR) + AR * y[-1] + m * meal + struct
            rows.append((y[-1], meal, y_next))
            y.append(y_next)
        subjects.append(rows)
    return subjects


def solve(A, b):
    """3x3 正規方程式をガウス消去で解く。"""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[p] = M[p], M[i]
        piv = M[i][i]
        if abs(piv) < 1e-12:
            continue
        M[i] = [v / piv for v in M[i]]
        for r in range(n):
            if r != i and abs(M[r][i]) > 1e-12:
                f = M[r][i]
                M[r] = [a - f * c for a, c in zip(M[r], M[i])]
    return [M[i][n] for i in range(n)]


def fit(rows):
    """特徴 [1, y_prev, meal] の最小二乗係数を返す。"""
    A = [[0.0] * 3 for _ in range(3)]
    b = [0.0] * 3
    for yp, meal, yn in rows:
        x = [1.0, yp, meal]
        for i in range(3):
            b[i] += x[i] * yn
            for j in range(3):
                A[i][j] += x[i] * x[j]
    return solve(A, b)


def predict(coef, yp, meal):
    return coef[0] + coef[1] * yp + coef[2] * meal


def rmse(rows, coef):
    se = sum((predict(coef, yp, meal) - yn) ** 2 for yp, meal, yn in rows)
    return math.sqrt(se / len(rows)) if rows else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="population vs subject-conditioned forecasting")
    ap.add_argument("--subjects", type=int, default=8)
    ap.add_argument("--length", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    data = make_data(args.subjects, args.length)
    # 各被験者を train(前70%)/test(後30%)に分割
    splits = [(r[:int(len(r) * 0.7)], r[int(len(r) * 0.7):]) for r in data]

    # 集団モデル: 全被験者の train を束ねて単一係数
    pooled = [row for tr, _ in splits for row in tr]
    pop_coef = fit(pooled)

    pop_errs, subj_errs = [], []
    for tr, te in splits:
        pop_errs.append(rmse(te, pop_coef))
        subj_errs.append(rmse(te, fit(tr)))   # 被験者別に係数を推定

    pop_rmse = sum(pop_errs) / len(pop_errs)
    subj_rmse = sum(subj_errs) / len(subj_errs)
    red = (pop_rmse - subj_rmse) / pop_rmse * 100 if pop_rmse else 0.0

    if args.json:
        import json
        print(json.dumps({"subjects": args.subjects,
                          "population_rmse": round(pop_rmse, 3),
                          "subject_conditioned_rmse": round(subj_rmse, 3),
                          "rmse_reduction_pct": round(red, 1),
                          "per_subject": [{"population": round(p, 2), "subject": round(s, 2)}
                                          for p, s in zip(pop_errs, subj_errs)]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"被験者 {args.subjects}  系列長 {args.length}  (train70%/test30%)\n")
        print(f"{'subject':>8} {'population':>11} {'subject-cond':>13}")
        for i, (p, s) in enumerate(zip(pop_errs, subj_errs)):
            print(f"{i:>8} {p:>11.2f} {s:>13.2f}")
        print(f"\n  平均RMSE  集団={pop_rmse:.2f}   被験者条件付け={subj_rmse:.2f}  ★")
        print(f"-- 被験者条件付けで一歩先予測RMSEを {red:.1f}% 低減"
              "(集団モデルは個体差の大きい被験者で誤差が大きい)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
