# stepcheck — 推論チェーンのステップ整合性リンター

ai-project-loop **Cycle 7** の成果物(2026-07-23)。

## 概要

推論チェーンの各ステップを**既知事実ベース(KB)**および**先行ステップ**と照合し、
ステップ単位で `OK` / `CONTRADICTS-KB`(事実と矛盾) / `SELF-INCONSISTENT`(自己矛盾) /
`UNVERIFIABLE`(照合対象なし)を判定する静的リンター。最終回答だけ見ても気づけない
途中ステップのハルシネーションを可視化する。Python 3 標準ライブラリのみ。

主張の書式(KB・ステップ共通):

```
subject | relation | object      # 明示トリプル
subject is object                # 糖衣 (relation=is)
subject is not object            # 否定主張
```

## 着想元(11_AI Archive)

- [[2026-07-23-reasoning-error-from-known-fact-step-level-self-consistency-484d]] —
  長い推論ほどステップ内にハルシネーションが増え検出困難になる問題に対し、**既知の事実と
  照らして各推論ステップの整合性を評価**するステップレベル自己整合性GRPOの論文。本ツールは
  その「事実照合によるステップ単位の検出」を、学習不要の静的チェックとして実装。
- 系譜: Cycle 6 [[2026-07-23-copy-less-ground-more-overcoming-repetitive-copying-in-long-d725|copyrate]] は逐語コピーを、本ツールは**事実矛盾**を見る(トレース解析の別軸)。

## 使い方

```bash
python stepcheck.py sample/facts.txt sample/trace.txt
```

- `--json` でJSON出力 / 終了コード: 矛盾・自己不整合を検出=1・なし=0

## 動作確認結果(2026-07-23)

KB6件に対し、正しいステップと2つの植込みハルシネーションを含む6ステップのチェーン:

```
  step  1 [        ✓] The capital of france is paris.
  step  3 [     ✗ 矛盾] oxygen | atomic_number | 16     └ KBでは oxygen atomic_number ['8']
  step  5 [     ✗ 矛盾] The capital of france is lyon.   └ KBでは capital of france is ['paris']
-- 2 ステップが矛盾/自己不整合 (ハルシネーション疑い)
```

事実と食い違う2ステップ(酸素の原子番号・フランスの首都)のみを正しく検出、他はOK。

## 制限事項

- 主張は上記の軽量書式に一致するものだけを照合(自由文からの一般的な事実抽出はしない)
- 照合は表層正規化(冠詞除去・casefold)。同義語・言い換え・単位換算は判定しない
- KBに無い関係は `UNVERIFIABLE`。KBの網羅性がそのまま検出力になる
