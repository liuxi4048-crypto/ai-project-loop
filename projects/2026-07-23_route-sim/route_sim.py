#!/usr/bin/env python3
"""route-sim: コーディングエージェントの回復ルーティングを予算固定で比較する。

コーディングエージェントは失敗時、従来「安いモデル→高いモデル」へ機械的にエスカレート
していた。CodeRescue の着想は、実行フィードバックで各タスクの回復見込みを校正し、
安いモデルでの回復を最大化しつつ、高いモデルは効きそうな時だけ使う、というもの。
本シミュレータは同一の乱数実現の下で3方策を比較し、固定予算あたりの解決数を測る。
Python 3 標準ライブラリのみ・シード固定で再現可能。

モデル: まず全タスクに安モデルを1回試す(必須, コスト N)。残った予算 R = budget - N を
「回復(recovery)」に充てる。各方策は R の使い方が異なる。
  cheap-only        : 回復なし(安1回のみ)
  always-escalate   : 失敗タスクを出現順に高モデルへ、Rが尽きるまで(従来手法)
  budget-calibrated : フィードバック信号 d̂ から各失敗タスクの「1コストあたり期待回復利得」を
                      見積り、価値の高い回復(安で再試行 or 高モデル)を優先配分(CodeRescue風)

使い方:
    python route_sim.py [--tasks 300] [--budget 400] [--cost-exp 5] [--seed 0] [--json]
"""
import argparse
import json
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

COST_CHEAP = 1


def p_cheap(d: float) -> float:
    """安モデルの成功確率(難易度dが上がるほど低い)。"""
    return max(0.03, 1.0 - d)


def p_exp(d: float) -> float:
    """高モデルの成功確率(難所に強い)。"""
    return max(0.05, 1.0 - 0.35 * d)


def make_tasks(n: int, rng: random.Random) -> list:
    """各タスクに難易度と、方策間で共有する乱数実現を持たせる(公平比較のため)。"""
    tasks = []
    for _ in range(n):
        d = rng.random()
        tasks.append({
            "d": d,
            "u_cheap1": rng.random(),
            "u_cheap2": rng.random(),
            "u_exp": rng.random(),
            "dhat": min(1.0, max(0.0, d + rng.gauss(0, 0.15))),  # ノイズ付き実行フィードバック
        })
    return tasks


def solved(u: float, p: float) -> bool:
    return u < p


def phase1(tasks, budget):
    """全タスクに安モデルを1回。solved数と、未解決タスク・残予算を返す。"""
    n = len(tasks)
    attempted = min(n, budget)                 # 予算が足りなければ手前で尽きる
    win = 0
    failed = []
    for t in tasks[:attempted]:
        if solved(t["u_cheap1"], p_cheap(t["d"])):
            win += 1
        else:
            failed.append(t)
    return win, failed, budget - attempted     # 残予算 R


def run_cheap_only(tasks, budget, cost_exp):
    win, _failed, rem = phase1(tasks, budget)
    return win, budget - rem


def run_always_escalate(tasks, budget, cost_exp):
    win, failed, rem = phase1(tasks, budget)
    spent = budget - rem
    for t in failed:                            # 出現順に高モデルへ(素朴)
        if rem < cost_exp:
            break
        rem -= cost_exp
        spent += cost_exp
        if solved(t["u_exp"], p_exp(t["d"])):
            win += 1
    return win, spent


def run_calibrated(tasks, budget, cost_exp):
    win, failed, rem = phase1(tasks, budget)
    spent = budget - rem
    # 各失敗タスクの最良回復アクションを d̂ ベースの「1コストあたり期待利得」で決め、降順配分
    plans = []
    for t in failed:
        dhat = t["dhat"]
        retry = (p_cheap(dhat) / COST_CHEAP, COST_CHEAP, "retry", t)
        esc = (p_exp(dhat) / cost_exp, cost_exp, "escalate", t)
        plans.append(max(retry, esc, key=lambda x: x[0]))
    plans.sort(key=lambda x: -x[0])
    for _ratio, cost, action, t in plans:
        if rem < cost:
            continue                            # この予算では無理、次(より安い)候補へ
        rem -= cost
        spent += cost
        if action == "retry":
            if solved(t["u_cheap2"], p_cheap(t["d"])):
                win += 1
        else:
            if solved(t["u_exp"], p_exp(t["d"])):
                win += 1
    return win, spent


POLICIES = [
    ("cheap-only", run_cheap_only),
    ("always-escalate", run_always_escalate),
    ("budget-calibrated", run_calibrated),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="budget-calibrated recovery routing simulator")
    ap.add_argument("--tasks", type=int, default=300)
    ap.add_argument("--budget", type=int, default=400)
    ap.add_argument("--cost-exp", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    tasks = make_tasks(args.tasks, rng)

    results = []
    for name, fn in POLICIES:
        win, spent = fn(tasks, args.budget, args.cost_exp)
        eff = win / spent * 100 if spent else 0.0
        results.append({"policy": name, "solved": win, "spent": spent,
                        "solved_per_100_cost": round(eff, 2)})

    if args.json:
        print(json.dumps({"tasks": args.tasks, "budget": args.budget,
                          "cost_exp": args.cost_exp, "results": results},
                         ensure_ascii=False, indent=2))
    else:
        print(f"tasks={args.tasks}  budget={args.budget}  "
              f"cost(cheap={COST_CHEAP}, exp={args.cost_exp})  seed={args.seed}\n")
        print(f"{'policy':>18} {'solved':>7} {'spent':>7} {'solved/100cost':>15}")
        best = max(results, key=lambda r: r["solved"])
        for r in results:
            star = "  ★" if r is best else ""
            print(f"{r['policy']:>18} {r['solved']:>7} {r['spent']:>7} "
                  f"{r['solved_per_100_cost']:>15}{star}")
        base = next(r for r in results if r["policy"] == "always-escalate")
        cal = next(r for r in results if r["policy"] == "budget-calibrated")
        if base["solved"]:
            lift = (cal["solved"] - base["solved"]) / base["solved"] * 100
            print(f"\n-- budget-calibrated は always-escalate 比で解決数 {lift:+.1f}%"
                  f"(同一予算 {args.budget})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
