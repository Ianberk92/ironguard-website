"""Bundle the whole static site into ONE self-contained HTML file (no server, no hosting, works offline).

Every page from dashboard/ is embedded as a <template>; a tiny router shows one at a time and the navigation
and in-site links work via URL hashes. Output: dashboard/rainmaker_offline.html (share by email/AirDrop/USB).
Usage: python scripts/bundle.py   (run after site.py)
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import checkpoint, get_logger, now_iso, path  # noqa: E402

log = get_logger("bundle")


def body_of(doc: str) -> str:
    m = re.search(r"<body[^>]*>(.*)</body>", doc, re.S)
    return m.group(1) if m else doc


def style_of(doc: str) -> str:
    return "\n".join(re.findall(r"<style>(.*?)</style>", doc, re.S))


def main() -> None:
    site = path("dashboard").parent
    home = (site / "index.html").read_text(encoding="utf-8")
    pages = {p.stem: p.read_text(encoding="utf-8") for p in sorted((site / "pages").glob("*.html"))}
    css = style_of(home) + "\n" + style_of(next(iter(pages.values()))) if pages else style_of(home)

    def localize(frag: str) -> str:
        # pages/X.html -> #X ; ../index.html or index.html -> #home ; strip nav (the bundle has its own)
        frag = re.sub(r'<nav class="top">.*?</nav>', "", frag, flags=re.S)
        frag = re.sub(r'href="(?:\.\./)?pages/([^"#]+)\.html"', r'href="#\1"', frag)
        frag = re.sub(r'href="([A-Za-z0-9_\-]+)\.html"', lambda m: f'href="#{m.group(1)}"', frag)
        frag = re.sub(r'href="(?:\.\./)?index\.html"', 'href="#home"', frag)
        return frag

    templates = [f'<template id="t-home">{localize(body_of(home))}</template>']
    for slug, doc in pages.items():
        templates.append(f'<template id="t-{html.escape(slug)}">{localize(body_of(doc))}</template>')
    nav = [("Start here", "00_START_HERE"), ("Money", "07_money_on_one_screen"), ("Calendar", "13_daily_cash_calendar"), ("Messages", "19_messages_to_send"), ("Recovery", "15_recovery_plan"), ("Dashboard", "home"), ("Plan", "04_make_it_work"), ("Executive summary", "A_executive_summary"), ("Decisions", "00_decisions_and_defaults"), ("Sales plan", "02_head_of_sales_plan"), ("Financials", "03_financial_reality"), ("Targets", "P_target_accounts"),
           ("Top-3 plan", "F_top3_recruitment_plan"), ("Playbook", "F2_approach_and_offer_playbook"), ("Economics", "G_compensation_economics_model"),
           ("Revenue plan", "H2_revenue_confidence_plan"), ("Rankings", "06_rankings"), ("Companies", "B_target_company_intelligence"), ("All documents", "index")]
    nav_html = "".join(f'<a href="#{slug}" data-slug="{slug}">{label}</a>' for label, slug in nav)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Rainmaker Briefing</title>
<style>{css}
nav.top{{position:sticky;top:0;background:var(--surface);border-bottom:1px solid var(--border);padding:8px 16px;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13.5px;z-index:2}}
nav.top a{{color:var(--ink2);text-decoration:none;padding:4px 2px}}nav.top a.active,nav.top a:hover{{color:var(--accent)}}nav.top .brand{{font-weight:600;color:var(--ink);margin-right:8px}}
#view main{{max-width:1240px}}.banner{{background:var(--surface);border-bottom:1px solid var(--border);padding:6px 16px;font-size:12px;color:var(--muted)}}
</style></head><body>
<nav class="top"><span class="brand">Operation Rainmaker</span>{nav_html}</nav>
<div class="banner">Confidential briefing for Ironguard IT · self-contained file generated {now_iso()} · nothing here has been sent to any candidate</div>
<div id="view"></div>
{''.join(templates)}
<script>
(function(){{
  // Switch views by direct click handling; hash updates are optional because some
  // embedded viewers (sandboxed preview panes) block or ignore hash navigation.
  var current='';
  function show(slug){{
    slug=slug||'00_START_HERE';
    var t=document.getElementById('t-'+slug)||document.getElementById('t-home');
    if(!t) return;
    current=slug;
    var v=document.getElementById('view'); v.innerHTML=''; v.appendChild(t.content.cloneNode(true));
    document.querySelectorAll('nav.top a').forEach(function(a){{a.classList.toggle('active',a.dataset.slug===slug);}});
    try{{window.scrollTo(0,0);}}catch(e){{}}
  }}
  document.addEventListener('click',function(e){{
    var a=e.target.closest&&e.target.closest('a[href^="#"]'); if(!a) return;
    var slug=a.getAttribute('href').slice(1); if(!slug) return;
    if(!document.getElementById('t-'+slug)) return;   // same-page anchors fall through
    e.preventDefault(); show(slug);
    try{{history.replaceState(null,'','#'+slug);}}catch(err){{}}
  }});
  window.addEventListener('hashchange',function(){{var s=location.hash.slice(1); if(s&&s!==current) show(s);}});
  var start=''; try{{start=location.hash.slice(1);}}catch(e){{}}
  show(start);
}})();
</script></body></html>"""
    out = site / "rainmaker_offline.html"
    out.write_text(doc, encoding="utf-8")
    checkpoint("bundle", pages=len(pages) + 1, bytes=len(doc))
    log.info("offline bundle written: %s (%d pages, %.1f KB)", out, len(pages) + 1, len(doc) / 1024)


if __name__ == "__main__":
    main()
