#!/usr/bin/env python3
"""exposurebias: 教師強制(teacher forcing)評価が露呈バイアスを隠すことを実証する。

系列生成モデルを「教師強制」で評価すると、各ステップは常に正解の直前文脈を条件にするため、
1つの誤りが後段に波及しない。しかし実運用の「自己回帰(free-running)」生成では、モデルは
自分の直前出力を条件にするため、一度の誤りが連鎖して精度が崩れる(露呈バイアス)。
本ツールは同じ予測器を両方式で評価し、系列長ごとにその乖離を定量化する。標準ライブラリのみ・決定論的。

使い方:
    python exposurebias.py [--k 5] [--error-at 3] [--json]
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")


def gold_seq(T, K):
    """正解系列: y[t] = (y[t-1]+1) mod K のインクリメント鎖。"""
    y = [0]
    for _ in range(1, T):
        y.append((y[-1] + 1) % K)
    return y


def model_step(prev, t, K, error_at):
    """本来の規則は (prev+1)%K。ただし t==error_at では1つずれる(単一の誤り)。"""
    if t == error_at:
        return (prev + 2) % K
    return (prev + 1) % K


def run(gold, K, error_at, teacher_forcing):
    T = len(gold)
    preds = [gold[0]]                     # 先頭は所与
    for t in range(1, T):
        cond = gold[t - 1] if teacher_forcing else preds[-1]   # 条件にする直前値
        preds.append(model_step(cond, t, K, error_at))
    correct = sum(1 for t in range(T) if preds[t] == gold[t])
    return preds, correct / T


def main() -> int:
    ap = argparse.ArgumentParser(description="teacher forcing vs free-running: exposure bias")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--error-at", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    lengths = [10, 20, 40, 80]
    rows = []
    for T in lengths:
        gold = gold_seq(T, args.k)
        _, tf = run(gold, args.k, args.error_at, True)
        _, fr = run(gold, args.k, args.error_at, False)
        rows.append({"length": T, "teacher_forcing_acc": round(tf, 3),
                     "free_running_acc": round(fr, 3), "gap": round(tf - fr, 3)})

    # 可視化用に T=12 の系列を並べる
    demoT = 12
    g = gold_seq(demoT, args.k)
    ptf, _ = run(g, args.k, args.error_at, True)
    pfr, _ = run(g, args.k, args.error_at, False)

    if args.json:
        print(json.dumps({"k": args.k, "error_at": args.error_at, "by_length": rows,
                          "demo": {"gold": g, "teacher_forcing": ptf, "free_running": pfr}},
                         ensure_ascii=False, indent=2))
    else:
        print(f"インクリメント鎖 K={args.k}  単一の誤りを t={args.error_at} に注入\n")
        print(f"  T={demoT} の系列:")
        print(f"    gold          : {g}")
        print(f"    teacher forcing: {ptf}  (誤りは1箇所に留まる)")
        print(f"    free-running  : {pfr}  (誤り以降が全て崩れる)\n")
        print(f"{'length':>7} {'teacher_forcing':>16} {'free_running':>13} {'gap':>7}")
        for r in rows:
            print(f"{r['length']:>7} {r['teacher_forcing_acc']:>16.1%} "
                  f"{r['free_running_acc']:>13.1%} {r['gap']:>7.1%}")
        print(f"\n-- 教師強制の精度は系列が伸びても高いまま、自己回帰は誤り以降が連鎖して崩れ、"
              "乖離(露呈バイアス)は長さとともに拡大する")
    return 0


if __name__ == "__main__":
    sys.exit(main())
