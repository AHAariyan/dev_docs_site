#!/usr/bin/env python3
"""Offline checks for the site: run before every push.

    python3 tools/check.py

- HTML is well-formed (every tag closed, no stray end tags), one <h1> per page
- <title> <= 60 chars and meta description <= 155 chars, canonical starts with SITE_URL
- every JSON-LD block parses
- every internal link / src resolves to a file (and #fragments to an id on the page)
- every <img> has alt, width and height, and the file's real aspect ratio matches
- every page in sitemap.xml exists, and every indexable page is in the sitemap
- page weight: HTML + CSS + JS + eagerly loaded images per page
Exit code 1 on any error.
"""
import json
import os
import re
import struct
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = open(os.path.join(ROOT, "SITE_URL")).read().strip()
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
errors = []


def err(page, msg):
    errors.append(f"{page}: {msg}")


def image_size(path):
    with open(path, "rb") as f:
        head = f.read(64)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", head[16:24])
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        kind = head[12:16]
        if kind == b"VP8X":
            w = int.from_bytes(head[24:27], "little") + 1
            h = int.from_bytes(head[27:30], "little") + 1
            return w, h
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", head[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if kind == b"VP8L":
            b = head[21:25]
            w = 1 + (((b[1] & 0x3F) << 8) | b[0])
            h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
            return w, h
    if head[:2] == b"\xff\xd8":
        with open(path, "rb") as f:
            data = f.read()
        i = 2
        while i < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.ids, self.links, self.imgs, self.ld = [], set(), [], [], []
        self.h1 = 0
        self.title = ""
        self.desc = None
        self.canonical = None
        self.noindex = False
        self._in = None
        self._buf = ""
        self.problems = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            if a["id"] in self.ids:
                self.problems.append(f"duplicate id {a['id']}")
            self.ids.add(a["id"])
        if tag == "h1":
            self.h1 += 1
        if tag in ("a", "link") and a.get("href"):
            self.links.append(a["href"])
        if tag in ("script", "img", "source") and a.get("src"):
            self.links.append(a["src"])
        if tag == "img":
            self.imgs.append(a)
        if tag == "meta" and a.get("name") == "description":
            self.desc = a.get("content", "")
        if tag == "meta" and a.get("name") == "robots" and "noindex" in a.get("content", ""):
            self.noindex = True
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag == "title" or (tag == "script" and a.get("type") == "application/ld+json"):
            self._in, self._buf = tag, ""
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.problems.append(f"unexpected </{tag}> (open: {self.stack[-3:]})")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()
        if tag == self._in:
            if tag == "title":
                self.title = self._buf.strip()
            else:
                self.ld.append(self._buf)
            self._in = None

    def handle_data(self, data):
        if self._in:
            self._buf += data


def local_target(page_path, href):
    """Map a link to a local file path, or None if external."""
    if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None, None
    if href.startswith(BASE):
        href = "/" + href[len(BASE):]
        rel_root = True
    elif href.startswith(("http://", "https://", "//")):
        return None, None
    else:
        rel_root = False
    u = urlparse(href)
    path = unquote(u.path)
    if rel_root:
        target = os.path.join(ROOT, path.lstrip("/"))
    elif path == "":
        target = page_path
    else:
        target = os.path.normpath(os.path.join(os.path.dirname(page_path), path))
    if os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return target, u.fragment


pages = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("tools", "node_modules")]
    for name in filenames:
        if name.endswith(".html") and name != "og-share.html":
            pages.append(os.path.join(dirpath, name))
pages.sort()

parsed = {}
for p in pages:
    rel = os.path.relpath(p, ROOT)
    pg = Page()
    pg.feed(open(p, encoding="utf-8").read())
    pg.close()
    parsed[p] = pg
    for prob in pg.problems:
        err(rel, prob)
    if pg.stack:
        err(rel, f"unclosed tags: {pg.stack}")
    if pg.h1 != 1:
        err(rel, f"{pg.h1} <h1> elements")
    if len(pg.title) > 60:
        err(rel, f"title {len(pg.title)} chars")
    if not pg.noindex:
        if pg.desc is None or len(pg.desc) > 155:
            err(rel, f"meta description missing or {len(pg.desc or '')} chars")
        if not (pg.canonical or "").startswith(BASE):
            err(rel, f"canonical {pg.canonical} does not start with {BASE}")
    for block in pg.ld:
        try:
            json.loads(block)
        except ValueError as e:
            err(rel, f"JSON-LD does not parse: {e}")
    for img in pg.imgs:
        if "alt" not in img:
            err(rel, f"img without alt: {img.get('src')}")
        if not img.get("width") or not img.get("height"):
            err(rel, f"img without width/height: {img.get('src')}")

for p, pg in parsed.items():
    rel = os.path.relpath(p, ROOT)
    for href in pg.links:
        target, frag = local_target(p, href)
        if target is None:
            continue
        if not os.path.exists(target):
            err(rel, f"broken link {href}")
            continue
        if frag and target.endswith(".html"):
            other = parsed.get(target)
            if other and frag not in other.ids:
                err(rel, f"missing anchor {href}")
    for img in pg.imgs:
        target, _ = local_target(p, img.get("src", ""))
        if target and os.path.exists(target) and img.get("width") and img.get("height"):
            size = image_size(target)
            if size:
                want = int(img["width"]) / int(img["height"])
                got = size[0] / size[1]
                if abs(want - got) > 0.01:
                    err(rel, f"{img['src']} is {size[0]}x{size[1]} but tagged {img['width']}x{img['height']}")

# sitemap
sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
locs = re.findall(r"<loc>(.*?)</loc>", sm)
for loc in locs:
    target, _ = local_target(os.path.join(ROOT, "index.html"), loc)
    if not target or not os.path.exists(target):
        err("sitemap.xml", f"missing page {loc}")
for p, pg in parsed.items():
    if not pg.noindex and pg.canonical not in locs:
        err("sitemap.xml", f"{pg.canonical} not listed")

# weight
print("Page weight (HTML + CSS + JS + eager images; lazy images listed separately):")
css = os.path.getsize(os.path.join(ROOT, "styles.css"))
js = os.path.getsize(os.path.join(ROOT, "assets", "site.js"))
for p, pg in parsed.items():
    eager = lazy = 0
    for img in pg.imgs:
        target, _ = local_target(p, img.get("src", ""))
        if target and os.path.exists(target):
            if img.get("loading") == "lazy":
                lazy += os.path.getsize(target)
            else:
                eager += os.path.getsize(target)
    total = os.path.getsize(p) + css + js + eager
    print(f"  {os.path.relpath(p, ROOT):48s} {total / 1024:6.1f} KB  (+{lazy / 1024:.0f} KB lazy)")
    if total > 300 * 1024:
        err(os.path.relpath(p, ROOT), f"initial weight {total / 1024:.0f} KB > 300 KB")

if errors:
    print(f"\n{len(errors)} problem(s):")
    for e in errors:
        print("  " + e)
    sys.exit(1)
print(f"\nOK: {len(pages)} pages, {len(locs)} sitemap URLs, links, anchors, images and JSON-LD all good.")
