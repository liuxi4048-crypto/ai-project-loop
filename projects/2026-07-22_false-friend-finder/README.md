# false-friend-finder — クロスリンガル・ホモグラフ(偽の友)検出器

ai-project-loop **Cycle 3** の成果物(2026-07-22)。

## 概要

言語別の語彙リストを突き合わせ、**綴りが同じで意味の異なる語**(false friends /
crosslingual homographs)を洗い出すCLI。語義(gloss)があれば「偽の友(意味が食い違う)」か
「同源らしい(意味が重なる)」かを自動判定する。Python 3 標準ライブラリのみ。

## 着想元(11_AI Archive)

- [[2026-07-22-the-shared-discovery-paradox-how-a-one-answer-rule-turns-bet-a1e9]] —
  多言語LLMの**共有サブワード語彙**が、言語をまたいで同じ表層形の語を1トークンに潰し、
  言語ごとの意味差を均してしまう問題(crosslingual homograph / false friend)を扱った論文。
  本ツールはその「同綴異義の衝突」を、トークナイザ語彙を跨いで実際に列挙する診断器。

## 使い方

```bash
python finder.py sample
```

- 入力: `<lang>.txt` を並べたディレクトリ。各行は `word` または `word<TAB>gloss`
- `--min-langs N`: N言語以上で共有される語のみ / `--only false-friend|cognate|unknown`: 関係で絞込み
- `--json`: JSON出力 / 終了コード: 検出=1・なし=0
- 判定: gloss同士で意味語(機能語除去後)が重なれば `cognate`、全く重ならなければ `false-friend`、glossが2言語分揃わなければ `unknown`

## 動作確認結果(2026-07-22)

`sample/`(en/es/it/de の小語彙)で6つの同綴異義を検出、全件正しく分類:

```
       ≈ cognate  'actor'   [en, es]        # 両言語とも「役者」
  ⚠ FALSE-FRIEND  'actual'  [en, es]        # en=実際の / es=現在の
  ⚠ FALSE-FRIEND  'burro'   [es, it]        # es=ロバ / it=バター
  ⚠ FALSE-FRIEND  'gift'    [de, en]        # de=毒 / en=贈り物
       ≈ cognate  'libro'   [es, it]        # 両言語とも「本」
  ⚠ FALSE-FRIEND  'pie'     [en, es]        # en=パイ / es=足
-- 4 languages, 6 shared surface forms (cognate=2, false-friend=4)
```

## 制限事項

- 判定は英語メタ言語の gloss に対する語彙重なりヒューリスティック(語義辞書や埋め込みは使わない)
- 表層は完全一致(casefold正規化のみ)。サブワード分割後の部分衝突は対象外 — 全単語での衝突を見る
- 実運用では各言語の頻度語リスト(例: 上位1万語)を `<lang>.txt` に入れて使う想定
