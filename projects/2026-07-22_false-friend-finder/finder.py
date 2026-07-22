#!/usr/bin/env python3
"""false-friend-finder: 多言語語彙から「同綴異義(クロスリンガル・ホモグラフ)」を検出する。

多言語LLMの共有サブワード語彙は、言語をまたいで綴りが同じでも意味の異なる語
(false friends / crosslingual homographs)を1つのトークンに潰してしまう。
本ツールは、言語別の語彙リストを突き合わせて「複数言語に同じ表層形で現れる語」を洗い出し、
語義(gloss)が付いていれば「偽の友(意味が食い違う)」か「同源らしい(意味が重なる)」かを判定する。

入力: <lang>.txt を並べたディレクトリ。各行は  word  または  word<TAB>gloss
使い方:
    python finder.py <wordlists_dir> [--json] [--min-langs N] [--only false-friend]
終了コード: 同綴異義を検出=1 / なし=0
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# glossの意味重なり判定で無視する機能語(英語メタ言語のgloss前提)
_STOP = {"a", "an", "the", "to", "of", "or", "and", "kind", "type",
         "sort", "form", "used", "for", "act", "thing"}


def load_lists(root: Path) -> dict:
    """{lang: {surface: gloss_or_None}} を返す。"""
    langs = {}
    for path in sorted(root.glob("*.txt")):
        lang = path.stem
        entries = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" in line:
                word, gloss = line.split("\t", 1)
            else:
                word, gloss = line, None
            word = word.strip().casefold()
            if word:
                entries[word] = (gloss.strip() if gloss else None)
        if entries:
            langs[lang] = entries
    return langs


def gloss_tokens(gloss: str) -> set:
    return {t for t in _WORD_RE.findall(gloss.casefold()) if t not in _STOP}


def classify(glosses: dict) -> str:
    """言語→gloss の辞書から関係を判定する。"""
    present = {lang: g for lang, g in glosses.items() if g}
    if len(present) < 2:
        return "unknown"          # glossが足りず意味比較できない
    token_sets = [gloss_tokens(g) for g in present.values()]
    # すべてのペアで意味語が全く重ならなければ false-friend
    shared_any = False
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            if token_sets[i] & token_sets[j]:
                shared_any = True
    return "cognate" if shared_any else "false-friend"


def find(langs: dict, min_langs: int) -> list:
    surface_to_lang = defaultdict(dict)   # surface -> {lang: gloss}
    for lang, entries in langs.items():
        for surface, gloss in entries.items():
            surface_to_lang[surface][lang] = gloss

    results = []
    for surface, per_lang in sorted(surface_to_lang.items()):
        if len(per_lang) < min_langs:
            continue
        results.append({
            "surface": surface,
            "langs": sorted(per_lang),
            "glosses": per_lang,
            "relation": classify(per_lang),
        })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="crosslingual homograph / false-friend finder")
    ap.add_argument("root", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-langs", type=int, default=2, help="この言語数以上で共有される語のみ")
    ap.add_argument("--only", choices=["false-friend", "cognate", "unknown"],
                    help="この関係のものだけ表示")
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2

    langs = load_lists(args.root)
    if len(langs) < 2:
        print(f"error: need >=2 wordlists (*.txt), found {len(langs)}", file=sys.stderr)
        return 2

    results = find(langs, args.min_langs)
    if args.only:
        results = [r for r in results if r["relation"] == args.only]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        icon = {"false-friend": "⚠ FALSE-FRIEND", "cognate": "≈ cognate",
                "unknown": "? unknown"}
        for r in results:
            print(f"{icon[r['relation']]:>16}  {r['surface']!r}  [{', '.join(r['langs'])}]")
            for lang in r["langs"]:
                g = r["glosses"][lang]
                print(f"{'':18}{lang}: {g if g else '(no gloss)'}")
        counts = defaultdict(int)
        for r in results:
            counts[r["relation"]] += 1
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none"
        print(f"\n-- {len(langs)} languages, {len(results)} shared surface forms ({summary})")

    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
