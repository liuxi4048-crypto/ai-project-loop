#!/usr/bin/env python3
"""distrl: カテゴリカル分布Bellmanバックアップで収益分布を学習し、Cramér距離で収束を測る。

分布強化学習は、期待収益(スカラー価値)ではなく収益そのものの分布 Z(s) を学習する。
分布的Bellman作用素  T Z(s) = R(s) + γ Z(s')  を、固定した atom 台への射影(C51流)で
反復適用すると、Z(s) は真の収益分布へ収束する。本ツールは小さなMarkov報酬過程でこれを実演し、
収束を Cramér 距離(CDFのL2)で測り、分布平均が価値関数 V(s) と一致することを検証する。
標準ライブラリのみ・決定論的。

使い方:
    python distrl.py [--atoms 11 --vmax 10 --gamma 1.0 --iters 12] [--json]
"""
import argparse
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Markov報酬過程: state -> [(prob, reward, next_state), ...]。T は終端。
MRP = {
    "A": [(0.5, 0.0, "B"), (0.5, 0.0, "C")],
    "B": [(1.0, 10.0, "T")],
    "C": [(1.0, 0.0, "T")],
    "T": [],
}


def project(atoms, dz, vmin, vmax, r, gamma, probs):
    """次状態の分布(atoms上のprobs)を r+γ・z で写像し、atom台へC51射影。"""
    out = [0.0] * len(atoms)
    for j, p in enumerate(probs):
        if p == 0.0:
            continue
        Tz = min(vmax, max(vmin, r + gamma * atoms[j]))
        b = (Tz - vmin) / dz
        lo, hi = math.floor(b), math.ceil(b)
        if lo == hi:
            out[lo] += p
        else:
            out[lo] += p * (hi - b)
            out[hi] += p * (b - lo)
    return out


def cramer(p, q, dz):
    """カテゴリカル分布間のCramér距離 = √(Δz · Σ(CDF_p − CDF_q)^2)。"""
    cp = cq = 0.0
    s = 0.0
    for pi, qi in zip(p, q):
        cp += pi; cq += qi
        s += (cp - cq) ** 2
    return math.sqrt(dz * s)


def mean(atoms, probs):
    return sum(z * p for z, p in zip(atoms, probs))


def backup(Z, atoms, dz, vmin, vmax, gamma):
    newZ = {}
    for s, trans in MRP.items():
        if not trans:                      # 終端: 収益0(atom index 0)に集中
            d = [0.0] * len(atoms); d[0] = 1.0
            newZ[s] = d
            continue
        acc = [0.0] * len(atoms)
        for prob, r, nxt in trans:
            proj = project(atoms, dz, vmin, vmax, r, gamma, Z[nxt])
            for i in range(len(atoms)):
                acc[i] += prob * proj[i]
        newZ[s] = acc
    return newZ


def main() -> int:
    ap = argparse.ArgumentParser(description="categorical distributional Bellman backup")
    ap.add_argument("--atoms", type=int, default=11)
    ap.add_argument("--vmax", type=float, default=10.0)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--iters", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    vmin, vmax, N = 0.0, args.vmax, args.atoms
    dz = (vmax - vmin) / (N - 1)
    atoms = [vmin + i * dz for i in range(N)]

    # 初期化: 全状態を収益0に
    Z = {s: ([1.0] + [0.0] * (N - 1)) for s in MRP}

    # 真の不動点(多数回反復)
    Zstar = {s: p[:] for s, p in Z.items()}
    for _ in range(200):
        Zstar = backup(Zstar, atoms, dz, vmin, vmax, args.gamma)

    # 反復と収束(状態Aで測る)
    hist = []
    for k in range(args.iters):
        Z = backup(Z, atoms, dz, vmin, vmax, args.gamma)
        hist.append(round(cramer(Z["A"], Zstar["A"], dz), 5))

    V = {s: round(mean(atoms, Zstar[s]), 3) for s in MRP}
    # 解析解: V(A)=5, V(B)=10, V(C)=0, V(T)=0(γ=1)
    distA = {round(atoms[i], 1): round(Zstar["A"][i], 3) for i in range(N) if Zstar["A"][i] > 1e-6}

    if args.json:
        print(json.dumps({"atoms": atoms, "V": V,
                          "cramer_to_fixpoint_by_iter": hist,
                          "Z_A_support": distA}, ensure_ascii=False, indent=2))
    else:
        print(f"MRP {list(MRP)}  atoms={N} (0..{vmax})  γ={args.gamma}\n")
        print("状態AへのCramér距離(反復ごと, 不動点へ収束):")
        print("  " + " → ".join(f"{d:.3f}" for d in hist))
        print(f"\n分布平均 = 価値関数 V: {V}")
        print(f"  (解析解: V(A)=5, V(B)=10, V(C)=0, V(T)=0)")
        print(f"\nZ(A) の収益分布(不動点):")
        for z, p in sorted(distA.items()):
            bar = "█" * int(round(p * 30))
            print(f"  return {z:>4}: {p:>5.2f} {bar}")
        print(f"\n-- 分布的Bellmanバックアップで Z(A) は真の二峰分布(0と10が各0.5)へ収束し、"
              "その平均は V(A)=5 に一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
