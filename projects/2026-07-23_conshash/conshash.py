#!/usr/bin/env python3
"""conshash: コンシステントハッシュで、ノード増減時のキー再マッピングを最小化する。

分散LLMサービングやKVキャッシュのシャーディングでは、多数のGPU/ノードにキーを割り当てる。
素朴な hash(key) % N は、ノードを1台足すと**ほぼ全キー**の割当先が変わり、キャッシュが総崩れする。
コンシステントハッシュはノードをハッシュ環に配置し、キーは環を時計回りに最近傍ノードへ割り当てる。
ノード増減時に移動するキーは**約 1/N のみ**。仮想ノードで負荷も均等化する。本ツールは、
負荷分散とノード増減時の再マッピング量を、素朴な mod と比較して実証する。標準ライブラリのみ・決定論的。

使い方:
    python conshash.py [--nodes 8 --keys 10000 --vnodes 100] [--json]
"""
import argparse
import bisect
import hashlib
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

RING = 1 << 32


def h(s):
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big") % RING


class Ring:
    def __init__(self, nodes, vnodes):
        self.vnodes = vnodes
        self.points = []   # sorted (pos, node)
        self._pos = []
        self._node = []
        for n in nodes:
            self.add(n)

    def add(self, node):
        for v in range(self.vnodes):
            self.points.append((h(f"{node}#{v}"), node))
        self.points.sort()
        self._pos = [p for p, _ in self.points]
        self._node = [n for _, n in self.points]

    def lookup(self, key):
        i = bisect.bisect(self._pos, h(key))
        return self._node[i % len(self._node)]


def naive(key, nodes):
    return nodes[h(key) % len(nodes)]


def main() -> int:
    ap = argparse.ArgumentParser(description="consistent hashing vs modulo")
    ap.add_argument("--nodes", type=int, default=8)
    ap.add_argument("--keys", type=int, default=10000)
    ap.add_argument("--vnodes", type=int, default=100)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    nodes = [f"gpu{i}" for i in range(args.nodes)]
    keys = [f"key{i}" for i in range(args.keys)]

    ring = Ring(nodes, args.vnodes)
    assign_ch = {k: ring.lookup(k) for k in keys}
    assign_mod = {k: naive(k, nodes) for k in keys}

    def spread(assign):
        c = Counter(assign.values())
        loads = [c.get(n, 0) for n in nodes]
        mean = sum(loads) / len(loads)
        return {"min": min(loads), "max": max(loads),
                "imbalance": round(max(loads) / mean, 3) if mean else 0}

    # ノードを1台追加した時の再マッピング量
    new_nodes = nodes + ["gpu_new"]
    ring2 = Ring(new_nodes, args.vnodes)
    moved_ch = sum(1 for k in keys if ring2.lookup(k) != assign_ch[k])
    moved_mod = sum(1 for k in keys if naive(k, new_nodes) != assign_mod[k])

    ch_spread, mod_spread = spread(assign_ch), spread(assign_mod)
    K = len(keys)

    if args.json:
        print(json.dumps({
            "nodes": args.nodes, "keys": K, "vnodes": args.vnodes,
            "consistent": {"load": ch_spread, "moved_on_add": moved_ch,
                           "moved_pct": round(moved_ch / K * 100, 1)},
            "modulo": {"load": mod_spread, "moved_on_add": moved_mod,
                       "moved_pct": round(moved_mod / K * 100, 1)}}, ensure_ascii=False, indent=2))
    else:
        print(f"ノード {args.nodes}台  キー {K}  仮想ノード {args.vnodes}/台\n")
        print(f"{'方式':>18} {'最小':>6} {'最大':>6} {'不均衡':>7} {'+1台で移動':>12}")
        print(f"{'コンシステントハッシュ':>18} {ch_spread['min']:>6} {ch_spread['max']:>6} "
              f"{ch_spread['imbalance']:>7} {moved_ch:>7}({moved_ch/K:.1%})")
        print(f"{'素朴な hash%N':>18} {mod_spread['min']:>6} {mod_spread['max']:>6} "
              f"{mod_spread['imbalance']:>7} {moved_mod:>7}({moved_mod/K:.1%})")
        print(f"\n-- ノードを1台追加した時、コンシステントハッシュは約1/N({1/(args.nodes+1):.1%})の"
              f"キーだけ移動。素朴なmodはほぼ全キー({moved_mod/K:.0%})が移動しキャッシュが総崩れ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
