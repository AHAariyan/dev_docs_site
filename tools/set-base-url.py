#!/usr/bin/env python3
"""Change the site's public URL everywhere.

The current URL lives in ../SITE_URL (one line, ending in "/"). This script replaces it in every
.html, .xml and .txt file (canonical links, Open Graph/Twitter tags, JSON-LD, sitemap.xml,
robots.txt, 404.html) and then writes the new URL into SITE_URL.

    python3 tools/set-base-url.py https://devdocs.example.com/
"""
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
    sys.exit("usage: set-base-url.py https://new.example/path/")
new = sys.argv[1] if sys.argv[1].endswith("/") else sys.argv[1] + "/"
url_file = os.path.join(root, "SITE_URL")
old = open(url_file).read().strip()
if old == new:
    sys.exit("SITE_URL is already " + new)

changed = 0
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "tools"]
    for name in filenames:
        if name.endswith((".html", ".xml", ".txt")):
            path = os.path.join(dirpath, name)
            text = open(path, encoding="utf-8").read()
            if old in text:
                open(path, "w", encoding="utf-8").write(text.replace(old, new))
                changed += 1
open(url_file, "w").write(new + "\n")
print(f"{old} -> {new}: {changed} files updated")
