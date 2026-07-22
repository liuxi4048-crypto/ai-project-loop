# splitaudit — 学習データ分割の漏洩監査

ai-project-loop **Cycle 15** の成果物(2026-07-23)。

## 概要

同じデータセットに対し **random / grouped(エンティティ横断) / temporal(時間軸)** の3分割を
生成し、各分割の「エンティティ漏洩」「時間漏洩」を監査するCLI。ランダム分割が汎化性能を
過大評価する仕組みを数値で可視化する。Python 3 標準ライブラリ(csv)のみ・シード固定で再現可能。

- エンティティ漏洩% = test のエンティティのうち train にも現れる割合
- 時間漏洩% = test 行のうち train の最大時刻以前に属する割合

## 着想元(11_AI Archive)

- [[2026-07-23-benchmarking-generalization-in-financial-statement-fraud-det-c3d9]] —
  財務諸表不正検知でランダム分割が**未知企業・将来期間への汎化を過大評価**する問題を指摘し、
  企業横断・時間軸での堅牢な評価を提案した論文。本ツールはその漏洩を任意のCSVで監査する。
- 系譜: 分布シフト評価の [[2026-07-22-the-label-complexity-of-class-conditional-coverage-under-dis-6834|conformal-coverage]] と同じ「評価の落とし穴」テーマだが、こちらは**データ分割の漏洩**が対象。

## 使い方

```bash
python make_sample.py                 # デモ用の合成データ(企業×年)を生成
python splitaudit.py sample/fraud.csv --group-col company_id --time-col year --test-frac 0.3
```

- `--seed` で乱数固定 / `--json` で機械可読出力

## 動作確認結果(2026-07-23)

合成データ(12社×6年=72行)の監査:

```
           split  test行   エンティティ漏洩   時間漏洩
          random     22       100.0%     100.0%   ← 両方を漏洩=過大評価
   grouped(企業横断)  24         0.0%     100.0%   ← 未知企業の評価に適
   temporal(時間軸)   24       100.0%       0.0%   ← 将来期間の評価に適
```

random は既知企業・過去期間を test に混ぜ両軸で100%漏洩。grouped はエンティティ漏洩を、
temporal は時間漏洩をそれぞれ0%に落とし、測りたい汎化軸を正しく分離できている。

## 制限事項

- 漏洩は「エンティティ一致」「時刻順序」の2軸のみ(特徴量経由のリークは検出しない)
- grouped/temporal は test_frac に近い境界を選ぶ近似(厳密な層化はしない)
- 時刻は文字列比較(等幅の年など)を想定。任意日時は正規化が必要
