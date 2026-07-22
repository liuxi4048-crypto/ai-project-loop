#!/usr/bin/env python3
"""ci-guard: CI/CDのコードから「秘密→外部送信」フローと承認偽装を静的検出する。

エージェント型CI/CDパイプラインへの攻撃(権限フレーミング=「事前承認済み」の偽装 +
難読化コードによる秘密の外部流出)を、パイプラインに流す前に静的検査するリンター。
Python 3 標準ライブラリのみ。

検出:
  A. 秘密の外部流出フロー(high) — env/secret を読んだ値が、外部URLへの送信コマンドや
     ネットワーク送信APIに渡っている(同一行 or 汚染変数の追跡)
  B. 難読化実行(high) — `curl ... | bash` / `base64 -d | sh` / eval(デコード) など
  C. 承認偽装・レビュー抑止フレーズ(medium) — 「事前承認済み」「レビュー不要」等(英/日)

使い方:
    python ci_guard.py <repo_dir> [--json]
終了コード: 検出=1 / なし=0
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SCAN_SUFFIXES = {".sh", ".bash", ".yml", ".yaml", ".py", ".js", ".ts", ".ps1"}

# 秘密の出所
SECRET_RE = re.compile(
    r"\$\{\{\s*secrets\.\w+|"                 # GitHub Actions: ${{ secrets.X }}
    r"\bos\.environ|\bprocess\.env|"          # py / node
    r"\bprintenv\b|\benv\s*\||"               # env ダンプ
    r"\$(?:GITHUB_TOKEN|[A-Z_]*(?:TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL)[A-Z_]*)|"
    r"\b[A-Z_]*(?:TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL)[A-Z_]*\s*[:=]",
    re.IGNORECASE,
)

# ネットワーク送信シンク
SINK_RE = re.compile(
    r"\bcurl\b|\bwget\b|\bnc\b|\bInvoke-WebRequest\b|\bInvoke-RestMethod\b|"
    r"requests\.(?:post|get|put)|urllib\.request|http\.client|"
    r"\bfetch\s*\(|axios\.",
    re.IGNORECASE,
)

# 外部URL(ドメインにドットを含む http(s))。localhost系は除外
EXTERNAL_URL_RE = re.compile(r"https?://(?!localhost|127\.0\.0\.1)[\w.-]+\.[\w.-]+", re.IGNORECASE)

# 難読化実行
OBFUSCATED_EXEC = [
    (re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(bash|sh)\b", re.IGNORECASE), "リモート取得を直接シェル実行 (curl|bash)"),
    (re.compile(r"base64\s+(?:-d|--decode)\b[^\n|]*\|\s*(bash|sh)", re.IGNORECASE), "base64復号をシェル実行"),
    (re.compile(r"\beval\s*\(\s*(?:atob|base64|Buffer\.from)", re.IGNORECASE), "デコード結果を eval 実行"),
    (re.compile(r"\b(?:bash|sh)\s+-c\s+.{0,4}\$\(.*base64.*-d", re.IGNORECASE), "base64復号を -c で実行"),
]

# 承認偽装・レビュー抑止(権限フレーミング)
AUTHORITY_MARKERS = [
    r"pre[-\s]?approved", r"already\s+(?:approved|reviewed)", r"do\s+not\s+block",
    r"skip\s+(?:the\s+)?review", r"no\s+review\s+needed", r"auto[-\s]?merge",
    r"override\s+(?:the\s+)?(?:safety|security|policy)", r"bypass\s+(?:the\s+)?check",
    r"事前(?:に)?承認(?:済|され)", r"承認済みのため", r"レビュー(?:は)?不要",
    r"ブロックしないで", r"チェックを(?:スキップ|飛ばして)",
]
AUTHORITY_RE = re.compile("|".join(AUTHORITY_MARKERS), re.IGNORECASE)

# 汚染変数の代入(値に秘密を含む) — shell / py / js を軽くカバー
ASSIGN_RE = re.compile(r"(?:^|\s)(?:const\s+|let\s+|var\s+)?([A-Za-z_]\w*)\s*=\s*(.+)$")


def scan_file(path: Path, rel: str) -> list:
    findings = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return [{"file": rel, "line": 0, "severity": "low", "type": "read-error", "detail": str(e)}]

    tainted = set()
    for i, line in enumerate(lines, 1):
        # 汚染追跡: 値が秘密 or 既存の汚染変数を参照する代入の左辺を汚染変数に(多段ロンダリング対応)
        m = ASSIGN_RE.search(line)
        if m:
            lhs, rhs = m.group(1), m.group(2)
            refs_tainted_rhs = any(re.search(rf"\b{re.escape(v)}\b", rhs) for v in tainted)
            if SECRET_RE.search(rhs) or refs_tainted_rhs:
                tainted.add(lhs)

        is_sink = SINK_RE.search(line)
        has_ext = EXTERNAL_URL_RE.search(line)
        refs_secret = SECRET_RE.search(line)
        refs_tainted = any(re.search(rf"\$?\{{?\b{re.escape(v)}\b", line) for v in tainted)

        # A. 秘密→外部送信
        if is_sink and (refs_secret or refs_tainted) and has_ext:
            findings.append({
                "file": rel, "line": i, "severity": "high", "type": "secret-egress",
                "detail": f"秘密が外部URL({has_ext.group(0)})への送信に渡っている: {line.strip()[:100]}",
            })
        # 秘密参照 + シンク だが外部URLが変数化されている場合も疑う
        elif is_sink and refs_secret and not has_ext and re.search(r"https?://|\$\w*url", line, re.IGNORECASE):
            findings.append({
                "file": rel, "line": i, "severity": "medium", "type": "secret-egress-suspect",
                "detail": f"秘密参照と送信が同一行(URLが変数化の疑い): {line.strip()[:100]}",
            })

        # B. 難読化実行
        for rx, label in OBFUSCATED_EXEC:
            if rx.search(line):
                findings.append({
                    "file": rel, "line": i, "severity": "high", "type": "obfuscated-exec",
                    "detail": f"{label}: {line.strip()[:100]}",
                })

        # C. 承認偽装
        if AUTHORITY_RE.search(line):
            findings.append({
                "file": rel, "line": i, "severity": "medium", "type": "authority-framing",
                "detail": f"承認偽装/レビュー抑止の疑い: {line.strip()[:100]}",
            })
    return findings


def scan(root: Path) -> list:
    findings = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SCAN_SUFFIXES:
            findings += scan_file(path, str(path.relative_to(root)))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="CI/CD secret-egress & approval-spoofing linter")
    ap.add_argument("root", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2

    findings = scan(args.root)
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["file"], f["line"]))

    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"[{f['severity']:6}] {f['file']}:{f['line']} {f['type']}\n"
                  f"         {f['detail']}")
        counts = {}
        for f in findings:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "clean"
        n_files = len({f["file"] for f in findings})
        print(f"\n-- {len(findings)} findings in {n_files} files ({summary})")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
