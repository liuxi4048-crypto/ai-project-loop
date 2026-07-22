#!/usr/bin/env python3
"""rubric-score: 宣言的ルーブリックでエッセイを基準別に採点し、改善フィードバックを生成する。

自動エッセイ採点(AES)は「点数を当てる」だけでなく、なぜその点かを説明し改善につながる
フィードバックを返せることが実用上重要。本ツールは、重み付きの評価基準(criteria)を書いた
ルーブリック(JSON)に対しエッセイを採点し、基準ごとのサブスコアと具体的な改善提案を出す
透明・決定論的なスコアラ。Python 3 標準ライブラリのみ。

基準タイプ:
  metric   : 表層特徴(文数/語数/平均文長/接続詞数/段落数/語彙多様性)を ideal 範囲と比較
  keywords : 内容カバレッジ(any: いずれか / all: 全て を要求)

使い方:
    python rubric_score.py <rubric.json> <essay.txt> [--json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CONNECTIVES = {"however", "therefore", "because", "moreover", "thus", "furthermore",
               "for example", "in contrast", "consequently", "although", "whereas",
               "as a result", "on the other hand", "first", "second", "finally"}


def features(text: str) -> dict:
    words = re.findall(r"[A-Za-z']+", text.lower())
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    low = text.lower()
    conn = sum(low.count(c) for c in CONNECTIVES)
    n_words = len(words)
    return {
        "word_count": n_words,
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "avg_sentence_len": (n_words / len(sentences)) if sentences else 0,
        "connective_count": conn,
        "unique_word_ratio": (len(set(words)) / n_words) if n_words else 0,
    }


def score_metric(x: float, ideal: list, hard: list) -> float:
    """ideal[lo,hi] 内なら1.0、hard 境界へ線形に0へ低下。"""
    lo, hi = ideal
    hmin, hmax = hard
    if lo <= x <= hi:
        return 1.0
    if x < lo:
        return max(0.0, (x - hmin) / (lo - hmin)) if lo > hmin else 0.0
    return max(0.0, (hmax - x) / (hmax - hi)) if hmax > hi else 0.0


def score_keywords(text: str, spec: dict):
    low = text.lower()
    any_kw = [k for k in spec.get("any", [])]
    all_kw = [k for k in spec.get("all", [])]
    missing_all = [k for k in all_kw if k.lower() not in low]
    hit_any = [k for k in any_kw if k.lower() in low]
    parts, fb = [], []
    if all_kw:
        parts.append((len(all_kw) - len(missing_all)) / len(all_kw))
        if missing_all:
            fb.append(f"必須語が不足: {', '.join(missing_all)}")
    if any_kw:
        parts.append(1.0 if hit_any else 0.0)
        if not hit_any:
            fb.append(f"いずれかの語が必要: {', '.join(any_kw)}")
    sub = sum(parts) / len(parts) if parts else 1.0
    return sub, fb


def evaluate(rubric: dict, text: str) -> dict:
    feat = features(text)
    rows, total_w, weighted = [], 0.0, 0.0
    for c in rubric["criteria"]:
        w = float(c.get("weight", 1))
        total_w += w
        fb = []
        if c["type"] == "metric":
            x = feat[c["feature"]]
            sub = score_metric(x, c["ideal"], c["hard"])
            if sub < 1.0:
                lo, hi = c["ideal"]
                if x < lo:
                    fb.append(f"{c['feature']}={x:.1f} は低い(目安 {lo}〜{hi})→ 増やす")
                else:
                    fb.append(f"{c['feature']}={x:.1f} は高い(目安 {lo}〜{hi})→ 減らす")
        else:
            sub, fb = score_keywords(text, c)
        weighted += w * sub
        rows.append({"criterion": c["name"], "weight": w,
                     "sub_score": round(sub, 3), "feedback": fb})
    overall = round(weighted / total_w * 100, 1) if total_w else 0.0
    return {"overall": overall, "features": feat, "criteria": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description="rubric-based essay scorer with feedback")
    ap.add_argument("rubric", type=Path)
    ap.add_argument("essay", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for p in (args.rubric, args.essay):
        if not p.is_file():
            print(f"error: no such file: {p}", file=sys.stderr)
            return 2

    rubric = json.loads(args.rubric.read_text(encoding="utf-8"))
    result = evaluate(rubric, args.essay.read_text(encoding="utf-8"))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"essay={args.essay.name}   総合スコア: {result['overall']} / 100\n")
        print(f"{'criterion':>18} {'weight':>6} {'score':>6}")
        for r in result["criteria"]:
            print(f"{r['criterion']:>18} {r['weight']:>6.0f} {r['sub_score']:>6.2f}")
        print("\n改善フィードバック:")
        any_fb = False
        for r in result["criteria"]:
            for f in r["feedback"]:
                print(f"  - [{r['criterion']}] {f}")
                any_fb = True
        if not any_fb:
            print("  (全基準を満たしています)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
