#!/usr/bin/env python3
"""capexroi: AIインフラ投資のDCF評価(回収期間・NPV・IRR・ROI)。

「巨額のAI設備投資は正当化されるのか」を、割引キャッシュフロー(DCF)で定量評価する。
資本支出(capex)・耐用年数・増分収益とその成長率・粗利率・運用費・割引率から、年次
キャッシュフロー、回収期間(payback)、正味現在価値(NPV)、内部収益率(IRR)、ROIを算出し、
投資が正当化されるか(NPV>0 かつ 回収<耐用年数)を判定する。標準ライブラリのみ・決定論的。

入力(JSON): {"capex","life_years","annual_revenue","revenue_growth",
             "gross_margin","annual_opex","discount_rate"}(単位は任意, 例:十億ドル)
使い方:
    python capexroi.py [<scenario.json>] [--json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT = {"capex": 10.0, "life_years": 6, "annual_revenue": 4.0, "revenue_growth": 0.15,
           "gross_margin": 0.60, "annual_opex": 0.8, "discount_rate": 0.10}


def cash_flows(p):
    cfs = []
    for t in range(p["life_years"]):
        rev = p["annual_revenue"] * (1 + p["revenue_growth"]) ** t
        cf = rev * p["gross_margin"] - p["annual_opex"]
        cfs.append(cf)
    return cfs


def npv(capex, cfs, rate):
    return -capex + sum(cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cfs))


def payback(capex, cfs):
    cum = 0.0
    for t, cf in enumerate(cfs):
        if cum + cf >= capex:
            frac = (capex - cum) / cf if cf > 0 else 0
            return round(t + frac, 2)
        cum += cf
    return None   # 期間内に回収できない


def irr(capex, cfs, lo=-0.9, hi=5.0, iters=200):
    f_lo, f_hi = npv(capex, cfs, lo), npv(capex, cfs, hi)
    if f_lo * f_hi > 0:
        return None   # 符号変化なし=IRR未定義(この範囲)
    for _ in range(iters):
        mid = (lo + hi) / 2
        f_mid = npv(capex, cfs, mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def main() -> int:
    ap = argparse.ArgumentParser(description="AI infrastructure capex DCF evaluation")
    ap.add_argument("scenario", type=Path, nargs="?")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    p = DEFAULT.copy()
    if args.scenario:
        if not args.scenario.is_file():
            print(f"error: no such file: {args.scenario}", file=sys.stderr)
            return 2
        p.update(json.loads(args.scenario.read_text(encoding="utf-8")))

    cfs = cash_flows(p)
    r = p["discount_rate"]
    v_npv = npv(p["capex"], cfs, r)
    pb = payback(p["capex"], cfs)
    v_irr = irr(p["capex"], cfs)
    total_cf = sum(cfs)
    roi = (total_cf - p["capex"]) / p["capex"]
    justified = v_npv > 0 and pb is not None and pb <= p["life_years"]

    if args.json:
        print(json.dumps({"cash_flows": [round(c, 3) for c in cfs],
                          "npv": round(v_npv, 3), "payback_years": pb,
                          "irr": round(v_irr, 4) if v_irr is not None else None,
                          "roi": round(roi, 3), "justified": justified}, ensure_ascii=False, indent=2))
    else:
        print(f"AIインフラ投資 DCF評価  capex={p['capex']}  耐用{p['life_years']}年  "
              f"割引率{r:.0%}\n")
        print(f"  増分収益 {p['annual_revenue']}(成長{p['revenue_growth']:.0%}/年)  "
              f"粗利{p['gross_margin']:.0%}  運用費{p['annual_opex']}/年\n")
        print(f"{'年':>4} {'キャッシュフロー':>14} {'累計':>8}")
        cum = 0.0
        for t, cf in enumerate(cfs, 1):
            cum += cf
            print(f"{t:>4} {cf:>14.2f} {cum:>8.2f}")
        pb_s = f"{pb}年" if pb is not None else "期間内に回収せず"
        irr_s = f"{v_irr:.1%}" if v_irr is not None else "N/A"
        print(f"\n  回収期間 {pb_s}   NPV {v_npv:+.2f}   IRR {irr_s}   ROI {roi:+.0%}")
        verdict = "✓ 投資は正当化される(NPV>0 かつ 期間内に回収)" if justified else "✗ 正当化されない"
        print(f"\n-- {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
