#!/usr/bin/env python3
"""detiler: タイル分割推論の継ぎ目アーティファクトを、重複スライディング窓の平均で低減する実証。

大規模画像をタイルに分けて推論すると、各タイルが独立に事後分布からサンプルされる場合、
タイル境界に不整合(継ぎ目)が生じる。SWITi の着想は、重複するスライディングウィンドウの
予測を平均し、隣接サンプル間の不整合を固定の継ぎ目座標に溜めず全体へ分散させること。
本ツールは 2D 数値場でこれを再現し、境界不連続量(Total Variation)の低減を定量化する。
Python 3 標準ライブラリのみ・決定論的(乱数なし・ハッシュで擬似オフセット)。

使い方:
    python detiler.py [--size 24] [--tile 8] [--stride 4] [--json]
"""
import argparse
import hashlib
import sys

sys.stdout.reconfigure(encoding="utf-8")


def ground_truth(H, W):
    """滑らかな真の場(なだらかな勾配)。"""
    return [[(x + y) / (H + W) for x in range(W)] for y in range(H)]


def tile_offset(iy, ix, tag):
    """タイル/窓ごとに独立な擬似オフセット(事後サンプルのばらつきを模擬)。[-1,1)。"""
    h = hashlib.sha256(f"{tag}|{iy}|{ix}".encode()).digest()
    return (int.from_bytes(h[:4], "big") % 2000) / 1000.0 - 1.0


def recon_nonoverlap(g, T):
    H, W = len(g), len(g[0])
    out = [[0.0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            o = tile_offset(y // T, x // T, "tile")
            out[y][x] = g[y][x] + o
    return out


def recon_sliding(g, T, S):
    """重複窓(サイズT・ストライドS)の平均。各画素を覆う全窓のオフセットを平均。"""
    H, W = len(g), len(g[0])
    starts_y = sorted(set(list(range(0, H - T + 1, S)) + [H - T]))
    starts_x = sorted(set(list(range(0, W - T + 1, S)) + [W - T]))
    acc = [[0.0] * W for _ in range(H)]
    cnt = [[0] * W for _ in range(H)]
    for wy in starts_y:
        for wx in starts_x:
            o = tile_offset(wy, wx, "win")
            for y in range(wy, wy + T):
                for x in range(wx, wx + T):
                    acc[y][x] += o
                    cnt[y][x] += 1
    return [[g[y][x] + (acc[y][x] / cnt[y][x] if cnt[y][x] else 0.0)
             for x in range(W)] for y in range(H)]


def max_jump(f):
    H, W = len(f), len(f[0])
    m = 0.0
    for y in range(H):
        for x in range(W):
            if x + 1 < W:
                m = max(m, abs(f[y][x + 1] - f[y][x]))
            if y + 1 < H:
                m = max(m, abs(f[y + 1][x] - f[y][x]))
    return m


def boundary_discontinuity(f, T):
    """タイル境界(座標が T の倍数)を跨ぐ隣接画素の平均段差 = 継ぎ目アーティファクト量。"""
    H, W = len(f), len(f[0])
    tot, cnt = 0.0, 0
    for y in range(H):
        for x in range(W):
            if x + 1 < W and (x + 1) % T == 0:      # 縦の継ぎ目を跨ぐ
                tot += abs(f[y][x + 1] - f[y][x]); cnt += 1
            if y + 1 < H and (y + 1) % T == 0:      # 横の継ぎ目を跨ぐ
                tot += abs(f[y + 1][x] - f[y][x]); cnt += 1
    return tot / cnt if cnt else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="tiling-artifact reduction via sliding-window averaging")
    ap.add_argument("--size", type=int, default=24)
    ap.add_argument("--tile", type=int, default=8)
    ap.add_argument("--stride", type=int, default=4)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    H = W = args.size
    g = ground_truth(H, W)
    a = recon_nonoverlap(g, args.tile)
    b = recon_sliding(g, args.tile, args.stride)

    # 継ぎ目量は (recon - g) = オフセット場で測る(g の滑らかさは両者共通の基線)
    na = [[a[y][x] - g[y][x] for x in range(W)] for y in range(H)]
    nb = [[b[y][x] - g[y][x] for x in range(W)] for y in range(H)]
    bd_a = boundary_discontinuity(na, args.tile)   # 境界の平均段差(=継ぎ目)
    bd_b = boundary_discontinuity(nb, args.tile)
    mj_a, mj_b = max_jump(na), max_jump(nb)         # 最大段差
    bd_red = (bd_a - bd_b) / bd_a * 100 if bd_a else 0.0
    mj_red = (mj_a - mj_b) / mj_a * 100 if mj_a else 0.0

    if args.json:
        import json
        print(json.dumps({"size": H, "tile": args.tile, "stride": args.stride,
                          "nonoverlap": {"boundary_disc": round(bd_a, 3), "max_jump": round(mj_a, 3)},
                          "sliding": {"boundary_disc": round(bd_b, 3), "max_jump": round(mj_b, 3)},
                          "boundary_disc_reduction_pct": round(bd_red, 1),
                          "max_jump_reduction_pct": round(mj_red, 1)}, ensure_ascii=False, indent=2))
    else:
        print(f"場 {H}x{W}  tile={args.tile}  stride={args.stride}\n")
        print(f"{'method':>20} {'境界段差':>9} {'最大段差':>9}")
        print(f"{'non-overlap(独立タイル)':>20} {bd_a:>9.3f} {mj_a:>9.3f}")
        print(f"{'sliding-window(平均)':>20} {bd_b:>9.3f} {mj_b:>9.3f}  ★")
        print(f"\n-- スライディング窓平均で 境界段差 {bd_red:.1f}% / 最大段差 {mj_red:.1f}% 低減"
              "(継ぎ目座標への不整合の蓄積を全体へ分散)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
