# sancscreen — 制裁・禁輸ウォッチリスト名寄せスクリーニング

ai-project-loop **Cycle 43** の成果物(2026-07-23)。

## 概要

取引相手名を制裁・禁輸ウォッチリスト(別名付き)に照合するスクリーニングCLI。法人/汎用接尾辞を
正規化し、トークンの**被覆率**と**Jaccard**を混合したスコアで各社を照合、
**MATCH(一致)/ POSSIBLE(要確認)/ CLEAR(問題なし)** に帯域分けする。表記ゆれ・別名・語順・
法人格の違いに頑健。標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- 本サイクル時点のアーカイブで目立った**輸出規制・対中制裁の地政学クラスタ**:
  [[2026-07-22-us-threatens-sanctions-against-chinese-ai-models-over-ip-the-a837]] /
  [[2026-07-23-microsoft-mistral-partnership-is-about-sovereign-ai-7611]](ソブリンAI)など。
  この横断テーマ(制裁・禁輸コンプライアンス)を切り口に、実務で要る名寄せ照合を実装。

## 使い方

```bash
python sancscreen.py sample/screen.json
```

- 入力: `{watchlist:[{name,aliases,program}], queries:[...], match, possible}`
- `--json` で機械可読出力 / 終了コード: 検出=1・全てCLEAR=0

## 動作確認結果(2026-07-23)

架空のウォッチリスト3社に対し6件を照合:

```
⛔一致  Redstar Semiconductor Co., Ltd.        → Redstar Semiconductor      1.0(法人接尾辞を正規化)
⛔一致  RSS Microelectronics Group             → Redstar Semiconductor      1.0(別名で一致)
⛔一致  Aurora Artificial Intelligence Limited → Aurora AI Labs             1.0(言い換え別名)
⚠要確認 Redstar Research Institute             → Redstar Semiconductor      0.75(識別社名を共有)
○問題なし Acme Cloud Services
⛔一致  Blue Harbor Robotics Holdings          → Blue Harbor Robotics       1.0
```

法人格違い・別名・言い換えを一致として検出し、識別性の高い社名だけ共有する例は「要確認」、
無関係な社名はクリア。表記ゆれに頑健な三段階スクリーニングを実現できている。

## 制限事項

- 英字トークンベース(音写・多言語表記・略語展開・翻字ゆれは限定的)
- ウォッチリストと別名は所与(実運用は OFAC/EL 等の公式データと更新が必要)
- スコアは目安。誤検出/取りこぼしの許容度は組織のリスク方針次第(POSSIBLEは人手確認前提)
- **架空データのデモ**。実在の制裁判定には使用しないこと
