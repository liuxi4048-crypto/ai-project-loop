#!/usr/bin/env python3
"""optmem: 学習時メモリ(重み+勾配+オプティマイザ状態)を方式別に見積り、階層割当の効果を出す。

MoE学習ではオプティマイザ状態がメモリ予算最大の項目になる。例えば bf16 重み 12.6GB を
AdamW で更新すると、一次・二次モーメントで約 50.6GB を保持する。パラメータ種別
(密なバックボーン/エキスパート/ルータ)ごとに状態表現を変える「Tiered State Allocation」で
これを削減できる。本ツールはモデル仕様(JSON)から各方式のメモリを計算し比較する。
Python 3 標準ライブラリのみ・決定論的。GB = 10^9 バイト。

使い方:
    python optmem.py <spec.json> [--json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

GB = 1e9

# オプティマイザ状態の「1パラメータあたりバイト数」(保持する状態の数 × dtype)
STATE_BYTES = {
    "adamw_fp32": 8,   # m(fp32=4) + v(fp32=4)
    "adamw_bf16": 4,   # m(bf16=2) + v(bf16=2)
    "adamw_8bit": 2,   # m(int8=1) + v(int8=1)  (bitsandbytes 等)
    "sgd_momentum": 4, # momentum(fp32=4) のみ
    "sgd": 0,          # 状態なし
}

UNIFORM_SCHEMES = ["adamw_fp32", "adamw_bf16", "adamw_8bit", "sgd_momentum"]

# Tiered(SkewAdam風)の既定方針: 種別ごとに状態表現を変える
DEFAULT_TIER_POLICY = {
    "backbone": "adamw_fp32",   # 密・勾配統計が安定 → 高精度状態
    "experts":  "adamw_8bit",   # 多数・疎に更新 → 低精度で十分
    "router":   "adamw_fp32",   # 小さいが要所 → 高精度
}


def group_bytes(params: float, w_bytes: int, g_bytes: int, state_bytes: int) -> float:
    return params * (w_bytes + g_bytes + state_bytes)


def analyze(spec: dict) -> dict:
    w_bytes = int(spec.get("weight_dtype_bytes", 2))   # bf16
    g_bytes = int(spec.get("grad_dtype_bytes", 2))     # bf16
    groups = spec["groups"]
    total_params = sum(g["params"] for g in groups)

    weights_gb = total_params * w_bytes / GB
    grads_gb = total_params * g_bytes / GB

    uniform = {}
    for scheme in UNIFORM_SCHEMES:
        sb = STATE_BYTES[scheme]
        state_gb = total_params * sb / GB
        uniform[scheme] = {
            "state_gb": round(state_gb, 2),
            "total_gb": round((weights_gb + grads_gb + state_gb), 2),
        }

    # Tiered: 種別ごとに状態方式を割当(spec.tier で上書き可)
    policy = {**DEFAULT_TIER_POLICY, **spec.get("tier", {})}
    tier_state_gb = 0.0
    tier_rows = []
    for g in groups:
        scheme = policy.get(g["name"], "adamw_fp32")
        sb = STATE_BYTES[scheme]
        gsb = g["params"] * sb / GB
        tier_state_gb += gsb
        tier_rows.append({"group": g["name"], "params_b": round(g["params"] / 1e9, 3),
                          "scheme": scheme, "state_gb": round(gsb, 2)})
    tiered_total = weights_gb + grads_gb + tier_state_gb

    baseline = uniform["adamw_fp32"]["total_gb"]
    return {
        "total_params_b": round(total_params / 1e9, 3),
        "weights_gb": round(weights_gb, 2),
        "grads_gb": round(grads_gb, 2),
        "uniform": uniform,
        "tiered": {"total_gb": round(tiered_total, 2),
                   "state_gb": round(tier_state_gb, 2),
                   "breakdown": tier_rows},
        "tiered_savings_gb": round(baseline - tiered_total, 2),
        "tiered_savings_pct": round((baseline - tiered_total) / baseline * 100, 1) if baseline else 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="training memory / optimizer state planner")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.spec.is_file():
        print(f"error: no such file: {args.spec}", file=sys.stderr)
        return 2

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    r = analyze(spec)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"{spec.get('name','model')}  総パラメータ {r['total_params_b']}B  "
              f"(weights {r['weights_gb']}GB + grads {r['grads_gb']}GB, GB=10^9)\n")
        print(f"{'scheme':>16} {'state(GB)':>10} {'total(GB)':>10}")
        for s in UNIFORM_SCHEMES:
            u = r["uniform"][s]
            print(f"{s:>16} {u['state_gb']:>10} {u['total_gb']:>10}")
        print(f"{'tiered(SkewAdam風)':>16} {r['tiered']['state_gb']:>10} {r['tiered']['total_gb']:>10}  ★")
        print("\n  tiered 内訳:")
        for b in r["tiered"]["breakdown"]:
            print(f"    - {b['group']:<10} {b['params_b']:>6}B  {b['scheme']:<12} → state {b['state_gb']}GB")
        print(f"\n-- tiered は adamw_fp32 比で {r['tiered_savings_gb']}GB 削減 "
              f"({r['tiered_savings_pct']}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
