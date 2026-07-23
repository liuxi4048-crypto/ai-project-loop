# capexroi — AIインフラ投資のDCF評価(回収・NPV・IRR)

ai-project-loop **Cycle 44** の成果物(2026-07-23)。

## 概要

「巨額のAI設備投資は正当化されるのか」を**割引キャッシュフロー(DCF)**で定量評価するCLI。
資本支出・耐用年数・増分収益とその成長率・粗利率・運用費・割引率から、年次キャッシュフロー・
**回収期間(payback)・NPV・IRR・ROI**を算出し、投資が正当化されるか(NPV>0 かつ 期間内に回収)を
判定する。標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- 本サイクルのアーカイブで目立った「AI設備投資は正当化されるか」クラスタ:
  [[2026-07-23-google-justifies-its-massive-ai-spending-with-a-booming-clou-e99b]](クラウド好調で正当化)/
  [[2026-07-23-after-shocking-quarter-ibm-insists-that-ai-isn-t-killing-the-ac40]](AI投資がHW予算を一時圧迫)。
  この横断テーマを切り口に、投資判断そのものを DCF で計算する道具を実装。

## 使い方

```bash
python capexroi.py                    # 既定シナリオ(好調クラウド想定)
python capexroi.py sample/marginal.json
```

- 入力: `{capex,life_years,annual_revenue,revenue_growth,gross_margin,annual_opex,discount_rate}`
- `--json` で機械可読出力

## 動作確認結果(2026-07-23)

```
既定(capex10, 増分収益4/成長15%, 粗利60%, 割引10%):
  回収 4.36年   NPV +1.19   IRR 13.4%   ROI +62%   → ✓ 正当化される
厳しい(capex20, 成長5%, 粗利45%, 割引12%):
  回収 期間内せず  NPV -16.84  IRR -34.4%  ROI -78%  → ✗ 正当化されない
```

好調な収益成長では IRR(13.4%)が割引率(10%)を上回り NPV 正=正当化、高capex・薄利では
回収できず NPV 大幅マイナス。手計算(NPV=−capex+ΣCF/(1+r)^t)と一致。

## 制限事項

- 単純化した増分DCF(税・減価償却の詳細・残存価値・段階投資・稼働率変動は未考慮)
- 増分収益・成長率・粗利は所与の前提(実際は不確実 ― 感度分析/モンテカルロが望ましい)
- IRRは二分法(範囲外・複数解のケースは None)。会計利益ではなくキャッシュフロー基準
