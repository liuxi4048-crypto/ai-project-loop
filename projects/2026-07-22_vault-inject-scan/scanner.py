#!/usr/bin/env python3
"""vault-inject-scan: Markdownノート群からプロンプトインジェクションの兆候を検出する。

Obsidian vault のように「外部由来のテキスト(RSS/Web)が毎日流れ込み、
かつAIエージェントがそれを読む」環境では、ノートに仕込まれた指示文が
エージェントへの注入経路になる。本ツールはその兆候を静的に検査する。

使い方:
    python scanner.py <scan_root> [--json] [--min-severity {low,medium,high}]

終了コード: 検出あり=1 / なし=0 (CI・フック組込み用)
"""
import argparse
import base64
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# --- 検出ルール ---------------------------------------------------------

# エージェントへの命令を装う文言 (英/日)
INSTRUCTION_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "high"),
    (r"disregard\s+(all\s+)?(previous|prior|above)", "high"),
    (r"you\s+are\s+now\s+(a|an|in)\b", "medium"),
    (r"(override|bypass)\s+(the\s+)?(system|safety|security)", "high"),
    (r"do\s+not\s+(tell|inform|alert)\s+the\s+user", "high"),
    (r"(exfiltrate|send|post)\s+.{0,40}(credentials?|secrets?|tokens?|api\s*keys?)", "high"),
    (r"これまでの(指示|命令|ルール)を(無視|忘れ)", "high"),
    (r"(以前|上記|過去)の(指示|命令)を無視", "high"),
    (r"(ユーザー|人間)には(伝え|知らせ|報告し)ないで", "high"),
    (r"あなたは今から.{0,20}(として|になり)", "medium"),
    (r"(必ず|絶対に)(この|次の)(指示|命令)に従", "medium"),
    (r"new\s+system\s+prompt\s*[:：]", "high"),
]

# 不可視・方向制御文字 (隠しテキストの典型)
HIDDEN_CHARS = {
    "​": "ZERO WIDTH SPACE",
    "‌": "ZERO WIDTH NON-JOINER",
    "‍": "ZERO WIDTH JOINER",
    "⁠": "WORD JOINER",
    "﻿": "BOM (mid-file)",
    "‮": "RTL OVERRIDE",
    "‭": "LTR OVERRIDE",
}

# エージェントが指示ファイルとして拾い得る予約名 (claude.md シャドウ事件の教訓)
RESERVED_BASENAMES = {
    "claude.md", "agents.md", "gemini.md", ".cursorrules",
    "copilot-instructions.md", "system.md",
}

BASE64_RE = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")
HTML_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)

SEV_ORDER = {"low": 0, "medium": 1, "high": 2}


def decodes_to_text(blob: str) -> bool:
    """base64塊が自然言語らしきASCIIに復号できるか(誤検知抑制)。"""
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=False)
        text = raw.decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return False
    printable = sum(c.isprintable() or c.isspace() for c in text)
    return printable / max(len(text), 1) > 0.9 and " " in text


def scan_text(text: str, findings: list, relpath: str) -> None:
    lines = text.splitlines()

    for lineno, line in enumerate(lines, 1):
        for pattern, sev in INSTRUCTION_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": relpath, "line": lineno, "severity": sev,
                    "type": "instruction-like",
                    "detail": line.strip()[:120],
                })
        for ch, name in HIDDEN_CHARS.items():
            if ch in line:
                # 行頭BOMはファイル先頭のみ正常
                if ch == "﻿" and lineno == 1:
                    continue
                findings.append({
                    "file": relpath, "line": lineno, "severity": "medium",
                    "type": "hidden-char", "detail": f"{name} x{line.count(ch)}",
                })
        for blob in BASE64_RE.findall(line):
            if decodes_to_text(blob):
                findings.append({
                    "file": relpath, "line": lineno, "severity": "medium",
                    "type": "base64-text", "detail": blob[:60] + "...",
                })

    # HTMLコメント内の命令文 (レンダリングされない=人間に見えない層)
    for m in HTML_COMMENT_RE.finditer(text):
        body = m.group(1)
        for pattern, _ in INSTRUCTION_PATTERNS:
            if re.search(pattern, body, re.IGNORECASE):
                lineno = text[: m.start()].count("\n") + 1
                findings.append({
                    "file": relpath, "line": lineno, "severity": "high",
                    "type": "hidden-comment-instruction",
                    "detail": body.strip()[:120],
                })
                break


def scan(root: Path) -> list:
    findings = []
    for path in sorted(root.rglob("*.md")):
        rel = str(path.relative_to(root))
        if path.name.lower() in RESERVED_BASENAMES:
            findings.append({
                "file": rel, "line": 0, "severity": "high",
                "type": "reserved-filename",
                "detail": "エージェントが指示ファイルとして読み得る名前",
            })
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            findings.append({
                "file": rel, "line": 0, "severity": "low",
                "type": "read-error", "detail": str(e),
            })
            continue
        scan_text(text, findings, rel)
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown prompt-injection scanner")
    ap.add_argument("root", type=Path)
    ap.add_argument("--json", action="store_true", help="JSONで出力")
    ap.add_argument("--min-severity", choices=SEV_ORDER, default="low")
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2

    findings = [f for f in scan(args.root)
                if SEV_ORDER[f["severity"]] >= SEV_ORDER[args.min_severity]]

    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"[{f['severity']:6}] {f['file']}:{f['line']} "
                  f"{f['type']} — {f['detail']}")
        counts = {}
        for f in findings:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "clean"
        n_files = len({f["file"] for f in findings})
        print(f"\n-- {len(findings)} findings in {n_files} files ({summary})")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
