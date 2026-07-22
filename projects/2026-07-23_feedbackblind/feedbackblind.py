#!/usr/bin/env python3
"""feedbackblind: 「観測のみ検索」が同一観測・異結果の履歴を区別できない失敗を実証する。

非定常・部分観測な逐次意思決定では、観測が同じでも「今どのレジームか」で最適行動が変わる。
観測の類似性だけで過去履歴を検索する決定モデルは、観測は同一だが行動・報酬の結果が異なる
履歴を区別できない(=フィードバック盲目的検索)。本ツールは、記憶(成功デモの軌跡群)と
「現在のレジームを示す最近の(観測,行動,報酬)」を与えたとき、
  - obs-only(盲目) : 観測一致の成功行動を全軌跡から多数決 → レジーム衝突で誤答
  - utility-aware   : 最近の報酬文脈に整合する軌跡に絞ってから検索 → 正答
を比較する。Python 3 標準ライブラリのみ・決定論的。

使い方:
    python feedbackblind.py [--json]
"""
import argparse
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

# 2つのレジームで、同じ観測に対する正解行動が入れ替わる(観測だけでは決められない)
CORRECT = {
    "A": {"o1": 0, "o2": 1},
    "B": {"o1": 1, "o2": 0},
}
OBS = ["o1", "o2"]


def make_memory():
    """各レジーム3本ずつの成功デモ軌跡。軌跡=同一レジームの (o,a,r=1) 列。regimeは隠れ変数。"""
    trajs = []
    for regime in ("A", "A", "A", "B", "B", "B"):
        traj = [{"o": o, "a": CORRECT[regime][o], "r": 1} for o in OBS]
        trajs.append(traj)   # 方策は regime ラベルを見られない
    return trajs


def obs_only(trajs, query_o, context):
    """観測一致の成功行動を全軌跡から多数決(報酬文脈を無視)。同数は小さい行動へ。"""
    votes = Counter()
    for traj in trajs:
        for step in traj:
            if step["o"] == query_o and step["r"] == 1:
                votes[step["a"]] += 1
    if not votes:
        return None
    top = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))
    return top[0][0]


def utility_aware(trajs, query_o, context):
    """最近の報酬文脈 context=(o,a,r) に整合する軌跡だけに絞ってから観測検索。"""
    co, ca, cr = context["o"], context["a"], context["r"]
    consistent = [t for t in trajs
                  if any(s["o"] == co and s["a"] == ca and s["r"] == cr for s in t)]
    pool = consistent or trajs
    votes = Counter()
    for traj in pool:
        for step in traj:
            if step["o"] == query_o and step["r"] == 1:
                votes[step["a"]] += 1
    if not votes:
        return None
    top = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))
    return top[0][0]


def main() -> int:
    ap = argparse.ArgumentParser(description="feedback-blind vs utility-aware retrieval demo")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    trajs = make_memory()

    # クエリ: (現在レジーム, 問い合わせ観測)。context は現在レジームを示す別観測の成功例。
    queries = []
    for regime in ("A", "B"):
        for qo in OBS:
            ctx_o = "o2" if qo == "o1" else "o1"
            queries.append({
                "regime": regime, "query_o": qo,
                "context": {"o": ctx_o, "a": CORRECT[regime][ctx_o], "r": 1},
                "answer": CORRECT[regime][qo],
            })

    rows, blind_ok, util_ok = [], 0, 0
    for q in queries:
        b = obs_only(trajs, q["query_o"], q["context"])
        u = utility_aware(trajs, q["query_o"], q["context"])
        blind_ok += (b == q["answer"])
        util_ok += (u == q["answer"])
        rows.append({"regime": q["regime"], "query_o": q["query_o"],
                     "context": f'{q["context"]["o"]}→a{q["context"]["a"]}(r1)',
                     "answer": q["answer"], "obs_only": b, "utility_aware": u})

    n = len(queries)
    if args.json:
        print(json.dumps({"rows": rows,
                          "obs_only_acc": round(blind_ok / n, 3),
                          "utility_aware_acc": round(util_ok / n, 3)}, ensure_ascii=False, indent=2))
    else:
        print(f"記憶: 成功デモ軌跡 {len(trajs)}本(レジームA/B各3, regimeは隠れ)  クエリ {n}件\n")
        print(f"{'regime':>7} {'query':>6} {'context':>12} {'正解':>4} {'obs_only':>9} {'utility':>8}")
        for r in rows:
            b_mark = "" if r["obs_only"] == r["answer"] else " ✗"
            u_mark = "" if r["utility_aware"] == r["answer"] else " ✗"
            print(f"{r['regime']:>7} {r['query_o']:>6} {r['context']:>12} {r['answer']:>4} "
                  f"{str(r['obs_only'])+b_mark:>9} {str(r['utility_aware'])+u_mark:>8}")
        print(f"\n-- obs_only 正答率 {blind_ok/n:.0%}(観測が衝突すると盲目)  /  "
              f"utility_aware 正答率 {util_ok/n:.0%}(報酬文脈で軌跡を絞り区別)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
