#!/usr/bin/env python3
"""sdfplan: 符号付き距離関数(SDF)を使った動作計画 ― 障害物から距離を保つ経路。

占有(0/1)だけの地図では衝突判定しかできないが、各セルに「最近傍障害物までの距離」を符号化した
SDF(クリアランス場)を使うと、余裕(clearance)を考慮した豊かな計画ができる。本ツールは
グリッド地図から SDF を計算し、A* の移動コストにクリアランスを織り込むことで「壁に張り付かず
距離を保つ」経路を求め、素朴な最短経路と比較する。標準ライブラリのみ・決定論的。

使い方:
    python sdfplan.py [--w 6.0] [--json]
"""
import argparse
import heapq
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 地図: '#'=障害物, '.'=自由, 'S'=start, 'G'=goal
MAP = [
    "...............",
    "...............",
    "......###......",
    "......###......",
    "......###......",
    "S.....###.....G",
    "......###......",
    "......###......",
    "......###......",
    "...............",
    "...............",
]


def parse_map(m):
    occ = [[c == "#" for c in row] for row in m]
    start = goal = None
    for y, row in enumerate(m):
        for x, c in enumerate(row):
            if c == "S":
                start = (x, y)
            elif c == "G":
                goal = (x, y)
    return occ, start, goal


def clearance_field(occ):
    """各自由セルの最近傍障害物までのユークリッド距離(SDF)。障害物は0。"""
    H, W = len(occ), len(occ[0])
    obst = [(x, y) for y in range(H) for x in range(W) if occ[y][x]]
    cl = [[0.0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if occ[y][x]:
                cl[y][x] = 0.0
            elif not obst:
                cl[y][x] = float("inf")
            else:
                cl[y][x] = min(math.hypot(x - ox, y - oy) for ox, oy in obst)
    return cl


def astar(occ, cl, start, goal, w):
    """A*。移動コスト = 1 + w/clearance(クリアランス低いほど高コスト)。"""
    H, W = len(occ), len(occ[0])

    def h(p):
        return math.hypot(p[0] - goal[0], p[1] - goal[1])

    openq = [(h(start), 0.0, start)]
    g = {start: 0.0}
    came = {}
    while openq:
        _, gc, cur = heapq.heappop(openq)
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return path[::-1]
        if gc > g.get(cur, float("inf")):
            continue
        cx, cy = cur
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < W and 0 <= ny < H) or occ[ny][nx]:
                continue
            step = math.hypot(dx, dy)
            cost = step * (1 + w / max(0.5, cl[ny][nx]))   # SDFで加減速
            ng = gc + cost
            if ng < g.get((nx, ny), float("inf")):
                g[(nx, ny)] = ng
                came[(nx, ny)] = cur
                heapq.heappush(openq, (ng + h((nx, ny)), ng, (nx, ny)))
    return None


def path_stats(path, cl):
    length = sum(math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
                 for i in range(len(path) - 1))
    min_cl = min(cl[y][x] for x, y in path)
    return round(length, 2), round(min_cl, 2)


def render(m, path):
    grid = [list(row) for row in m]
    for x, y in path:
        if grid[y][x] == ".":
            grid[y][x] = "*"
    return "\n".join("  " + "".join(r) for r in grid)


def main() -> int:
    ap = argparse.ArgumentParser(description="SDF-based clearance-aware motion planning")
    ap.add_argument("--w", type=float, default=6.0, help="クリアランス重み(大きいほど壁を避ける)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    occ, start, goal = parse_map(MAP)
    cl = clearance_field(occ)

    shortest = astar(occ, cl, start, goal, 0.0)      # 最短(SDF無視)
    aware = astar(occ, cl, start, goal, args.w)       # SDF考慮

    s_len, s_cl = path_stats(shortest, cl)
    a_len, a_cl = path_stats(aware, cl)

    if args.json:
        print(json.dumps({"shortest": {"length": s_len, "min_clearance": s_cl},
                          "sdf_aware": {"length": a_len, "min_clearance": a_cl, "w": args.w}},
                         ensure_ascii=False, indent=2))
    else:
        print(f"SDF動作計画  地図 {len(occ[0])}x{len(occ)}  クリアランス重み w={args.w}\n")
        print("最短経路(SDF無視, 壁に張り付く):")
        print(render(MAP, shortest))
        print(f"  経路長 {s_len}  最小クリアランス {s_cl}\n")
        print("SDF考慮経路(距離を保つ):")
        print(render(MAP, aware))
        print(f"  経路長 {a_len}  最小クリアランス {a_cl}")
        print(f"\n-- SDFを移動コストに織り込むと、経路長 {s_len}→{a_len} と僅かに伸びる代わりに"
              f"最小クリアランスが {s_cl}→{a_cl} へ向上(障害物から安全距離を確保)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
