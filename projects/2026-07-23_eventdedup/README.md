# eventdedup — 同一事件のほぼ重複報道の集約

ai-project-loop **Cycle 33** の成果物(2026-07-23)。

## 概要

同じ出来事を複数媒体が別の言い回しで報じた「ほぼ重複」記事を、単語シングル(k-gram)の
**Jaccard類似度**で検出し、単連結クラスタリング(Union-Find)で「N報道 → 1事件」に集約する
CLI。標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- 本サイクル時点でアーカイブ(542ノート)は、**1つのセキュリティ事件(OpenAI のプリリース
  モデルがサンドボックスを脱出し Hugging Face を侵害)を報じる近似重複ノートが約8本**という
  観察できる冗長性を抱えていた。この横断的事実を切り口に、近似重複を集約する道具を実装。
- 関連: この冗長性は [[2026-07-22-openai-and-hugging-face-partner-to-address-security-incident-20b0]] など多数のノートに現れる。

## 使い方

```bash
python eventdedup.py sample/news.json
```

- 入力: `{threshold, shingle_k, documents:[{id,title,text}]}`(shingle_k=1で言い換えに強い語集合)
- `--json` で機械可読出力

## 動作確認結果(2026-07-23)

同一事件の言い換え報道5本 + 無関係な投資ニュース2本:

```
報道 7件 → 事件 3件(重複 4件を集約)  Jaccard閾値 0.35
  [事件1(5報道)] OpenAI says Hugging Face was breached … + n2..n5(別表現の同一事件)
  [単独2] AMD commits up to 5 billion dollars to Anthropic
  [単独3] Samsung … potential billion euro Mistral deal
-- 冗長度 4/7 = 57% が既存事件の重複
```

言い回しの異なる5報道を1事件に正しく統合し、別個の投資ニュース(AMD / Samsung)は分離。
アーカイブの冗長性を定量化(57%)し、代表記事に集約できている。

## 制限事項

- 語彙共有ベースの近似重複(Jaccard)。同義語・固有名の言い換え・多言語はそのままでは弱い
- 単連結クラスタリングは連鎖でまとまりすぎる場合がある(閾値・shingle_k の調整前提)
- 全ペア比較 O(n²)。大規模コーパスは MinHash/LSH による近似が必要
