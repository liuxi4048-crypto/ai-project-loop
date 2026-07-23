#!/usr/bin/env python3
"""fundflow: AI投資・資金調達イベントを集計し、資本の流れを分析する。

AI分野には巨額の投資・資金調達が集中している。本ツールは投資イベント(日付・投資家・調達先・
金額)を受け取り、総額・調達先/投資家ランキング・ディールサイズ分布・調達先の資本集中度
(HHI)・最大ディールを算出する。標準ライブラリのみ・決定論的。

入力(JSON): {"events":[{"date","investor","recipient","amount_usd"}...]}
使い方:
    python fundflow.py <events.json> [--json]
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

B = 1e9


def bucket(amount):
    if amount >= 1e9:
        return ">=$1B"
    if amount >= 1e8:
        return "$100M-1B"
    return "<$100M"


def main() -> int:
    ap = argparse.ArgumentParser(description="AI funding / deal-flow analytics")
    ap.add_argument("events", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.events.is_file():
        print(f"error: no such file: {args.events}", file=sys.stderr)
        return 2

    ev = json.loads(args.events.read_text(encoding="utf-8"))["events"]
    total = sum(e["amount_usd"] for e in ev)

    by_recipient = defaultdict(float)
    by_investor = defaultdict(float)
    buckets = defaultdict(int)
    for e in ev:
        by_recipient[e["recipient"]] += e["amount_usd"]
        by_investor[e["investor"]] += e["amount_usd"]
        buckets[bucket(e["amount_usd"])] += 1

    hhi = sum((v / total) ** 2 for v in by_recipient.values()) if total else 0.0
    biggest = max(ev, key=lambda e: e["amount_usd"])
    top_recipients = sorted(by_recipient.items(), key=lambda x: -x[1])
    top_investors = sorted(by_investor.items(), key=lambda x: -x[1])

    if args.json:
        print(json.dumps({"events": len(ev), "total_usd_b": round(total / B, 3),
                          "by_recipient_b": {k: round(v / B, 3) for k, v in top_recipients},
                          "by_investor_b": {k: round(v / B, 3) for k, v in top_investors},
                          "size_buckets": dict(buckets),
                          "recipient_hhi": round(hhi, 3),
                          "biggest_deal": biggest}, ensure_ascii=False, indent=2))
    else:
        print(f"投資イベント {len(ev)}件  総額 ${total/B:.1f}B\n")
        print("調達先ランキング(資本):")
        for r, v in top_recipients:
            print(f"  {r:<22} ${v/B:>6.2f}B  ({v/total:.0%})")
        print("\n投資家ランキング(拠出):")
        for r, v in top_investors:
            print(f"  {r:<22} ${v/B:>6.2f}B")
        print("\nディールサイズ分布:")
        for b in (">=$1B", "$100M-1B", "<$100M"):
            if buckets.get(b):
                print(f"  {b:<10} {buckets[b]}件")
        print(f"\n最大ディール: {biggest['investor']} → {biggest['recipient']} "
              f"${biggest['amount_usd']/B:.2f}B ({biggest['date']})")
        print(f"-- 調達先集中度HHI {hhi:.3f}"
              f"({'高集中(資本が少数の研究所へ)' if hhi >= 0.25 else '分散'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
