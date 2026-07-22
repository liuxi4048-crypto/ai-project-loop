#!/usr/bin/env python3
"""pareto-sweep: 宣言的設定でコマンドをパラメータグリッド上に掃引し、Pareto最適を出す。

NVIDIA srt-slurm(宣言的YAML→再現可能なベンチマーク→パラメータスイープ→Pareto分析)の
着想を、依存ゼロ(Python標準ライブラリのみ)のローカル版として実装したもの。
任意のコマンドの stdout から正規表現で指標を抽出できるため、LLMサービングに限らず
「設定を変えて回し、速度と品質のトレードオフを見たい」あらゆる対象に使える。

使い方:
    python sweep.py config.json [--csv out.csv] [--quiet]

config(JSON):
    {
      "command": "python target.py --workers {workers} --batch {batch}",
      "grid": {"workers": [1,2,4], "batch": [8,16,32]},
      "metrics": {
        "throughput": {"pattern": "throughput=([0-9.]+)", "goal": "max"},
        "latency_ms": {"pattern": "latency_ms=([0-9.]+)", "goal": "min"}
      },
      "repeat": 1,
      "cwd": "."
    }
"""
import argparse
import csv
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def expand_grid(grid: dict) -> list:
    """{"a":[1,2],"b":[8,16]} -> [{"a":1,"b":8}, {"a":1,"b":16}, ...]"""
    keys = list(grid)
    return [dict(zip(keys, combo)) for combo in itertools.product(*(grid[k] for k in keys))]


def extract_metric(text: str, pattern: str) -> float:
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"pattern not found in output: {pattern!r}")
    return float(m.group(1))


def run_one(command_tmpl: str, params: dict, metrics: dict, repeat: int, cwd: str) -> dict:
    cmd = command_tmpl.format(**params)
    acc = {name: [] for name in metrics}
    for _ in range(repeat):
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
        )
        if proc.returncode != 0:
            raise RuntimeError(f"command failed ({proc.returncode}): {cmd}\n{proc.stderr.strip()}")
        for name, spec in metrics.items():
            acc[name].append(extract_metric(proc.stdout, spec["pattern"]))
    return {name: sum(vals) / len(vals) for name, vals in acc.items()}


def dominates(a: dict, b: dict, metrics: dict) -> bool:
    """a が b を支配する = 全指標で a>=b かつ 少なくとも1指標で a>b(goal方向を考慮)。"""
    better_or_equal, strictly_better = True, False
    for name, spec in metrics.items():
        av, bv = a[name], b[name]
        if spec["goal"] == "min":
            av, bv = -av, -bv  # 「大きいほど良い」に正規化
        if av < bv:
            better_or_equal = False
            break
        if av > bv:
            strictly_better = True
    return better_or_equal and strictly_better


def pareto_frontier(rows: list, metrics: dict) -> list:
    """支配されていない行のインデックス集合を返す。"""
    front = []
    for i, ri in enumerate(rows):
        if not any(j != i and dominates(rj, ri, metrics) for j, rj in enumerate(rows)):
            front.append(i)
    return front


def ascii_scatter(rows: list, front: set, metrics: dict, width=48, height=16) -> str:
    """指標がちょうど2つのとき、Pareto最適を # 他を . でプロット。"""
    names = list(metrics)
    if len(names) != 2:
        return ""
    xs = [r[names[0]] for r in rows]
    ys = [r[names[1]] for r in rows]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    def scale(v, lo, hi, n):
        return 0 if hi == lo else int(round((v - lo) / (hi - lo) * (n - 1)))

    grid = [[" "] * width for _ in range(height)]
    for i, r in enumerate(rows):
        col = scale(r[names[0]], xmin, xmax, width)
        row = height - 1 - scale(r[names[1]], ymin, ymax, height)  # y上向き
        grid[row][col] = "#" if i in front else ("." if grid[row][col] == " " else grid[row][col])

    body = "\n".join("  |" + "".join(row) for row in grid)
    axis = "  +" + "-" * width
    return (f"\n  {names[1]} (縦, {ymin:g}..{ymax:g}) / {names[0]} (横, {xmin:g}..{xmax:g})\n"
            f"{body}\n{axis}\n  ( # = Pareto最適 / . = 支配されている )")


def main() -> int:
    ap = argparse.ArgumentParser(description="declarative parameter sweep + Pareto analysis")
    ap.add_argument("config", type=Path)
    ap.add_argument("--csv", type=Path, help="結果をCSVに書き出す")
    ap.add_argument("--quiet", action="store_true", help="各実行の進捗を出さない")
    args = ap.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    command = cfg["command"]
    grid = cfg["grid"]
    metrics = cfg["metrics"]
    repeat = int(cfg.get("repeat", 1))
    cwd = cfg.get("cwd") or str(args.config.resolve().parent)

    combos = expand_grid(grid)
    rows = []
    for i, params in enumerate(combos, 1):
        if not args.quiet:
            print(f"[{i}/{len(combos)}] {params}", file=sys.stderr)
        vals = run_one(command, params, metrics, repeat, cwd)
        rows.append({**params, **vals})

    metric_only = [{k: r[k] for k in metrics} for r in rows]
    front = set(pareto_frontier(metric_only, metrics))

    param_keys = list(grid)
    metric_keys = list(metrics)
    header = param_keys + metric_keys + ["pareto"]
    print("\n" + "  ".join(f"{h:>12}" for h in header))
    print("  ".join("-" * 12 for _ in header))
    for i, r in enumerate(rows):
        cells = [f"{r[k]!s:>12}" for k in param_keys]
        cells += [f"{r[k]:>12.3f}" for k in metric_keys]
        cells += [f"{'  ★ PARETO' if i in front else '':>12}"]
        print("  ".join(cells))

    plot = ascii_scatter(metric_only, front, metrics)
    if plot:
        print(plot)

    print(f"\n-- {len(rows)} configs swept, {len(front)} on the Pareto frontier")

    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for i, r in enumerate(rows):
                w.writerow({**r, "pareto": int(i in front)})
        print(f"-- wrote {args.csv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
