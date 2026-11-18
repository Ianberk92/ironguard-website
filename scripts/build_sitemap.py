#!/usr/bin/env python3
"""Rebuild sitemap.xml from the pages that exist. Run from the repo root:

    python3 scripts/build_sitemap.py

Every indexable .html page is listed (pages with noindex or a meta refresh are
skipped), each with the date of its last git commit as <lastmod>.
"""
import re, subprocess
from pathlib import Path

BASE = "https://www.ironguardit.com/"
ROOT = Path(__file__).resolve().parent.parent
SKIP = re.compile(r"^(google[0-9a-f]+\.html|thank-you\.html|node_modules/)")


def lastmod(rel):
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    return out or subprocess.run(["date", "+%F"], capture_output=True, text=True).stdout.strip()


def pages():
    for f in sorted(ROOT.rglob("*.html")):
        rel = f.relative_to(ROOT).as_posix()
        if SKIP.search(rel):
            continue
        html = f.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"<meta[^>]+noindex", html) or 'http-equiv="refresh"' in html:
            continue
        yield rel


def main():
    rels = list(pages())
    rels.sort(key=lambda r: (r != "index.html", r.count("/"), r))
    rows = []
    for rel in rels:
        url = BASE + ("" if rel == "index.html" else rel)
        rows.append(f"  <url><loc>{url}</loc><lastmod>{lastmod(rel)}</lastmod></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n")
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"sitemap.xml: {len(rows)} pages")


if __name__ == "__main__":
    main()
