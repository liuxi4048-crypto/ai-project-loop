#!/usr/bin/env python3
"""codebench: 候補解プログラムをI/Oテストケースで実際に実行し、pass率を集計する。

科学コード生成の評価は「動くか」を実行して確かめる必要がある。本ツールは、問題ごとに
指定された解プログラムを subprocess で走らせ、標準入力にテスト入力を与えて標準出力を
期待値と照合し、問題別のテスト通過数と全体の pass@1(全テスト通過した問題の割合)を出す
実行型ベンチマークランナー。Python 3 標準ライブラリのみ。

⚠ 与えられたコードを実行する。信頼できる自分のサンプルに対してのみ使うこと。

入力(JSON, bench.json と同じ場所からの相対パスで解を指定):
    {"problems": [{"id":"add","solution_file":"solutions/add.py",
                   "tests":[{"input":"2 3","expected":"5"}, ...]}, ...]}
使い方:
    python codebench.py <bench.json> [--timeout 5] [--json]
終了コード: 全問full pass=0 / 1問でも不合格=1
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def run_case(sol: Path, stdin_text: str, timeout: float):
    try:
        p = subprocess.run([sys.executable, str(sol)], input=stdin_text,
                           capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if p.returncode != 0:
        return None, f"exit {p.returncode}: {p.stderr.strip()[:60]}"
    return p.stdout.strip(), None


def run_problem(prob: dict, base: Path, timeout: float) -> dict:
    sol = (base / prob["solution_file"]).resolve()
    if not sol.is_file():
        return {"id": prob["id"], "passed": 0, "total": len(prob["tests"]),
                "status": "solution not found", "fail_detail": str(sol)}
    passed, detail = 0, None
    for i, t in enumerate(prob["tests"], 1):
        out, err = run_case(sol, t["input"], timeout)
        if err:
            detail = detail or f"test{i}: {err}"
            continue
        if out == str(t["expected"]).strip():
            passed += 1
        else:
            detail = detail or f"test{i}: got {out!r} want {t['expected']!r}"
    total = len(prob["tests"])
    status = "PASS" if passed == total else "FAIL"
    return {"id": prob["id"], "passed": passed, "total": total,
            "status": status, "fail_detail": detail}


def main() -> int:
    ap = argparse.ArgumentParser(description="executable code-generation benchmark runner")
    ap.add_argument("bench", type=Path)
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.bench.is_file():
        print(f"error: no such file: {args.bench}", file=sys.stderr)
        return 2

    spec = json.loads(args.bench.read_text(encoding="utf-8"))
    base = args.bench.resolve().parent
    results = [run_problem(p, base, args.timeout) for p in spec["problems"]]
    full = sum(1 for r in results if r["status"] == "PASS")
    pass_at_1 = full / len(results) if results else 0.0

    if args.json:
        print(json.dumps({"pass_at_1": round(pass_at_1, 3), "results": results},
                         ensure_ascii=False, indent=2))
    else:
        print(f"{args.bench.name}  問題 {len(results)}  timeout={args.timeout}s\n")
        for r in results:
            mark = "✓" if r["status"] == "PASS" else "✗"
            line = f"  {mark} {r['id']:<12} {r['passed']}/{r['total']} tests"
            if r["status"] != "PASS":
                line += f"   {r['fail_detail']}"
            print(line)
        print(f"\n-- pass@1 = {pass_at_1:.1%} ({full}/{len(results)} 問題が全テスト通過)")
    return 0 if full == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
