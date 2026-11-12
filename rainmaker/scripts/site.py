"""Build a complete static site in dashboard/: the dashboard home plus every report, dossier, outreach draft,
assessment page and research note rendered from Markdown to HTML with shared navigation.

Usage: python scripts/site.py        (run after dashboard.py; run_pipeline.sh does this)
Output: dashboard/index.html (home, with nav), dashboard/pages/*.html, dashboard/pages/index.html (document index)
Uses the `markdown` package when available (pip install markdown); otherwise a small built-in converter.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, checkpoint, get_logger, now_iso, path  # noqa: E402

log = get_logger("site")

try:
    import markdown as _md

    def md_to_html(text: str) -> str:
        return _md.markdown(text, extensions=["tables", "fenced_code", "sane_lists", "toc"])
except ImportError:  # minimal fallback: headings, lists, tables, paragraphs, bold/italic/links/code
    def _inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+|[^)]+\.html)\)", r'<a href="\2">\1</a>', s)
        return s

    def md_to_html(text: str) -> str:
        out, i, lines = [], 0, text.splitlines()
        while i < len(lines):
            ln = lines[i]
            if ln.startswith("```"):
                j = i + 1
                while j < len(lines) and not lines[j].startswith("```"):
                    j += 1
                out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
                i = j + 1
                continue
            m = re.match(r"^(#{1,6})\s+(.*)", ln)
            if m:
                out.append(f"<h{len(m.group(1))}>{_inline(m.group(2))}</h{len(m.group(1))}>")
                i += 1
                continue
            if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
                head = [c.strip() for c in ln.strip("|").split("|")]
                rows, j = [], i + 2
                while j < len(lines) and lines[j].startswith("|"):
                    rows.append([c.strip() for c in lines[j].strip("|").split("|")])
                    j += 1
                out.append("<table><thead><tr>" + "".join(f"<th>{_inline(h)}</th>" for h in head) + "</tr></thead><tbody>" +
                           "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")
                i = j
                continue
            if re.match(r"^\s*([-*]|\d+\.)\s+", ln):
                ordered = bool(re.match(r"^\s*\d+\.", ln))
                items, j = [], i
                while j < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[j]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[j]))
                    j += 1
                tag = "ol" if ordered else "ul"
                out.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{tag}>")
                i = j
                continue
            if ln.startswith(">"):
                out.append(f"<blockquote>{_inline(ln.lstrip('> '))}</blockquote>")
                i += 1
                continue
            if ln.strip():
                para, j = [ln], i + 1
                while j < len(lines) and lines[j].strip() and not re.match(r"^(#|\||>|```|\s*[-*]\s|\s*\d+\.\s)", lines[j]):
                    para.append(lines[j])
                    j += 1
                out.append(f"<p>{_inline(' '.join(para))}</p>")
                i = j
                continue
            i += 1
        return "\n".join(out)


# Navigation: (label, published page or section)
NAV = [
    ("Start here", "pages/00_START_HERE.html"),
    ("Dashboard", "index.html"),
    ("Executive summary", "pages/A_executive_summary.html"),
    ("Decisions", "pages/00_decisions_and_defaults.html"),
    ("Sales plan", "pages/02_head_of_sales_plan.html"),
    ("Financials", "pages/03_financial_reality.html"),
    ("Targets", "pages/P_target_accounts.html"),
    ("Top-3 plan", "pages/F_top3_recruitment_plan.html"),
    ("Playbook", "pages/F2_approach_and_offer_playbook.html"),
    ("Economics", "pages/G_compensation_economics_model.html"),
    ("Revenue plan", "pages/H2_revenue_confidence_plan.html"),
    ("Rankings", "pages/06_rankings.html"),
    ("Companies", "pages/B_target_company_intelligence.html"),
    ("All documents", "pages/index.html"),
]

SECTIONS = [
    ("Reports", "reports", "*.md"),
    ("Candidate dossiers", "candidates", "*.md"),
    ("Outreach drafts (approval required)", "outreach", "*.md"),
    ("Assessment toolkit", "assessment", "*.md"),
    ("Research and methodology", "research", "*.md"),
    ("Research prompts", "research/prompts", "*.md"),
    ("Operations", ".", "README.md"),
    ("Operations", ".", "OPERATIONS.md"),
    ("Operations", ".", "PRIVATE_REPO_NOTICE.md"),
]

CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--border:rgba(11,11,11,.10);--accent:#2a78d6}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--border:rgba(255,255,255,.10);--accent:#3987e5}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--border:rgba(255,255,255,.10);--accent:#3987e5}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
nav.top{position:sticky;top:0;background:var(--surface);border-bottom:1px solid var(--border);padding:8px 16px;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13.5px;z-index:2}
nav.top a{color:var(--ink2);text-decoration:none;padding:4px 2px}nav.top a.active,nav.top a:hover{color:var(--accent)}nav.top .brand{font-weight:600;color:var(--ink);margin-right:8px}
main{max-width:1000px;margin:0 auto;padding:24px 16px 64px}article{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px 24px}
h1{font-size:24px;margin:0 0 8px}h2{font-size:18px;margin:26px 0 8px}h3{font-size:16px;margin:20px 0 6px}h4{font-size:15px;margin:16px 0 4px}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0;display:block;overflow-x:auto}th{text-align:left;color:var(--ink2);font-weight:600;border-bottom:1px solid var(--grid);padding:6px 8px;white-space:nowrap}
td{padding:6px 8px;border-bottom:1px solid var(--grid);vertical-align:top}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
blockquote{border-left:3px solid var(--grid);margin:8px 0;padding:4px 12px;color:var(--ink2)}code{font-size:13px;background:var(--page);padding:1px 4px;border-radius:4px}pre{background:var(--page);padding:12px;border-radius:8px;overflow-x:auto}
.meta{color:var(--muted);font-size:12.5px;margin-bottom:14px}.idx h2{margin-top:22px}.idx li{margin:4px 0}footer{margin-top:28px;font-size:12px;color:var(--muted)}
"""


def nav_html(active: str, depth: int) -> str:
    prefix = "../" * depth
    links = "".join(f'<a href="{prefix}{href}" class="{"active" if href == active else ""}">{label}</a>' for label, href in NAV)
    return f'<nav class="top"><span class="brand">Operation Rainmaker</span>{links}</nav>'


def wrap(title: str, body: str, active: str, depth: int, source: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="robots" content="noindex, nofollow"><title>{html.escape(title)}</title><style>{CSS}</style></head><body>'
            f'{nav_html(active, depth)}<main><div class="meta">Confidential · Ironguard IT · generated {now_iso()} · source: {html.escape(source)}</div>'
            f'<article>{body}</article><footer>Rendered by rainmaker/scripts/site.py. Names link to public professional profiles where available. No message is sent without CEO approval.</footer></main></body></html>')


def rewrite_links(body: str) -> str:
    """Point in-repo Markdown links at their rendered pages."""
    def repl(m):
        target = m.group(1)
        name = Path(target).name
        if name.endswith(".md"):
            return f'href="{name[:-3]}.html"'
        return m.group(0)
    return re.sub(r'href="((?!https?://)[^"]+\.md)"', repl, body)


def main() -> None:
    out_dir = path("dashboard").parent
    pages = out_dir / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    index_sections: dict[str, list[tuple[str, str]]] = {}
    n = 0
    for section, rel, pattern in SECTIONS:
        base = ROOT / rel
        for f in sorted(base.glob(pattern)):
            if f.name.startswith("weekly_intel") and "weekly" not in pattern:
                pass
            text = f.read_text(encoding="utf-8", errors="ignore")
            title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("# ")), f.stem)
            body = rewrite_links(md_to_html(text))
            slug = f.stem
            (pages / f"{slug}.html").write_text(wrap(title, body, f"pages/{slug}.html", 1, f"{rel}/{f.name}".replace("./", "")), encoding="utf-8")
            index_sections.setdefault(section, []).append((title, f"{slug}.html"))
            n += 1
    # document index
    idx = ['<h1>All documents</h1><div class="idx">']
    for section, items in index_sections.items():
        idx.append(f"<h2>{html.escape(section)}</h2><ul>" + "".join(f'<li><a href="{href}">{html.escape(t)}</a></li>' for t, href in items) + "</ul>")
    idx.append("</div>")
    (pages / "index.html").write_text(wrap("All documents", "".join(idx), "pages/index.html", 1, "generated index"), encoding="utf-8")
    # inject nav into the dashboard home
    home = path("dashboard")
    if home.exists():
        doc = home.read_text(encoding="utf-8")
        doc = re.sub(r'<nav class="top">.*?</nav>', "", doc, flags=re.S)
        doc = doc.replace("<body><main>", f"<body>{nav_html('index.html', 0)}<main>", 1)
        doc = doc.replace("<head>", f"<head><meta name=\"robots\" content=\"noindex, nofollow\"><style>nav.top{{position:sticky;top:0;background:var(--surface);border-bottom:1px solid var(--border);padding:8px 16px;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13.5px;z-index:2}}nav.top a{{color:var(--ink2);text-decoration:none;padding:4px 2px}}nav.top a.active,nav.top a:hover{{color:var(--accent)}}nav.top .brand{{font-weight:600;color:var(--ink);margin-right:8px}}</style>", 1)
        doc = doc.replace("reports/F_top3_recruitment_plan.md", "pages/F_top3_recruitment_plan.html").replace("reports/F2_approach_and_offer_playbook.md", "pages/F2_approach_and_offer_playbook.html")
        doc = doc.replace("reports/G_compensation_economics_model.md", "pages/G_compensation_economics_model.html").replace("reports/H2_revenue_confidence_plan.md, section 4", "pages/H2_revenue_confidence_plan.html (section 4)")
        doc = doc.replace("see candidates/ dossiers for open questions", 'see the <a href="pages/index.html">dossiers</a> for open questions')
        home.write_text(doc, encoding="utf-8")
    # Azure Static Web Apps: require an invited 'admin' role for every route (site holds confidential names).
    swa = {
        "routes": [
            {"route": "/.auth/*", "allowedRoles": ["anonymous", "authenticated", "admin"]},
            {"route": "/*", "allowedRoles": ["admin"]},
        ],
        "responseOverrides": {
            "401": {"redirect": "/.auth/login/aad?post_login_redirect_uri=.referrer", "statusCode": 302},
            "403": {"rewrite": "/forbidden.html", "statusCode": 403},
        },
        "navigationFallback": {"rewrite": "/index.html", "exclude": ["/pages/*", "/*.png", "/*.md"]},
        "globalHeaders": {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"},
    }
    import json as _json
    (out_dir / "staticwebapp.config.json").write_text(_json.dumps(swa, indent=2), encoding="utf-8")
    (out_dir / "forbidden.html").write_text(wrap("Access restricted", "<h1>Access restricted</h1><p>This site is private. Your account is signed in but has not been given the <b>admin</b> role. The site owner grants it in the Azure portal: Static Web App → Role management → Invite.</p>", "", 0, "generated"), encoding="utf-8")
    checkpoint("site", pages=n)
    log.info("site built: %s pages under %s", n, pages)


if __name__ == "__main__":
    main()
