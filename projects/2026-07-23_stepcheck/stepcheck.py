#!/usr/bin/env python3
"""stepcheck: 推論チェーンの各ステップを既知事実と照合し、矛盾・自己不整合を検出する。

長い多段推論では、ステップが進むほどハルシネーション(既知事実と食い違う主張)が
混入しやすく、最終回答だけ見ても気づけない。本ツールは、各推論ステップに含まれる
主張を「事実ベース(KB)」および「先行ステップ」と突き合わせ、ステップ単位で
OK / CONTRADICTS-KB / SELF-INCONSISTENT / UNVERIFIABLE を判定する静的リンター。
Python 3 標準ライブラリのみ。

主張の書式(KB・ステップ共通):
    subject | relation | object      (明示トリプル)
    subject is object                (糖衣, relation=is)
    subject is not object            (否定主張)

使い方:
    python stepcheck.py <facts_file> <trace_file> [--json]
終了コード: 矛盾/不整合を検出=1 / なし=0
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

_ARTICLES = {"a", "an", "the"}


def norm(s: str) -> str:
    words = [w for w in s.strip().casefold().split() if w not in _ARTICLES]
    return " ".join(words)


def parse_claim(line: str):
    """1行から (subject, relation, object, negated) を抽出。無ければ None。"""
    line = line.strip().rstrip(".")
    if not line:
        return None
    if "|" in line:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and all(parts):
            return (norm(parts[0]), norm(parts[1]), norm(parts[2]), False)
        return None
    m = re.match(r"(.{1,40}?)\s+is\s+not\s+(.{1,60})$", line, re.IGNORECASE)
    if m:
        return (norm(m.group(1)), "is", norm(m.group(2)), True)
    m = re.match(r"(.{1,40}?)\s+is\s+(.{1,60})$", line, re.IGNORECASE)
    if m:
        return (norm(m.group(1)), "is", norm(m.group(2)), False)
    return None


def load_kb(text: str) -> dict:
    """(subject, relation) -> 正しい object の集合。"""
    kb = {}
    for line in text.splitlines():
        c = parse_claim(line)
        if c and not c[3]:
            kb.setdefault((c[0], c[1]), set()).add(c[2])
    return kb


def split_steps(text: str) -> list:
    """番号付き or 箇条書き or 行ごとにステップ分割。"""
    steps = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^\s*(?:\d+[.)]|[-*•]|step\s*\d+\s*[:.)])\s*", "", line, flags=re.IGNORECASE)
        steps.append(line)
    return steps


def check(kb: dict, steps: list) -> list:
    seen = {}   # (subj, rel) -> object  先行ステップで確立した値
    results = []
    for idx, step in enumerate(steps, 1):
        claim = parse_claim(step)
        verdict, reason = "UNVERIFIABLE", "主張を抽出できず(照合対象なし)"
        if claim:
            subj, rel, obj, neg = claim
            key = (subj, rel)
            kb_vals = kb.get(key)
            if neg:
                # 「subj is not obj」がKBの事実と衝突するか
                if kb_vals and obj in kb_vals:
                    verdict, reason = "CONTRADICTS-KB", f"KBでは {subj} {rel} {obj}"
                else:
                    verdict, reason = "OK", "KBと矛盾しない否定主張"
            else:
                if kb_vals is not None and obj not in kb_vals:
                    verdict, reason = "CONTRADICTS-KB", f"KBでは {subj} {rel} {sorted(kb_vals)}"
                elif key in seen and seen[key] != obj:
                    verdict, reason = "SELF-INCONSISTENT", f"先行ステップでは {subj} {rel} {seen[key]}"
                elif kb_vals is not None:
                    verdict, reason = "OK", "KBに支持される"
                    seen[key] = obj
                else:
                    verdict, reason = "UNVERIFIABLE", "KBに該当事実なし"
                    seen.setdefault(key, obj)
        results.append({"step": idx, "text": step, "verdict": verdict, "reason": reason})
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="reasoning-chain step consistency linter")
    ap.add_argument("facts", type=Path)
    ap.add_argument("trace", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for p in (args.facts, args.trace):
        if not p.is_file():
            print(f"error: no such file: {p}", file=sys.stderr)
            return 2

    kb = load_kb(args.facts.read_text(encoding="utf-8"))
    steps = split_steps(args.trace.read_text(encoding="utf-8"))
    results = check(kb, steps)

    bad = [r for r in results if r["verdict"] in ("CONTRADICTS-KB", "SELF-INCONSISTENT")]

    if args.json:
        print(json.dumps({"kb_facts": len(kb), "results": results,
                          "flagged": len(bad)}, ensure_ascii=False, indent=2))
    else:
        mark = {"OK": "✓", "CONTRADICTS-KB": "✗ 矛盾", "SELF-INCONSISTENT": "✗ 自己不整合",
                "UNVERIFIABLE": "· 未検証"}
        print(f"KB {len(kb)} facts / {len(steps)} steps\n")
        for r in results:
            print(f"  step {r['step']:>2} [{mark[r['verdict']]:>10}] {r['text'][:70]}")
            if r["verdict"] in ("CONTRADICTS-KB", "SELF-INCONSISTENT"):
                print(f"          └ {r['reason']}")
        print(f"\n-- {len(bad)} ステップが矛盾/自己不整合 "
              f"({'ハルシネーション疑い' if bad else 'チェーンは整合的'})")

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
