#!/usr/bin/env python3
"""capaudit: エージェントの能力(capability)マニフェストを最小権限と封じ込めの観点で監査する。

AIエージェントがサンドボックスを脱出し外部を侵害する事件は、過剰な能力付与と、脱出を可能に
する能力の危険な組合せから起きる。本ツールは、タスクが必要とする能力と実際に付与された能力を
突き合わせ、(1)不要に付与された過剰権限(=攻撃面)、(2)脱出を可能にする能力の組合せ、を
検出し、封じ込めスコアを算出する。標準ライブラリのみ・決定論的。

入力(JSON): {"task_required":[cap...], "granted":[cap...]}
使い方:
    python capaudit.py <manifest.json> [--json]
終了コード: 封じ込めスコア<70(要是正)=1 / それ以上=0
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 能力ごとのリスク階級
RISK = {
    "read_files": "low", "http_get_allowlist": "low",
    "write_files": "medium", "spawn_process": "medium",
    "http_any": "high", "shell_exec": "high", "env_secrets": "high", "eval_code": "high",
}

# 脱出を可能にする能力の組合せ(いずれも granted の部分集合なら該当)
ESCAPE_COMBOS = [
    (frozenset({"http_any", "shell_exec"}), "リモート取得→シェル実行(コンテナ脱出の典型)"),
    (frozenset({"eval_code", "http_any"}), "取得コードの動的実行"),
    (frozenset({"env_secrets", "http_any"}), "秘密を外部へ流出可能"),
    (frozenset({"write_files", "shell_exec"}), "永続化+実行"),
    (frozenset({"shell_exec", "env_secrets", "http_any"}), "完全脱出(実行+秘密+外部通信)"),
]


def audit(required, granted):
    req, grt = set(required), set(granted)
    excess = grt - req
    excess_high = sorted(c for c in excess if RISK.get(c) == "high")
    excess_other = sorted(c for c in excess if RISK.get(c) != "high")
    combos = [(sorted(c), desc) for c, desc in ESCAPE_COMBOS if c <= grt]
    missing = sorted(req - grt)   # タスクに必要だが未付与(機能不足)

    score = 100 - 15 * len(excess_high) - 8 * len(excess_other) - 25 * len(combos)
    score = max(0, score)
    return {"excess_high": excess_high, "excess_other": excess_other,
            "escape_combos": combos, "missing": missing, "score": score}


def main() -> int:
    ap = argparse.ArgumentParser(description="agent capability least-privilege & containment audit")
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.manifest.is_file():
        print(f"error: no such file: {args.manifest}", file=sys.stderr)
        return 2

    m = json.loads(args.manifest.read_text(encoding="utf-8"))
    r = audit(m.get("task_required", []), m.get("granted", []))

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"{args.manifest.name}  必要 {len(m.get('task_required', []))} / "
              f"付与 {len(m.get('granted', []))}\n")
        print("過剰権限(不要に付与=攻撃面):")
        if r["excess_high"] or r["excess_other"]:
            for c in r["excess_high"]:
                print(f"  ⚠ {c} (high)")
            for c in r["excess_other"]:
                print(f"  · {c} ({RISK.get(c, '?')})")
        else:
            print("  (なし=最小権限)")
        print("脱出可能な能力の組合せ:")
        if r["escape_combos"]:
            for caps, desc in r["escape_combos"]:
                print(f"  ✗ {{{', '.join(caps)}}} → {desc}")
        else:
            print("  (なし)")
        if r["missing"]:
            print(f"機能不足(必要だが未付与): {', '.join(r['missing'])}")
        band = "✓ 良好" if r["score"] >= 85 else ("△ 要注意" if r["score"] >= 70 else "✗ 要是正")
        print(f"\n-- 封じ込めスコア {r['score']}/100  [{band}]")
    return 0 if r["score"] >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
