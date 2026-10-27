#!/usr/bin/env python3
"""Generates the site's illustrations (original vector art, no screenshots).

    python3 tools/make-art.py

Writes assets/art/*.svg and refreshes the inline hero art in index.html (between the
<!--hero-art--> markers). One visual language for everything:
- palette from styles.css and the app icon: rose #d24f7a/#f283a6, plum #8e4aa6/#c39be0,
  mint #1f8a50/#7fdca6, plum-black surfaces; code blocks are always dark;
- 14px card radius, 1px hairline borders, soft plum shadows, pill chips, monospace for code;
- "themed" files carry their own light and dark palettes (prefers-color-scheme), so they
  match the page in both modes; hero-type art (on the always-dark hero band) is dark only.
Docset numbers shown in the art come from the docset pages; update DOCSETS when they change.
"""
import os
import re
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "art")

SANS = '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif'
MONO = 'ui-monospace,"SF Mono",Menlo,Consolas,"Roboto Mono",monospace'

# Light palette first, dark override second. Class names are kept short on purpose.
THEME = (
    "text{font-family:%s}.mo{font-family:%s}"
    ".s{fill:#fff}.k{stroke:#ead9e2}.s2{fill:#f8eff4}.t{fill:#2a1a2b}.m{fill:#86707f}"
    ".b{fill:#eee2e8}.b2{fill:#ddccd6}.a{fill:#d24f7a}.as{fill:#fbe4ec}.p{fill:#8e4aa6}.ps{fill:#f1e4f6}"
    ".g{fill:#1f8a50}.gs{fill:#dcf2e5}.ak{stroke:#d24f7a}.sh{flood-color:#5a1f3c;flood-opacity:.13}"
    ".gl{stop-color:#f6c9d8}.cd{fill:#221326}.on{fill:#fff}"
    "@media(prefers-color-scheme:dark){.s{fill:#201522}.k{stroke:#3b2a40}.s2{fill:#2a1b2d}.t{fill:#f3e9f0}"
    ".m{fill:#a893a3}.b{fill:#35253a}.b2{fill:#47334d}.a{fill:#f283a6}.as{fill:#45202f}.p{fill:#c39be0}"
    ".ps{fill:#33223f}.g{fill:#7fdca6}.gs{fill:#173527}.ak{stroke:#f283a6}.sh{flood-color:#000;flood-opacity:.5}"
    ".gl{stop-color:#5a2140}.cd{fill:#110811;stroke:#3b2a40}.on{fill:#1e0e1e}}"
) % (SANS, MONO)
# Dark-only art (hero band, share image).
DARK = (
    "text{font-family:%s}.mo{font-family:%s}"
) % (SANS, MONO)
# Code colours (on dark code blocks in both themes).
CODE = ".c0{fill:#eadbe6}.c1{fill:#f283a6}.c2{fill:#d4b2ff}.c3{fill:#8fe3b0}.c4{fill:#ffc48a}.c5{fill:#8f7b8b}"


def num(v):
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return s if s != "-0" else "0"


def R(x, y, w, h, r=0, cls=None, extra=""):
    c = f' class="{cls}"' if cls else ""
    rr = f' rx="{num(r)}"' if r else ""
    return f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"{rr}{c}{extra}/>'


def T(x, y, s, size=12, cls="t", weight=None, mono=False, anchor=None, extra="", raw=False):
    cl = cls + (" mo" if mono else "")
    a = f' font-size="{num(size)}"'
    if weight:
        a += f' font-weight="{weight}"'
    if anchor:
        a += f' text-anchor="{anchor}"'
    body = s if raw else escape(s)
    return f'<text x="{num(x)}" y="{num(y)}" class="{cl}"{a}{extra}>{body}</text>'


def code(x, y, lines, size=11, lh=17):
    """lines: list of lists of (text, colour class index)."""
    out = []
    for i, toks in enumerate(lines):
        spans = "".join(f'<tspan class="c{c}">{escape(t)}</tspan>' for t, c in toks)
        out.append(f'<text x="{num(x)}" y="{num(y + i * lh)}" class="mo" font-size="{num(size)}" xml:space="preserve">{spans}</text>')
    return "".join(out)


def bars(x, y, widths, cls="b", h=6, gap=12, r=3):
    return "".join(R(x, y + i * gap, w, h, r, cls) for i, w in enumerate(widths))


def chip(x, y, label, cls_bg="as", cls_tx="a", size=11, mono=False, pad=10, h=22, weight=600):
    w = len(label) * size * (0.62 if mono else 0.56) + pad * 2
    return R(x, y, w, h, h / 2, cls_bg) + T(x + w / 2, y + h / 2 + size * 0.36, label, size, cls_tx, weight, mono, "middle"), w


def region(w, h):
    """Filter region = whole canvas, so blurred shadows of small shapes are never clipped into boxes."""
    return f'filterUnits="userSpaceOnUse" x="-40" y="-40" width="{w + 80}" height="{h + 80}"'


def shadow(w, h, fid="d", dy=10, sd=14):
    return f'<filter id="{fid}" {region(w, h)}><feDropShadow dy="{dy}" stdDeviation="{sd}" class="sh"/></filter>'


def svg(w, h, body, themed=True, defs="", extra_css="", attrs="", pad=0):
    """pad: empty margin around the drawing so soft shadows are never cut by the image edge."""
    css = (THEME if themed else DARK) + extra_css
    d = f"<defs>{defs}</defs>" if defs else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}" '
            f'width="{w + 2 * pad}" height="{h + 2 * pad}"{attrs}>'
            f"<style>{css}</style>{d}{body}</svg>")


def glow(cx, cy, r, gid, w=None, h=None):
    if w:
        r = min(r, cx, w - cx, cy, h - cy)
    return f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" fill="url(#{gid})"/>'


def radial(gid, color, op):
    return (f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="{op}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')


PAD = 28
THEMED_GLOW = '<radialGradient id="bg"><stop offset="0" class="gl"/><stop offset="1" class="gl" stop-opacity="0"/></radialGradient>'

# Small icon paths shared by the art (24 px grid, drawn with stroke).
ICON = {
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>',
    "plane": '<path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "down": '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>',
    "book": '<path d="M12 6.5C10 5 7 4.5 3.5 5v13c3.5-.5 6.5 0 8.5 1.5 2-1.5 5-2 8.5-1.5V5C17 4.5 14 5 12 6.5zM12 6.5v13"/>',
    "mark": '<path d="M7 3.5h10a1 1 0 0 1 1 1V20l-6-4-6 4V4.5a1 1 0 0 1 1-1z"/>',
    "spark": '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v4.5h-4.5"/>',
    "bolt": '<path d="M13 3L5 13.5h6L10 21l8-10.5h-6z"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    "cloud": '<path d="M7 18.5h10.5a4 4 0 0 0 .4-8 6 6 0 0 0-11.5 1.3A3.4 3.4 0 0 0 7 18.5z"/>',
    "slash": '<path d="M4 4l16 16"/>',
    "tabs": '<rect x="3" y="4.5" width="18" height="15" rx="2"/><path d="M12 4.5v15"/>',
    "cards": '<rect x="3" y="8" width="13.5" height="11" rx="2"/><path d="M7.5 4.5H19a2 2 0 0 1 2 2V15"/>',
}


def icon(name, x, y, size=16, cls="a", sw=1.9):
    s = size / 24
    stroke = {"a": "#d24f7a"}.get(cls)
    return (f'<g transform="translate({num(x)} {num(y)}) scale({s:.3f})" fill="none" class="i{cls}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{ICON[name]}</g>')


# stroke colours for icons (classes on <g>, so both themes work)
ICON_CSS = (
    ".ia{stroke:#d24f7a}.ip{stroke:#8e4aa6}.ig{stroke:#1f8a50}.it{stroke:#2a1a2b}.im{stroke:#a08a99}.iw{stroke:#fff}"
    "@media(prefers-color-scheme:dark){.ia{stroke:#f283a6}.ip{stroke:#c39be0}.ig{stroke:#7fdca6}.it{stroke:#f3e9f0}.im{stroke:#7d6a79}.iw{stroke:#1e0e1e}}"
)
ICON_CSS_DARK = ".ia{stroke:#f283a6}.ip{stroke:#c39be0}.ig{stroke:#7fdca6}.it{stroke:#f3e9f0}.im{stroke:#9c8698}.iw{stroke:#fff}.id{stroke:#1e0e1e}"


# ---------------------------------------------------------------- hero (dark, inline)
def hero():
    W, H = 560, 540
    defs = (
        radial("g1", "#e0608a", .55) + radial("g2", "#8a4aa0", .55) + radial("g3", "#7fdca6", .22)
        + '<linearGradient id="ph" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3d2541"/><stop offset="1" stop-color="#1c101e"/></linearGradient>'
        + '<linearGradient id="sc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d1020"/><stop offset="1" stop-color="#130914"/></linearGradient>'
        + '<linearGradient id="ro" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff9fbd"/><stop offset="1" stop-color="#e0608a"/></linearGradient>'
        + f'<filter id="d" {region(W, H)}><feDropShadow dy="18" stdDeviation="18" flood-color="#000" flood-opacity=".5"/></filter>'
    )
    b = []
    b.append(glow(310, 260, 250, "g1", W, H) + glow(130, 400, 220, "g2", W, H) + glow(470, 440, 140, "g3", W, H))
    b.append('<circle cx="300" cy="262" r="226" fill="none" stroke="#fff" stroke-opacity=".07" stroke-dasharray="2 7"/>')
    b.append('<circle cx="300" cy="262" r="168" fill="none" stroke="#fff" stroke-opacity=".05"/>')

    # Reader page (light paper) behind the phone
    pg = []
    pg.append(R(0, 0, 214, 292, 16, None, ' fill="#fbf4f8"'))
    pg.append(T(18, 30, "PYTHON 3.15 · itertools", 9, "", 600, True, extra=' fill="#c0446d"'))
    pg.append(T(18, 56, "groupby()", 20, "", 750, True, extra=' fill="#24152a"'))
    pg.append(bars(18, 72, [176, 150, 166], None, 6, 12).replace("/>", ' fill="#e6d6df"/>'))
    pg.append(R(18, 112, 178, 70, 10, None, ' fill="#211224"'))
    pg.append(code(30, 134, [[("for ", 1), ("k, g ", 0), ("in ", 1)], [("  groupby", 2), ("(rows):", 0)],
                             [("  print", 2), ("(k)", 0)]], 10, 16))
    pg.append(bars(18, 198, [170, 120, 160, 140, 96], None, 6, 13).replace("/>", ' fill="#e6d6df"/>'))
    pg.append(R(18, 268, 64, 6, 3, None, ' fill="#f0b7c9"'))
    b.append(f'<g transform="translate(26 112) rotate(-9 107 146)" filter="url(#d)">{"".join(pg)}</g>')

    # Phone
    px, py, pw, ph = 196, 30, 216, 470
    b.append(f'<g filter="url(#d)">{R(px, py, pw, ph, 38, None, " fill=\"url(#ph)\"")}</g>')
    b.append(R(px + .5, py + .5, pw - 1, ph - 1, 37.5, None, ' fill="none" stroke="#fff" stroke-opacity=".14"'))
    sx, sy, sw, sh = px + 9, py + 9, pw - 18, ph - 18
    b.append(R(sx, sy, sw, sh, 30, None, ' fill="url(#sc)"'))
    b.append(R(sx + sw / 2 - 26, sy + 9, 52, 9, 4.5, None, ' fill="#000" fill-opacity=".55"'))
    # app bar
    b.append(icon("book", sx + 14, sy + 30, 16, "a").replace('class="ia"', 'stroke="#f283a6"'))
    b.append(T(sx + 36, sy + 43, "Search", 13, "", 700, extra=' fill="#f6ecf3"'))
    b.append(T(sx + sw - 14, sy + 43, "806", 9.5, "", 600, True, "end", ' fill="#a893a3"'))
    # search field
    fy = sy + 58
    b.append(R(sx + 10, fy, sw - 20, 36, 18, None, ' fill="#2b1a2e" stroke="#f283a6" stroke-opacity=".55"'))
    b.append(icon("search", sx + 20, fy + 10, 16, "a").replace('class="ia"', 'stroke="#f283a6"'))
    b.append(T(sx + 42, fy + 23, "groupby", 13, "", 600, True, extra=' fill="#fff"'))
    b.append(R(sx + 42 + 7 * 7.9, fy + 10, 2, 16, 1, None, ' fill="#f283a6"'))
    # filter chips
    cy = fy + 46
    cx = sx + 10
    for i, (lab, w) in enumerate([("All", 34), ("Python", 54), ("Kotlin", 50), ("Pandas", 54)]):
        on = i == 0
        if cx + w > sx + sw:
            break
        b.append(R(cx, cy, w, 20, 10, None, ' fill="#f283a6"' if on else ' fill="none" stroke="#fff" stroke-opacity=".16"'))
        b.append(T(cx + w / 2, cy + 13.5, lab, 9.5, "", 650, anchor="middle", extra=' fill="#1e0e1e"' if on else ' fill="#d2c1cd"'))
        cx += w + 6
    # results
    rows = [("itertools.groupby", "Python", "f", "#f283a6"), ("groupBy", "Kotlin", "f", "#f283a6"),
            ("DataFrame.groupby", "Pandas", "m", "#c39be0"), ("groupingBy", "Kotlin", "f", "#f283a6")]
    ry = cy + 34
    for i, (name, ds, t, col) in enumerate(rows):
        y = ry + i * 50
        if i == 0:
            b.append(R(sx + 6, y - 6, sw - 12, 46, 12, None, ' fill="#fff" fill-opacity=".06"'))
        b.append(R(sx + 14, y + 2, 28, 28, 8, None, f' fill="{col}" fill-opacity=".16"'))
        b.append(T(sx + 28, y + 20.5, t, 12, "", 700, True, "middle", f' fill="{col}"'))
        b.append(T(sx + 52, y + 13, name, 10.5, "", 600, True, extra=' fill="#f6ecf3"'))
        b.append(T(sx + 52, y + 28, ds, 9.5, "", None, extra=' fill="#a893a3"'))
    # recent searches
    b.append(T(sx + 14, sy + 362, "RECENT", 8.5, "", 700, True, extra=' fill="#8f7b8b" letter-spacing=".8"'))
    rx = sx + 12
    for lab in ["lru_cache", "useEffect"]:
        w = len(lab) * 6.1 + 20
        b.append(R(rx, sy + 371, w, 22, 11, None, ' fill="#fff" fill-opacity=".06" stroke="#fff" stroke-opacity=".1"'))
        b.append(T(rx + w / 2, sy + 386, lab, 9.5, "", 600, True, "middle", ' fill="#d2c1cd"'))
        rx += w + 6
    # bottom nav
    ny = sy + sh - 40
    b.append(R(sx, ny - 8, sw, 1, 0, None, ' fill="#fff" fill-opacity=".07"'))
    for i, n in enumerate(["book", "down", "search", "mark"]):
        x = sx + 22 + i * (sw - 44) / 3 - 9
        on = n == "search"
        if on:
            b.append(R(x - 9, ny - 1, 36, 22, 11, None, ' fill="#f283a6" fill-opacity=".18"'))
        b.append(icon(n, x, ny + 1, 18, "a").replace('class="ia"', 'stroke="%s"' % ("#f283a6" if on else "#8f7b8b")))

    # Code card (front, lower right)
    cc = []
    cc.append(R(0, 0, 204, 116, 16, None, ' fill="#241428" stroke="#fff" stroke-opacity=".1"'))
    for i, c in enumerate(["#f283a6", "#c39be0", "#7fdca6"]):
        cc.append(f'<circle cx="{18 + i * 13}" cy="17" r="4" fill="{c}" fill-opacity=".8"/>')
    cc.append(T(188, 21, "Kotlin", 9.5, "", 600, True, "end", ' fill="#a893a3"'))
    cc.append(code(16, 50, [[("val ", 1), ("byLen ", 0), ("= ", 5), ("words", 0)],
                            [("  .", 5), ("groupBy ", 2), ("{ ", 5), ("it", 1), (".length ", 0), ("}", 5)],
                            [("// offline: 0 ms", 5)]], 10.5, 19))
    b.append(f'<g transform="translate(348 372) rotate(4 102 58)" filter="url(#d)">{"".join(cc)}</g>')

    # Offline badge (top right)
    ob = []
    ob.append(R(0, 0, 128, 40, 20, None, ' fill="#1f2a24" stroke="#7fdca6" stroke-opacity=".45"'))
    ob.append('<circle cx="20" cy="20" r="12" fill="#7fdca6" fill-opacity=".18"/>')
    ob.append(icon("plane", 12, 12, 16, "g").replace('class="ig"', 'stroke="#7fdca6"'))
    ob.append(T(40, 18, "Airplane mode", 9, "", 600, extra=' fill="#a9d9bd"'))
    ob.append(T(40, 31, "Docs still work", 10.5, "", 700, extra=' fill="#e9fff2"'))
    b.append(f'<g transform="translate(372 62)" filter="url(#d)">{"".join(ob)}</g>')

    # Docset chips
    def pill(x, y, label, dot):
        w = len(label) * 6.9 + 34
        return (f'<g transform="translate({x} {y})" filter="url(#d)">' + R(0, 0, w, 30, 15, None, ' fill="#2b1a2e" stroke="#fff" stroke-opacity=".12"')
                + f'<circle cx="15" cy="15" r="4" fill="{dot}"/>' + T(26, 19.5, label, 12, "", 650, extra=' fill="#f6ecf3"') + "</g>")
    b.append(pill(40, 46, "Python", "#f283a6"))
    b.append(pill(440, 196, "Pandas", "#c39be0"))

    # Download done (bottom left)
    dl = []
    dl.append(R(0, 0, 196, 60, 16, None, ' fill="#241428" stroke="#fff" stroke-opacity=".1"'))
    dl.append('<circle cx="30" cy="30" r="16" fill="#7fdca6" fill-opacity=".16"/>')
    dl.append(icon("check", 21, 21, 18, "g").replace('class="ig"', 'stroke="#7fdca6"'))
    dl.append(T(56, 26, "Django 6.1.2", 11.5, "", 700, extra=' fill="#f6ecf3"'))
    dl.append(T(178, 26, "10 MB", 9.5, "", 600, True, "end", ' fill="#a893a3"'))
    dl.append(R(56, 36, 122, 5, 2.5, None, ' fill="#7fdca6"'))
    b.append(f'<g transform="translate(18 448)" filter="url(#d)">{"".join(dl)}</g>')

    # sparkles
    for x, y, s, c in [(150, 70, 14, "#f283a6"), (520, 300, 11, "#c39be0"), (300, 515, 9, "#f7a3bd")]:
        b.append(f'<path transform="translate({x} {y}) scale({s / 24:.3f})" d="M12 0l2.6 9.4L24 12l-9.4 2.6L12 24l-2.6-9.4L0 12l9.4-2.6z" fill="{c}"/>')
    return svg(W, H, "".join(b), themed=False, defs=defs, extra_css=CODE, attrs=' class="hero-svg" aria-hidden="true" focusable="false"')


# ---------------------------------------------------------------- themed spot art helpers
def card(x, y, w, h, r=14, shadow_on=True):
    f = ' filter="url(#d)"' if shadow_on else ""
    return f'<g{f}>{R(x, y, w, h, r, "s k")}</g>'


def spot(w, h, body, extra_defs="", css=""):
    return svg(w, h, glow(w * .5, h * .5, min(w, h) * .5, "bg") + body, True,
               THEMED_GLOW + shadow(w, h) + extra_defs, CODE + ICON_CSS + css, pad=PAD)


def monogram(x, y, s, label, bg="as", fg="a"):
    return R(x, y, s, s, s * .28, bg) + T(x + s / 2, y + s / 2 + s * .13, label, s * .34, fg, 750, True, "middle")


# -- Home bento: reader themes (wide)
def art_themes():
    W, H = 740, 300
    out = []
    themes = [("Light", "#fffdfe", "#2a1a2b", "#eadde4", "#d24f7a", "#f3e9ef"),
              ("Sepia", "#f5ead8", "#43311f", "#e3d3ba", "#a4552e", "#ecdec6"),
              ("Dark", "#160e17", "#f0e4ee", "#33243a", "#f283a6", "#2a1d2c")]
    for i, (name, bg, ink, bar, acc, cbg) in enumerate(themes):
        x = 66 + i * 212
        y = 34 if i != 1 else 22
        g = [f'<g filter="url(#d)">{R(0, 0, 196, 222, 14, None, f" fill=\"{bg}\" stroke=\"#7a6478\" stroke-opacity=\".28\"")}</g>']
        g.append(R(14, 16, 28, 6, 3, None, f' fill="{bar}"') + R(150, 14, 32, 10, 5, None, f' fill="{bar}"'))
        g.append(T(14, 50, "str.format()", 15, "", 750, True, extra=f' fill="{ink}"'))
        g.append(bars(14, 62, [166, 138, 156], None, 5, 11).replace("/>", f' fill="{bar}"/>'))
        g.append(R(14, 98, 168, 54, 9, None, f' fill="{cbg}"'))
        g.append(T(24, 118, '"{0} of {1}"', 10, "", 600, True, extra=f' fill="{acc}"'))
        g.append(T(24, 136, ".format(1, 9)", 10, "", 600, True, extra=f' fill="{ink}" fill-opacity=".8"'))
        g.append(bars(14, 166, [160, 120, 146], None, 5, 11).replace("/>", f' fill="{bar}"/>'))
        out.append(f'<g transform="translate({x} {y})">{"".join(g)}</g>')
        lab, w = chip(x + 98 - (len(name) * 6.2 + 20) / 2, y + 236, name, "s2", "t", 11)
        out.append(lab)
    # text size control
    ctl = [f'<g filter="url(#d)">{R(0, 0, 54, 132, 14, "s k")}</g>']
    for j, s in enumerate([10, 13, 16, 20]):
        ctl.append(T(27, 28 + j * 29, "A", s, "a" if j == 2 else "m", 700, anchor="middle"))
    out.append(f'<g transform="translate(676 64)">{"".join(ctl)}</g>')
    return spot(W, H, "".join(out))


# -- Home bento: store
def art_store():
    W, H = 360, 300
    out = []
    out.append(card(34, 24, 292, 38, 19))
    out.append(icon("search", 48, 35, 16, "m"))
    out.append(T(72, 48, "Search 806 docsets", 12, "m"))
    labs = [("Py", "as", "a"), ("Kt", "ps", "p"), ("Js", "gs", "g"), ("Go", "s2", "t"),
            ("Rs", "ps", "p"), ("C++", "as", "a"), ("Dj", "gs", "g"), ("Re", "as", "a"),
            ("Sql", "s2", "t"), ("Sh", "gs", "g"), ("Md", "as", "a"), ("Np", "ps", "p")]
    for i, (l, bg, fg) in enumerate(labs):
        c, r = i % 4, i // 4
        x, y = 34 + c * 76, 80 + r * 70
        out.append(f'<g filter="url(#d)">{R(x, y, 64, 60, 14, "s k")}</g>')
        out.append(monogram(x + 14, y + 10, 36, l, bg, fg))
        if i == 5:
            out.append(f'<circle cx="{x + 56}" cy="{y + 6}" r="11" class="a"/>' + icon("down", x + 49, y - 1, 14, "w"))
    return spot(W, H, "".join(out))


# -- Home bento: library
def art_library():
    W, H = 360, 300
    out = [card(30, 22, 300, 256)]
    out.append(T(50, 54, "Library", 15, "t", 750))
    out.append(T(310, 54, "3 docsets", 10.5, "m", 600, anchor="end"))
    rows = [("Py", "Python", "3.15.0", "28.8 MB", "as", "a"), ("Re", "React", "19.3.1", "18.7 MB", "ps", "p"),
            ("Dj", "Django", "6.1.2", "10.0 MB", "gs", "g")]
    for i, (m, n, v, s, bg, fg) in enumerate(rows):
        y = 74 + i * 52
        out.append(monogram(50, y, 36, m, bg, fg))
        out.append(T(98, y + 16, n, 13, "t", 700) + T(98, y + 31, "v" + v, 10.5, "m", None, True))
        out.append(T(310, y + 23, s, 11, "m", 600, True, "end"))
    out.append(T(50, 248, "Storage", 10.5, "m", 600))
    x = 50
    for w, c in [(98, "a"), (64, "p"), (34, "g")]:
        out.append(R(x, 256, w, 8, 4, c))
        x += w + 3
    out.append(R(x, 256, 310 - x, 8, 4, "b"))
    return spot(W, H, "".join(out))


# -- Home bento: bookmarks (wide)
def art_bookmarks():
    W, H = 740, 300
    out = [card(40, 30, 330, 240)]
    out.append(T(62, 64, "Bookmarks", 15, "t", 750))
    rows = [("functools.lru_cache", "Python · Function"), ("useEffect › Caveats", "React · Section"),
            ("groupBy", "Kotlin · Function")]
    for i, (n, d) in enumerate(rows):
        y = 84 + i * 58
        if i == 1:
            out.append(R(52, y - 6, 306, 54, 12, "as"))
        out.append(R(62, y + 2, 32, 32, 9, "s2" if i != 1 else "s") + icon("mark", 68, y + 8, 20, "a"))
        out.append(T(106, y + 16, n, 12, "t", 650, True) + T(106, y + 33, d, 10.5, "m"))
    # opened page, scrolled to the section
    pg = [f'<g filter="url(#d)">{R(0, 0, 300, 250, 14, "s k")}</g>']
    pg.append(T(20, 32, "useEffect", 17, "t", 750, True))
    pg.append(bars(20, 46, [250, 210], "b", 6, 12))
    pg.append(R(0, 80, 300, 70, 0, "as") + R(0, 80, 4, 70, 0, "a"))
    pg.append(T(20, 108, "Caveats", 15, "a", 750))
    pg.append(bars(20, 120, [240, 200], "b2", 6, 12))
    pg.append(bars(20, 168, [256, 230, 180, 220], "b", 6, 13))
    out.append(f'<g transform="translate(410 26)">{"".join(pg)}</g>')
    out.append('<path d="M358 141 C385 141 382 141 408 141" fill="none" class="ak" stroke-width="2" stroke-dasharray="3 4" stroke-linecap="round"/>')
    out.append('<circle cx="410" cy="141" r="4" class="a"/>')
    return spot(W, H, "".join(out))


# -- Home: privacy (on-device)
def art_private():
    W, H = 440, 420
    out = []
    # phone
    out.append(f'<g filter="url(#d)">{R(130, 30, 180, 360, 32, "s k")}</g>')
    out.append(R(140, 40, 160, 340, 24, "s2"))
    out.append(R(196, 50, 48, 8, 4, "b2"))
    # local database
    for i, (body, top) in enumerate([("p", "ps"), ("p", "ps"), ("a", "as")]):
        y = 196 - i * 34
        out.append(f'<ellipse cx="220" cy="{y + 24}" rx="50" ry="14" class="{body}"/>')
        out.append(R(170, y, 100, 24, 0, body))
        out.append(f'<ellipse cx="220" cy="{y}" rx="50" ry="14" class="{top}"/>')
    out.append(T(220, 250, "Index on your phone", 11.5, "t", 700, anchor="middle"))
    out.append(T(220, 266, "searches never leave it", 10, "m", anchor="middle"))
    out.append(R(158, 288, 124, 28, 14, "s") + icon("search", 168, 294, 16, "a") + T(190, 306, "lru_cache", 10.5, "t", 600, True))
    out.append(R(158, 324, 124, 28, 14, "s") + icon("mark", 168, 330, 16, "a") + T(190, 342, "3 bookmarks", 10.5, "t", 600))
    # shield
    out.append(f'<g transform="translate(266 54)" filter="url(#d)"><path d="M32 0l30 11v22c0 20-13 33-30 41C15 66 2 53 2 33V11z" class="g"/>'
               + icon("check", 18, 22, 28, "w", 2.6) + "</g>")
    # crossed cloud + chips
    out.append(f'<g transform="translate(30 70)"><g filter="url(#d)">{R(0, 0, 92, 72, 16, "s k")}</g>'
               + icon("cloud", 22, 6, 48, "m", 1.6) + icon("slash", 28, 12, 36, "a", 2.4) + T(46, 64, "No account", 10, "m", 600, anchor="middle") + "</g>")
    c1, w1 = chip(44, 160, "No ads", "gs", "g", 11)
    out.append(f'<g filter="url(#d)">{c1}</g>')
    out.append(f'<g transform="translate(316 252)"><g filter="url(#d)">{R(0, 0, 110, 40, 20, "s k")}</g>'
               + icon("plane", 12, 12, 16, "g") + T(36, 24.5, "Offline", 11.5, "t", 700) + '<circle cx="94" cy="20" r="4" class="g"/></g>')
    return spot(W, H, "".join(out))


# -- Ask with citations (home + pro)
def art_ask():
    W, H = 460, 420
    out = []
    q = "How do I stop my script when anything fails?"
    out.append(f'<g filter="url(#d)">{R(150, 26, 280, 52, 18, "a")}</g>')
    out.append(T(166, 48, "How do I stop my script", 12.5, "", 600, extra=' fill="#fff"') + T(166, 66, "when anything fails?", 12.5, "", 600, extra=' fill="#fff"'))
    out.append(card(30, 98, 340, 196))
    out.append(R(50, 116, 22, 22, 7, "as") + icon("spark", 53, 119, 16, "a") + T(80, 132, "AI answer · from your docs", 10.5, "m", 650))
    out.append(T(50, 164, "Start it with", 13, "t"))
    out.append(R(50, 174, 186, 30, 8, "cd"))
    out.append(code(62, 194, [[("set ", 1), ("-e ", 0), ("-o ", 0), ("pipefail", 3)]], 12))
    out.append(R(244, 180, 22, 18, 6, "as") + T(255, 193, "1", 10.5, "a", 750, True, "middle"))
    out.append(bars(50, 218, [290, 250], "b", 6, 13))
    out.append(T(50, 260, "A pipeline then fails if any part fails", 11, "m"))
    out.append(R(282, 248, 22, 18, 6, "as") + T(293, 261, "2", 10.5, "a", 750, True, "middle"))
    # sources
    srcs = [("1", "4.3.1 The Set Builtin"), ("2", "3.2.3 Pipelines")]
    for i, (n, s) in enumerate(srcs):
        y = 312 + i * 50
        x = 110 + i * 26
        out.append(card(x, y, 316, 40, 12))
        out.append(R(x + 10, y + 10, 20, 20, 6, "a") + T(x + 20, y + 24, n, 10.5, "", 750, True, "middle", ' fill="#fff"'))
        out.append(T(x + 40, y + 18, s, 11.5, "t", 650) + T(x + 40, y + 32, "Bash manual · opens offline", 9.5, "m"))
        out.append(icon("book", x + 284, y + 11, 18, "a"))
    return spot(W, H, "".join(out))


def art_explain():
    W, H = 460, 420
    out = [card(40, 20, 380, 250)]
    out.append(T(62, 54, "3.2.3 Pipelines", 15, "t", 750))
    out.append(bars(62, 68, [320, 280], "b", 6, 12))
    out.append(R(62, 100, 336, 84, 10, "cd"))
    out.append(R(70, 120, 250, 38, 4, None, ' fill="#f283a6" fill-opacity=".28"'))
    out.append(code(76, 134, [[("cmd1 ", 0), ("| ", 1), ("cmd2 ", 0), ("|& ", 1), ("cmd3", 0)],
                              [("echo ", 2), ("$", 1), ("{PIPESTATUS[@]}", 4)], [("# exit status of each", 5)]], 11, 20))
    out.append(R(68, 116, 3, 46, 1.5, "a") + '<circle cx="69.5" cy="114" r="4" class="a"/>')
    out.append(R(319, 116, 3, 46, 1.5, "a") + '<circle cx="320.5" cy="164" r="4" class="a"/>')
    # selection toolbar
    out.append(f'<g transform="translate(150 196)"><g filter="url(#d)">{R(0, 0, 176, 36, 12, "t")}</g>'
               + T(22, 23, "Copy", 11.5, "s", 600) + R(64, 10, 1, 16, 0, "m") + icon("spark", 78, 9, 18, "a")
               + T(100, 23, "Explain", 11.5, "s", 700) + "</g>")
    # bottom sheet
    out.append(card(20, 252, 420, 150, 18))
    out.append(R(206, 262, 48, 5, 2.5, "b2"))
    out.append(R(40, 282, 24, 24, 8, "as") + icon("spark", 44, 286, 16, "a") + T(74, 299, "Explain", 14, "t", 750))
    out.append(T(40, 330, "Each command's output feeds the next.", 11.5, "t"))
    out.append(T(40, 348, "|& also passes error output along.", 11.5, "t"))
    out.append(bars(40, 362, [300], "b", 6))
    c, w = chip(40, 374, "3.2.3 Pipelines", "as", "a", 10)
    out.append(c)
    return spot(W, H, "".join(out))


def art_meaning():
    W, H = 460, 420
    out = [card(30, 22, 400, 46, 23)]
    out.append(icon("spark", 48, 35, 20, "a") + T(78, 50, "abort when anything goes wrong", 12.5, "t", 600))
    x = 30
    for lab, on in [("By name", False), ("By meaning", True)]:
        w = len(lab) * 6.6 + 26
        out.append(R(x, 82, w, 26, 13, "a" if on else "s2") + T(x + w / 2, 99, lab, 11, "s" if on else "m", 650, anchor="middle"))
        x += w + 8
    res = [("4.3.1 The Set Builtin", "Bash › Shell Builtin Commands", "set -e", "Exit immediately if a pipeline returns", "a"),
           ("3.2.3 Pipelines", "Bash › Shell Commands", "pipefail", "The return status is the last command", "p"),
           ("pcall (f [, arg1, ···])", "Lua › Basic Functions", "pcall", "Calls f in protected mode", "g")]
    for i, (t, path, hl, ex, c) in enumerate(res):
        y = 124 + i * 94
        out.append(card(30, y, 400, 82, 14))
        out.append(R(30, y + 14, 4, 54, 2, c))
        out.append(T(48, y + 24, t, 13, "t", 700) + T(48, y + 40, path, 10, "m", None, True))
        cw = len(hl) * 6.6 + 12
        out.append(R(48, y + 51, cw, 18, 5, c + "s" if c != "a" else "as") + T(48 + cw / 2, y + 64, hl, 10.5, c, 700, True, "middle"))
        out.append(T(56 + cw, y + 64, ex, 10.5, "m"))
    return spot(W, H, "".join(out))


def art_learn():
    W, H = 460, 420
    out = []
    out.append(f'<g transform="rotate(-7 230 190)">{card(80, 60, 300, 230, 18)}</g>')
    out.append(f'<g transform="rotate(4 230 190)">{card(80, 54, 300, 230, 18)}</g>')
    out.append(card(70, 44, 320, 240, 18))
    out.append(R(90, 64, 82, 22, 11, "ps") + T(131, 79, "Python", 10.5, "p", 700, anchor="middle"))
    out.append(T(370, 79, "3 / 10", 10.5, "m", 600, True, "end"))
    out.append(T(90, 124, "What does", 17, "t", 700))
    out.append(T(90, 150, "@lru_cache(maxsize=None)", 14, "a", 700, True))
    out.append(T(90, 176, "do to a function?", 17, "t", 700))
    out.append(R(90, 218, 280, 42, 12, "s2") + T(230, 244, "Show answer", 12.5, "t", 650, anchor="middle"))
    btn = [("Again", "1m", "as", "a"), ("Good", "1d", "ps", "p"), ("Easy", "4d", "gs", "g")]
    for i, (l, d, bg, fg) in enumerate(btn):
        x = 70 + i * 110
        out.append(f'<g filter="url(#d)">{R(x, 312, 100, 52, 14, bg)}</g>' + T(x + 50, 334, l, 12.5, fg, 700, anchor="middle") + T(x + 50, 352, d, 10.5, fg, 600, True, "middle"))
    for i in range(10):
        out.append(f'<circle cx="{171 + i * 13}" cy="390" r="3.5" class="{"a" if i < 3 else "b2"}"/>')
    return spot(W, H, "".join(out))


def art_tabs():
    W, H = 460, 420
    out = [card(14, 40, 432, 300, 20)]
    out.append(R(24, 50, 412, 280, 12, "s2"))
    # tab strip
    tabs = [("io.open", True), ("pathlib", False), ("+", False)]
    x = 34
    for lab, on in tabs:
        w = 30 if lab == "+" else len(lab) * 7 + 34
        out.append(R(x, 58, w, 26, 9, "s" if on else "b") + T(x + w / 2, 75, lab, 10.5, "t" if on else "m", 650, lab != "+", "middle"))
        x += w + 6
    # panes
    for i, (title, code_l) in enumerate([("pathlib.Path", [[("Path", 2), ("(", 0), ('"a.txt"', 3), (")", 0)], [(".read_text", 2), ("()", 0)]]),
                                         ("io.open", [[("open", 2), ("(", 0), ("f", 0), (", ", 0), ('"r"', 3), (")", 0)], [("# text mode", 5)]])]):
        px = 34 + i * 202
        out.append(R(px, 94, 192, 226, 10, "s"))
        out.append(T(px + 14, 120, title, 13, "t", 750, True))
        out.append(bars(px + 14, 132, [160, 132, 150], "b", 5, 11))
        out.append(R(px + 14, 172, 164, 52, 8, "cd"))
        out.append(code(px + 24, 192, code_l, 10, 18))
        out.append(bars(px + 14, 238, [156, 120, 146, 100], "b", 5, 12))
    out.append(R(227, 180, 6, 50, 3, "a"))
    # long-press menu
    out.append(f'<g transform="translate(250 268)"><g filter="url(#d)">{R(0, 0, 170, 76, 14, "s k")}</g>'
               + icon("tabs", 14, 14, 18, "a") + T(40, 28, "Open in new tab", 11.5, "t", 650)
               + icon("book", 14, 44, 18, "m") + T(40, 58, "Copy link", 11.5, "m", 600) + "</g>")
    return spot(W, H, "".join(out))


def art_more():
    W, H = 460, 420
    out = []
    # look up anywhere
    out.append(card(24, 20, 300, 120, 18))
    out.append(T(44, 50, "Any app", 10.5, "m", 650))
    out.append(T(44, 76, "try", 13, "t", None, True) + R(72, 62, 64, 20, 4, "as") + T(76, 76, "flatMap", 13, "a", 700, True) + T(142, 76, "on the list", 13, "t", None, True))
    out.append(f'<g transform="translate(44 92)"><g filter="url(#d)">{R(0, 0, 222, 34, 11, "t")}</g>'
               + T(16, 22, "Copy", 11, "s", 600) + T(64, 22, "Share", 11, "s", 600) + R(110, 9, 1, 16, 0, "m")
               + icon("book", 120, 8, 18, "a") + T(144, 22, "DevDocs", 11, "s", 700) + "</g>")
    # widget
    out.append(f'<g transform="translate(150 160)"><g filter="url(#d)">{R(0, 0, 290, 96, 26, "a")}</g>'
               + R(14, 14, 262, 46, 23, None, ' fill="#fff" fill-opacity=".92"') + icon("book", 28, 26, 22, "a")
               + T(60, 42, "Search docs", 13, "", 600, extra=' fill="#5d5060"') + T(18, 82, "Home-screen widget", 10.5, "on", 700) + "</g>")
    # updates
    out.append(card(24, 276, 330, 120, 18))
    out.append('<circle cx="70" cy="320" r="24" class="gs"/>' + icon("refresh", 56, 306, 28, "g"))
    out.append(T(108, 314, "3 docsets updated", 13, "t", 700) + T(108, 332, "while charging, on Wi-Fi", 11, "m"))
    out.append(R(48, 360, 34, 18, 5, "b2") + R(82, 365, 3, 8, 1, "b2") + R(51, 363, 22, 12, 3, "g") + icon("bolt", 55, 362, 14, "w", 1.6))
    out.append(T(96, 374, "Python · Kotlin · React", 10.5, "m", None, True))
    return spot(W, H, "".join(out))


# ---------------------------------------------------------------- Pro hero (dark)
def art_pro_hero():
    W, H = 480, 400
    defs = (radial("g1", "#e0608a", .5) + radial("g2", "#8a4aa0", .55)
            + f'<filter id="d" {region(W, H)}><feDropShadow dy="16" stdDeviation="16" flood-color="#000" flood-opacity=".5"/></filter>')
    o = [glow(260, 200, 220, "g1", W, H), glow(130, 300, 170, "g2", W, H)]
    o.append('<circle cx="250" cy="200" r="170" fill="none" stroke="#fff" stroke-opacity=".07" stroke-dasharray="2 7"/>')

    def dcard(x, y, w, h, r=16):
        return f'<g filter="url(#d)">{R(x, y, w, h, r, None, " fill=\"#241428\" stroke=\"#fff\" stroke-opacity=\".1\"")}</g>'
    # answer card
    o.append(dcard(70, 70, 330, 210))
    o.append(R(90, 90, 24, 24, 8, None, ' fill="#f283a6" fill-opacity=".18"') + icon("spark", 94, 94, 16, "a").replace('class="ia"', 'stroke="#f283a6"'))
    o.append(T(124, 107, "Ask your docs", 13, "", 700, extra=' fill="#f6ecf3"'))
    o.append(T(380, 107, "AI · cited", 10, "", 600, True, "end", ' fill="#a893a3"'))
    o.append(R(90, 128, 200, 30, 8, None, ' fill="#140a15"'))
    o.append(code(102, 148, [[("set ", 1), ("-e ", 0), ("-o ", 0), ("pipefail", 3)]], 12))
    o.append(R(298, 134, 22, 18, 6, None, ' fill="#f283a6"') + T(309, 147, "1", 10.5, "", 750, True, "middle", ' fill="#1e0e1e"'))
    o.append(bars(90, 174, [290, 240, 266], None, 6, 13).replace("/>", ' fill="#3d2b42"/>'))
    o.append(R(90, 226, 290, 38, 10, None, ' fill="#f283a6" fill-opacity=".1" stroke="#f283a6" stroke-opacity=".35"'))
    o.append(R(100, 236, 18, 18, 5, None, ' fill="#f283a6"') + T(109, 249, "1", 10, "", 750, True, "middle", ' fill="#1e0e1e"'))
    o.append(T(128, 249, "4.3.1 The Set Builtin · Bash", 11, "", 600, extra=' fill="#f7c4d4"'))
    # floating feature chips
    chips = [(18, 34, "Explain", "spark", "#f283a6"), (330, 30, "By meaning", "search", "#c39be0"),
             (16, 300, "Flashcards", "cards", "#7fdca6"), (300, 306, "Split view", "tabs", "#f7a3bd")]
    for x, y, lab, ic, col in chips:
        w = len(lab) * 7 + 46
        o.append(f'<g transform="translate({x} {y})" filter="url(#d)">' + R(0, 0, w, 36, 18, None, ' fill="#2b1a2e" stroke="#fff" stroke-opacity=".12"')
                 + icon(ic, 12, 9, 18, "a").replace('class="ia"', f'stroke="{col}"') + T(36, 23, lab, 12, "", 650, extra=' fill="#f6ecf3"') + "</g>")
    for x, y, s, c in [(440, 200, 13, "#f283a6"), (40, 200, 10, "#c39be0")]:
        o.append(f'<path transform="translate({x} {y}) scale({s / 24:.3f})" d="M12 0l2.6 9.4L24 12l-9.4 2.6L12 24l-2.6-9.4L0 12l9.4-2.6z" fill="{c}"/>')
    return svg(W, H, "".join(o), False, defs, CODE)


# ---------------------------------------------------------------- docsets
DOCSETS = {
    "python": dict(name="Python", motif=">>>", ver="3.15.0", entries="16,146", size="28.8 MB", hue="#f2c46d",
                   code=[[(">>> ", 5), ("from ", 1), ("functools ", 0), ("import ", 1), ("cache", 0)],
                         [(">>> ", 5), ("@cache", 2)], [("... ", 5), ("def ", 1), ("fib", 2), ("(n): ...", 0)]],
                   q="groupby", res=[("itertools.groupby", "Function"), ("functools.lru_cache", "Function"),
                                     ("collections.Counter", "Class"), ("pathlib.Path.glob", "Method")]),
    "kotlin": dict(name="Kotlin", motif="fun", ver="1.9.20", entries="12,301", size="91.1 MB", hue="#b48cff",
                   code=[[("val ", 1), ("xs ", 0), ("= ", 5), ("listOf", 2), ("(1, 2, 3)", 4)],
                         [("xs.", 0), ("groupBy ", 2), ("{ ", 5), ("it ", 1), ("% 2 ", 4), ("}", 5)],
                         [("  .", 5), ("mapValues ", 2), ("{ it.value }", 0)]],
                   q="list", res=[("listOf", "Function"), ("mapNotNull", "Function"), ("buildList", "Function"),
                                  ("windowed", "Function")]),
    "java": dict(name="Java", motif="{ }", ver="SE 27", entries="59,956", size="82.7 MB", hue="#ffab76",
                 code=[[("var ", 1), ("byCity ", 0), ("= ", 5), ("people", 0)],
                       [("  .", 5), ("stream", 2), ("()", 0)],
                       [("  .", 5), ("collect", 2), ("(", 0), ("groupingBy", 2), ("(..))", 0)]],
                 q="groupingBy", res=[("groupingBy(Function)", "Method"), ("Collectors", "Class"), ("HashMap<K,V>", "Class"),
                                      ("CompletableFuture<T>", "Class")]),
    "javascript": dict(name="JavaScript", motif="=>", ver="MDN", entries="9,447", size="327 MB", hue="#f5d76e",
                       code=[[("const ", 1), ("ids ", 0), ("= ", 5), ("items", 0)],
                             [("  .", 5), ("flatMap", 2), ("(", 0), ("x ", 0), ("=> ", 1), ("x.tags", 0), (")", 0)],
                             [("await ", 1), ("Promise", 2), (".all", 2), ("(jobs)", 0)]],
                       q="flatMap", res=[("Array.prototype.flatMap", "Method"), ("Promise.all", "Method"),
                                         ("Object.entries", "Method"), ("JSON.parse", "Method")]),
    "android": dict(name="Android", sub="Kotlin API reference", motif="</>", ver="Feed build", entries="200,572", size="299 MB", hue="#8fe3b0",
                    code=[[("class ", 1), ("Main", 2), (" : ", 0), ("ComponentActivity", 2), ("()", 0)],
                          [("  val ", 1), ("vm ", 0), ("by ", 1), ("viewModels", 2), ("<", 0), ("VM", 2), (">()", 0)],
                          [("  // viewModelScope.launch { }", 5)]],
                    q="ViewModel", res=[("androidx.lifecycle.ViewModel", "Class"), ("viewModelScope", "Property"),
                                        ("android.content.Intent", "Class"), ("androidx.work.WorkManager", "Class")]),
    "react": dict(name="React", motif="</>", ver="19.3.1", entries="1,369", size="18.7 MB", hue="#7fd3f0",
                  code=[[("const ", 1), ("[n, setN] ", 0), ("= ", 5), ("useState", 2), ("(0)", 4)],
                        [("useEffect", 2), ("(() ", 0), ("=> ", 1), ("{ ... }", 0), (", [n])", 0)],
                        [("return ", 1), ("<", 5), ("Counter ", 2), ("n", 4), ("={n} ", 0), ("/>", 5)]],
                  q="use", res=[("useState", "Guide"), ("useEffect", "Guide"), ("useTransition", "Guide"),
                                ("useActionState", "Guide")]),
    "django": dict(name="Django", motif="{% %}", ver="6.1.2", entries="5,705", size="10.0 MB", hue="#7fdca6",
                   code=[[("{% ", 1), ("for ", 1), ("post ", 0), ("in ", 1), ("posts ", 0), ("%}", 1)],
                         [("  {{ ", 1), ("post.title", 3), ("|", 5), ("upper", 2), (" }}", 1)],
                         [("{% ", 1), ("endfor ", 1), ("%}", 1)]],
                   q="select_related", res=[("QuerySet.select_related", "Method"), ("QuerySet.prefetch_related", "Method"),
                                            ("get_object_or_404()", "Section"), ("TemplateView", "Class")]),
}
# Android shares "</>" with React in spirit only; give it its own motif.
DOCSETS["android"]["motif"] = "API"


def art_docset_head(key):
    d = DOCSETS[key]
    W, H = 480, 360
    hue = d["hue"]
    defs = (radial("g1", "#e0608a", .5) + radial("g2", "#8a4aa0", .5) + radial("g3", hue, .3)
            + '<linearGradient id="ro" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb3cb"/><stop offset=".55" stop-color="#f283a6"/>'
            + f'<stop offset="1" stop-color="{hue}"/></linearGradient>'
            + f'<filter id="d" {region(W, H)}><feDropShadow dy="16" stdDeviation="16" flood-color="#000" flood-opacity=".5"/></filter>')
    o = [glow(260, 180, 210, "g1", W, H), glow(110, 260, 170, "g2", W, H), glow(380, 110, 120, "g3", W, H)]
    o.append('<circle cx="250" cy="180" r="160" fill="none" stroke="#fff" stroke-opacity=".07" stroke-dasharray="2 7"/>')
    # back card
    o.append(f'<g transform="rotate(-6 250 180)" filter="url(#d)">{R(110, 40, 300, 250, 18, None, " fill=\"#1d1020\" stroke=\"#fff\" stroke-opacity=\".07\"")}</g>')
    # main card
    o.append(f'<g filter="url(#d)">{R(70, 50, 320, 250, 18, None, " fill=\"#241428\" stroke=\"#fff\" stroke-opacity=\".11\"")}</g>')
    for i, c in enumerate(["#f283a6", "#c39be0", "#7fdca6"]):
        o.append(f'<circle cx="{92 + i * 13}" cy="72" r="4" fill="{c}" fill-opacity=".8"/>')
    motif = d["motif"]
    fs = 74 if len(motif) <= 3 else 62
    o.append(T(92, 160, motif, fs, "", 800, True, extra=' fill="url(#ro)" letter-spacing="-2"'))
    o.append(T(92, 194, d["name"], 22, "", 750, extra=' fill="#fff" letter-spacing="-.5"'))
    if d.get("sub"):
        o.append(T(92 + len(d["name"]) * 13.2 + 10, 194, d["sub"], 12, "", 600, extra=' fill="#a893a3"'))
    o.append(R(92, 210, 276, 72, 10, None, ' fill="#140a15"'))
    o.append(code(104, 230, d["code"], 10.5, 18))
    # stats chips
    sx = 300
    st = [("version", d["ver"]), ("entries", d["entries"]), ("download", d["size"])]
    y = 30
    pos = [(318, 18), (382, 120), (360, 300)]
    for (lab, val), (x, y) in zip(st, pos):
        w = max(len(val) * 7.4, len(lab) * 5.6) + 26
        o.append(f'<g transform="translate({x} {y})" filter="url(#d)">' + R(0, 0, w, 44, 14, None, ' fill="#2b1a2e" stroke="#fff" stroke-opacity=".13"')
                 + T(13, 18, lab.upper(), 8.5, "", 650, True, extra=' fill="#a893a3" letter-spacing=".6"')
                 + T(13, 34, val, 12.5, "", 750, extra=' fill="#fff"') + "</g>")
    # airplane badge
    o.append('<g transform="translate(26 270)" filter="url(#d)">' + R(0, 0, 40, 40, 20, None, ' fill="#1f2a24" stroke="#7fdca6" stroke-opacity=".45"')
             + icon("plane", 10, 10, 20, "g").replace('class="ig"', 'stroke="#7fdca6"') + "</g>")
    o.append(f'<path transform="translate(40 60) scale(.5)" d="M12 0l2.6 9.4L24 12l-9.4 2.6L12 24l-2.6-9.4L0 12l9.4-2.6z" fill="{hue}"/>')
    return svg(W, H, "".join(o), False, defs, CODE)


def art_docset_search(key):
    d = DOCSETS[key]
    W, H = 400, 430
    o = [card(20, 20, 360, 400, 22)]
    o.append(R(38, 38, 324, 40, 20, "s2") + icon("search", 52, 50, 16, "a") + T(76, 63, d["q"], 13, "t", 650, True))
    o.append(R(76 + len(d["q"]) * 7.9 + 2, 49, 2, 18, 1, "a"))
    x = 38
    for lab, on in [("All", False), (d["name"], True)]:
        w = len(lab) * 6.4 + 24
        o.append(R(x, 92, w, 24, 12, "a" if on else "s2") + T(x + w / 2, 108, lab, 11, "s" if on else "m", 650, anchor="middle"))
        x += w + 8
    tcol = {"Function": ("as", "a"), "Method": ("ps", "p"), "Class": ("gs", "g"), "Guide": ("as", "a"),
            "Section": ("ps", "p"), "Property": ("gs", "g")}
    for i, (n, t) in enumerate(d["res"]):
        y = 134 + i * 66
        if i == 0:
            o.append(R(30, y - 6, 340, 60, 14, "as"))
        bg, fg = tcol[t]
        o.append(R(42, y + 6, 36, 36, 10, bg if i else "s") + T(60, y + 29, t[0], 14, fg, 750, True, "middle"))
        size = 12.5 if len(n) <= 24 else 11
        o.append(T(90, y + 22, n, size, "t", 650, True) + T(90, y + 39, f'{d["name"]} · {t}', 10.5, "m"))
    o.append(R(38, 396, 324, 1, 0, "b2"))
    o.append(icon("plane", 38, 402, 12, "g") + T(56, 412, "Searched on the phone, no connection", 10, "m", 600))
    return spot(W, H, "".join(o))


# ---------------------------------------------------------------- write
def write(name, data):
    data = re.sub(r">\s+<", "><", data)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(data + "\n")
    return len(data)


def sync_sizes():
    """Keep width/height of every <img src=".../assets/art/X.svg"> in the pages equal to the file's size."""
    sizes = {}
    for name in os.listdir(OUT):
        m = re.search(r'<svg[^>]* width="([\d.]+)" height="([\d.]+)"', open(os.path.join(OUT, name), encoding="utf-8").read())
        if m:
            sizes[name] = m.groups()
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if not f.endswith(".html"):
                continue
            path = os.path.join(dirpath, f)
            html = open(path, encoding="utf-8").read()
            new = re.sub(r'(<img src="[^"]*assets/art/([\w-]+\.svg)"[^>]*?) width="\d+" height="\d+"',
                         lambda m: f'{m.group(1)} width="{sizes[m.group(2)][0]}" height="{sizes[m.group(2)][1]}"' if m.group(2) in sizes else m.group(0), html)
            if new != html:
                open(path, "w", encoding="utf-8").write(new)


def main():
    os.makedirs(OUT, exist_ok=True)
    files = {
        "themes.svg": art_themes(), "store.svg": art_store(), "library.svg": art_library(),
        "bookmarks.svg": art_bookmarks(), "private.svg": art_private(), "ask.svg": art_ask(),
        "explain.svg": art_explain(), "meaning.svg": art_meaning(), "learn.svg": art_learn(),
        "tabs.svg": art_tabs(), "more.svg": art_more(), "pro-hero.svg": art_pro_hero(), "hero.svg": hero(),
    }
    for k in DOCSETS:
        files[f"head-{k}.svg"] = art_docset_head(k)
        files[f"search-{k}.svg"] = art_docset_search(k)
    for name, data in sorted(files.items()):
        print(f"  {name:22s} {write(name, data) / 1024:5.1f} KB")
    sync_sizes()
    # inline hero
    idx = os.path.join(ROOT, "index.html")
    html = open(idx, encoding="utf-8").read()
    h = re.sub(r">\s+<", "><", hero())
    h = h.replace(' xmlns="http://www.w3.org/2000/svg"', "")
    new = re.sub(r"<!--hero-art-->.*?<!--/hero-art-->", lambda m: f"<!--hero-art-->{h}<!--/hero-art-->", html, flags=re.S)
    if new != html:
        open(idx, "w", encoding="utf-8").write(new)
        print("  index.html hero art updated")


if __name__ == "__main__":
    main()
