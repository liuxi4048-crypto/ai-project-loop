#!/usr/bin/env python3
"""make_sample.py: 動物×乗り物の作画スコアグリッドを決定論的に生成。
pelican×bicycle だけを加法期待より大きく上振れさせる(=ベンチマーク汚染の模擬)。"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

rows = ["pelican", "cat", "dog", "horse", "fish", "bird", "cow", "frog"]
cols = ["bicycle", "car", "boat", "plane", "train", "skateboard"]
# 行効果(その動物の一般的な描きやすさ)・列効果(その乗り物)
r_eff = {"pelican": 1.0, "cat": 0.5, "dog": 0.3, "horse": 0.0, "fish": -0.5,
         "bird": 0.4, "cow": -0.2, "frog": -0.3}
c_eff = {"bicycle": 0.8, "car": 0.5, "boat": 0.0, "plane": 0.2, "train": -0.1, "skateboard": -0.4}
GRAND = 5.0

scores = []
for i, a in enumerate(rows):
    row = []
    for j, v in enumerate(cols):
        base = GRAND + r_eff[a] + c_eff[v]
        wobble = ((i * 7 + j * 3) % 5 - 2) * 0.08     # 決定論的な小さなばらつき
        val = base + wobble
        if a == "pelican" and v == "bicycle":
            val += 3.5                                  # 汚染: この組合せだけ突出
        row.append(round(val, 3))
    scores.append(row)

out = Path(__file__).parent / "sample" / "pelican_grid.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"rows": rows, "cols": cols, "scores": scores, "z_threshold": 2.5},
                          ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {out}")
