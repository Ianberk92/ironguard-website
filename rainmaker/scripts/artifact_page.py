"""Derive the claude.ai artifact variant of the offline bundle (host wraps the page, hash slugs use hyphens).

Usage: python scripts/artifact_page.py --out /path/to/rainmaker-briefing.html
The artifact keeps its URL only when republished from the SAME file path, so always pass the same --out.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import get_logger, path  # noqa: E402

log = get_logger("artifact")

GUTTER = """<style>
body{padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0}
nav.top{margin:0 calc(-1*max(16px,env(safe-area-inset-left,0px))) 0 calc(-1*max(16px,env(safe-area-inset-right,0px)));top:env(safe-area-inset-top,0px)}
#view main{padding-left:0;padding-right:0}body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--surface)}
table{display:block;overflow-x:auto;max-width:100%}.tablewrap{min-width:0}
</style>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    doc = (path("dashboard").parent / "rainmaker_offline.html").read_text(encoding="utf-8")
    head = re.search(r"<head>(.*?)</head>", doc, re.S).group(1)
    body = re.search(r"<body>(.*)</body>", doc, re.S).group(1)
    styles = "".join(re.findall(r"<style>.*?</style>", head, re.S))
    hy = lambda s: s.replace("_", "-")
    body = re.sub(r'href="#([A-Za-z0-9_\-]+)"', lambda m: f'href="#{hy(m.group(1))}"', body)
    body = re.sub(r'data-slug="([A-Za-z0-9_\-]+)"', lambda m: f'data-slug="{hy(m.group(1))}"', body)
    body = re.sub(r'<template id="t-([A-Za-z0-9_\-]+)">', lambda m: f'<template id="t-{hy(m.group(1))}">', body)
    page = '<title>Rainmaker Briefing</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n' + styles + GUTTER + body
    Path(a.out).write_text(page, encoding="utf-8")
    log.info("artifact page written to %s (%.0f KB)", a.out, len(page) / 1024)


if __name__ == "__main__":
    main()
