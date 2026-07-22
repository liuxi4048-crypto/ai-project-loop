#!/usr/bin/env python3
"""aiinnov: 商標レコードから AI イノベーション指標(比率・成長・セクター拡散)を算出する。

AI特許は研究開発を捉えるが、企業が AI を新製品・サービスに実装する動きは商標(trademark)
データの方がよく捉える(全経済セクターを最新かつ横断的にカバー)。本ツールは商標レコード
(年・セクター・名称テキスト)から AI 関連を分類し、AI比率・年次成長率・セクター拡散
(HHI濃度・AI導入セクター数)を算出する。標準ライブラリのみ・決定論的。

入力(CSV): year,sector,text
使い方:
    python aiinnov.py <marks.csv> [--json]
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AI_KEYWORDS = ["ai", "artificial intelligence", "machine learning", "neural",
               "deep learning", "llm", "generative", "chatbot", "computer vision",
               "predictive", "smart", "automation", "algorithm", "intelligent"]
# 単語境界で照合(「ai」が retail/email 等に誤マッチしないように)
_AI_RE = re.compile("|".join(r"\b" + re.escape(k) + r"\b" for k in AI_KEYWORDS), re.IGNORECASE)


def is_ai(text: str) -> bool:
    return bool(_AI_RE.search(text))


def main() -> int:
    ap = argparse.ArgumentParser(description="AI innovation indicators from trademark records")
    ap.add_argument("csv", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.csv.is_file():
        print(f"error: no such file: {args.csv}", file=sys.stderr)
        return 2

    with args.csv.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    ai_rows = [r for r in rows if is_ai(r["text"])]
    ai_total = len(ai_rows)

    by_year_ai = defaultdict(int)
    by_year_all = defaultdict(int)
    by_sector_ai = defaultdict(int)
    sectors_by_year = defaultdict(set)
    for r in rows:
        y = r["year"]
        by_year_all[y] += 1
        if is_ai(r["text"]):
            by_year_ai[y] += 1
            by_sector_ai[r["sector"]] += 1
            sectors_by_year[y].add(r["sector"])

    years = sorted(by_year_all)
    year_rows, prev = [], None
    for y in years:
        ai = by_year_ai[y]
        share = ai / by_year_all[y] if by_year_all[y] else 0.0
        yoy = ((ai - prev) / prev * 100) if prev else None
        year_rows.append({"year": y, "ai": ai, "share": round(share, 3),
                          "yoy_pct": round(yoy, 1) if yoy is not None else None,
                          "sectors": len(sectors_by_year[y])})
        prev = ai

    # セクター拡散: AI商標のセクター濃度 HHI(低いほど広く拡散)
    hhi = sum((c / ai_total) ** 2 for c in by_sector_ai.values()) if ai_total else 0.0
    breadth = len(by_sector_ai)

    if args.json:
        print(json.dumps({"total": total, "ai_total": ai_total,
                          "ai_share": round(ai_total / total, 3) if total else 0,
                          "per_year": year_rows,
                          "sector_breadth": breadth, "sector_hhi": round(hhi, 3),
                          "by_sector": dict(sorted(by_sector_ai.items(), key=lambda x: -x[1]))},
                         ensure_ascii=False, indent=2))
    else:
        print(f"商標 {total}件  AI関連 {ai_total}件 (share {ai_total/total:.1%})\n")
        print(f"{'year':>6} {'AI件数':>7} {'AI比率':>7} {'前年比':>8} {'導入セクター':>10}")
        for r in year_rows:
            yoy = f"{r['yoy_pct']:+.0f}%" if r["yoy_pct"] is not None else "—"
            print(f"{r['year']:>6} {r['ai']:>7} {r['share']:>6.1%} {yoy:>8} {r['sectors']:>10}")
        print(f"\nセクター別AI商標(多い順):")
        for s, c in sorted(by_sector_ai.items(), key=lambda x: -x[1]):
            print(f"  {s:<14} {c}")
        print(f"\n-- AI導入セクター数 {breadth}  セクター濃度HHI {hhi:.3f}"
              "(低いほど全セクターへ広く拡散)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
