#!/usr/bin/env python3
"""make_sample.py: 監査デモ用の合成データ(企業×年)を決定論的に生成する。"""
import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

rows = []
for c in range(1, 13):                      # 12社
    for year in range(2020, 2026):          # 6年
        # 決定論的な擬似特徴・ラベル(乱数なし)
        feat = (c * 7 + year) % 100
        label = 1 if (c + year) % 5 == 0 else 0
        rows.append({"company_id": f"C{c:02d}", "year": year,
                     "feature": feat, "label": label})

out = Path(__file__).parent / "sample" / "fraud.csv"
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["company_id", "year", "feature", "label"])
    w.writeheader()
    w.writerows(rows)
print(f"wrote {out} ({len(rows)} rows)")
