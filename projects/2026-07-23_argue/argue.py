#!/usr/bin/env python3
"""argue: 議論の攻撃/支持関係から、受理される主張(grounded extension)と証拠被覆を計算する。

臨床推論などでは、主張(claim)と前提(premise)がスパン単位で結ばれ、互いに支持/攻撃する。
どの主張が正当化されるかは、Dung の抽象議論フレームワークの grounded 意味論で決まる:
特性関数 F(S)={a: a の全攻撃者が S により攻撃される} を空集合から反復し最小不動点を取る。
本ツールはそれを実装し、各引数を受理(IN)/却下(OUT)/未決(UNDEC)に分類し、さらに
受理された主張が受理された前提に支持されているか(証拠被覆)を検査する。標準ライブラリのみ・決定論的。

入力(JSON): {"arguments":[{"id","type":"claim|premise"}...],
             "attacks":[["x","y"]...],   # x が y を攻撃
             "supports":[["p","c"]...]}  # p が c を支持(任意)
使い方:
    python argue.py <data.json> [--json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def grounded(args, attackset):
    attackers = {a: set() for a in args}
    for x, y in attackset:
        attackers[y].add(x)

    def defends(S, a):   # a が S に受容可能: a の全攻撃者が S の誰かに攻撃される
        return all(any((s, x) in attackset for s in S) for x in attackers[a])

    S = set()
    while True:
        nxt = {a for a in args if defends(S, a)}
        if nxt == S:
            break
        S = nxt
    IN = S
    OUT = {y for x, y in attackset if x in IN}
    UNDEC = set(args) - IN - OUT
    return IN, OUT, UNDEC


def main() -> int:
    ap = argparse.ArgumentParser(description="abstract argumentation grounded extension + evidence coverage")
    ap.add_argument("data", type=Path)
    ap.add_argument("--json", action="store_true")
    args_ns = ap.parse_args()

    if not args_ns.data.is_file():
        print(f"error: no such file: {args_ns.data}", file=sys.stderr)
        return 2

    data = json.loads(args_ns.data.read_text(encoding="utf-8"))
    nodes = data["arguments"]
    ids = [n["id"] for n in nodes]
    typ = {n["id"]: n.get("type", "arg") for n in nodes}
    attackset = {(x, y) for x, y in data.get("attacks", [])}
    supports = data.get("supports", [])

    IN, OUT, UNDEC = grounded(ids, attackset)
    status = {a: ("IN" if a in IN else "OUT" if a in OUT else "UNDEC") for a in ids}

    # 証拠被覆: 受理された各主張(claim)が、受理された前提(premise)に支持されているか
    supporters = {}
    for p, c in supports:
        supporters.setdefault(c, []).append(p)
    coverage = []
    for c in ids:
        if typ.get(c) == "claim" and status[c] == "IN":
            sup_in = [p for p in supporters.get(c, []) if status.get(p) == "IN"]
            coverage.append({"claim": c, "supported": bool(sup_in), "by": sup_in})

    if args_ns.json:
        print(json.dumps({"status": status, "accepted": sorted(IN),
                          "rejected": sorted(OUT), "undecided": sorted(UNDEC),
                          "evidence_coverage": coverage}, ensure_ascii=False, indent=2))
    else:
        mark = {"IN": "✓ 受理", "OUT": "✗ 却下", "UNDEC": "· 未決"}
        print(f"引数 {len(ids)}  攻撃 {len(attackset)}  支持 {len(supports)}\n")
        print("grounded extension(各引数の状態):")
        for a in ids:
            print(f"  [{mark[status[a]]}] {a} ({typ.get(a)})")
        print("\n受理された主張の証拠被覆:")
        if not coverage:
            print("  (受理された claim なし)")
        for c in coverage:
            m = "✓ 根拠あり" if c["supported"] else "⚠ 根拠なし(証拠欠落)"
            bys = (" ← " + ", ".join(c["by"])) if c["by"] else ""
            print(f"  {m}: {c['claim']}{bys}")
        print(f"\n-- 受理 {len(IN)} / 却下 {len(OUT)} / 未決 {len(UNDEC)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
