#!/usr/bin/env python3
"""rocket: ランダム畳み込み特徴(ROCKET系)による時系列分類。

時系列分類では、多数の「ランダムな畳み込みカーネル」を当てて固定次元の表形式特徴へ写像し、
その上で線形分類器を学習する手法(ROCKET)が単純ながら強力。各カーネルの畳み込み出力から
最大値(max)と正値割合(PPV: proportion of positive values)の2特徴を取り、K本で 2K 次元。
本ツールはこれを実装し、周波数の異なる2クラスの合成時系列を分類する。標準ライブラリのみ・
乱数シード固定で決定論的。

使い方:
    python rocket.py [--kernels 100 --length 80 --seed 0] [--json]
"""
import argparse
import json
import math
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")


def gen_data(n_per_class, length, rng):
    data = []
    for label, freq in ((0, 0.10), (1, 0.16)):     # 低周波 / 高周波(近め=やや難)
        for _ in range(n_per_class):
            phase = rng.uniform(0, 2 * math.pi)
            amp = rng.uniform(0.8, 1.2)
            series = [amp * math.sin(2 * math.pi * freq * t + phase) + rng.gauss(0, 0.5)
                      for t in range(length)]
            data.append((series, label))
    rng.shuffle(data)
    return data


def make_kernels(K, rng):
    kernels = []
    for _ in range(K):
        L = rng.choice([7, 9, 11])
        w = [rng.gauss(0, 1) for _ in range(L)]
        mean = sum(w) / L
        w = [x - mean for x in w]                   # 平均0(ROCKET流)
        dil = rng.choice([1, 2, 4])
        bias = rng.uniform(-1, 1)
        pad = ((L - 1) * dil) // 2
        kernels.append({"w": w, "bias": bias, "dil": dil, "pad": pad})
    return kernels


def apply_kernel(series, k):
    w, bias, dil, pad = k["w"], k["bias"], k["dil"], k["pad"]
    L, n = len(w), len(series)
    mx, pos, cnt = -1e18, 0, 0
    for i in range(-pad, n - (L - 1) * dil + pad):
        s = bias
        ok = True
        for j in range(L):
            idx = i + j * dil
            if 0 <= idx < n:
                s += w[j] * series[idx]
        mx = max(mx, s)
        pos += 1 if s > 0 else 0
        cnt += 1
    ppv = pos / cnt if cnt else 0.0
    return mx, ppv


def transform(data, kernels):
    X = []
    for series, _ in data:
        feats = []
        for k in kernels:
            mx, ppv = apply_kernel(series, k)
            feats.append(mx); feats.append(ppv)
        X.append(feats)
    return X, [lbl for _, lbl in data]


def standardize(X, mean=None, std=None):
    d = len(X[0])
    if mean is None:
        mean = [sum(row[j] for row in X) / len(X) for j in range(d)]
        std = [(sum((row[j] - mean[j]) ** 2 for row in X) / len(X)) ** 0.5 or 1.0 for j in range(d)]
    return [[(row[j] - mean[j]) / std[j] for j in range(d)] for row in X], mean, std


def train_logistic(X, y, iters=300, lr=0.1, l2=1e-3):
    d = len(X[0])
    w = [0.0] * d
    b = 0.0
    n = len(X)
    for _ in range(iters):
        gw = [0.0] * d
        gb = 0.0
        for i in range(n):
            z = b + sum(w[j] * X[i][j] for j in range(d))
            p = 1 / (1 + math.exp(-max(-30, min(30, z))))
            e = p - y[i]
            gb += e
            for j in range(d):
                gw[j] += e * X[i][j]
        b -= lr * gb / n
        for j in range(d):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
    return w, b


def predict(X, w, b):
    out = []
    for row in X:
        z = b + sum(w[j] * row[j] for j in range(len(row)))
        out.append(1 if z > 0 else 0)
    return out


def acc(pred, y):
    return sum(1 for a, b in zip(pred, y) if a == b) / len(y)


def main() -> int:
    ap = argparse.ArgumentParser(description="ROCKET-style time series classification")
    ap.add_argument("--kernels", type=int, default=100)
    ap.add_argument("--length", type=int, default=80)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    train = gen_data(30, args.length, rng)   # 各クラス30 → 60
    test = gen_data(20, args.length, rng)    # 各クラス20 → 40
    kernels = make_kernels(args.kernels, rng)

    Xtr, ytr = transform(train, kernels)
    Xte, yte = transform(test, kernels)
    Xtr, mean, std = standardize(Xtr)
    Xte, _, _ = standardize(Xte, mean, std)

    w, b = train_logistic(Xtr, ytr)
    tr_acc = acc(predict(Xtr, w, b), ytr)
    te_acc = acc(predict(Xte, w, b), yte)

    if args.json:
        print(json.dumps({"kernels": args.kernels, "features": 2 * args.kernels,
                          "train_acc": round(tr_acc, 3), "test_acc": round(te_acc, 3)},
                         ensure_ascii=False, indent=2))
    else:
        print(f"ROCKET  カーネル {args.kernels}本 → 特徴 {2*args.kernels}次元  "
              f"系列長 {args.length}  seed {args.seed}\n")
        print(f"  学習: {len(train)}系列(2クラス)  テスト: {len(test)}系列")
        print(f"  訓練精度 {tr_acc:.1%}   テスト精度 {te_acc:.1%}")
        print(f"\n-- ランダム畳み込み特徴(max + PPV)+ 線形分類で、周波数の異なる2クラスの"
              f"時系列をテスト精度 {te_acc:.0%} で分類")
    return 0


if __name__ == "__main__":
    sys.exit(main())
