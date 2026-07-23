#!/usr/bin/env python3
"""cmsketch: Count-Minスケッチで、少メモリにストリームの頻度を推定する。

エッジ/オンデバイスで大量のイベントストリームを扱うとき、全項目の厳密な頻度を保持するメモリが
ない。Count-Minスケッチは d本のハッシュ×w列の小さなカウンタ表だけで頻度を近似する確率的
データ構造。各項目を d 個のセルに加算し、推定は d セルの最小値をとる。性質:
真の頻度を「下回らない」(常に est ≥ true)、誤差は有界、メモリは項目数に依らず一定。
本ツールはこれを実装し、厳密計数と比較して上位ヒッタの復元と誤差・メモリ削減を確認する。
標準ライブラリのみ・決定論的(hashlibでハッシュ)。

使い方:
    python cmsketch.py [--width 256 --depth 4 --seed 0] [--json]
"""
import argparse
import hashlib
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")


class CountMin:
    def __init__(self, width, depth):
        self.w, self.d = width, depth
        self.t = [[0] * width for _ in range(depth)]

    def _h(self, i, item):
        return int.from_bytes(hashlib.sha256(f"{i}|{item}".encode()).digest()[:8], "big") % self.w

    def add(self, item, c=1):
        for i in range(self.d):
            self.t[i][self._h(i, item)] += c

    def estimate(self, item):
        return min(self.t[i][self._h(i, item)] for i in range(self.d))


def make_stream():
    """決定論的ストリーム: 5個のヘビーヒッタ + 多数のレア項目(各1回)。"""
    stream = []
    heavy = [("hot_0", 500), ("hot_1", 400), ("hot_2", 300), ("hot_3", 200), ("hot_4", 100)]
    for name, freq in heavy:
        stream += [name] * freq
    for k in range(1500):
        stream.append(f"item_{k}")
    # 決定論的に混ぜる(インデックスベースの並べ替え)
    stream.sort(key=lambda s: hashlib.md5(s.encode()).digest())
    return stream


def main() -> int:
    ap = argparse.ArgumentParser(description="Count-Min Sketch frequency estimation")
    ap.add_argument("--width", type=int, default=256)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    stream = make_stream()
    truth = Counter(stream)
    cm = CountMin(args.width, args.depth)
    for x in stream:
        cm.add(x)

    # 上位項目の推定 vs 真値
    top_true = truth.most_common(5)
    rows = []
    never_under = True
    max_err = 0
    for item, tv in top_true:
        est = cm.estimate(item)
        never_under &= est >= tv
        max_err = max(max_err, est - tv)
        rows.append({"item": item, "true": tv, "est": est, "err": est - tv})
    # レア項目の過大評価も確認
    rare_errs = []
    for k in range(0, 1500, 300):
        it = f"item_{k}"
        est = cm.estimate(it)
        never_under &= est >= truth[it]
        rare_errs.append(est - truth[it])

    # スケッチ上位k vs 真の上位k(復元一致)
    sk_top = sorted(truth, key=lambda x: -cm.estimate(x))[:5]
    topk_match = [i for i, _ in top_true] == sk_top

    counters = args.width * args.depth
    distinct = len(truth)

    if args.json:
        print(json.dumps({"stream_len": len(stream), "distinct": distinct,
                          "sketch_counters": counters, "never_underestimates": never_under,
                          "max_error_top5": max_err, "topk_recovered": topk_match,
                          "top": rows}, ensure_ascii=False, indent=2))
    else:
        print(f"Count-Minスケッチ  幅{args.width}×深さ{args.depth}={counters}カウンタ  "
              f"ストリーム{len(stream)}件・異なり{distinct}種\n")
        print(f"{'項目':>8} {'真値':>6} {'推定':>6} {'誤差':>6}")
        for r in rows:
            print(f"{r['item']:>8} {r['true']:>6} {r['est']:>6} {r['err']:>+6}")
        print(f"\n  レア項目(真値1)の推定誤差サンプル: {rare_errs}")
        print(f"  常に true 以下にならない(est≥true): {'✓' if never_under else '✗'}")
        print(f"  スケッチ上位5 = 真の上位5(復元): {'✓' if topk_match else '✗'}")
        print(f"\n-- {counters}カウンタ(異なり{distinct}種の {counters/distinct:.0%})で頻度を近似。"
              "厳密計数を持たずに上位ヒッタを復元でき、推定は決して過小にならない(誤差は片側・有界)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
