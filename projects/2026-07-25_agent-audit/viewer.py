"""agent-audit の監査結果を自己完結HTMLのタイムラインビューアに描画する。

外部CSS/JSを読み込まない(オフラインで開ける)。JSは検出のフィルタと
連鎖ステップのハイライトのみを担当し、判定はすべてPython側で確定済み。
"""

from __future__ import annotations

import html
import json
from dataclasses import asdict

SEV_LABEL = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}

TEMPLATE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agent-audit — __SOURCE__</title>
<style>
:root {
  --bg:#f7f8fa; --fg:#1c2024; --muted:#6b7280; --card:#fff; --line:#e3e6ea;
  --critical:#c0392b; --high:#d97706; --medium:#2563eb; --low:#6b7280; --ok:#15803d;
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#15181c; --fg:#e6e8ea; --muted:#9aa3ad; --card:#1d2126; --line:#2c3138;
          --critical:#ef6a5a; --high:#f0a44a; --medium:#6aa2f5; --low:#9aa3ad; --ok:#5ec27a; }
}
* { box-sizing:border-box; }
body { margin:0; padding:24px; background:var(--bg); color:var(--fg);
  font:14px/1.6 "Segoe UI","Yu Gothic UI",system-ui,sans-serif; }
h1 { font-size:20px; margin:0 0 4px; }
.sub { color:var(--muted); font-size:13px; margin-bottom:20px; }
.wrap { max-width:1080px; margin:0 auto; }
.summary { display:flex; gap:16px; flex-wrap:wrap; align-items:center;
  background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; margin-bottom:20px; }
.verdict { font-size:22px; font-weight:700; letter-spacing:.04em; }
.verdict.BLOCK { color:var(--critical); } .verdict.REVIEW { color:var(--high); } .verdict.PASS { color:var(--ok); }
.gauge { flex:1; min-width:220px; height:10px; background:var(--line); border-radius:6px; overflow:hidden; }
.gauge > i { display:block; height:100%; background:linear-gradient(90deg,var(--ok),var(--high),var(--critical)); }
.pill { font-size:12px; padding:2px 8px; border-radius:99px; border:1px solid currentColor; }
.pill.critical { color:var(--critical); } .pill.high { color:var(--high); }
.pill.medium { color:var(--medium); } .pill.low { color:var(--low); }
h2 { font-size:15px; margin:24px 0 10px; }
.finding { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--line);
  border-radius:8px; padding:10px 14px; margin-bottom:8px; cursor:pointer; }
.finding.critical { border-left-color:var(--critical); } .finding.high { border-left-color:var(--high); }
.finding.medium { border-left-color:var(--medium); } .finding.low { border-left-color:var(--low); }
.finding .ttl { font-weight:600; }
.finding .meta, .finding .det { color:var(--muted); font-size:12.5px; }
.finding .det { font-family:Consolas,"Courier New",monospace; word-break:break-all; margin-top:4px; }
.filters { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; }
.filters button { font:inherit; font-size:12.5px; padding:4px 12px; border-radius:99px; cursor:pointer;
  border:1px solid var(--line); background:var(--card); color:var(--fg); }
.filters button[aria-pressed="true"] { background:var(--fg); color:var(--bg); border-color:var(--fg); }
table { width:100%; border-collapse:collapse; background:var(--card);
  border:1px solid var(--line); border-radius:8px; overflow:hidden; }
th, td { text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:12px; color:var(--muted); font-weight:600; }
tr:last-child td { border-bottom:none; }
td.cmd { font-family:Consolas,"Courier New",monospace; font-size:12.5px; word-break:break-all; }
td.step { color:var(--muted); width:52px; } td.tool { width:110px; font-weight:600; }
tr.hot { background:color-mix(in srgb, var(--critical) 12%, transparent); }
tr.dim { opacity:.38; }
.scroll { overflow-x:auto; }
footer { color:var(--muted); font-size:12px; margin-top:24px; }
</style></head><body><div class="wrap">
<h1>agent-audit — __SOURCE__</h1>
<div class="sub">エージェント行動ログの事後監査 / __NEVENTS__ events · __NFINDINGS__ findings</div>

<div class="summary">
  <span class="verdict __VERDICT__">__VERDICT__</span>
  <span class="sub" style="margin:0">risk score __SCORE__/100</span>
  <span class="gauge"><i style="width:__SCORE__%"></i></span>
  __PILLS__
</div>

<h2>検出</h2>
<div class="filters">
  <button data-sev="all" aria-pressed="true">すべて</button>
  <button data-sev="critical" aria-pressed="false">critical</button>
  <button data-sev="high" aria-pressed="false">high</button>
  <button data-sev="medium" aria-pressed="false">medium</button>
</div>
<div id="findings">__FINDINGS__</div>

<h2>タイムライン <span class="sub" style="margin:0">— 検出をクリックすると関係ステップを強調</span></h2>
<div class="scroll"><table><thead><tr>
  <th>step</th><th>時刻</th><th>tool</th><th>入力</th>
</tr></thead><tbody id="timeline">__ROWS__</tbody></table></div>

<footer>生成: agent-audit (ai-project-loop Cycle 49) — 判定はルールベース。見落としも誤検知もありうる。</footer>
</div>
<script>
const FINDINGS = __DATA__;
const rows = [...document.querySelectorAll('#timeline tr')];
const cards = [...document.querySelectorAll('.finding')];

function highlight(steps) {
  const set = new Set(steps);
  rows.forEach(r => {
    const s = Number(r.dataset.step);
    r.classList.toggle('hot', set.size > 0 && set.has(s));
    r.classList.toggle('dim', set.size > 0 && !set.has(s));
  });
}
cards.forEach((card, i) => card.addEventListener('click', () => {
  const active = card.getAttribute('data-active') === '1';
  cards.forEach(c => c.setAttribute('data-active', '0'));
  if (active) { highlight([]); return; }
  card.setAttribute('data-active', '1');
  const f = FINDINGS[i];
  highlight(f.chain && f.chain.length ? f.chain : [f.step]);
  rows.find(r => Number(r.dataset.step) === f.step)?.scrollIntoView({block:'center', behavior:'smooth'});
}));
document.querySelectorAll('.filters button').forEach(btn => btn.addEventListener('click', () => {
  const sev = btn.dataset.sev;
  document.querySelectorAll('.filters button')
    .forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
  cards.forEach((c, i) => {
    c.style.display = (sev === 'all' || FINDINGS[i].severity === sev) ? '' : 'none';
  });
}));
</script></body></html>
"""


def _finding_card(f: dict) -> str:
    chain = ""
    if f["chain"]:
        chain = " · chain " + " → ".join(f"step {s}" for s in f["chain"])
    return (
        f'<div class="finding {f["severity"]}" data-active="0">'
        f'<div class="ttl">{html.escape(f["title"])}</div>'
        f'<div class="meta">{SEV_LABEL[f["severity"]]} · {html.escape(f["type"])} · step {f["step"]}{chain}</div>'
        f'<div class="det">{html.escape(f["detail"])}</div></div>'
    )


def _row(ev) -> str:
    text = ev.text if len(ev.text) <= 220 else ev.text[:220] + " …"
    return (
        f'<tr data-step="{ev.step}"><td class="step">{ev.step}</td>'
        f'<td class="sub">{html.escape(ev.ts)}</td>'
        f'<td class="tool">{html.escape(ev.tool)}</td>'
        f'<td class="cmd">{html.escape(text)}</td></tr>'
    )


def render_html(result: dict, source: str) -> str:
    findings = [asdict(f) for f in result["findings"]]
    pills = "".join(
        f'<span class="pill {sev}">{sev} {n}</span>'
        for sev, n in result["counts"].items() if n
    ) or '<span class="pill low">検出なし</span>'

    replacements = {
        "__SOURCE__": html.escape(source),
        "__NEVENTS__": str(len(result["events"])),
        "__NFINDINGS__": str(len(findings)),
        "__VERDICT__": result["verdict"],
        "__SCORE__": str(result["score"]),
        "__PILLS__": pills,
        "__FINDINGS__": "".join(_finding_card(f) for f in findings) or '<div class="sub">検出なし。</div>',
        "__ROWS__": "".join(_row(ev) for ev in result["events"]),
        "__DATA__": json.dumps(findings, ensure_ascii=False),
    }
    out = TEMPLATE
    for key, val in replacements.items():
        out = out.replace(key, val)
    return out
