#!/usr/bin/env python3
"""promptlint: プロンプトの指示遵守・ハルシネーションのリスク因子を静的に採点する。

「プロンプト設計の3因子——書式(format)・指示数(instruction count)・文脈長(context length)
——が指示遵守率とハルシネーションを左右する」という実証研究に基づき、プロンプト文を解析して
各因子のリスクを見積り、合成リスクスコアと具体的な改善警告を出す静的リンター。
Python 3 標準ライブラリのみ・決定論的。

しきい値は上記研究の定性的知見に基づくヒューリスティック(絶対的基準ではない)。

使い方:
    python promptlint.py <prompt_file> [--json]
終了コード: 高リスク(score>=60)=1 / それ未満=0
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

IMPERATIVES = {
    "do", "don't", "dont", "always", "never", "ensure", "use", "return", "output",
    "include", "exclude", "avoid", "follow", "make", "write", "generate", "provide",
    "list", "explain", "summarize", "translate", "format", "respond", "answer",
    "consider", "remember", "note", "add", "remove", "keep", "set", "call",
}
MODALS = re.compile(r"\b(must|should|shall|required to|need to|have to)\b", re.IGNORECASE)


def est_tokens(text: str) -> int:
    """粗いトークン数見積り(語数 * 1.3 と 文字数/4 の平均)。"""
    words = len(re.findall(r"\S+", text))
    return int(round((words * 1.3 + len(text) / 4) / 2))


def count_instructions(text: str) -> int:
    lines = text.splitlines()
    count = 0
    listed_line_idx = set()
    for i, line in enumerate(lines):
        s = line.strip()
        if re.match(r"^(\d+[.)]|[-*•])\s+\S", s):        # 箇条書き/番号付き
            count += 1
            listed_line_idx.add(i)
    # リスト外の命令文(命令形の動詞始まり or 助動詞)
    prose = "\n".join(l for i, l in enumerate(lines) if i not in listed_line_idx)
    for sent in re.split(r"[.!?]\s+|\n", prose):
        s = sent.strip()
        if not s:
            continue
        first = re.findall(r"[A-Za-z']+", s.lower())
        if first and first[0] in IMPERATIVES:
            count += 1
        elif MODALS.search(s):
            count += 1
    return count


def detect_formats(text: str) -> list:
    fmts = []
    if re.search(r"^#{1,6}\s", text, re.MULTILINE):
        fmts.append("markdown-heading")
    if re.search(r"^\s*[-*•]\s", text, re.MULTILINE):
        fmts.append("bullet")
    if re.search(r"^\s*\d+[.)]\s", text, re.MULTILINE):
        fmts.append("numbered")
    if re.search(r"\|.*\|", text):
        fmts.append("table")
    if re.search(r"<[a-zA-Z][\w-]*>", text):
        fmts.append("xml/html")
    if re.search(r"[{\[].*[:,].*[}\]]", text, re.DOTALL) and re.search(r'"\w+"\s*:', text):
        fmts.append("json")
    return fmts


def ramp(x, lo, hi):
    """x<=lo で0、x>=hi で1、間は線形。"""
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    return (x - lo) / (hi - lo)


def analyze(text: str) -> dict:
    n_instr = count_instructions(text)
    tokens = est_tokens(text)
    fmts = detect_formats(text)
    # 構造的フォーマットの混在数(散文以外)
    structural = [f for f in fmts if f != "markdown-heading"]

    r_instr = ramp(n_instr, 10, 30)          # 10超で上昇、30で飽和
    r_ctx = ramp(tokens, 4000, 16000)        # 中盤忘却が顕在化する帯
    r_fmt = ramp(len(structural), 1, 4)      # 構造フォーマット2種以上で上昇

    warnings = []
    if n_instr > 25:
        warnings.append(f"指示数 {n_instr} が多い(>25)。単一プロンプトで確実に守れる上限を超え遵守率低下の恐れ")
    elif n_instr > 10:
        warnings.append(f"指示数 {n_instr}。分割やチェックリスト化で遵守率を保ちやすい")
    if tokens > 16000:
        warnings.append(f"推定 {tokens} トークン。文脈中盤の想起が落ち(lost in the middle)ハルシネーション増の恐れ")
    elif tokens > 4000:
        warnings.append(f"推定 {tokens} トークン。重要指示は末尾/冒頭に置き中盤に埋めない")
    if len(structural) >= 3:
        warnings.append(f"構造フォーマット混在({', '.join(structural)})。1つに統一すると遵守率が安定")
    elif len(structural) == 2:
        warnings.append(f"フォーマット2種({', '.join(structural)})。混在は最小限に")

    score = round((0.4 * r_instr + 0.35 * r_ctx + 0.25 * r_fmt) * 100, 1)
    return {
        "risk_score": score,
        "instruction_count": n_instr,
        "est_tokens": tokens,
        "formats": fmts,
        "sub_risk": {"instructions": round(r_instr, 2),
                     "context": round(r_ctx, 2), "format": round(r_fmt, 2)},
        "warnings": warnings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="prompt adherence/hallucination risk linter")
    ap.add_argument("prompt", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.prompt.is_file():
        print(f"error: no such file: {args.prompt}", file=sys.stderr)
        return 2

    r = analyze(args.prompt.read_text(encoding="utf-8"))

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        band = "高リスク" if r["risk_score"] >= 60 else ("中リスク" if r["risk_score"] >= 30 else "低リスク")
        print(f"{args.prompt.name}  risk score = {r['risk_score']} /100  [{band}]\n")
        print(f"  指示数        : {r['instruction_count']}  (risk {r['sub_risk']['instructions']})")
        print(f"  推定トークン  : {r['est_tokens']}  (risk {r['sub_risk']['context']})")
        print(f"  フォーマット  : {', '.join(r['formats']) or 'なし'}  (risk {r['sub_risk']['format']})")
        print("\n警告:")
        for w in r["warnings"]:
            print(f"  - {w}")
        if not r["warnings"]:
            print("  (顕著なリスク因子なし)")

    return 1 if r["risk_score"] >= 60 else 0


if __name__ == "__main__":
    sys.exit(main())
