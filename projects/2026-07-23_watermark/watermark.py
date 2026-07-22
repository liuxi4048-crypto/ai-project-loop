#!/usr/bin/env python3
"""watermark: グリーンリスト統計透かしの埋め込みと z 検定による検出のデモ。

生成テキストの来歴(AI生成か)を判定する古典的手法に「グリーンリスト透かし」がある。
各位置で直前トークンのハッシュから語彙を green/red に分割し、透かし入り生成器は green を
優先して選ぶ。検出側は鍵を知っていれば、各トークンが green である割合を数え、無透かしの
期待割合 γ に対する z スコアで有意に多ければ「透かしあり」と判定する。
本ツールは埋め込み・検出を最小構成で実装する。Python 3 標準ライブラリのみ・決定論的。

使い方:
    python watermark.py               # 透かし入り/無し を生成して検出(デモ)
    python watermark.py <text_file>   # 空白区切りトークン列を検出
"""
import argparse
import hashlib
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

VOCAB = [f"w{i:02d}" for i in range(50)]   # 語彙(50語)
KEY = "loop-secret"
GAMMA = 0.5                                 # green の割合


def green_set(prev: str, key: str, gamma: float) -> set:
    """直前トークン+鍵のハッシュで語彙を決定論的に並べ替え、先頭 γ 割を green に。"""
    h = hashlib.sha256(f"{key}|{prev}".encode()).digest()
    order = sorted(VOCAB, key=lambda w: hashlib.sha256(h + w.encode()).digest())
    return set(order[:int(len(VOCAB) * gamma)])


def generate(n: int, key: str, gamma: float, watermarked: bool) -> list:
    toks = ["w00"]
    for i in range(n):
        prev = toks[-1]
        g = sorted(green_set(prev, key, gamma))
        if watermarked and not (i % 5 == 0):        # 5回に1回だけ red(現実味)
            toks.append(g[hashlib.md5(f"{i}".encode()).digest()[0] % len(g)])
        else:
            toks.append(VOCAB[(i * 7 + 3) % len(VOCAB)])  # green を考慮しない選択
    return toks[1:]


def detect(tokens: list, key: str, gamma: float) -> dict:
    prev = "w00"
    scored = green = 0
    for t in tokens:
        if t in VOCAB:
            scored += 1
            if t in green_set(prev, key, gamma):
                green += 1
        prev = t
    if scored == 0:
        return {"scored": 0, "green": 0, "green_frac": 0.0, "z": 0.0, "watermarked": False}
    expected = gamma * scored
    var = gamma * (1 - gamma) * scored
    z = (green - expected) / math.sqrt(var) if var > 0 else 0.0
    return {"scored": scored, "green": green, "green_frac": round(green / scored, 3),
            "z": round(z, 2), "watermarked": z > 4.0}


def main() -> int:
    ap = argparse.ArgumentParser(description="green-list watermark embed & z-test detect")
    ap.add_argument("text_file", nargs="?", type=Path)
    ap.add_argument("--key", default=KEY)
    ap.add_argument("--gamma", type=float, default=GAMMA)
    args = ap.parse_args()

    if args.text_file:
        if not args.text_file.is_file():
            print(f"error: no such file: {args.text_file}", file=sys.stderr)
            return 2
        toks = args.text_file.read_text(encoding="utf-8").split()
        r = detect(toks, args.key, args.gamma)
        verdict = "透かしあり(AI生成の疑い)" if r["watermarked"] else "透かしなし"
        print(f"{args.text_file.name}: green {r['green']}/{r['scored']} "
              f"(frac {r['green_frac']}, γ={args.gamma})  z={r['z']}  → {verdict}")
        return 0

    # デモ: 透かし入り / 無し を生成して検出
    print(f"green-list 透かし  vocab={len(VOCAB)}  γ={args.gamma}  key='{args.key}'\n")
    for label, wm in (("watermarked", True), ("human(無透かし)", False)):
        toks = generate(80, args.key, args.gamma, wm)
        r = detect(toks, args.key, args.gamma)
        verdict = "✓ 透かし検出" if r["watermarked"] else "· 透かしなし"
        print(f"  {label:>16}: green_frac={r['green_frac']:<5} z={r['z']:>6}  {verdict}")
    print(f"\n-- 透かし入りは green 率が γ={args.gamma} を大きく上回り z>4 で検出、"
          "無透かしは z≈0。鍵なしでは green/red 分割が不明で検出不可")
    return 0


if __name__ == "__main__":
    sys.exit(main())
