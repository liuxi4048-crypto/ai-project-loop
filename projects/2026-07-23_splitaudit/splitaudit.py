#!/usr/bin/env python3
"""splitaudit: 学習用データ分割の「漏洩」を監査し、ランダム分割の楽観バイアスを可視化する。

不正検知などでランダムな train/test 分割を使うと、同じ企業・同じ期間が両側に現れて情報が
漏洩し、未知の企業・将来期間への汎化性能を過大評価してしまう。本ツールは同じデータに対し
random / grouped(企業横断) / temporal(時間軸) の3分割を生成し、各分割の
「エンティティ漏洩」「時間漏洩」を監査して、どの分割がどの汎化を正しく測るかを示す。
Python 3 標準ライブラリのみ・シード固定で再現可能。

使い方:
    python splitaudit.py <data.csv> --group-col company_id --time-col year [--test-frac 0.3] [--seed 0] [--json]
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def split_random(rows, test_frac, rng):
    idx = list(range(len(rows)))
    rng.shuffle(idx)
    k = int(round(len(rows) * test_frac))
    test = set(idx[:k])
    return [i for i in range(len(rows)) if i not in test], sorted(test)


def split_grouped(rows, group_col, test_frac, rng):
    """エンティティ単位で分割(同じエンティティは train/test のどちらか一方のみ)。"""
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(r[group_col], []).append(i)
    keys = list(groups)
    rng.shuffle(keys)
    target = len(rows) * test_frac
    test_idx, acc = [], 0
    for kk in keys:
        if acc >= target:
            break
        test_idx += groups[kk]
        acc += len(groups[kk])
    test = set(test_idx)
    return [i for i in range(len(rows)) if i not in test], sorted(test)


def split_temporal(rows, time_col, test_frac):
    """時間の境界でカット(train=過去 / test=未来)。同じ時点が跨がないので時間漏洩ゼロ。"""
    n = len(rows)
    times = sorted({r[time_col] for r in rows})
    # test = time > boundary が test_frac に最も近い境界を選ぶ
    best = None
    for b in times:
        frac = sum(1 for r in rows if r[time_col] > b) / n
        score = abs(frac - test_frac)
        if best is None or score < best[0]:
            best = (score, b)
    boundary = best[1]
    train = [i for i in range(n) if rows[i][time_col] <= boundary]
    test = [i for i in range(n) if rows[i][time_col] > boundary]
    return train, sorted(test)


def audit(rows, train, test, group_col, time_col):
    tr_ents = {rows[i][group_col] for i in train}
    te_ents = {rows[i][group_col] for i in test}
    overlap_ents = tr_ents & te_ents
    ent_overlap = len(overlap_ents) / len(te_ents) * 100 if te_ents else 0.0

    tr_times = [rows[i][time_col] for i in train]
    max_train_t = max(tr_times) if tr_times else None
    leaked = sum(1 for i in test if max_train_t is not None and rows[i][time_col] <= max_train_t)
    time_leak = leaked / len(test) * 100 if test else 0.0
    return {"test_rows": len(test),
            "entity_overlap_pct": round(ent_overlap, 1),
            "time_leakage_pct": round(time_leak, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description="train/test split leakage auditor")
    ap.add_argument("data", type=Path)
    ap.add_argument("--group-col", required=True)
    ap.add_argument("--time-col", required=True)
    ap.add_argument("--test-frac", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    with args.data.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for c in (args.group_col, args.time_col):
        if not rows or c not in rows[0]:
            print(f"error: column not found: {c}", file=sys.stderr)
            return 2

    rng = random.Random(args.seed)
    splits = {
        "random": split_random(rows, args.test_frac, rng),
        "grouped(企業横断)": split_grouped(rows, args.group_col, args.test_frac, rng),
        "temporal(時間軸)": split_temporal(rows, args.time_col, args.test_frac),
    }
    results = {name: audit(rows, tr, te, args.group_col, args.time_col)
               for name, (tr, te) in splits.items()}

    if args.json:
        print(json.dumps({"rows": len(rows), "results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"{args.data.name}  {len(rows)}行  "
              f"group={args.group_col} time={args.time_col} test_frac={args.test_frac}\n")
        print(f"{'split':>16} {'test行':>6} {'エンティティ漏洩':>14} {'時間漏洩':>10}")
        for name, r in results.items():
            print(f"{name:>16} {r['test_rows']:>6} {r['entity_overlap_pct']:>13}% {r['time_leakage_pct']:>9}%")
        print("\n-- random は既知企業・過去期間がtestに混じり汎化を過大評価。"
              "未知企業の評価は grouped、将来期間の評価は temporal を使う")
    return 0


if __name__ == "__main__":
    sys.exit(main())
