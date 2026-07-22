#!/usr/bin/env python3
"""make_sample.py: 自宅滞在→移動→カフェ滞在 のノイズ入り軌跡を決定論的に生成。"""
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HOME = (35.0000, 139.0000)
CAFE = (35.0100, 139.0100)   # 自宅から約1.4km

pts = []
# 自宅滞在: t=0..600s, 100s毎に7点。±約15mの決定論的ノイズ
for k in range(7):
    off = (math.sin(k) * 0.00013, math.cos(k) * 0.00013)
    pts.append({"lat": round(HOME[0] + off[0], 6), "lon": round(HOME[1] + off[1], 6), "t": k * 100})
# 移動: t=700,800,900 に自宅→カフェへ(距離閾値を超える)
for k, frac in enumerate([0.33, 0.66, 1.0], start=7):
    lat = HOME[0] + (CAFE[0] - HOME[0]) * frac
    lon = HOME[1] + (CAFE[1] - HOME[1]) * frac
    pts.append({"lat": round(lat, 6), "lon": round(lon, 6), "t": k * 100})
# カフェ滞在: t=1000..1500s, 100s毎に6点。±約15mのノイズ
for k in range(6):
    off = (math.cos(k) * 0.00013, math.sin(k) * 0.00013)
    pts.append({"lat": round(CAFE[0] + off[0], 6), "lon": round(CAFE[1] + off[1], 6), "t": 1000 + k * 100})

out = Path(__file__).parent / "sample" / "trip.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"distance_m": 50, "time_s": 300, "points": pts},
                          ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {out} ({len(pts)} points)")
