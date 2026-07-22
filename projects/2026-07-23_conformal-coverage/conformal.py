#!/usr/bin/env python3
"""conformal-coverage: 分割共形予測が分布シフト下でクラス別カバレッジを崩すことを実演する。

分割共形予測(split conformal prediction)は、較正集合から非適合スコアの分位点 q̂ を1つ求め、
「非適合スコア ≤ q̂ なら真ラベルを予測集合に含む」とすることで、周辺(marginal)カバレッジ 1-α を
有限標本で保証する。しかし q̂ は全クラス共通の1つの閾値であるため、クラスごとにスコア品質や
出現率が異なると、周辺カバレッジは 1-α でもクラス別カバレッジは大きくばらつく。
較正集合と評価集合の分布がずれる(distribution shift)と、この乖離が顕著になる。

本スクリプトは合成データでこれを再現する(依存ゼロ・乱数シード固定で再現可能)。

使い方:
    python conformal.py [--alpha 0.1] [--n-cal 2000] [--n-test 4000] [--seed 0]
"""
import argparse
import math
import random
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

# クラスごとの「真ラベルへ付く確率の質」= 平均。値が低いクラスほどモデルが自信を持てない。
CLASS_QUALITY = {0: 0.85, 1: 0.70, 2: 0.55, 3: 0.40}
CLASSES = sorted(CLASS_QUALITY)


def sample_p_true(cls: int, rng: random.Random) -> float:
    """クラスの質を平均とするガウスを(0,1)にクリップし、真ラベルへ付く確率とする。"""
    p = rng.gauss(CLASS_QUALITY[cls], 0.15)
    return min(max(p, 1e-4), 1.0 - 1e-4)


def make_dataset(n: int, priors: dict, rng: random.Random) -> list:
    """(class, nonconformity_score) のリストを返す。非適合スコア = 1 - p_true。"""
    classes = list(priors)
    weights = [priors[c] for c in classes]
    data = []
    for _ in range(n):
        cls = rng.choices(classes, weights=weights, k=1)[0]
        score = 1.0 - sample_p_true(cls, rng)
        data.append((cls, score))
    return data


def conformal_quantile(scores: list, alpha: float) -> float:
    """分割共形の閾値 q̂: (⌈(n+1)(1-α)⌉) 番目に小さい非適合スコア。"""
    n = len(scores)
    s = sorted(scores)
    k = math.ceil((n + 1) * (1 - alpha))
    if k > n:
        return float("inf")          # 保証には標本が足りない → 常にカバー
    return s[k - 1]                   # 1-indexed の k 番目


def coverage_by_class(data: list, qhat: float) -> dict:
    """真ラベルが予測集合に入った割合を、全体とクラス別に返す。"""
    covered = defaultdict(int)
    total = defaultdict(int)
    for cls, score in data:
        total[cls] += 1
        if score <= qhat:
            covered[cls] += 1
    per_class = {c: covered[c] / total[c] for c in total}
    overall = sum(covered.values()) / sum(total.values())
    return overall, per_class


def run_scenario(name: str, cal_priors, test_priors, alpha, n_cal, n_test, rng) -> None:
    cal = make_dataset(n_cal, cal_priors, rng)
    test = make_dataset(n_test, test_priors, rng)
    qhat = conformal_quantile([s for _, s in cal], alpha)
    overall, per_class = coverage_by_class(test, qhat)

    target = 1 - alpha
    print(f"\n=== {name} ===")
    print(f"q̂ = {qhat:.4f}   目標カバレッジ = {target:.0%}")
    print(f"{'class':>6} {'quality':>8} {'test比率':>9} {'カバレッジ':>10} {'目標との差':>10}")
    for c in CLASSES:
        if c not in per_class:
            continue
        frac = test_priors.get(c, 0) / sum(test_priors.values())
        cov = per_class[c]
        flag = "  ← 崩れ" if abs(cov - target) > 0.05 else ""
        print(f"{c:>6} {CLASS_QUALITY[c]:>8.2f} {frac:>9.0%} {cov:>10.1%} {cov - target:>+10.1%}{flag}")
    spread = max(per_class.values()) - min(per_class.values())
    print(f"周辺カバレッジ = {overall:.1%}  /  クラス別カバレッジの幅 = {spread:.1%}")


def main() -> int:
    ap = argparse.ArgumentParser(description="split conformal class-conditional coverage demo")
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--n-cal", type=int, default=2000)
    ap.add_argument("--n-test", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    uniform = {c: 1.0 for c in CLASSES}
    # シフト: 較正は均等だが、評価は自信の低いクラス(2,3)が多数を占める
    shifted = {0: 0.1, 1: 0.2, 2: 0.3, 3: 0.4}

    run_scenario("シフトなし(較正=評価=均等)", uniform, uniform,
                 args.alpha, args.n_cal, args.n_test, rng)
    run_scenario("分布シフトあり(評価は低品質クラスに偏る)", uniform, shifted,
                 args.alpha, args.n_cal, args.n_test, rng)

    print("\n-- シフトなしでは周辺カバレッジは目標どおりだがクラス別は大きくばらつく"
          "(単一閾値の宿命)。分布シフトは交換可能性を壊し、周辺カバレッジ自体も目標を割る")
    return 0


if __name__ == "__main__":
    sys.exit(main())
