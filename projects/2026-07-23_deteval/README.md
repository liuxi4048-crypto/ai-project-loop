# deteval — 物体検出の mAP 評価(IoUマッチ)

ai-project-loop **Cycle 25** の成果物(2026-07-23)。

## 概要

物体検出の予測ボックスと正解を **IoU で貪欲マッチ**し、クラス別 **AP(全点補間)**・**mAP@IoU**・
全体の適合率/再現率を算出する評価ハーネス。図面レイアウト検出などの検出精度評価に使える。
標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- [[2026-07-23-benchmarking-deep-learning-approaches-for-aec-engineering-dr-8953]] —
  AEC(建築・土木・建設)図面のレイアウト検出を5アーキテクチャで比較し、**mAP_50=0.949** 等で
  評価したベンチマーク。本ツールはその評価指標(IoUマッチ→AP→mAP)の計算部分を実装。
- 系譜: 検索評価 [[2026-07-23-ailqa-evaluating-ai-driven-legal-question-answering-systems-15e7|ireval]]・実行評価 [[2026-07-23-scicodepile-a-128gb-corpus-and-executable-benchmark-for-chal-e2d8|codebench]] と同じ評価系だが、こちらは**物体検出(空間マッチ)**が対象。

## 使い方

```bash
python deteval.py sample/drawings.json
```

- 入力: `{iou_threshold, images:[{gt:[{class,box}], pred:[{class,box,score}]}]}`(box=[x1,y1,x2,y2])
- `--json` で機械可読出力

## 動作確認結果(2026-07-23)

図面2枚・2クラス(wall/door)、一部に誤検出と見逃しを含む例:

```
     class     AP   TP   FP   FN   gt
      door  0.500    1    1    1    2   ← 1枚目は正解、2枚目は誤位置(FP)+見逃し(FN)
      wall  1.000    3    0    0    3   ← 全て高IoUで正解
-- mAP@0.5 = 0.750   全体 precision=0.800 recall=0.800
```

wall は全予測が IoU≥0.5 で AP=1.0、door は適合率-再現率曲線から AP=0.5(手検算一致)、
両者平均で mAP=0.75。誤検出・見逃しを含む検出結果を正しく採点できている。

## 制限事項

- 単一 IoU 閾値の AP。COCO 式の AP@[.5:.95] 平均や small/medium/large 別集計は未実装
- 貪欲マッチ(スコア降順に最大IoUの未使用GTへ割当)。重複検出の抑制(NMS)は前段の想定
- 軸並行ボックスのみ(回転ボックス・セグメンテーションIoUは対象外)
