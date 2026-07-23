#!/usr/bin/env python3
"""sancscreen: 取引相手名を制裁・禁輸ウォッチリストに照合するスクリーニング。

輸出規制・制裁の強化で、取引相手が禁輸リストに載っていないかの名寄せ照合(screening)が要る。
表記ゆれ(法人接尾辞・別名・語順)に強いことが肝心。本ツールは、法人/汎用接尾辞を正規化し、
トークンの被覆率とJaccardを混合したスコアで各社をウォッチリスト(別名付き)に照合し、
MATCH(一致)/POSSIBLE(要確認)/CLEAR(問題なし)に帯域分けする。標準ライブラリのみ・決定論的。

入力(JSON): {"watchlist":[{"name","aliases":[...],"program"}...], "queries":[...],
             "match":0.8, "possible":0.45}
使い方:
    python sancscreen.py <data.json> [--json]
終了コード: MATCH/POSSIBLE を検出=1 / 全てCLEAR=0
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 法人・汎用接尾辞(照合の邪魔になる語)
GENERIC = {"co", "ltd", "inc", "corp", "corporation", "technologies", "technology",
           "tech", "group", "holdings", "limited", "plc", "llc", "company", "the",
           "and", "of", "international", "intl", "sa", "ag", "gmbh",
           # 汎用的な組織記述語(識別トークンを埋もれさせないため除外)
           "research", "institute", "labs", "laboratory", "laboratories", "services",
           "solutions", "systems", "global", "national", "industries", "enterprises"}


def toks(name):
    return {w for w in re.findall(r"[a-z0-9]+", name.lower()) if w not in GENERIC}


def score(q, c):
    a, b = toks(q), toks(c)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    cov = inter / min(len(a), len(b))          # 短い側の被覆(スクリーニングは再現率重視)
    jac = inter / len(a | b)
    return cov * (0.5 + 0.5 * jac)             # 被覆を主、Jaccardで薄めすぎを抑制


def best_match(q, watchlist):
    best = {"score": 0.0, "name": None, "program": None, "via": None}
    for w in watchlist:
        for cand in [w["name"]] + w.get("aliases", []):
            s = score(q, cand)
            if s > best["score"]:
                best = {"score": round(s, 3), "name": w["name"],
                        "program": w.get("program"), "via": cand}
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description="sanctions / denied-party name screening")
    ap.add_argument("data", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    d = json.loads(args.data.read_text(encoding="utf-8"))
    wl = d["watchlist"]
    m_thr = float(d.get("match", 0.8))
    p_thr = float(d.get("possible", 0.45))

    rows = []
    for q in d["queries"]:
        b = best_match(q, wl)
        band = "MATCH" if b["score"] >= m_thr else ("POSSIBLE" if b["score"] >= p_thr else "CLEAR")
        rows.append({"query": q, "band": band, **b})

    hits = sum(1 for r in rows if r["band"] != "CLEAR")

    if args.json:
        print(json.dumps({"match": m_thr, "possible": p_thr,
                          "results": rows, "hits": hits}, ensure_ascii=False, indent=2))
    else:
        mark = {"MATCH": "⛔ 一致", "POSSIBLE": "⚠ 要確認", "CLEAR": "○ 問題なし"}
        print(f"ウォッチリスト {len(wl)}社  照合 {len(d['queries'])}件  "
              f"閾値 一致≥{m_thr}/要確認≥{p_thr}\n")
        for r in rows:
            if r["band"] == "CLEAR":
                print(f"  [{mark[r['band']]}] {r['query']}")
            else:
                via = f" (別名:{r['via']})" if r["via"] and r["via"] != r["name"] else ""
                print(f"  [{mark[r['band']]}] {r['query']} → {r['name']}{via} "
                      f"score {r['score']} / {r['program']}")
        print(f"\n-- 検出 {hits}/{len(d['queries'])}(一致・要確認)。"
              "表記ゆれ・別名・法人接尾辞を正規化して照合")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
