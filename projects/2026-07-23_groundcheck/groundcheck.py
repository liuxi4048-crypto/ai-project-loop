#!/usr/bin/env python3
"""groundcheck: 生成回答の各主張が提供ソースに根拠づけられているか(幻覚でないか)を検証する。

LLMは本質的に非根拠テキスト(幻覚)を生成しうる。これを前提に、生成後の「事後検証」で各主張が
ソースに支持されているかを確かめるのが階層的監視の要。本ツールは回答を文(主張)に分割し、
各主張の内容語がいずれかのソースにどれだけ被覆されるか(containment)を測り、閾値未満の主張を
「根拠なし=幻覚候補」として検出、全体の根拠率とゲート判定を出す。標準ライブラリのみ・決定論的。

入力(JSON): {"sources":[{"id","text"}...], "answer":"...", "threshold":0.5}
使い方:
    python groundcheck.py <data.json> [--json]
終了コード: 全主張が根拠あり=0 / 根拠なしの主張あり=1
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

STOP = {"the", "a", "an", "of", "to", "in", "on", "and", "is", "was", "it", "its",
        "that", "this", "by", "with", "for", "as", "at", "be", "are", "were", "has",
        "have", "had", "which", "used", "from", "or"}


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[:-len(suf)]
    return w


def content(text):
    return {stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="RAG grounding / hallucination verifier")
    ap.add_argument("data", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    data = json.loads(args.data.read_text(encoding="utf-8"))
    thr = float(data.get("threshold", 0.5))
    src = [(s["id"], content(s["text"])) for s in data["sources"]]

    rows = []
    for claim in sentences(data["answer"]):
        cw = content(claim)
        if not cw:
            continue
        best_id, best_cov = None, 0.0
        for sid, sw in src:
            cov = len(cw & sw) / len(cw)
            if cov > best_cov:
                best_cov, best_id = cov, sid
        grounded = best_cov >= thr
        rows.append({"claim": claim, "grounded": grounded,
                     "coverage": round(best_cov, 2), "source": best_id if grounded else None})

    n = len(rows)
    ok = sum(r["grounded"] for r in rows)
    rate = ok / n if n else 0.0

    if args.json:
        print(json.dumps({"threshold": thr, "grounding_rate": round(rate, 3),
                          "all_grounded": ok == n, "claims": rows}, ensure_ascii=False, indent=2))
    else:
        print(f"ソース {len(src)}  主張 {n}  被覆閾値 {thr}\n")
        for r in rows:
            if r["grounded"]:
                print(f"  ✓ [{r['source']} cov {r['coverage']}] {r['claim'][:64]}")
            else:
                print(f"  ✗ 根拠なし(幻覚候補, cov {r['coverage']}) {r['claim'][:64]}")
        gate = "✓ 全主張が根拠あり(合格)" if ok == n else f"✗ {n-ok}件の根拠なし主張(不合格)"
        print(f"\n-- 根拠率 {ok}/{n} = {rate:.0%}  → {gate}")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
