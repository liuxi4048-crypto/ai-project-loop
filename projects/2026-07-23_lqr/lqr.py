#!/usr/bin/env python3
"""lqr: 離散時間LQR(線形二次レギュレータ)で最適フィードバック制御器を合成する。

線形系 x_{t+1}=A x_t + B u_t を、二次コスト J=Σ(xᵀQx + uᵀRu) を最小化するよう制御する。
最適解は離散代数リッカチ方程式の解 P から得る定数フィードバック u=-Kx。本ツールは
リッカチ方程式を反復で解いてゲイン K を求め、二重積分系を閉ループ制御して状態が0へ収束し、
素朴な比例制御や無制御よりコストが低いことを示す。標準ライブラリのみ・決定論的。

使い方:
    python lqr.py [--steps 60 --r 0.1] [--json]
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")


def mm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))]
            for i in range(len(A))]


def T(A):
    return [[A[j][i] for j in range(len(A))] for i in range(len(A[0]))]


def add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def sub(A, B):
    return [[A[i][j] - B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def inv(M):
    n = len(M)
    A = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(M)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        piv = A[i][i]
        A[i] = [v / piv for v in A[i]]
        for r in range(n):
            if r != i:
                f = A[r][i]
                A[r] = [a - f * b for a, b in zip(A[r], A[i])]
    return [row[n:] for row in A]


def dare_gain(A, B, Q, R, iters=500, tol=1e-12):
    """離散リッカチを反復し、収束したPから最適ゲインKを返す。"""
    P = [row[:] for row in Q]
    At, Bt = T(A), T(B)
    for _ in range(iters):
        BtP = mm(Bt, P)
        S = add(R, mm(BtP, B))              # (R + BᵀPB)
        K = mm(inv(S), mm(BtP, A))          # (R+BᵀPB)⁻¹ BᵀPA
        Pn = add(Q, sub(mm(mm(At, P), A), mm(mm(At, mm(P, B)), K)))
        if max(abs(Pn[i][j] - P[i][j]) for i in range(len(P)) for j in range(len(P[0]))) < tol:
            P = Pn
            break
        P = Pn
    BtP = mm(Bt, P)
    K = mm(inv(add(R, mm(BtP, B))), mm(BtP, A))
    return K


def simulate(A, B, Q, R, K, x0, steps):
    x = [[v] for v in x0]
    cost = 0.0
    norms = []
    for _ in range(steps):
        u = mm([[-K[i][j] for j in range(len(K[0]))] for i in range(len(K))], x)
        xc = sum(x[i][0] * mm(Q, x)[i][0] for i in range(len(x)))
        uc = sum(u[i][0] * mm(R, u)[i][0] for i in range(len(u)))
        cost += xc + uc
        x = add(mm(A, x), mm(B, u))
        norms.append(round((sum(v[0] ** 2 for v in x)) ** 0.5, 4))
    return cost, norms


def main() -> int:
    ap = argparse.ArgumentParser(description="discrete-time LQR optimal control")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--r", type=float, default=0.1, help="制御コスト重み R")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    dt = 0.1
    A = [[1.0, dt], [0.0, 1.0]]     # 二重積分系(位置・速度)
    B = [[0.0], [dt]]              # 制御=加速度
    Q = [[1.0, 0.0], [0.0, 1.0]]
    R = [[args.r]]
    x0 = [1.0, 0.0]               # 初期: 位置1・速度0

    K = dare_gain(A, B, Q, R)
    cost_lqr, norms_lqr = simulate(A, B, Q, R, K, x0, args.steps)
    # 比較1: 素朴な比例制御(位置のみに一定ゲイン)
    Kn = [[3.0, 0.0]]
    cost_naive, norms_naive = simulate(A, B, Q, R, Kn, x0, args.steps)
    # 比較2: 無制御
    Kzero = [[0.0, 0.0]]
    cost_open, norms_open = simulate(A, B, Q, R, Kzero, x0, args.steps)

    if args.json:
        print(json.dumps({"gain_K": [[round(v, 4) for v in row] for row in K],
                          "cost": {"lqr": round(cost_lqr, 3), "naive": round(cost_naive, 3),
                                   "open_loop": round(cost_open, 3)},
                          "final_state_norm": {"lqr": norms_lqr[-1], "naive": norms_naive[-1],
                                               "open_loop": norms_open[-1]}},
                         ensure_ascii=False, indent=2))
    else:
        print(f"二重積分系  steps={args.steps}  R={args.r}\n")
        print(f"  最適ゲイン K = [{K[0][0]:.3f}, {K[0][1]:.3f}]  (u = -K·x)\n")
        print(f"  状態ノルム |x| の推移(LQR): "
              + " ".join(f"{norms_lqr[i]}" for i in range(0, args.steps, max(1, args.steps // 8))))
        print(f"\n{'制御方式':>16} {'総コスト':>10} {'最終|x|':>9}")
        print(f"{'LQR(最適)':>16} {cost_lqr:>10.3f} {norms_lqr[-1]:>9}  ★")
        print(f"{'素朴な比例制御':>16} {cost_naive:>10.3f} {norms_naive[-1]:>9}")
        print(f"{'無制御':>16} {cost_open:>10.3f} {norms_open[-1]:>9}")
        print(f"\n-- LQRは状態を0へ収束させつつ総コスト最小。素朴比例は振動的で高コスト、"
              "無制御は状態が減衰せず発散的にコストが積む")
    return 0


if __name__ == "__main__":
    sys.exit(main())
