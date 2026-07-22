#!/usr/bin/env python3
"""staypoint: GPS軌跡から滞在点(staypoint)を検出し、意味ある「場所」へ変換する。

生の位置座標列には「移動」と「滞在(自宅・職場・店)」が混在する。滞在点検出は、距離閾値 D 内に
時間閾値 T 以上とどまった連続点群を1つの滞在点(重心)にまとめる古典手法(Li et al.)。
本ツールはそれをノイズ入り軌跡に適用し、滞在点(到着/出発/滞在時間/点数)と移動点数を出す。
標準ライブラリのみ・決定論的。

入力(JSON): {"distance_m":50, "time_s":300, "points":[{"lat","lon","t"}...]}
使い方:
    python staypoint.py <trajectory.json> [--json]
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

R = 6371000.0  # 地球半径(m)


def haversine(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dphi = math.radians(b["lat"] - a["lat"])
    dlmb = math.radians(b["lon"] - a["lon"])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def centroid(pts):
    n = len(pts)
    return (sum(p["lat"] for p in pts) / n, sum(p["lon"] for p in pts) / n)


def detect(points, D, T):
    """Li et al. の滞在点検出。アンカー点から距離D内に留まる連続点群を、時間≥Tなら滞在点に。"""
    n = len(points)
    sps, i = [], 0
    while i < n - 1:
        j = i + 1
        while j < n and haversine(points[i], points[j]) <= D:
            j += 1
        arrival, departure = points[i]["t"], points[j - 1]["t"]
        if departure - arrival >= T:
            cluster = points[i:j]
            clat, clon = centroid(cluster)
            sps.append({"lat": round(clat, 6), "lon": round(clon, 6),
                        "arrival": arrival, "departure": departure,
                        "duration_s": departure - arrival, "n_points": len(cluster)})
            i = j
        else:
            i += 1
    return sps


def main() -> int:
    ap = argparse.ArgumentParser(description="staypoint detection from GPS trajectory")
    ap.add_argument("trajectory", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.trajectory.is_file():
        print(f"error: no such file: {args.trajectory}", file=sys.stderr)
        return 2

    data = json.loads(args.trajectory.read_text(encoding="utf-8"))
    D = float(data.get("distance_m", 50))
    T = float(data.get("time_s", 300))
    pts = data["points"]
    sps = detect(pts, D, T)
    covered = sum(s["n_points"] for s in sps)

    if args.json:
        print(json.dumps({"distance_m": D, "time_s": T, "n_points": len(pts),
                          "staypoints": sps, "moving_points": len(pts) - covered},
                         ensure_ascii=False, indent=2))
    else:
        print(f"軌跡 {len(pts)}点  距離閾値 {D}m  時間閾値 {T}s\n")
        if not sps:
            print("  (滞在点なし=全て移動中)")
        for k, s in enumerate(sps, 1):
            mins = s["duration_s"] / 60
            print(f"  滞在点{k}: ({s['lat']}, {s['lon']})  "
                  f"到着 t={s['arrival']}s 出発 t={s['departure']}s "
                  f"滞在 {mins:.0f}分 ({s['n_points']}点)")
        print(f"\n-- 滞在点 {len(sps)}件 / 滞在点に属する点 {covered} / 移動点 {len(pts)-covered}"
              "(生座標列を意味ある場所へ変換)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
