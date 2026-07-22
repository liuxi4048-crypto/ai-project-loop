#!/usr/bin/env python3
"""biaslens: ニュース文の扇情的・主観的な語(loaded language)を検出し中立化する。

自動ジャーナリズムでは、生成文に書き手の主観・偏向が紛れ込みやすい。本ツールは、
編集的断定・扇情的な動詞/形容詞・レッテル的な名詞などを語彙ベースで検出し、
中立な言い換え(または削除)を提案して中立化テキストを生成する。
Python 3 標準ライブラリのみ・決定論的。

使い方:
    python biaslens.py <text_file> [--json] [--rewrite-only]
終了コード: バイアス語を検出=1 / なし=0
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# (パターン, カテゴリ, 中立化後(None=削除), 重み)。長い句を先に置く(最長一致)。
LEXICON = [
    (r"everyone knows that", "editorializing", None, 1.5),
    (r"it is clear that", "editorializing", None, 1.5),
    (r"there is no doubt that", "editorializing", None, 1.5),
    (r"so-?called", "labeling", None, 1.2),
    (r"clearly", "editorializing", None, 1.5),
    (r"obviously", "editorializing", None, 1.5),
    (r"undoubtedly", "editorializing", None, 1.5),
    (r"disastrous", "loaded_adj", "significant", 1.0),
    (r"catastrophic", "loaded_adj", "serious", 1.0),
    (r"reckless", "loaded_adj", "contested", 1.0),
    (r"shocking", "loaded_adj", "notable", 1.0),
    (r"stunning", "loaded_adj", "notable", 1.0),
    (r"radical", "loaded_adj", "significant", 1.0),
    (r"slammed", "loaded_verb", "criticized", 1.0),
    (r"blasted", "loaded_verb", "criticized", 1.0),
    (r"boasted", "loaded_verb", "said", 1.0),
    (r"admitted", "loaded_verb", "said", 1.0),
    (r"refused to", "loaded_verb", "did not", 1.0),
    (r"regime", "labeling", "government", 1.0),
    (r"propaganda", "labeling", "messaging", 1.0),
]

COMPILED = [(re.compile(rf"\b{pat}\b", re.IGNORECASE), cat, repl, w)
            for pat, cat, repl, w in LEXICON]


def detect(text: str) -> list:
    findings = []
    for rx, cat, repl, w in COMPILED:
        for m in rx.finditer(text):
            findings.append({
                "match": m.group(0), "category": cat,
                "suggestion": repl if repl is not None else "(削除)",
                "weight": w, "start": m.start(),
            })
    return sorted(findings, key=lambda f: f["start"])


def neutralize(text: str) -> str:
    out = text
    for rx, _cat, repl, _w in COMPILED:
        out = rx.sub("" if repl is None else repl, out)
    out = re.sub(r"[ \t]{2,}", " ", out)               # 削除で生じた二重空白
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)          # 記号前の空白
    out = re.sub(r"([.!?])\s*,\s*", r"\1 ", out)        # 「.,」→「. 」(語削除の名残)
    out = re.sub(r"^[\s,;:]+", "", out)                 # 先頭の孤立した記号
    # 文頭の大文字化(先頭 と .?! の直後)
    out = re.sub(r"(^|[.!?]\s+)([a-z])",
                 lambda m: m.group(1) + m.group(2).upper(), out)
    return out.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="news bias detector and neutralizer")
    ap.add_argument("text", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rewrite-only", action="store_true", help="中立化テキストのみ出力")
    args = ap.parse_args()

    if not args.text.is_file():
        print(f"error: no such file: {args.text}", file=sys.stderr)
        return 2

    text = args.text.read_text(encoding="utf-8")
    findings = detect(text)
    neutral = neutralize(text)
    n_words = len(re.findall(r"[A-Za-z']+", text))
    bias_score = round(sum(f["weight"] for f in findings) / n_words * 100, 2) if n_words else 0.0

    if args.rewrite_only:
        print(neutral)
        return 1 if findings else 0

    if args.json:
        print(json.dumps({"bias_score_per_100w": bias_score, "findings": findings,
                          "neutralized": neutral}, ensure_ascii=False, indent=2))
    else:
        print(f"bias score = {bias_score} /100語   検出 {len(findings)} 件\n")
        by_cat = {}
        for f in findings:
            by_cat.setdefault(f["category"], []).append(f)
        for cat, items in sorted(by_cat.items()):
            print(f"  [{cat}] {len(items)}件")
            for f in items:
                print(f"    - 「{f['match']}」 → {f['suggestion']}")
        print("\n--- 中立化テキスト ---")
        print(neutral)

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
