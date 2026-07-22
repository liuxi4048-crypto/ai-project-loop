#!/usr/bin/env python3
"""svgsurgeon: SVGの「外科的編集」を検証する ― 修復が適用され、保護対象が無傷か。

SVG編集の良し悪しは「指示された修復が正しく入ったか」だけでなく「それ以外(保護対象
オブジェクト)を一切壊していないか」で決まる。本ツールは元SVGと編集後SVGを id で対応づけ、
(1) 各修復(要素の属性→期待値)が適用されたか、(2) 保護対象 id の要素が完全に不変か、
(3) 修復対象でない要素の巻き添え変更(collateral)を検出する。標準ライブラリ(xml.etree)のみ。

タスク(JSON):
    {"original": "orig.svg", "edited": "edited.svg",
     "repairs": [{"id":"c1","attr":"fill","expected":"red"}],
     "protected": ["bg","r1","t1"]}
使い方:
    python svgsurgeon.py <task.json> [--json]
終了コード: 外科的成功(修復全て&保護全て無傷)=0 / それ以外=1
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def load_elems(path: Path) -> dict:
    """id を持つ全要素を {id: (tag, attrib, text)} に。"""
    root = ET.parse(path).getroot()
    out = {}
    for el in root.iter():
        eid = el.get("id")
        if eid is not None:
            attrib = {k: v for k, v in el.attrib.items() if k != "id"}
            out[eid] = (el.tag, attrib, (el.text or "").strip())
    return out


def same(a, b) -> bool:
    return a[0] == b[0] and a[1] == b[1] and a[2] == b[2]


def main() -> int:
    ap = argparse.ArgumentParser(description="verify surgical SVG edits")
    ap.add_argument("task", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.task.is_file():
        print(f"error: no such file: {args.task}", file=sys.stderr)
        return 2

    task = json.loads(args.task.read_text(encoding="utf-8"))
    base = args.task.resolve().parent
    orig = load_elems(base / task["original"])
    edit = load_elems(base / task["edited"])

    repairs = task.get("repairs", [])
    protected = task.get("protected", [])
    repair_targets = {r["id"] for r in repairs}

    # 1) 修復チェック
    repair_rows = []
    for r in repairs:
        el = edit.get(r["id"])
        got = el[1].get(r["attr"]) if el else None
        ok = got == r["expected"]
        repair_rows.append({"id": r["id"], "attr": r["attr"],
                            "expected": r["expected"], "got": got, "pass": ok})

    # 2) 保護対象の非破壊チェック
    prot_rows = []
    for pid in protected:
        o, e = orig.get(pid), edit.get(pid)
        ok = o is not None and e is not None and same(o, e)
        prot_rows.append({"id": pid, "preserved": ok})

    # 3) 巻き添え変更(修復対象でも保護指定でもない要素が変わった)
    collateral = []
    for eid, o in orig.items():
        if eid in repair_targets:
            continue
        e = edit.get(eid)
        if e is None or not same(o, e):
            collateral.append(eid)

    rp = sum(r["pass"] for r in repair_rows)
    pp = sum(r["preserved"] for r in prot_rows)
    surgical = (rp == len(repair_rows)) and (pp == len(prot_rows)) and not collateral

    if args.json:
        print(json.dumps({"repairs_passed": rp, "repairs_total": len(repair_rows),
                          "protected_preserved": pp, "protected_total": len(prot_rows),
                          "collateral": collateral, "surgical": surgical,
                          "repair_detail": repair_rows, "protected_detail": prot_rows},
                         ensure_ascii=False, indent=2))
    else:
        print(f"{task['original']} → {task['edited']}\n")
        print("修復:")
        for r in repair_rows:
            m = "✓" if r["pass"] else "✗"
            print(f"  {m} #{r['id']} {r['attr']}: got={r['got']!r} want={r['expected']!r}")
        print("保護対象の非破壊:")
        for r in prot_rows:
            m = "✓" if r["preserved"] else "✗ 破壊"
            print(f"  {m} #{r['id']}")
        if collateral:
            print(f"巻き添え変更(collateral): {', '.join('#'+c for c in collateral)}")
        verdict = "✓ 外科的編集 成功" if surgical else "✗ 外科的編集 失敗"
        print(f"\n-- 修復 {rp}/{len(repair_rows)}  保護 {pp}/{len(prot_rows)}  "
              f"巻き添え {len(collateral)}  → {verdict}")
    return 0 if surgical else 1


if __name__ == "__main__":
    sys.exit(main())
