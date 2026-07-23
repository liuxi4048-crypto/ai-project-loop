#!/usr/bin/env python3
"""merkle: Merkleツリーで、データ集合の完全性検証と改竄検出を行う。

学習データやモデル成果物の来歴・完全性を担保するには、集合全体を1つのハッシュ(ルート)に
まとめ、個々の要素をルートだけから検証できると都合がよい。Merkleツリーは各チャンクのハッシュを
二分木状に結合し、ルート1個で全体を代表する。任意の1要素について、兄弟ハッシュの列
(inclusion proof)を辿ればルートに一致するかを検証でき、どこか1バイトでも改竄するとルートが
変わる。本ツールはツリー構築・ルート算出・包含証明・改竄検出を実装する。標準ライブラリのみ・決定論的。

使い方:
    python merkle.py            # 組込みデモ(構築→包含証明→改竄検出)
    python merkle.py <file>     # ファイルを行単位でチャンク化して検証
"""
import argparse
import hashlib
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def H(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leaf(data: bytes) -> str:
    return H(b"\x00" + data)          # 葉と内部を区別(第二原像攻撃対策)


def node(a: str, b: str) -> str:
    return H(b"\x01" + bytes.fromhex(a) + bytes.fromhex(b))


def build(chunks):
    """各段のハッシュ列を返す(levels[0]=葉, levels[-1]=[root])。奇数は末尾を複製。"""
    levels = [[leaf(c) for c in chunks]]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        if len(cur) % 2:
            cur = cur + [cur[-1]]
        levels.append([node(cur[i], cur[i + 1]) for i in range(0, len(cur), 2)])
    return levels


def root(levels):
    return levels[-1][0] if levels[-1] else leaf(b"")


def proof(levels, index):
    """index の葉に対する包含証明: [(兄弟ハッシュ, 兄弟が右か)] の列。"""
    path = []
    for lv in levels[:-1]:
        cur = lv + ([lv[-1]] if len(lv) % 2 else [])
        sib = index ^ 1
        path.append((cur[sib], sib > index))
        index //= 2
    return path


def verify(data: bytes, index, path, expected_root) -> bool:
    h = leaf(data)
    for sib, sib_is_right in path:
        h = node(h, sib) if sib_is_right else node(sib, h)
    return h == expected_root


def main() -> int:
    ap = argparse.ArgumentParser(description="Merkle tree integrity verification")
    ap.add_argument("file", type=Path, nargs="?")
    args = ap.parse_args()

    if args.file:
        if not args.file.is_file():
            print(f"error: no such file: {args.file}", file=sys.stderr)
            return 2
        chunks = [ln.encode("utf-8") for ln in args.file.read_text(encoding="utf-8").splitlines()]
    else:
        chunks = [f"record-{i}".encode() for i in range(6)]

    levels = build(chunks)
    r = root(levels)
    print(f"チャンク {len(chunks)}件  木の高さ {len(levels)}段")
    print(f"Merkleルート: {r[:24]}…\n")

    # 各要素の包含証明を検証(ルートだけで個別要素を検証)
    ok = 0
    for i, c in enumerate(chunks):
        p = proof(levels, i)
        if verify(c, i, p, r):
            ok += 1
    print(f"包含証明: {ok}/{len(chunks)} 件がルートに整合(全要素を検証)")
    if chunks:
        print(f"  例: 要素0の証明長 = {len(proof(levels, 0))} ハッシュ"
              f"(全{len(chunks)}件でなく log₂ 個で検証)")

    # 改竄検出: 1要素を書き換えるとルートが変わる
    if chunks:
        tampered = list(chunks)
        tampered[len(chunks) // 2] = tampered[len(chunks) // 2] + b"!"
        r2 = root(build(tampered))
        changed = r2 != r
        # 旧証明で改竄要素を検証すると失敗する
        idx = len(chunks) // 2
        stale_ok = verify(tampered[idx], idx, proof(levels, idx), r)
        print(f"\n改竄検出: 要素{idx}を1バイト改竄 → ルート変化 {'✓' if changed else '✗'}"
              f"  改竄要素は旧ルートに不整合 {'✓' if not stale_ok else '✗'}")
        print(f"  改竄後ルート: {r2[:24]}…")

    print(f"\n-- ルート1個で集合全体の完全性を代表。改竄は必ずルートを変え、"
          "各要素は log₂ 個の兄弟ハッシュ(包含証明)だけでルートから検証できる")
    return 0


if __name__ == "__main__":
    sys.exit(main())
