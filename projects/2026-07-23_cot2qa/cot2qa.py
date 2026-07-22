#!/usr/bin/env python3
"""cot2qa: 推論チェーンを依存関係付きの中間QAレコードへ変換する。

Chain-of-Thought の教師信号は「推論系列全体」を平坦に最適化するため、局所的な結論が
後続の判断をどう支えるか(依存関係)への信号が乏しい。DAIS の着想は、各中間ステップを
「直前の必要な状態を条件に局所回答を予測する」QAレコードへ分解し、依存を明示すること。
本ツールは推論チェーンを解析してステップ間の依存グラフを構築し、中間QAレコード群を生成する。
Python 3 標準ライブラリのみ・決定論的。

入力(JSON): {"question": "...", "steps": ["...", ...], "answer": "..."}
使い方:
    python cot2qa.py <trace.json> [--json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

STOP = {"the", "a", "an", "of", "to", "in", "is", "it", "and", "so", "as", "that",
        "this", "these", "with", "for", "on", "at", "by", "we", "are", "was", "how",
        "many", "much", "then", "which", "amount", "number", "total", "there"}

NUM_RE = re.compile(r"\d+(?:\.\d+)?")
WORD_RE = re.compile(r"[A-Za-z]{4,}")
BACKREF_RE = re.compile(r"\b(therefore|thus|hence|so|this|these|as (?:shown|above|established)|"
                        r"step\s*\d+|previous|earlier)\b", re.IGNORECASE)
STEP_NUM_RE = re.compile(r"step\s*(\d+)", re.IGNORECASE)


def nums_of(text: str) -> set:
    return set(NUM_RE.findall(text))


def words_of(text: str) -> set:
    return {w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOP}


def find_dependencies(steps: list) -> list:
    """各ステップの依存(先行ステップindex集合)を返す。"""
    n = len(steps)
    nums = [nums_of(s) for s in steps]
    words = [words_of(s) for s in steps]
    # 全ステップに近く頻出する語はドメイン語(例: apples)で依存信号にならない → 除外
    df = {}
    for ws in words:
        for w in ws:
            df[w] = df.get(w, 0) + 1
    cap = max(1, n // 2)
    # 数値は具体的なので常に保持、語は df<=cap のみリンク信号に使う
    sig = [nums[i] | {w for w in words[i] if df[w] <= cap} for i in range(n)]
    deps = []
    for i in range(len(steps)):
        d = set()
        # 明示的な step N 参照
        for m in STEP_NUM_RE.finditer(steps[i]):
            j = int(m.group(1)) - 1
            if 0 <= j < i:
                d.add(j)
        # 内容(数値・固有語)の重なり
        for j in range(i):
            shared = sig[i] & sig[j]
            if shared:
                d.add(j)
        # バックリファレンスがあり依存未検出なら直前ステップを既定依存に
        if not d and i > 0 and BACKREF_RE.search(steps[i]):
            d.add(i - 1)
        deps.append(sorted(d))
    return deps


def build_records(question: str, steps: list, answer: str, deps: list) -> list:
    records = []
    for i, step in enumerate(steps):
        ctx = [f"Q: {question}"] + [f"[step {j+1}] {steps[j]}" for j in deps[i]]
        records.append({
            "step": i + 1,
            "depends_on": [j + 1 for j in deps[i]],
            "context": ctx,
            "intermediate_question": "この段階で局所的に何が結論できるか?",
            "local_answer": step,
        })
    # 最終レコード(元タスク形式を保持)
    records.append({
        "step": "final",
        "depends_on": list(range(1, len(steps) + 1)),
        "context": [f"Q: {question}"] + [f"[step {i+1}] {s}" for i, s in enumerate(steps)],
        "intermediate_question": question,
        "local_answer": answer,
    })
    return records


def main() -> int:
    ap = argparse.ArgumentParser(description="convert a reasoning chain into dependency-aware QA records")
    ap.add_argument("trace", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.trace.is_file():
        print(f"error: no such file: {args.trace}", file=sys.stderr)
        return 2

    data = json.loads(args.trace.read_text(encoding="utf-8"))
    question, steps, answer = data["question"], data["steps"], data.get("answer", "")
    deps = find_dependencies(steps)
    records = build_records(question, steps, answer, deps)

    if args.json:
        print(json.dumps({"question": question, "dependencies":
                          {i + 1: [j + 1 for j in d] for i, d in enumerate(deps)},
                          "records": records}, ensure_ascii=False, indent=2))
    else:
        print(f"Q: {question}\n")
        print("依存グラフ(step ← 依存先):")
        for i, d in enumerate(deps):
            arrow = ", ".join(f"step {j+1}" for j in d) if d else "(質問のみ)"
            print(f"  step {i+1}  ← {arrow}")
        n_edges = sum(len(d) for d in deps)
        print(f"\n中間QAレコード {len(records)} 件(依存エッジ {n_edges} 本):")
        for r in records:
            dep = ",".join(map(str, r["depends_on"])) or "-"
            print(f"  [{str(r['step']):>5}] deps={dep:<10} A: {r['local_answer'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
