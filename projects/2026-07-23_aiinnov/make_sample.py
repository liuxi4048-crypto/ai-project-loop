#!/usr/bin/env python3
"""make_sample.py: デモ用の商標レコードを決定論的に生成(年×セクターでAI導入が増加・拡散)。"""
import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SECTORS = ["software", "finance", "healthcare", "retail", "manufacturing", "media"]
# セクターごとの AI 導入開始年(software が先行、後年に他セクターへ拡散)
START = {"software": 2019, "finance": 2020, "healthcare": 2021,
         "retail": 2022, "manufacturing": 2023, "media": 2022}

rows = []
for year in range(2019, 2026):
    for si, sector in enumerate(SECTORS):
        # 非AI商標: 各年一定数
        for j in range(4):
            rows.append({"year": year, "sector": sector,
                         "text": f"classic {sector} product line {j}"})
        # AI商標: 導入開始後、年とともに増加(決定論的)
        if year >= START[sector]:
            n_ai = min(6, (year - START[sector]) + 1)
            for j in range(n_ai):
                rows.append({"year": year, "sector": sector,
                             "text": f"AI-powered {sector} assistant with machine learning {j}"})

out = Path(__file__).parent / "sample" / "marks.csv"
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["year", "sector", "text"])
    w.writeheader()
    w.writerows(rows)
print(f"wrote {out} ({len(rows)} rows)")
