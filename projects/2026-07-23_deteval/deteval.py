#!/usr/bin/env python3
"""deteval: 物体検出の予測を IoU マッチで評価し、クラス別 AP と mAP を出す。

図面レイアウト検出などの物体検出は、予測ボックスと正解を IoU で対応づけ、
適合率-再現率曲線から AP(Average Precision)、その平均 mAP で評価する。本ツールは
その標準手順(貪欲 IoU マッチ→全点補間 AP→mAP)を最小構成で実装する。標準ライブラリのみ・決定論的。

入力(JSON):
    {"iou_threshold": 0.5,
     "images": [{"gt":   [{"class":"wall","box":[x1,y1,x2,y2]}, ...],
                 "pred": [{"class":"wall","box":[...],"score":0.9}, ...]}, ...]}
使い方:
    python deteval.py <data.json> [--json]
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def iou(a, b) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def average_precision(matches, n_gt) -> float:
    """matches: スコア降順に並んだ 1(TP)/0(FP) 列。全点補間 AP。"""
    if n_gt == 0:
        return 0.0
    tp = fp = 0
    prec, rec = [], []
    for m in matches:
        if m:
            tp += 1
        else:
            fp += 1
        prec.append(tp / (tp + fp))
        rec.append(tp / n_gt)
    mrec = [0.0] + rec + [1.0]
    mpre = [0.0] + prec + [0.0]
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    ap = 0.0
    for i in range(1, len(mrec)):
        if mrec[i] != mrec[i - 1]:
            ap += (mrec[i] - mrec[i - 1]) * mpre[i]
    return ap


def evaluate(images, thr):
    # クラスごとに (予測: image_idx,box,score) と (正解: image_idx,box) を集約
    preds = defaultdict(list)
    gts = defaultdict(list)
    for ii, im in enumerate(images):
        for g in im.get("gt", []):
            gts[g["class"]].append((ii, g["box"]))
        for p in im.get("pred", []):
            preds[p["class"]].append((ii, p["box"], p.get("score", 1.0)))

    classes = sorted(set(gts) | set(preds))
    per_class = {}
    tot_tp = tot_fp = tot_fn = 0
    for c in classes:
        gt_list = gts[c]
        matched = [False] * len(gt_list)
        # gt を画像別に索引
        by_img = defaultdict(list)
        for gi, (ii, box) in enumerate(gt_list):
            by_img[ii].append(gi)
        matches = []
        tp = fp = 0
        for ii, box, score in sorted(preds[c], key=lambda x: -x[2]):
            best_iou, best_gi = 0.0, -1
            for gi in by_img.get(ii, []):
                if matched[gi]:
                    continue
                v = iou(box, gt_list[gi][1])
                if v > best_iou:
                    best_iou, best_gi = v, gi
            if best_gi >= 0 and best_iou >= thr:
                matched[best_gi] = True
                matches.append(1); tp += 1
            else:
                matches.append(0); fp += 1
        fn = len(gt_list) - sum(matched)
        ap = average_precision(matches, len(gt_list))
        per_class[c] = {"ap": round(ap, 3), "tp": tp, "fp": fp, "fn": fn, "n_gt": len(gt_list)}
        tot_tp += tp; tot_fp += fp; tot_fn += fn

    mAP = sum(v["ap"] for v in per_class.values()) / len(per_class) if per_class else 0.0
    precision = tot_tp / (tot_tp + tot_fp) if (tot_tp + tot_fp) else 0.0
    recall = tot_tp / (tot_tp + tot_fn) if (tot_tp + tot_fn) else 0.0
    return per_class, mAP, precision, recall


def main() -> int:
    ap = argparse.ArgumentParser(description="object detection mAP evaluator (IoU matching)")
    ap.add_argument("data", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.data.is_file():
        print(f"error: no such file: {args.data}", file=sys.stderr)
        return 2

    data = json.loads(args.data.read_text(encoding="utf-8"))
    thr = float(data.get("iou_threshold", 0.5))
    per_class, mAP, precision, recall = evaluate(data["images"], thr)

    if args.json:
        print(json.dumps({"iou_threshold": thr, "mAP": round(mAP, 3),
                          "precision": round(precision, 3), "recall": round(recall, 3),
                          "per_class": per_class}, ensure_ascii=False, indent=2))
    else:
        print(f"{args.data.name}  画像 {len(data['images'])}  IoU閾値 {thr}\n")
        print(f"{'class':>10} {'AP':>6} {'TP':>4} {'FP':>4} {'FN':>4} {'gt':>4}")
        for c, v in per_class.items():
            print(f"{c:>10} {v['ap']:>6.3f} {v['tp']:>4} {v['fp']:>4} {v['fn']:>4} {v['n_gt']:>4}")
        print(f"\n-- mAP@{thr} = {mAP:.3f}   全体 precision={precision:.3f} recall={recall:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
