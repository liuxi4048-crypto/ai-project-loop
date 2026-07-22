#!/usr/bin/env python3
"""specsim: 投機的デコーディングの高速化を閉形式で見積り、固定γ vs 文脈適応γを比較する。

投機的デコーディングは、軽量ドラフタが γ トークンの下書きを作り、ターゲットモデルが1回の
並列前向きで検証・受理する。1トークンの受理確率を α とすると、1ブロックあたりの期待受理
トークン数は  E[k] = (1 - α^(γ+1)) / (1 - α)  (最後の追加トークン込み)。文脈ごとに α が
変わるとき、単一の固定 γ は低α区間で下書きを無駄にする。AdaFlash の着想どおり、文脈ごとに
最適 γ を選ぶ適応方式が固定を上回ることを本ツールは定量化する。標準ライブラリのみ・決定論的。

使い方:
    python specsim.py [--c-draft 0.15] [--max-gamma 8] [--json]
"""
import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")


def expected_accepted(alpha: float, gamma: int) -> float:
    if alpha >= 1.0:
        return gamma + 1
    return (1 - alpha ** (gamma + 1)) / (1 - alpha)


def block_cost(gamma: int, c_draft: float) -> float:
    """ターゲット並列検証1回 + ドラフタγトークン分の相対コスト。"""
    return 1.0 + gamma * c_draft


def speedup(alpha: float, gamma: int, c_draft: float) -> float:
    """自己回帰(1トークン=1コスト)比の高速化 = 受理トークン数 / コスト。"""
    return expected_accepted(alpha, gamma) / block_cost(gamma, c_draft)


def best_gamma(alpha: float, c_draft: float, gmax: int):
    cand = [(g, speedup(alpha, g, c_draft)) for g in range(1, gmax + 1)]
    return max(cand, key=lambda gs: gs[1])


def throughput(alphas, gamma_fn, c_draft):
    """各文脈で1ブロック生成。総受理トークン / 総コスト = AR比の実効高速化。"""
    toks = cost = 0.0
    picks = []
    for a in alphas:
        g = gamma_fn(a)
        toks += expected_accepted(a, g)
        cost += block_cost(g, c_draft)
        picks.append(g)
    return toks / cost, picks


def main() -> int:
    ap = argparse.ArgumentParser(description="speculative decoding: fixed vs adaptive draft length")
    ap.add_argument("--c-draft", type=float, default=0.15, help="ドラフタ1トークンの相対コスト")
    ap.add_argument("--max-gamma", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    # 受理率が文脈で変動する系列(高い区間=予測しやすい, 低い区間=難しい)
    alphas = [0.9, 0.9, 0.85, 0.5, 0.4, 0.3, 0.45, 0.9, 0.88, 0.35, 0.6, 0.92]

    # 適応: 文脈ごとに最適 γ
    adaptive_tp, adaptive_picks = throughput(
        alphas, lambda a: best_gamma(a, args.c_draft, args.max_gamma)[0], args.c_draft)

    # 固定: 全文脈で単一 γ。最良の固定 γ を総当りで選ぶ(公平比較)
    fixed_results = []
    for g in range(1, args.max_gamma + 1):
        tp, _ = throughput(alphas, lambda a, gg=g: gg, args.c_draft)
        fixed_results.append((g, tp))
    best_fixed_g, best_fixed_tp = max(fixed_results, key=lambda gt: gt[1])

    improvement = (adaptive_tp - best_fixed_tp) / best_fixed_tp * 100 if best_fixed_tp else 0.0

    if args.json:
        import json
        print(json.dumps({
            "c_draft": args.c_draft, "alphas": alphas,
            "adaptive": {"throughput_x": round(adaptive_tp, 3), "gammas": adaptive_picks},
            "best_fixed": {"gamma": best_fixed_g, "throughput_x": round(best_fixed_tp, 3)},
            "improvement_pct": round(improvement, 1)}, ensure_ascii=False, indent=2))
    else:
        print(f"投機的デコード  文脈{len(alphas)}  ドラフタ相対コスト={args.c_draft}  "
              f"γ上限={args.max_gamma}\n")
        print("  文脈のα → 適応が選ぶγ:")
        for a, g in zip(alphas, adaptive_picks):
            print(f"    α={a:<5} → γ={g}  (speedup {speedup(a, g, args.c_draft):.2f}x)")
        print(f"\n  最良の固定γ = {best_fixed_g}   実効 {best_fixed_tp:.3f}x")
        print(f"  文脈適応 γ            実効 {adaptive_tp:.3f}x  ★")
        print(f"\n-- 適応は最良固定に対し実効スループット +{improvement:.1f}%"
              "(低α区間で下書きを削り、高α区間で伸ばす)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
