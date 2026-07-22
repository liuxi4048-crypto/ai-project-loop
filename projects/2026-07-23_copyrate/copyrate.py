#!/usr/bin/env python3
"""copyrate: 推論トレースが文脈をどれだけ「逐語コピー」しているかを測る。

長文脈で推論するLLMには、入力テキストをそのまま推論過程(reasoning trace)へ
コピーしてしまう「反復コピー(repetitive copying)」という失敗パターンがある。
本ツールは、トレース中のトークンのうち、文脈から連続 MIN_SPAN トークン以上の
逐語一致で覆われる割合(copy-rate)を測る診断器。値が高いほど「根拠に基づく推論」
ではなく「貼り付け」に近い。Python 3 標準ライブラリのみ。

使い方:
    python copyrate.py <context_file> <trace_file> [--min-span 8] [--json]
終了コード: copy-rate >= 0.30(高コピー)=1 / それ未満=0
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

_TOK_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list:
    return _TOK_RE.findall(text.casefold())


def joined(tokens: list) -> str:
    """トークン境界を保つため空白で挟む(部分トークン一致を防ぐ)。"""
    return " " + " ".join(tokens) + " "


def longest_match_len(trace: list, i: int, ctx_str: str, cap: int) -> int:
    """trace[i:] が文脈に連続部分列として現れる最大長を返す(cap で上限)。"""
    lo, hi = 0, min(cap, len(trace) - i)
    # 線形拡張(素直・十分速い): 1トークンずつ伸ばして最後に一致した長さを採用
    best = 0
    length = 1
    while length <= hi:
        span = joined(trace[i:i + length])
        if span in ctx_str:
            best = length
            length += 1
        else:
            break
    return best


def analyze(ctx_tokens: list, trace_tokens: list, min_span: int, cap: int) -> dict:
    ctx_str = joined(ctx_tokens)
    n = len(trace_tokens)
    covered = [False] * n
    spans = []
    i = 0
    while i < n:
        L = longest_match_len(trace_tokens, i, ctx_str, cap)
        if L >= min_span:
            for k in range(i, i + L):
                covered[k] = True
            spans.append({"start": i, "length": L,
                          "text": " ".join(trace_tokens[i:i + L])})
            i += L
        else:
            i += 1

    covered_count = sum(covered)
    copy_rate = covered_count / n if n else 0.0
    longest = max((s["length"] for s in spans), default=0)
    return {
        "trace_tokens": n,
        "copied_tokens": covered_count,
        "copy_rate": round(copy_rate, 4),
        "num_spans": len(spans),
        "longest_span_tokens": longest,
        "spans": spans,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="verbatim copy-rate of a reasoning trace vs its context")
    ap.add_argument("context", type=Path)
    ap.add_argument("trace", type=Path)
    ap.add_argument("--min-span", type=int, default=8, help="逐語コピーとみなす最小連続トークン数")
    ap.add_argument("--cap", type=int, default=200, help="1スパンの探索上限トークン数")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for p in (args.context, args.trace):
        if not p.is_file():
            print(f"error: no such file: {p}", file=sys.stderr)
            return 2

    ctx = tokenize(args.context.read_text(encoding="utf-8"))
    trace = tokenize(args.trace.read_text(encoding="utf-8"))
    result = analyze(ctx, trace, args.min_span, args.cap)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        verdict = ("⚠ 高コピー(貼り付け寄り)" if result["copy_rate"] >= 0.30
                   else "○ 低コピー(根拠に基づく寄り)")
        print(f"trace={args.trace.name}  vs  context={args.context.name}")
        print(f"  copy-rate     : {result['copy_rate']:.1%}  {verdict}")
        print(f"  copied/total  : {result['copied_tokens']}/{result['trace_tokens']} tokens")
        print(f"  copied spans  : {result['num_spans']}  (最長 {result['longest_span_tokens']} tokens)")
        for s in result["spans"][:5]:
            snippet = s["text"][:70] + ("…" if len(s["text"]) > 70 else "")
            print(f"    - @{s['start']} len {s['length']}: {snippet}")
        if result["num_spans"] > 5:
            print(f"    …他 {result['num_spans'] - 5} スパン")

    return 1 if result["copy_rate"] >= 0.30 else 0


if __name__ == "__main__":
    sys.exit(main())
