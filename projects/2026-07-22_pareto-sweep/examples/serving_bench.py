#!/usr/bin/env python3
"""サンプルのベンチマーク対象: LLMサービングのthroughput/latencyを決定論的に模擬する。

実クラスタは不要。workers と batch から簡単な待ち行列モデルで指標を計算し、
pareto-sweep が抽出できる形式(throughput=... / latency_ms=...)で出力する。
決定論的なので結果は再現可能。
"""
import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")

ap = argparse.ArgumentParser()
ap.add_argument("--workers", type=int, required=True)
ap.add_argument("--batch", type=int, required=True)
a = ap.parse_args()

# 単純な模擬モデル:
# - throughput は workers と batch にほぼ比例するが、batch 過大で逓減
# - latency は batch に比例し、workers で希釈されるが workers 過多で協調オーバーヘッド
base = a.workers * a.batch
throughput = base / (1 + a.batch / 64.0)                       # req/s
latency = a.batch * 6.0 / a.workers + a.workers * 1.5          # ms
print(f"throughput={throughput:.3f} latency_ms={latency:.3f}")
