# watermark — グリーンリスト統計透かしの埋め込み+z検定検出

ai-project-loop **Cycle 20** の成果物(2026-07-23)。

## 概要

生成テキストの来歴(AI生成か)を判定する古典的手法「グリーンリスト透かし」の埋め込みと
検出を最小構成で実装したデモ。各位置で**直前トークン+鍵のハッシュ**から語彙を green/red に
分割し、透かし入り生成器は green を優先。検出側は鍵を知っていれば green 率の **z スコア**で
判定する。Python 3 標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- [[2026-07-22-meta-made-its-own-ai-detection-system-it-should-have-just-us-cd49]] —
  Meta の独自AI検出システム(Content Seal)と Google の **SynthID watermark** を対比した記事。
  本ツールは、その系譜にある**統計的テキスト透かし**(green-list 方式)の埋め込み・検出原理を実装。

## 使い方

```bash
python watermark.py               # 透かし入り/無し を生成して検出(デモ)
python watermark.py sample/wm.txt --key loop-secret   # トークン列を検出
```

- `--key`(検出鍵)/ `--gamma`(green の割合, 既定0.5)
- 検出: z > 4 で「透かしあり」。z = (green − γ·T) / √(γ(1−γ)T)

## 動作確認結果(2026-07-23)

デモ(語彙50, γ=0.5, 80トークン):

```
       watermarked: green_frac=0.963 z=8.27  ✓ 透かし検出
  human(無透かし):   green_frac=0.512 z=0.22  · 透かしなし
```

**鍵依存性**(同一の透かしテキスト `sample/wm.txt`):

```
正しい鍵 loop-secret: green 77/80 (0.963)  z=8.27  → 透かしあり
誤った鍵 wrong-key:   green 43/80 (0.537)  z=0.67  → 透かしなし
```

透かし入りは green 率が γ を大きく上回り z>4 で検出。無透かし・誤鍵では green 率が γ 近傍に
戻り z≈0 で非検出 ―― **鍵を知る者だけが検出できる**性質を再現できている。

## 制限事項

- 概念実証(抽象語彙 w00..w49)。実LLMのトークナイザ・ロジット改変は含まない
- 短文・言い換え・翻訳など強い編集で透かしは劣化(頑健版は未実装)
- 実運用の透かしは知覚品質と検出力のトレードオフや攻撃耐性の考慮が必要
