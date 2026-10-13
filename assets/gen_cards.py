#!/usr/bin/env python3
"""Generate every card in the profile README, and the README itself.

The words are rogertito.com's: the portfolio publishes its copy as
https://rogertito.com/profile.json (in the page's order, in English), this
script reads it — or assets/profile.json, the last copy it read, when the site
cannot be reached — and .github/workflows/sync.yml runs it every day, so the
profile follows the site. To change a word, change the portfolio. What lives
here is only how the profile draws it: colours, mascots, tilts. Text is
measured with the real fonts, so wrapping, chip widths and card heights are
computed.

The SVGs are shown through <img>, which cannot load web fonts, so each file
embeds the glyphs it uses as subsetted WOFF2 (Bricolage Grotesque, Figtree,
Caveat — all OFL, from Google Fonts). The full fonts are downloaded once into
assets/.font-cache/ (gitignored).

    pip install fonttools brotli
    python3 assets/gen_cards.py
    PROFILE_URL=http://127.0.0.1:4321/profile.json python3 assets/gen_cards.py  # a local build
"""

import base64
import io
import json
import math
import os
import pathlib
import re
import urllib.request
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = HERE / ".font-cache"

# ═══════════════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════════════

# The words come from the portfolio: rogertito.com/profile.json is its copy in
# English, in the page's order (src/pages/profile.json.ts in the portfolio
# repo). It is fetched on every run and kept in assets/profile.json, which is
# also the fallback when the site cannot be reached. What lives here is only
# what the profile draws differently from the site: colours, mascots, tilts,
# and a few labels that only make sense on GitHub.

PROFILE_URL = os.environ.get("PROFILE_URL", "https://rogertito.com/profile.json")
PROFILE_CACHE = HERE / "profile.json"
PROFILE_VERSION = 1


def load_profile():
    try:
        req = urllib.request.Request(PROFILE_URL, headers={"User-Agent": "gen_cards"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
        json.loads(raw)
        PROFILE_CACHE.write_text(raw, encoding="utf-8")
        print(f"read {PROFILE_URL}")
    except Exception as e:  # offline, or the site is down: last known copy
        if not PROFILE_CACHE.exists():
            raise SystemExit(f"cannot read {PROFILE_URL} ({e}) and no cache")
        raw = PROFILE_CACHE.read_text(encoding="utf-8")
        print(f"read assets/profile.json ({PROFILE_URL} unreachable: {e})")
    data = json.loads(raw)
    if data.get("version") != PROFILE_VERSION:
        raise SystemExit(f"profile.json is version {data.get('version')}; "
                         f"this generator reads {PROFILE_VERSION}")
    return data


P = load_profile()

# ── what the profile draws its own way ────────────────────────────────────

TINTS = {"mint": "#cdeebc", "lavender": "#ddd2fd", "peach": "#ffd9c6",
         "sky": "#d6e7ff", "butter": "#ffeaa8", "pink": "#ffd3dc"}

# the binder's tab colours, per chapter
SECTION_TINT = {"experience": "mint", "work": "butter", "ai": "lavender",
                "stack": "sky", "about": "pink", "contact": "peach"}

# metro lines, by role key
ROLE_LOOK = {
    "mesoestetic": {"line": "#3fb560", "label_ink": "#23843f",
                    "bg": ("#e6f6da", "#cdeebc"), "mascot": ("happy", "laptop")},
    "proven": {"line": "#8b6cff", "label_ink": "#5a3fd6",
               "bg": ("#efe9ff", "#ddd2fd"), "mascot": ("calm", "magnifier")},
    "esypa": {"line": "#ff8a5c", "label_ink": "#b8501f",
              "bg": ("#fff0e6", "#ffd9c6"), "mascot": ("wave", "hardhat")},
}
ROLE_DEFAULT = {"line": "#3b7bea", "label_ink": "#2856b0",
                "bg": ("#e3eeff", "#c9dcfb"), "mascot": ("calm", "none")}

# work cards, by item key; a new item without an entry gets the next of these
PROJECT_LOOK = {
    "trainingHub": {"dot": "#e0a100", "bg": ("#fff4cf", "#ffe6a0"),
                    "mascot": ("sparkle", "trophy"), "tilt": -0.8},
    "hackfire": {"dot": "#ff5a2c", "bg": ("#ffe4da", "#ffcbb8"),
                 "mascot": ("happy", "headset"), "tilt": 0.8},
    "garantia": {"dot": "#3f8f2a", "bg": ("#e5f6da", "#c9ecb4"),
                 "mascot": ("calm", "receipt"), "tilt": 0.8},
    "site": {"dot": "#3b7bea", "bg": ("#e3eeff", "#c9dcfb"),
             "mascot": ("sparkle", "laptop"), "tilt": -0.8},
    "spectranet": {"dot": "#e8456b", "bg": ("#ffe4ea", "#fcc9d4"),
                   "mascot": ("calm", "hardhat"), "tilt": -0.8},
    "esypaAutomation": {"dot": "#7c5cff", "bg": ("#eee8ff", "#dacffd"),
                        "mascot": ("happy", "laptop"), "tilt": 0.8},
}
PROJECT_DEFAULTS = [look for look in PROJECT_LOOK.values()]
LINK_LABEL = {"hackfire": "Open the case"}  # anything else with a link: "Visit"

# stack clusters, by group key: dot, daily key, its shadow
STACK_LOOK = {
    "ai": ("#8b6cff", "#d9ccff", "#b3a0f5"),
    "frontend": ("#3b7bea", "#cfe2ff", "#9fc0f0"),
    "backend": ("#3fb560", "#cdeebc", "#9fd38a"),
    "infra": ("#ff8a5c", "#ffd6c2", "#f2ad8c"),
    "quality": ("#e0a100", "#ffe9a3", "#e8c860"),
}

SUBAGENT_MASCOTS = [("calm", "magnifier"), ("happy", "laptop"), ("calm", "shield")]


def kebab(key):
    return re.sub(r"(?<!^)([A-Z])", r"-\1", key).lower()


# ── the site's words, shaped for the cards ────────────────────────────────

LINKS = P["links"]

_stickers = P["hero"]["stickers"]
HERO = {
    "hello": P["hero"]["hello"],
    "name": P["hero"]["name"],
    "lead": P["hero"]["lead"],
    "pills": [(c, i == 0) for i, c in enumerate(P["hero"]["chips"][:2])],
    "rosette": (_stickers["winner"], _stickers["winnerOf"], _stickers["winnerYear"]),
    "bubble": "¡hola!",
    "hack": (_stickers["hackbarna"], _stickers["hackbarnaYear"]),
    "nvidia": _stickers["nemotron"],
    "note": "my sidekick",
}

_notes = {s["key"]: s["note"] for s in P["sections"]}
_legend = P["stack"]["legend"]
# The headers carry a short fact; the cards under them carry the site's
# handwritten note for that chapter.
_section_aside = {
    "experience": _notes["experience"],
    "work": f'{len(P["work"]["items"])} projects',
    "ai": "how I actually build",
    "stack": " · ".join([_legend["daily"], "real projects", _legend["exploring"]]),
    "about": _notes["about"],
    "contact": P["about"]["facts"][0]["value"],
}
# key, number, title, handwritten aside, sticker tint — in the page's order
SECTIONS = [(s["key"], s["num"], s["title"], _section_aside[s["key"]],
             SECTION_TINT.get(s["key"], "sky")) for s in P["sections"]]

METRO = {
    "kicker": P["experience"]["label"],
    "title": P["experience"]["title"],
    "aside": P["experience"]["aboard"],
    "months": P["experience"]["months"],
    "today": P["experience"]["today"],
}

ROLES = [{
    **ROLE_LOOK.get(r["key"], ROLE_DEFAULT),
    "badge": r["line"], "line_label": r["lineName"], "start": r["start"],
    "role": r["role"], "company": r["company"],
    "meta": f'{r["dates"]} · {r["place"]}',
    "bullets": r["bullets"], "stack": r["tags"],
} for r in P["experience"]["roles"]]

PROJECTS = [{
    **(PROJECT_LOOK.get(p["key"])
       or PROJECT_DEFAULTS[i % len(PROJECT_DEFAULTS)]),
    "slug": "rogertito-com" if p["key"] == "site" else kebab(p["key"]),
    "kicker": p["kicker"], "title": p["name"], "number": p["big"],
    "sub": p["sub"], "desc": p["text"], "stack": p["tags"],
    "link": (LINK_LABEL.get(p["key"], "Visit"), p["url"]) if p["url"] else None,
} for i, p in enumerate(P["work"]["items"])]

_chain = P["ai"]["chain"]
AI = {
    "aside": _notes["ai"],
    "title": P["ai"]["headline"],
    "intro": P["ai"]["lead"],
    "me": (_chain["me"], _chain["meSub"]),
    "orchestrator": (_chain["claude"], _chain["claudeSub"]),
    "subagents_label": _chain["parallel"].upper(),
    "subagents": [(a["name"], a["sub"], SUBAGENT_MASCOTS[i % 3])
                  for i, a in enumerate(_chain["agents"])],
    "ship": (_chain["main"], _chain["mainSub"]),
    "me_note": _chain["thatsMe"],
    "context": (P["ai"]["contextLabel"], P["ai"]["context"]),
    "guardrails": (P["ai"]["guardrailsLabel"], P["ai"]["guardrails"]),
}

# level: "daily" | "used" (in real projects) | "exploring"
D, U, X = "daily", "used", "exploring"
STACK = {
    "legend": [(D, _legend["daily"]), (U, _legend["used"]),
               (X, _legend["exploring"])],
    "aside": _notes["stack"],
    "clusters": [(g["name"], *STACK_LOOK.get(g["key"], STACK_LOOK["frontend"]),
                  [(k["label"], k["level"]) for k in g["keys"]])
                 for g in P["stack"]["groups"]],
}

CONTACT = {
    "aside": _notes["contact"],
    "title": P["contact"]["title"],
    "text": P["contact"]["lead"],
    "stamp_corner": "BCN · 26",
    "stamp_kicker": P["contact"]["replyLabel"],
    "stamp_value": P["contact"]["reply"],
    "postmark": ("BARCELONA", "OCT · 2026"),
}

ABOUT = P["about"]

# ═══════════════════════════════════════════════════════════════════════════
# FONTS
# ═══════════════════════════════════════════════════════════════════════════

FAMILIES = {
    # key: (css family, Google Fonts css2 query)
    "display": ("Bricolage Grotesque", "Bricolage+Grotesque:opsz,wght@48,800"),
    "sans": ("Figtree", "Figtree:wght@400;500;600;700;800"),
    "hand": ("Caveat", "Caveat:wght@700"),
}
FALLBACK = {"display": "sans-serif", "sans": "sans-serif", "hand": "cursive"}

DISPLAY = ("display", 800)
HAND = ("hand", 700)


def sans(weight):
    return ("sans", weight)


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/4.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def ensure_fonts():
    """Return {(family_key, weight): path}, downloading TTFs on first run."""
    CACHE.mkdir(exist_ok=True)
    paths = {}
    for key, (_, query) in FAMILIES.items():
        listed = sorted(CACHE.glob(f"{key}-*.ttf"))
        if not listed:
            css = _download(f"https://fonts.googleapis.com/css2?family={query}"
                            ).decode()
            for weight, url in re.findall(
                    r"font-weight:\s*(\d+);.*?src:\s*url\(([^)]+\.ttf)\)",
                    css, re.S):
                (CACHE / f"{key}-{weight}.ttf").write_bytes(_download(url))
            listed = sorted(CACHE.glob(f"{key}-*.ttf"))
        for p in listed:
            paths[(key, int(p.stem.split("-")[1]))] = p
    return paths


class Metrics:
    """Advance widths and vertical metrics, enough to lay out text."""

    def __init__(self, path):
        from fontTools.ttLib import TTFont
        self.font = TTFont(path)
        self.upm = self.font["head"].unitsPerEm
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"]
        hhea = self.font["hhea"]
        self.asc = hhea.ascent / self.upm
        self.desc = -hhea.descent / self.upm

    def width(self, text, size, ls=0.0):
        units = 0
        for ch in text:
            gid = self.cmap.get(ord(ch))
            if gid is None:
                raise SystemExit(f"glyph missing for {ch!r}")
            units += self.hmtx[gid][0]
        return units * size / self.upm + ls * len(text)

    def baseline(self, top, line_h, size):
        """Baseline of a single line laid out like CSS in a box of line_h."""
        content = (self.asc + self.desc) * size
        return top + (line_h - content) / 2 + self.asc * size


FONT_PATHS = {}
METRICS = {}


def m(font):
    if font not in METRICS:
        METRICS[font] = Metrics(FONT_PATHS[font])
    return METRICS[font]


def tw(text, font, size, ls=0.0):
    return m(font).width(text, size, ls)


def wrap(text, font, size, max_w, ls=0.0):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        cand = w if not cur else f"{cur} {w}"
        if cur and tw(cand, font, size, ls) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def subset_woff2(font, chars):
    from fontTools import subset
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern"]   # kerning only tightens: layout holds
    opts.hinting = False
    opts.desubroutinize = True
    opts.name_IDs = [1, 2]
    opts.notdef_outline = True
    f = subset.load_font(str(FONT_PATHS[font]), opts)
    s = subset.Subsetter(opts)
    s.populate(text="".join(sorted(chars)) + " ")
    s.subset(f)
    buf = io.BytesIO()
    subset.save_font(f, buf, opts)
    return base64.b64encode(buf.getvalue()).decode()


# ═══════════════════════════════════════════════════════════════════════════
# SVG TOOLKIT
# ═══════════════════════════════════════════════════════════════════════════

def n(v):
    if isinstance(v, float):
        v = round(v, 2)
        return str(int(v)) if v == int(v) else f"{v}"
    return str(v)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


MARGIN = 12          # transparent edge on full-width cards, so shadows fit
CONTENT_W = 880      # width every full-width card is designed at

ANIM_CSS = """
.m-wave{transform-box:fill-box;transform-origin:50% 100%;transform:rotate(24deg);animation:mwave 1.8s ease-in-out infinite}
@keyframes mwave{0%,100%{transform:rotate(12deg)}50%{transform:rotate(34deg)}}
.m-glow{animation:mglow 2.6s ease-in-out infinite}
@keyframes mglow{0%,100%{opacity:.35}50%{opacity:1}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.4s ease-out infinite}
@keyframes pulse{0%{transform:scale(1);opacity:.6}100%{transform:scale(2.8);opacity:0}}
@media (prefers-reduced-motion:reduce){.m-wave,.m-glow,.pulse{animation:none}}
"""


class Canvas:
    def __init__(self, w, h, label):
        self.w, self.h, self.label = w, h, label
        self.defs, self.els = [], []
        self.used = defaultdict(set)
        self.cache = {}
        self.count = 0
        self.animated = False

    def uid(self, prefix):
        self.count += 1
        return f"{prefix}{self.count}"

    def add(self, *els):
        self.els.extend(els)

    # — text ————————————————————————————————————————————————————————————
    def text(self, x, y, s, font, size, fill, anchor="start", ls=0.0,
             extra=""):
        fam, weight = font
        self.used[font].update(s)
        a = (f'x="{n(x)}" y="{n(y)}" font-family="{FAMILIES[fam][0]}, '
             f'{FALLBACK[fam]}" font-weight="{weight}" font-size="{n(size)}" '
             f'fill="{fill}"')
        if anchor != "start":
            a += f' text-anchor="{anchor}"'
        if ls:
            a += f' letter-spacing="{n(ls)}"'
        return f"<text {a}{extra}>{esc(s)}</text>"

    def text_box(self, x, top, s, font, size, fill, line_h=None, anchor="start",
                 ls=0.0, extra=""):
        """One line whose CSS box starts at `top`."""
        line_h = line_h or (m(font).asc + m(font).desc) * size
        return self.text(x, m(font).baseline(top, line_h, size), s, font, size,
                         fill, anchor, ls, extra)

    def lines(self, x, top, lines, font, size, fill, line_h, anchor="start",
              ls=0.0):
        return [self.text_box(x, top + i * line_h, ln, font, size, fill,
                              line_h, anchor, ls)
                for i, ln in enumerate(lines)]

    # — paint servers & filters ————————————————————————————————————————
    def linear(self, stops, angle=180):
        key = ("lin", tuple(stops), angle)
        if key not in self.cache:
            gid = self.uid("g")
            a = math.radians(angle)
            sx, sy = math.sin(a), -math.cos(a)
            st = "".join(f'<stop offset="{n(o)}" stop-color="{c}"'
                         f'{f" stop-opacity={chr(34)}{n(op)}{chr(34)}" if op != 1 else ""}/>'
                         for o, c, op in [s if len(s) == 3 else (*s, 1)
                                          for s in stops])
            self.defs.append(
                f'<linearGradient id="{gid}" x1="{n(.5 - sx / 2)}" '
                f'y1="{n(.5 - sy / 2)}" x2="{n(.5 + sx / 2)}" '
                f'y2="{n(.5 + sy / 2)}">{st}</linearGradient>')
            self.cache[key] = gid
        return f"url(#{self.cache[key]})"

    def radial(self, stops, cx=.5, cy=.5, r=.5, gid=None):
        key = ("rad", tuple(stops), cx, cy, r)
        if key not in self.cache:
            gid = gid or self.uid("r")
            st = "".join(f'<stop offset="{n(o)}" stop-color="{c}"'
                         f'{f" stop-opacity={chr(34)}{n(op)}{chr(34)}" if op != 1 else ""}/>'
                         for o, c, op in [s if len(s) == 3 else (*s, 1)
                                          for s in stops])
            self.defs.append(f'<radialGradient id="{gid}" cx="{n(cx)}" '
                             f'cy="{n(cy)}" r="{n(r)}">{st}</radialGradient>')
            self.cache[key] = gid
        return f"url(#{self.cache[key]})"

    def shadow(self, dy=4, blur=6, color="#141e3c", opacity=.12):
        key = ("sh", dy, blur, color, opacity)
        if key not in self.cache:
            fid = self.uid("f")
            self.defs.append(
                f'<filter id="{fid}" x="-30%" y="-30%" width="160%" '
                f'height="180%"><feDropShadow dx="0" dy="{n(dy)}" '
                f'stdDeviation="{n(blur)}" flood-color="{color}" '
                f'flood-opacity="{n(opacity)}"/></filter>')
            self.cache[key] = fid
        return f'filter="url(#{self.cache[key]})"'

    def dots(self, color="#3c508c", opacity=.13):
        key = ("dots", color, opacity)
        if key not in self.cache:
            pid = self.uid("p")
            self.defs.append(
                f'<pattern id="{pid}" width="22" height="22" '
                f'patternUnits="userSpaceOnUse"><circle cx="11" cy="11" '
                f'r="1.3" fill="{color}" fill-opacity="{n(opacity)}"/>'
                f'</pattern>')
            self.cache[key] = pid
        return f"url(#{self.cache[key]})"

    def clip_rrect(self, x, y, w, h, r):
        cid = self.uid("c")
        self.defs.append(f'<clipPath id="{cid}"><rect x="{n(x)}" y="{n(y)}" '
                         f'width="{n(w)}" height="{n(h)}" rx="{n(r)}"/>'
                         f'</clipPath>')
        return f'clip-path="url(#{cid})"'

    # — output ————————————————————————————————————————————————————————————
    def render(self):
        faces = []
        for font, chars in sorted(self.used.items()):
            fam, weight = font
            faces.append(
                f"@font-face{{font-family:'{FAMILIES[fam][0]}';"
                f"font-weight:{weight};src:url(data:font/woff2;base64,"
                f"{subset_woff2(font, chars)}) format('woff2')}}")
        css = "".join(faces) + (ANIM_CSS if self.animated else "")
        label = esc(self.label)
        return (
            # geometricPrecision: no hinting, so glyphs keep the advances the
            # layout was measured with (hinted Linux rendering rounds them up).
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'text-rendering="geometricPrecision" viewBox="0 0 {n(self.w)} '
            f'{n(self.h)}" width="{n(self.w)}" height="{n(self.h)}" role="img" '
            f'aria-label="{label}"><title>{label}</title>'
            f"<style>{css}</style><defs>{''.join(self.defs)}</defs>"
            + "".join(self.els) + "</svg>\n")


def rrect(x, y, w, h, r, fill, extra=""):
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" '
            f'rx="{n(r)}" fill="{fill}"{extra}/>')


def star(x, y, s, color):
    pts = [(.5, 0), (.62, .38), (1, .5), (.62, .62), (.5, 1), (.38, .62),
           (0, .5), (.38, .38)]
    p = " ".join(f"{n(x + a * s)},{n(y + b * s)}" for a, b in pts)
    return f'<polygon points="{p}" fill="{color}"/>'


def icon(path_d, x, y, size, stroke=None, fill="none", width=2.4):
    s = size / 24
    st = (f' stroke="{stroke}" stroke-width="{n(width)}" stroke-linecap="round"'
          f' stroke-linejoin="round"' if stroke else "")
    paths = "".join(f'<path d="{d}"/>' for d in path_d)
    return (f'<g transform="translate({n(x)} {n(y)}) scale({n(s)})" '
            f'fill="{fill}"{st}>{paths}</g>')


ICON = {
    "arrow": ["M7 17L17 7", "M9 7h8v8"],
    "mail": ["M4 6h16v12H4z", "M4 7l8 6 8-6"],
    "spark": ["M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"],
    "flame": ["M12 2c1 3.5 4.5 5.5 4.5 10a4.5 4.5 0 0 1-9 0c0-2 1-3.5 "
              "2-4.5.2 1.5 1 2.5 2 3 0-3-1-5.5.5-8.5z"],
    "layers": ["M4 5h16v4H4z", "M4 11h16v4H4z", "M4 17h10v2H4z"],
    "shield": ["M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z",
               "M8.5 12l2.5 2.5 4.5-5"],
}


def pill(cv, x, cy, label, font, size, h, pad, bg, fg, dot=None, gap=8,
         dot_size=8, extra=""):
    """Rounded pill centred on cy. Returns (elements, width)."""
    w = pad * 2 + tw(label, font, size) + (dot_size + gap if dot else 0)
    els = [rrect(x, cy - h / 2, w, h, h / 2, bg, extra)]
    tx = x + pad
    if dot:
        els.append(f'<circle cx="{n(tx + dot_size / 2)}" cy="{n(cy)}" '
                   f'r="{n(dot_size / 2)}" fill="{dot}"/>')
        tx += dot_size + gap
    els.append(cv.text_box(tx, cy - h / 2, label, font, size, fg, h))
    return els, w


def flow(items, max_w, gap_x, gap_y, item_h):
    """Greedy-wrap (width, payload) items; yields (x, y, payload)."""
    x = y = 0
    out = []
    for w, payload in items:
        if x and x + w > max_w:
            x, y = 0, y + item_h + gap_y
        out.append((x, y, payload, w))
        x += w + gap_x
    return out, y + item_h


# ═══════════════════════════════════════════════════════════════════════════
# MASCOT — a round bear-bun with an antenna, drawn on a 160×160 grid
# ═══════════════════════════════════════════════════════════════════════════

def mascot_defs(cv):
    if "mascot" in cv.cache:
        return
    cv.cache["mascot"] = True
    cv.defs.append(
        '<radialGradient id="mBody" cx=".36" cy=".28" r=".96">'
        '<stop offset="0" stop-color="#ffd8c0"/><stop offset=".4" '
        'stop-color="#f6a881"/><stop offset="1" stop-color="#df8058"/>'
        '</radialGradient>'
        '<radialGradient id="mShade" cx=".32" cy=".26" r=".95">'
        '<stop offset=".62" stop-color="#963c1e" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#963c1e" stop-opacity=".22"/>'
        '</radialGradient>'
        '<radialGradient id="mEar" cx=".4" cy=".35" r=".8">'
        '<stop offset="0" stop-color="#ffc6a5"/><stop offset=".75" '
        'stop-color="#e88d63"/></radialGradient>'
        '<radialGradient id="mArm" cx=".4" cy=".3" r=".9">'
        '<stop offset="0" stop-color="#f3a57f"/><stop offset="1" '
        'stop-color="#d9774e"/></radialGradient>'
        '<radialGradient id="mBelly" cx=".5" cy=".35" r=".75">'
        '<stop offset="0" stop-color="#fff3ea"/><stop offset="1" '
        'stop-color="#ffdcc8"/></radialGradient>'
        '<radialGradient id="mBall" cx=".35" cy=".35" r=".8">'
        '<stop offset="0" stop-color="#fff6c2"/><stop offset=".6" '
        'stop-color="#ffcf3f"/><stop offset="1" stop-color="#f0a91c"/>'
        '</radialGradient>'
        '<radialGradient id="mGlow"><stop offset="0" stop-color="#ffc43c" '
        'stop-opacity=".8"/><stop offset="1" stop-color="#ffc43c" '
        'stop-opacity="0"/></radialGradient>'
        '<linearGradient id="mHat" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#ffdf5e"/><stop offset="1" '
        'stop-color="#f4b41a"/></linearGradient>'
        '<linearGradient id="mCup" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#ffe17d"/><stop offset="1" '
        'stop-color="#f2b21d"/></linearGradient>'
        '<linearGradient id="mLap" x1=".33" y1="0" x2=".67" y2="1">'
        '<stop offset="0" stop-color="#e6ebf3"/><stop offset="1" '
        'stop-color="#b8c1d1"/></linearGradient>'
        '<linearGradient id="mShield" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#9fdcff"/><stop offset="1" '
        'stop-color="#4aa6ef"/></linearGradient>')


BODY_PATH = ("M22 102.3A58 68.3 0 0 1 80 34A58 68.3 0 0 1 138 102.3"
             "A53.4 53.7 0 0 1 84.6 156L75.4 156A53.4 53.7 0 0 1 22 102.3Z")


def mascot(cv, x, y, size, mood="wave", acc="none", animate=False):
    mascot_defs(cv)
    hold = acc in ("laptop", "trophy", "receipt", "shield")
    hands_free = acc in ("none", "headset", "hardhat")
    wave = mood == "wave" and hands_free
    mag = acc == "magnifier"
    if animate and (wave or acc != "hardhat"):
        cv.animated = True
    ink, mouth = "#2a1c18", "#6b3426"
    p = ['<ellipse cx="80" cy="153" rx="40" ry="5" fill="#281e3c" '
         'fill-opacity=".14"/>']
    if acc != "hardhat":
        glow = ' class="m-glow"' if animate else ' opacity=".55"'
        p += ['<rect x="79" y="14" width="3" height="20" rx="1.5" '
              'fill="#b86a45"/>',
              f'<circle cx="80.5" cy="10.5" r="17" fill="url(#mGlow)"{glow}/>',
              '<circle cx="80.5" cy="10.5" r="8.5" fill="url(#mBall)"/>']
    for ex in (50, 110):
        p += [f'<circle cx="{ex}" cy="46" r="20" fill="url(#mEar)"/>',
              f'<circle cx="{ex}" cy="46" r="9" fill="#ffdccb"/>']
    if not hold:
        p.append('<ellipse cx="24" cy="115" rx="12" ry="17" fill="url(#mArm)" '
                 'transform="rotate(24 24 115)"/>')
    if not hold and not wave and not mag:
        p.append('<ellipse cx="136" cy="115" rx="12" ry="17" '
                 'fill="url(#mArm)" transform="rotate(-24 136 115)"/>')
    p += [f'<path d="{BODY_PATH}" fill="url(#mBody)"/>',
          f'<path d="{BODY_PATH}" fill="url(#mShade)"/>',
          '<ellipse cx="80" cy="126" rx="30" ry="22" fill="url(#mBelly)"/>',
          '<ellipse cx="59" cy="151" rx="15" ry="7" fill="#d4724a"/>',
          '<ellipse cx="101" cy="151" rx="15" ry="7" fill="#d4724a"/>']
    if mood in ("wave", "sparkle", "calm"):
        for ex in (62, 98):
            p += [f'<ellipse cx="{ex}" cy="83.5" rx="10" ry="11.5" '
                  f'fill="{ink}"/>',
                  f'<circle cx="{ex + 1.5}" cy="78.5" r="3.5" fill="#fff"/>',
                  f'<circle cx="{ex - 4.5}" cy="87.5" r="1.5" fill="#fff" '
                  f'fill-opacity=".9"/>']
    elif mood == "happy":
        for ex in (62, 98):
            p.append(f'<path d="M{ex - 8} 90C{ex - 8} 80 {ex + 8} 80 {ex + 8} '
                     f'90" fill="none" stroke="{ink}" stroke-width="4" '
                     f'stroke-linecap="round"/>')
    elif mood == "dizzy":
        for ex in (62, 98):
            p.append(f'<path d="M{ex - 7} 77L{ex + 7} 91M{ex + 7} 77L{ex - 7} '
                     f'91" stroke="{ink}" stroke-width="4" '
                     f'stroke-linecap="round"/>')
    p += ['<ellipse cx="47" cy="103" rx="9" ry="5" fill="#ff8fa3" '
          'fill-opacity=".55"/>',
          '<ellipse cx="113" cy="103" rx="9" ry="5" fill="#ff8fa3" '
          'fill-opacity=".55"/>']
    if mood in ("wave", "calm"):
        p.append(f'<path d="M73 99.5Q80 107 87 99.5" fill="none" '
                 f'stroke="{mouth}" stroke-width="3" stroke-linecap="round"/>')
    elif mood in ("happy", "sparkle"):
        p += [f'<path d="M72 98H88Q88 109 80 109Q72 109 72 98Z" '
              f'fill="{mouth}"/>',
              '<ellipse cx="80" cy="105.5" rx="5" ry="3.2" fill="#ff7d98"/>']
    elif mood == "dizzy":
        p += [f'<rect x="71" y="99" width="18" height="3" rx="1.5" '
              f'fill="{mouth}"/>',
              '<path d="M78 101h9v6a4.5 4.5 0 0 1-9 0z" fill="#ff7d98"/>']
    if acc == "headset":
        p += ['<path d="M25 106V81A55 58 0 0 1 135 81V106" fill="none" '
              'stroke="#384152" stroke-width="6"/>',
              '<rect x="14" y="84" width="22" height="32" rx="11" '
              'fill="#384152"/>',
              '<rect x="124" y="84" width="22" height="32" rx="11" '
              'fill="#384152"/>',
              '<path d="M31 118L68 110" stroke="#384152" stroke-width="4" '
              'stroke-linecap="round"/>',
              '<circle cx="71" cy="108" r="5" fill="#ff7a59"/>']
    if acc == "hardhat":
        p += ['<path d="M32 58V50C32 27 54 14 80 14S128 27 128 50V58Z" '
              'fill="url(#mHat)"/>',
              '<rect x="75" y="15" width="10" height="38" rx="5" fill="#fff" '
              'fill-opacity=".35"/>',
              '<rect x="22" y="52" width="116" height="11" rx="5.5" '
              'fill="#e2a20d"/>']
    if acc == "laptop":
        p += ['<rect x="46" y="102" width="68" height="46" rx="8" '
              'fill="url(#mLap)"/>',
              '<circle cx="80" cy="124" r="5" fill="#fff" fill-opacity=".9"/>',
              '<rect x="38" y="146" width="84" height="8" rx="4" '
              'fill="#9ca6b8"/>']
    if acc == "trophy":
        p += ['<circle cx="58" cy="118" r="6" fill="none" stroke="#e9a91a" '
              'stroke-width="4"/>',
              '<circle cx="102" cy="118" r="6" fill="none" stroke="#e9a91a" '
              'stroke-width="4"/>',
              '<path d="M64 104H96Q100 104 100 108V116A20 20 0 0 1 60 116V108'
              'Q60 104 64 104Z" fill="url(#mCup)"/>',
              '<rect x="68" y="108" width="6" height="18" rx="3" fill="#fff" '
              'fill-opacity=".55"/>',
              '<rect x="76" y="135" width="8" height="8" fill="#dd9d12"/>',
              '<rect x="64" y="142" width="32" height="9" rx="3" '
              'fill="#b97f0c"/>']
    if acc == "receipt":
        zig = ("60,98 100,98 100,147.7 94.8,152 90,147.7 84.8,152 80,147.7 "
               "74.8,152 70,147.7 64.8,152 60,147.7")
        p.append(f'<g transform="rotate(-8 80 125)"><polygon points="{zig}" '
                 f'fill="#fff"/><rect x="67" y="107" width="26" height="3" '
                 f'rx="1.5" fill="#c9ced8"/><rect x="67" y="115" width="20" '
                 f'height="3" rx="1.5" fill="#c9ced8"/><rect x="67" y="123" '
                 f'width="24" height="3" rx="1.5" fill="#c9ced8"/><rect x="79" '
                 f'y="133" width="14" height="4" rx="2" fill="#6b7385"/></g>')
    if acc == "shield":
        p += ['<polygon points="80,100 99,107.4 96.7,128.5 80,146 63.3,128.5 '
              '61,107.4" fill="url(#mShield)"/>',
              '<path d="M73.5 121.5L78 126L86.5 117.5" fill="none" '
              'stroke="#fff" stroke-width="4" stroke-linecap="round" '
              'stroke-linejoin="round"/>']
    if hold:
        p += ['<ellipse cx="49" cy="122" rx="15" ry="10" fill="url(#mArm)" '
              'transform="rotate(30 49 122)"/>',
              '<ellipse cx="111" cy="122" rx="15" ry="10" fill="url(#mArm)" '
              'transform="rotate(-30 111 122)"/>']
    if mag:
        p.append('<rect x="133" y="56" width="7" height="22" rx="3" '
                 'fill="#4b5563" transform="rotate(12 136.5 67)"/>')
    if wave and animate:
        p.append('<ellipse class="m-wave" cx="133" cy="70" rx="11" ry="20" '
                 'fill="url(#mArm)"/>')
    elif wave or mag:
        rot = 12 if mag else 24
        p.append(f'<ellipse cx="133" cy="70" rx="11" ry="20" fill="url(#mArm)" '
                 f'transform="rotate({rot} 133 90)"/>')
    if mag:
        p += ['<circle cx="136" cy="40" r="17.5" fill="#d6ecff" '
              'fill-opacity=".55" stroke="#4b5563" stroke-width="5"/>',
              '<ellipse cx="130" cy="30.5" rx="4" ry="2.5" fill="#fff" '
              'fill-opacity=".9" transform="rotate(-30 130 30.5)"/>']
    if mood == "dizzy":
        p += [star(36, 6, 13, "#ffcf3f"), star(110, 4, 11, "#b59bff"),
              star(130, 28, 9, "#7cc6ff")]
    if mood == "sparkle":
        p += [star(6, 34, 18, "#ffcf3f"), star(138, 14, 13, "#7cc6ff"),
              star(146, 74, 10, "#ff8fb1"), star(12, 86, 9, "#b59bff")]
    return (f'<g transform="translate({n(x)} {n(y)}) scale({n(size / 160)})">'
            + "".join(p) + "</g>")


# ═══════════════════════════════════════════════════════════════════════════
# CARDS
# ═══════════════════════════════════════════════════════════════════════════

INK, TEXT, BODY, SUB, MUTED = "#121417", "#1d1d1f", "#3b4252", "#2f3542", "#4a5160"


def scallop_points(cx, cy, r_out, r_in, teeth=24):
    pts = []
    for i in range(teeth * 2):
        a = math.pi * 2 * i / (teeth * 2) - math.pi / 2
        r = r_out if i % 2 == 0 else r_in
        pts.append(f"{n(cx + r * math.cos(a))},{n(cy + r * math.sin(a))}")
    return " ".join(pts)


def sticker_panel(cv, h):
    """Dot-grid rounded panel used by the hero and contact cards."""
    clip = cv.clip_rrect(MARGIN, 0, CONTENT_W, h, 28)
    return (f'<g {clip}>' + rrect(MARGIN, 0, CONTENT_W, h, 0, "#eef4ff")
            + rrect(MARGIN, 0, CONTENT_W, h, 0, cv.dots()) + "{inner}</g>")


def build_hero():
    H = 480
    cv = Canvas(CONTENT_W + 2 * MARGIN, H, hero_alt())
    X = MARGIN
    inner = [
        f'<circle cx="{X + 690}" cy="220" r="150" fill="#e3dbff"/>',
        f'<circle cx="{X + 800}" cy="370" r="70" fill="#d6f3c9"/>',
        f'<circle cx="{X + 538}" cy="332" r="32" fill="#ffe0cf"/>',
    ]
    # left column
    hx, hy = X + 52, 48
    hello = cv.text_box(hx, hy, HERO["hello"], HAND, 32, "#e8456b", 35)
    hw = tw(HERO["hello"], HAND, 32)
    inner.append(f'<g transform="rotate(-4 {n(hx + hw / 2)} {n(hy + 17)})">'
                 f'{hello}</g>')
    name_top, name_lh, name_size = hy + 39, 62.7, 66
    name_ls = -0.04 * name_size
    name_lines = wrap(HERO["name"], DISPLAY, name_size, 400, name_ls)
    inner += cv.lines(X + 48, name_top, name_lines, DISPLAY, name_size, INK,
                      name_lh, ls=name_ls)
    sq_top = name_top + name_lh * len(name_lines) + 2
    inner.append(
        f'<path transform="translate({X + 50} {n(sq_top)})" d="M4 10 C 20 2, '
        f'30 16, 46 9 S 74 3, 90 10 S 120 16, 136 8 S 166 4, 182 10" '
        f'fill="none" stroke="#ff6b8a" stroke-width="5" stroke-linecap="round"'
        f' stroke-linejoin="round"/>')
    lead_top = sq_top + 18 + 14
    lead = wrap(HERO["lead"], sans(400), 18, 380)
    inner += cv.lines(X + 48, lead_top, lead, sans(400), 18, BODY, 26.1)
    pills_top = lead_top + 26.1 * len(lead) + 20
    items = []
    for label, live in HERO["pills"]:
        w = 28 + tw(label, sans(600), 14) + (16 if live else 0)
        items.append((w, (label, live)))
    placed, _ = flow(items, 400, 8, 8, 36)
    sh = cv.shadow(3, 5, "#141e3c", .09)
    for px, py, (label, live), w in placed:
        x0, cy = X + 48 + px, pills_top + py + 18
        inner.append(rrect(x0, cy - 18, w, 36, 18, "#fff", " " + sh))
        tx = x0 + 14
        if live:
            cv.animated = True
            inner += [f'<circle class="pulse" cx="{n(tx + 4)}" cy="{n(cy)}" '
                      f'r="4" fill="#22c55e" fill-opacity=".5"/>',
                      f'<circle cx="{n(tx + 4)}" cy="{n(cy)}" r="8" '
                      f'fill="#22c55e" fill-opacity=".18"/>',
                      f'<circle cx="{n(tx + 4)}" cy="{n(cy)}" r="4" '
                      f'fill="#22c55e"/>']
            tx += 16
        inner.append(cv.text_box(tx, cy - 18, label, sans(600), 14, TEXT, 36))
    # rosette
    rx, ry = X + 532, 114
    l1, l2, l3 = HERO["rosette"]
    ros = [f'<polygon points="{scallop_points(rx, ry, 64, 57.6)}" fill="#fff"/>',
           f'<polygon points="{scallop_points(rx, ry, 58, 52.2)}" '
           f'fill="{cv.radial([(0, "#ffe58a"), (1, "#f5b82e")], .4, .35, .7)}"/>',
           f'<circle cx="{rx}" cy="{ry}" r="42" fill="none" stroke="#6e4600" '
           f'stroke-opacity=".35" stroke-width="2" stroke-dasharray="5 4"/>',
           cv.text(rx, ry - 5, l1, DISPLAY, 17, "#4d3400", "middle", -0.17),
           cv.text(rx, ry + 9, l2, sans(700), 9, "#5c4000", "middle"),
           cv.text(rx, ry + 23, l3, sans(800), 11, "#4d3400", "middle")]
    inner.append(f'<g transform="rotate(-12 {rx} {ry})" '
                 f'{cv.shadow(6, 5, "#1e2850", .18)}>' + "".join(ros) + "</g>")
    inner.append(mascot(cv, X + 590, 150, 200, "wave", "none", animate=True))
    # speech bubble
    bw = tw(HERO["bubble"], HAND, 28) + 32
    bx, by, bh = X + 704, 78, 41
    bub = [f'<rect x="{n(bx + 16)}" y="{n(by + bh - 8)}" width="14" height="14"'
           f' fill="#fff" transform="rotate(45 {n(bx + 23)} {n(by + bh - 1)})"/>',
           rrect(bx, by, bw, bh, 18, "#fff"),
           cv.text_box(bx + 16, by + 6, HERO["bubble"], HAND, 28, TEXT, 31)]
    inner.append(f'<g transform="rotate(4 {n(bx + bw / 2)} {n(by + bh / 2)})" '
                 f'{cv.shadow(6, 6, "#1e2850", .14)}>' + "".join(bub) + "</g>")
    # HackBarna sticker
    t1, t2 = HERO["hack"]
    text_w = max(tw(t1, sans(800), 14), tw(t2, sans(700), 11))
    sw, shh = 4 + 12 + 18 + 8 + text_w + 12 + 4, 52
    sx, sy = X + 740, 270              # below the waving arm
    hk = [rrect(sx, sy, sw, shh, 16, "#fff"),
          rrect(sx + 4, sy + 4, sw - 8, shh - 8, 12, "#ffd2c2"),
          icon(ICON["flame"], sx + 16, sy + 17, 18, fill="#ff5a2c"),
          cv.text_box(sx + 42, sy + 11, t1, sans(800), 14, TEXT, 16),
          cv.text_box(sx + 42, sy + 27, t2, sans(700), 11, "#7a3420", 13)]
    inner.append(f'<g transform="rotate(10 {n(sx + sw / 2)} {n(sy + shh / 2)})"'
                 f' {cv.shadow(6, 6, "#1e2850", .16)}>' + "".join(hk) + "</g>")
    # NVIDIA pill
    nw = 4 + 14 + 14 + 8 + tw(HERO["nvidia"], sans(800), 13) + 14 + 4
    nx, ny = X + 480, 384
    nv = [rrect(nx, ny, nw, 40, 20, "#fff"),
          rrect(nx + 4, ny + 4, nw - 8, 32, 16, "#d4f2c4"),
          icon(ICON["spark"], nx + 18, ny + 13, 14, fill="#3f8f2a"),
          cv.text_box(nx + 40, ny + 4, HERO["nvidia"], sans(800), 13, TEXT, 32)]
    inner.append(f'<g transform="rotate(-6 {n(nx + nw / 2)} {n(ny + 20)})" '
                 f'{cv.shadow(6, 6, "#1e2850", .14)}>' + "".join(nv) + "</g>")
    # handwritten note + arrow
    inner.append(f'<g transform="translate({X + 722} 362)" fill="none" '
                 f'stroke="#5a3fd6" stroke-width="2.5" stroke-linecap="round" '
                 f'stroke-linejoin="round"><path d="M46 32 C 32 34, 16 24, 8 7"/>'
                 f'<path d="M8 7 L 7 17"/><path d="M8 7 L 16 12"/></g>')
    note = cv.text_box(X + 768, 392, HERO["note"], HAND, 26, "#5a3fd6")
    inner.append(f'<g transform="rotate(-4 {X + 820} 408)">{note}</g>')
    cv.add(sticker_panel(cv, H).replace("{inner}", "".join(inner)))
    return cv


def build_section(key, num, label, aside, tint, dark):
    H = 72
    title_c = "#f0f6fc" if dark else "#1f2328"
    aside_c = "#ff8fa8" if dark else "#e8456b"
    cv = Canvas(CONTENT_W + 2 * MARGIN, H, f"{num} · {label} — {aside}")
    X = MARGIN + 4
    cx, cy = X + 22, 36
    sticker = [rrect(cx - 22, cy - 22, 44, 44, 14, "#fff"),
               rrect(cx - 19, cy - 19, 38, 38, 11, TINTS[tint]),
               cv.text(cx, m(DISPLAY).baseline(cy - 22, 44, 16), num, DISPLAY,
                       16, TEXT, "middle")]
    cv.add(f'<g transform="rotate(-8 {cx} {cy})" '
           f'{cv.shadow(4, 4, "#1e2850", .2)}>' + "".join(sticker) + "</g>")
    cv.add(cv.text_box(X + 58, cy - 20, label, DISPLAY, 30, title_c, 40,
                       ls=-0.75))
    right = MARGIN + CONTENT_W - 4
    aw = tw(aside, HAND, 25)
    cv.add(f'<g transform="rotate(-2 {n(right - aw / 2)} {cy})">'
           + cv.text_box(right, cy - 16, aside, HAND, 25, aside_c, 32, "end")
           + "</g>")
    return cv


def build_experience():
    X0 = MARGIN
    metro_h, card_h, gap = 290, 244, 16
    H = metro_h + gap + len(ROLES) * (card_h + gap) - gap + MARGIN + 4
    cv = Canvas(CONTENT_W + 2 * MARGIN, H, experience_alt())
    # metro card
    cv.add(rrect(X0, 0, CONTENT_W, metro_h, 24, "#fff",
                 f' stroke="#eceef3" {cv.shadow(6, 8, "#141e3c", .07)}'))
    px, py = X0 + 28, 24
    cv.add(cv.text_box(px, py, METRO["kicker"], sans(600), 15, BODY, 18))
    cv.add(cv.text_box(px, py + 20, METRO["title"], DISPLAY, 32, INK, 38,
                       ls=-0.96))
    aw = tw(METRO["aside"], HAND, 26)
    ax = X0 + CONTENT_W - 28
    cv.add(f'<g transform="rotate(-3 {n(ax - aw / 2)} {py + 26})">'
           + cv.text_box(ax, py + 10, METRO["aside"], HAND, 26, "#e8456b", 32,
                         "end") + "</g>")
    ox, oy = px, py + 58 + 24              # chart origin
    months = METRO["months"]
    x0, x1 = 60, 740
    step = (x1 - x0) / (len(months) - 1)
    sx = [ox + x0 + i * step for i in range(len(months))]
    lanes = sorted(ROLES, key=lambda r: r["start"])
    for li, r in enumerate(lanes):
        ly = oy + 22 + li * 44
        start = sx[r["start"]]
        cv.add(rrect(start, ly - 4, sx[-1] - start, 8, 4, r["line"]))
    for li, r in enumerate(lanes):
        ly = oy + 22 + li * 44
        start = sx[r["start"]]
        cv.add(rrect(start - 40, ly - 16, 32, 32, 9, "#fff",
                     " " + cv.shadow(2, 3, "#1e2850", .18)),
               rrect(start - 38, ly - 14, 28, 28, 7, r["line"]),
               cv.text(start - 24, m(DISPLAY).baseline(ly - 16, 32, 15),
                       r["badge"], DISPLAY, 15, "#fff", "middle"))
        for i in range(r["start"], len(months) - 1):
            cv.add(f'<circle cx="{n(sx[i])}" cy="{n(ly)}" r="5.5" fill="#fff" '
                   f'stroke="{r["line"]}" stroke-width="3"/>')
        cv.add(cv.text_box(start + 4, ly + 10, r["line_label"], sans(700), 12,
                           r["label_ink"], 15))
    last_y = oy + 22 + (len(lanes) - 1) * 44
    cv.add(rrect(sx[-1] - 11.5, oy + 7.5, 23, last_y - oy + 7, 11.5, "#fff",
                 ' stroke="#1d1d1f" stroke-width="3"'))
    els, _ = pill(cv, sx[-1] + 24, oy + 66, METRO["today"], sans(700), 12, 26,
                  10, TEXT, "#fff")
    cv.add(*els)
    for i, mo in enumerate(months):
        last = i == len(months) - 1
        cv.add(cv.text_box(sx[i], oy + 142, mo, sans(700 if last else 600), 12,
                           TEXT if last else "#6b7180", 15, "middle"))
    # role cards
    for i, r in enumerate(ROLES):
        top = metro_h + gap + i * (card_h + gap)
        clip = cv.clip_rrect(X0, top, CONTENT_W, card_h, 24)
        el = [rrect(X0, top, CONTENT_W, card_h, 0,
                    cv.linear([(0, r["bg"][0]), (1, r["bg"][1])], 135))]
        cx, cy = X0 + 28, top + 26
        el += [rrect(cx, cy, 44, 44, 12, "#fff"),
               rrect(cx + 3, cy + 3, 38, 38, 9, r["line"]),
               cv.text(cx + 22, m(DISPLAY).baseline(cy, 44, 22), r["badge"],
                       DISPLAY, 22, "#fff", "middle")]
        tx = cx + 58
        el += [cv.text_box(tx, cy, r["role"], sans(700), 20, INK, 26),
               cv.text_box(tx, cy + 26, r["company"], sans(500), 15, SUB,
                           20.25),
               cv.text_box(tx, cy + 46.25, r["meta"], sans(400), 13, MUTED,
                           18.2)]
        by = cy + 64.45 + 14
        for b in r["bullets"]:
            lines = wrap(b, sans(400), 14, 674 - 16)
            el.append(f'<circle cx="{cx + 3}" cy="{n(by + 10.5)}" r="3" '
                      f'fill="{r["line"]}"/>')
            el += cv.lines(cx + 16, by, lines, sans(400), 14, "#262a33", 21)
            by += 21 * len(lines) + 4
        by += 10
        items = [(20 + tw(s, sans(600), 12.5), s) for s in r["stack"]]
        placed, _ = flow(items, 674, 6, 6, 26)
        for qx, qy, s, w in placed:
            e, _ = pill(cv, cx + qx, by + qy + 13, s, sans(600), 12.5, 26, 10,
                        "#ffffff", "#2b2f3a",
                        extra=' fill-opacity=".7"')
            el += e
        el.append(mascot(cv, X0 + CONTENT_W - 22 - 128, top + card_h - 8 - 128,
                         128, *r["mascot"]))
        cv.add(f"<g {clip}>" + "".join(el) + "</g>")
    return cv


def build_project(p):
    CW, CH, HEAD, SIDE, BOTTOM = 430, 340, 42, 18, 24
    cv = Canvas(CW + 2 * SIDE, HEAD + CH + BOTTOM, project_alt(p))
    x, y = SIDE, HEAD
    el = [rrect(x, y, CW, CH, 26, "#fff"),
          rrect(x + 4, y + 4, CW - 8, CH - 8, 22,
                cv.linear([(0, p["bg"][0]), (1, p["bg"][1])], 160))]
    ix, iy = x + 28, y + 26
    e, _ = pill(cv, ix, iy + 12, p["kicker"], sans(700), 11.5, 24, 10, "#fff",
                TEXT, dot=p["dot"], gap=7, dot_size=7)
    el += e
    el.append(cv.text_box(ix, iy + 38, p["title"], sans(700), 20, INK, 24))
    el.append(cv.text_box(ix, iy + 68, p["number"], DISPLAY, 40, INK, 40,
                          ls=-1.2))
    sub = wrap(p["sub"], sans(600), 13.5, 240)
    el += cv.lines(ix, iy + 112, sub, sans(600), 13.5, BODY, 18.2)
    dtop = iy + 112 + 18.2 * len(sub) + 12
    desc = wrap(p["desc"], sans(400), 13.5, CW - 8 - 48)
    el += cv.lines(ix, dtop, desc, sans(400), 13.5, SUB, 20.25)
    row_cy = y + CH - 26 - 14
    qx = ix
    for s in p["stack"]:
        e, w = pill(cv, qx, row_cy, s, sans(600), 12, 24, 10, "#ffffff",
                    "#2b2f3a", extra=' fill-opacity=".7"')
        el += e
        qx += w + 6
    if p["link"]:
        label, _ = p["link"]
        lw = 24 + tw(label, sans(700), 12) + 16
        lx = x + CW - 28 - lw
        el += [rrect(lx, row_cy - 14, lw, 28, 14, TEXT),
               cv.text_box(lx + 12, row_cy - 14, label, sans(700), 12, "#fff",
                           28),
               icon(ICON["arrow"], lx + lw - 22, row_cy - 5, 10, "#fff",
                    width=3.2)]
    el.append(mascot(cv, x + CW - 10 - 116, y - 32, 116, *p["mascot"]))
    cx, cy = x + CW / 2, y + CH / 2
    cv.add(f'<g transform="rotate({p["tilt"]} {n(cx)} {n(cy)})">'
           f'<g {cv.shadow(6, 7, "#141e3c", .12)}>{el[0]}</g>'
           + "".join(el[1:]) + "</g>")
    return cv


def build_ai():
    H = 550
    cv = Canvas(CONTENT_W + 2 * MARGIN, H, ai_alt())
    X = MARGIN
    clip = cv.clip_rrect(X, 0, CONTENT_W, H, 28)
    el = [rrect(X, 0, CONTENT_W, H, 0, "#f4f0ff"),
          rrect(X, 0, CONTENT_W, H, 0, cv.dots("#6e50c8", .12))]
    stroke = "#8a7fc0"
    cv.defs.append(f'<marker id="ah" orient="auto" markerWidth="5" '
                   f'markerHeight="5" refX="2" refY="2" overflow="visible">'
                   f'<path d="M0 0 L4 2 L0 4 Z" fill="{stroke}"/></marker>')

    def line(x1, y1, x2, y2, head=False):
        if head:   # stop short so the head's tip lands on (x2, y2)
            dx, dy = x2 - x1, y2 - y1
            ln = math.hypot(dx, dy)
            x2, y2 = x2 - dx / ln * 4, y2 - dy / ln * 4
        mk = ' marker-end="url(#ah)"' if head else ""
        return (f'<path d="M{n(X + x1)} {n(y1)}L{n(X + x2)} {n(y2)}" '
                f'stroke="{stroke}" stroke-width="2" stroke-linecap="round" '
                f'fill="none"{mk}/>')

    sub_tops = [130, 218, 306]
    sub_cy = [t + 32 for t in sub_tops]
    el += [line(164, 250, 211, 250, True), line(388, 250, 428, 250),
           line(428, sub_cy[0], 428, sub_cy[-1])]
    el += [line(428, c, 467, c, True) for c in sub_cy]
    el += [line(636, c, 676, c) for c in sub_cy]
    el += [line(676, sub_cy[0], 676, sub_cy[-1]), line(676, 250, 715, 250, True)]

    def card(x, y, w, h, title, body, fill, fg_t, fg_b, center=True, pad_l=12,
             stroke_c=None, shadow=None):
        out = [rrect(X + x, y, w, h, 16 if h < 80 else 18, fill,
                     (f' stroke="{stroke_c}" stroke-width="1.5"' if stroke_c
                      else "") + (" " + shadow if shadow else ""))]
        tsize = 15 if center else 14
        text_w = w - (pad_l + 10 if not center else 24)
        body_lines = wrap(body, sans(400), 13, text_w)
        block = 18 * (1 + len(body_lines))
        top = y + (h - block) / 2
        if center:
            ax, anchor = X + x + w / 2, "middle"
        else:
            ax, anchor = X + x + pad_l, "start"
        out.append(cv.text_box(ax, top, title, sans(700), tsize, fg_t, 18,
                               anchor))
        out += cv.lines(ax, top + 18, body_lines, sans(400), 13, fg_b, 18,
                        anchor)
        return out

    soft = cv.shadow(4, 6, "#503ca0", .1)
    el += card(32, 218, 132, 64, *AI["me"], "#fff", INK, BODY,
               stroke_c="#e0d8ff", shadow=soft)
    el += card(212, 208, 176, 84, *AI["orchestrator"], "#8b6cff", "#fff",
               "#f3efff", shadow=cv.shadow(8, 9, "#6e50e6", .3))
    for (t, b, _), top in zip(AI["subagents"], sub_tops):
        el += card(468, top, 168, 64, t, b, "#fff", INK, BODY, center=False,
                   pad_l=58, stroke_c="#e0d8ff", shadow=soft)
    el += card(716, 214, 132, 72, *AI["ship"], TEXT, "#fff", "#d9dbe3",
               shadow=cv.shadow(8, 9, "#141428", .22))
    # header
    aside = cv.text_box(X + 32, 18, AI["aside"], HAND, 26, "#e8456b", 32)
    el.append(f'<g transform="rotate(-3 {X + 120} 34)">{aside}</g>')
    el.append(cv.text_box(X + 32, 58, AI["title"], DISPLAY, 34, INK, 36,
                          ls=-1.02))
    intro = wrap(AI["intro"], sans(400), 14, 308)
    el += cv.lines(X + 848, 60, intro, sans(400), 14, MUTED, 20.3, "end")
    note = cv.text_box(X + 40, 180, AI["me_note"], HAND, 22, "#e8456b", 27)
    el.append(f'<g transform="rotate(-4 {X + 80} 193)">{note}</g>')
    el.append(cv.text_box(X + 552, 106, AI["subagents_label"], sans(800), 11,
                          "#6a4ee6", 14, "middle", 1.32))
    el.append(mascot(cv, X + 254, 120, 92, "sparkle", "none"))
    for (_, _, mz), top in zip(AI["subagents"], sub_tops):
        el.append(mascot(cv, X + 474, top + 8, 48, *mz))
    # trays
    for tx, (title, chips), ic, ic_c, chip_bg, chip_fg in (
            (32, AI["context"], "layers", "#6a4ee6", "#ece5ff", "#3a2a8c"),
            (448, AI["guardrails"], "shield", "#e8456b", "#ffe3ea", "#8c1f3d")):
        el.append(rrect(X + tx, 394, 400, 124, 18, "#fff",
                        ' fill-opacity=".75" stroke="#e6dfff"'))
        el.append(icon(ICON[ic], X + tx + 16, 410, 16, ic_c))
        el.append(cv.text_box(X + tx + 40, 408, title, sans(800), 14, INK, 20))
        items = [(20 + tw(c, sans(700), 12), c) for c in chips]
        placed, _ = flow(items, 368, 6, 6, 28)
        for qx, qy, c, w in placed:
            e, _ = pill(cv, X + tx + 16 + qx, 438 + qy + 14, c, sans(700), 12,
                        28, 10, chip_bg, chip_fg)
            el += e
    cv.add(f"<g {clip}>" + "".join(el) + "</g>")
    return cv


def key_w(label, level):
    return 24 + tw(label, sans(700 if level == D else 600), 13)


def draw_key(cv, x, y, label, level, daily_bg, daily_sh):
    if level == D:
        els = [rrect(x, y + 3, key_w(label, level), 34, 9, daily_sh),
               rrect(x, y, key_w(label, level), 34, 9, daily_bg)]
        font, fg = sans(700), TEXT
    elif level == U:
        w = key_w(label, level)
        els = [rrect(x, y + 3, w, 34, 9, "#cfd6e3"),
               rrect(x + .5, y + .5, w - 1, 33, 8.5,
                     cv.linear([(0, "#ffffff"), (1, "#f6f8fc")]),
                     ' stroke="#e3e8f0"')]
        font, fg = sans(600), "#1f2328"
    else:
        w = key_w(label, level)
        els = [rrect(x + .75, y + .75, w - 1.5, 32.5, 8.25, "none",
                     ' stroke="#9aa3b5" stroke-width="1.5" '
                     'stroke-dasharray="4 3"')]
        font, fg = sans(600), MUTED
    els.append(cv.text_box(x + 12, y, label, font, 13, fg, 34))
    return els


def build_stack():
    X, PAD = MARGIN, 22
    inner_w = CONTENT_W - 2 * PAD
    clusters = STACK["clusters"]

    def layout(keys, max_w):
        items = [(key_w(k, lv), (k, lv)) for k, lv in keys]
        return flow(items, max_w, 7, 8, 34)

    def section_h(rows_h):
        return 14 + 16 + 10 + rows_h + 3 + 14

    ai_placed, ai_h = layout(clusters[0][4], 680)
    grid = []
    col_w = (inner_w - 14) / 2
    for a, b in ((1, 2), (3, 4)):
        la, ha = layout(clusters[a][4], col_w - 32)
        lb, hb = layout(clusters[b][4], col_w - 32)
        grid.append(((a, la), (b, lb), section_h(max(ha, hb))))
    H = (PAD + 24 + 14 + section_h(ai_h) + 14
         + sum(g[2] for g in grid) + 14 * (len(grid) - 1) + PAD)
    cv = Canvas(CONTENT_W + 2 * MARGIN, H + MARGIN, stack_alt())
    cv.add(rrect(X, 0, CONTENT_W, H, 28, "#e9eef7",
                 ' stroke="#dde3ee" ' + cv.shadow(4, 6, "#141e3c", .05)))
    # legend
    lx, ly = X + PAD + 4, PAD
    samples = {D: (STACK["clusters"][0][2], STACK["clusters"][0][3])}
    for level, label in STACK["legend"]:
        if level == D:
            cv.add(rrect(lx, ly + 4, 22, 18, 6, samples[D][1]),
                   rrect(lx, ly + 2, 22, 18, 6, samples[D][0]))
        elif level == U:
            cv.add(rrect(lx, ly + 4, 22, 18, 6, "#cfd6e3"),
                   rrect(lx + .5, ly + 2.5, 21, 17, 5.5, "#fff",
                         ' stroke="#e3e8f0"'))
        else:
            cv.add(rrect(lx + .75, ly + 2.75, 20.5, 18.5, 5.25, "none",
                         ' stroke="#9aa3b5" stroke-width="1.5" '
                         'stroke-dasharray="3 2.5"'))
        cv.add(cv.text_box(lx + 30, ly, label, sans(600), 12.5, BODY, 24))
        lx += 30 + tw(label, sans(600), 12.5) + 18
    right = X + CONTENT_W - PAD - 4
    aw = tw(STACK["aside"], HAND, 24)
    cv.add(f'<g transform="rotate(-2 {n(right - aw / 2)} {ly + 12})">'
           + cv.text_box(right, ly - 3, STACK["aside"], HAND, 24, "#5a3fd6",
                         30, "end") + "</g>")

    def draw_section(x, y, w, h, cluster, placed):
        name, dot, dbg, dsh, _ = cluster
        out = [rrect(x, y, w, h, 18, "#fff", ' fill-opacity=".6"'),
               f'<circle cx="{n(x + 20)}" cy="{n(y + 22)}" r="4" fill="{dot}"/>',
               cv.text_box(x + 32, y + 14, name, sans(800), 13, INK, 16)]
        for qx, qy, (k, lv), _w in placed:
            out += draw_key(cv, x + 16 + qx, y + 40 + qy, k, lv, dbg, dsh)
        return out

    y = PAD + 24 + 14
    ai_sh = section_h(ai_h)
    cv.add(*draw_section(X + PAD, y, inner_w, ai_sh, clusters[0], ai_placed))
    cv.add(mascot(cv, X + PAD + inner_w - 18 - 88, y + ai_sh - 6 - 88, 88,
                  "happy", "laptop"))
    y += ai_sh + 14
    for (a, la), (b, lb), h in grid:
        cv.add(*draw_section(X + PAD, y, col_w, h, clusters[a], la))
        cv.add(*draw_section(X + PAD + col_w + 14, y, col_w, h, clusters[b],
                             lb))
        y += h + 14
    return cv


def build_contact():
    H = 300
    cv = Canvas(CONTENT_W + 2 * MARGIN, H, contact_alt())
    X = MARGIN
    inner = []
    ax, ay = X + 50, 40
    aside = cv.text_box(ax, ay, CONTACT["aside"], HAND, 28, "#e8456b", 31)
    inner.append(f'<g transform="rotate(-3 {n(ax + 80)} {ay + 15})">{aside}'
                 f'</g>')
    inner.append(cv.text_box(X + 48, 75, CONTACT["title"], DISPLAY, 54, INK, 54,
                             ls=-2.16))
    body = wrap(CONTACT["text"], sans(400), 17, 410)
    inner += cv.lines(X + 48, 141, body, sans(400), 17, BODY, 24.65)
    ptop = 141 + 24.65 * len(body) + 18
    email = LINKS["email"]
    pw = 20 + 18 + 10 + tw(email, sans(700), 16) + 10 + 12 + 20
    inner += [rrect(X + 48, ptop, pw, 46, 23, "#fff",
                    " " + cv.shadow(5, 7, "#141e3c", .12)),
              icon(ICON["mail"], X + 68, ptop + 14, 18, "#e8456b"),
              cv.text_box(X + 96, ptop, email, sans(700), 16, TEXT, 46),
              icon(ICON["arrow"], X + 48 + pw - 32, ptop + 17, 12, TEXT,
                   width=3)]
    # stamp: a white sheet with perforated edges, masked
    sx, sy, sw, sh = X + 566, 38, 196, 224
    mid = cv.uid("k")
    holes = []
    for i in range(0, sw + 1, 14):
        holes += [(i, 0), (i, sh)]
    for j in range(14, sh, 14):
        holes += [(0, j), (sw, j)]
    cv.defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="{sx - 10}" '
                   f'y="{sy - 10}" width="{sw + 20}" height="{sh + 20}">'
                   f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" '
                   f'fill="#fff"/>'
                   + "".join(f'<circle cx="{sx + a}" cy="{sy + b}" r="5"/>'
                             for a, b in holes) + "</mask>")
    ix, iy, iw, ih = sx + 9, sy + 9, sw - 18, sh - 18
    stamp = [f'<g {cv.shadow(8, 7, "#1e2850", .18)}><rect x="{sx}" y="{sy}" '
             f'width="{sw}" height="{sh}" fill="#fff" mask="url(#{mid})"/></g>',
             rrect(ix, iy, iw, ih, 3,
                   cv.linear([(0, "#e8e1ff"), (1, "#d6caff")])),
             cv.text_box(ix + 10, iy + 8, CONTACT["stamp_corner"], sans(800),
                         11, "#45309c", 14, ls=0.88),
             mascot(cv, ix + 29, iy + 22, 120, "wave", "none", animate=True),
             cv.text_box(ix + iw / 2, iy + ih - 12 - 31.5 - 13, CONTACT[
                 "stamp_kicker"], sans(800), 10.5, "#45309c", 13, "middle",
                 1.47),
             cv.text_box(ix + iw / 2, iy + ih - 12 - 31.5, CONTACT[
                 "stamp_value"], DISPLAY, 30, INK, 31.5, "middle", -0.9)]
    inner.append(f'<g transform="rotate(5 {sx + sw / 2} {sy + sh / 2})">'
                 + "".join(stamp) + "</g>")
    pcx, pcy = X + 552, 80
    p1, p2 = CONTACT["postmark"]
    inner.append(
        f'<g transform="rotate(-12 {pcx} {pcy})"><circle cx="{pcx}" '
        f'cy="{pcy}" r="44.75" fill="none" stroke="#1d1d1f" '
        f'stroke-opacity=".45" stroke-width="2.5"/>'
        + cv.text(pcx, pcy - 1, p1, sans(800), 10, "#1d1d1f", "middle", 1,
                  ' fill-opacity=".6"')
        + cv.text(pcx, pcy + 12, p2, sans(700), 10, "#1d1d1f", "middle", .6,
                  ' fill-opacity=".6"') + "</g>")
    inner.append(
        f'<g transform="translate({X + 594} 62)" fill="none" stroke="#1d1d1f" '
        f'stroke-opacity=".38" stroke-width="2.5" stroke-linecap="round">'
        + "".join(f'<path d="M2 {8 + k} C 22 {k}, 38 {16 + k}, 58 {8 + k} '
                  f'S 98 {k}, 118 {8 + k} S 150 {16 + k}, 168 {8 + k}"/>'
                  for k in (0, 12, 24)) + "</g>")
    inner.append(
        f'<g transform="translate({X + 772} 120)"><path d="M6 80 C 20 66, 30 '
        f'44, 62 30" fill="none" stroke="#5a3fd6" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-dasharray="2 7"/><path d="M60 22 L 92 '
        f'8 L 80 40 L 72 30 Z" fill="#8b6cff"/><path d="M72 30 L 92 8" '
        f'stroke="#5a3fd6" stroke-width="2" stroke-linecap="round"/></g>')
    cv.add(sticker_panel(cv, H).replace("{inner}", "".join(inner)))
    return cv


# ═══════════════════════════════════════════════════════════════════════════
# ALT TEXT — the cards' content, for screen readers and images-off readers
# ═══════════════════════════════════════════════════════════════════════════

def hero_alt():
    rosette = " ".join(HERO["rosette"][1:]) + " " + HERO["rosette"][0].lower()
    return (f"{HERO['name']} — {HERO['lead']} "
            f"{' · '.join(c for c, _ in HERO['pills'])}. Stickers: {rosette}, "
            f"{' '.join(HERO['hack'])}, {HERO['nvidia']}.")


def experience_alt():
    parts = [f"Experience — {METRO['title']}."]
    for r in ROLES:
        parts.append(f"{r['role']}, {r['company']} ({r['meta']}): "
                     + " ".join(r["bullets"]) + " Stack: "
                     + ", ".join(r["stack"]) + ".")
    return " ".join(parts)


def project_alt(p):
    return (f"{p['title']} ({p['kicker']}) — {p['number']}: {p['sub']}. "
            f"{p['desc']} Stack: {', '.join(p['stack'])}.")


def ai_alt():
    subs = "; ".join(f"{t} ({b})" for t, b, _ in AI["subagents"])
    me, orch, ship = AI["me"], AI["orchestrator"], AI["ship"]
    return (f"AI engineering — {AI['title']} {AI['intro']} {me[0]}: {me[1]}; "
            f"{orch[0]}: {orch[1]}, with {AI['subagents_label'].lower()}: "
            f"{subs}; {ship[0]}: {ship[1]}. {AI['context'][0]}: "
            f"{', '.join(AI['context'][1])}. {AI['guardrails'][0]}: "
            f"{', '.join(AI['guardrails'][1])}.")


def stack_alt():
    names = dict(STACK["legend"])
    parts = ["Stack by area and level."]
    for name, _, _, _, keys in STACK["clusters"]:
        by = defaultdict(list)
        for k, lv in keys:
            by[lv].append(k)
        parts.append(f"{name}: " + "; ".join(
            f"{names[lv]}: {', '.join(by[lv])}" for lv in (D, U, X) if by[lv])
            + ".")
    return " ".join(parts)


def contact_alt():
    return (f"Contact — {CONTACT['title']} {CONTACT['text']} "
            f"{LINKS['email']}. {CONTACT['stamp_kicker'].capitalize()} "
            f"{CONTACT['stamp_value']}.")


# ═══════════════════════════════════════════════════════════════════════════
# README
# ═══════════════════════════════════════════════════════════════════════════

def attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;")


def section_md(key):
    sec = next(s for s in SECTIONS if s[0] == key)
    alt = attr(f"{sec[1]} · {sec[2]} — {sec[3]}")
    return (f'<picture>\n'
            f'  <source media="(prefers-color-scheme: dark)" '
            f'srcset="assets/section-{key}-dark.svg">\n'
            f'  <source media="(prefers-color-scheme: light)" '
            f'srcset="assets/section-{key}-light.svg">\n'
            f'  <img alt="{alt}" src="assets/section-{key}-light.svg" '
            f'width="100%">\n'
            f'</picture>\n')


def about_md():
    a = ABOUT
    facts = " · ".join(f'{f["label"]} **{f["value"]}**' for f in a["facts"])
    services = "\n".join(f'- **{s["title"]}** — {s["text"]}'
                         for s in a["services"]["items"])
    return "\n\n".join([f'**{a["headline"]}**', *a["paragraphs"],
                         f'<sub>{facts}</sub>',
                         f'**{a["services"]["label"]}**', services]) + "\n"


def work_md():
    cards = []
    for p in PROJECTS:
        img = (f'<img alt="{attr(project_alt(p))}" '
               f'src="assets/work-{p["slug"]}.svg" width="49%">')
        cards.append(f'<a href="{p["link"][1]}">{img}</a>' if p["link"]
                     else img)
    rows = [cards[i:i + 2] for i in range(0, len(cards), 2)]
    return '<p align="center">\n' + "\n".join(
        "  " + "\n  ".join(r) + ("\n  <br>" if i < len(rows) - 1 else "")
        for i, r in enumerate(rows)) + "\n</p>\n"


def build_readme():
    body = {
        "experience": lambda: (f'<img alt="{attr(experience_alt())}" '
                               f'src="assets/experience.svg" width="100%">\n'),
        "work": work_md,
        "ai": lambda: (f'<img alt="{attr(ai_alt())}" '
                       f'src="assets/ai-engineering.svg" width="100%">\n'),
        "stack": lambda: (f'<img alt="{attr(stack_alt())}" '
                          f'src="assets/stack.svg" width="100%">\n'),
        "about": about_md,
        "contact": lambda: (f'<a href="mailto:{LINKS["email"]}"><img '
                            f'alt="{attr(contact_alt())}" '
                            f'src="assets/contact.svg" width="100%"></a>\n'),
    }
    out = ["<!-- Generated by assets/gen_cards.py from rogertito.com/profile.json "
           "— edit the portfolio, not this file. -->\n",
           f'<a href="{LINKS["portfolio"]}"><img alt="{attr(hero_alt())}" '
           f'src="assets/hero.svg" width="100%"></a>\n',
           f'<p align="center">\n'
           f'  <a href="{LINKS["portfolio"]}"><b>Portfolio</b></a>\n'
           f'  &nbsp;&nbsp;·&nbsp;&nbsp;\n'
           f'  <a href="{LINKS["linkedin"]}"><b>LinkedIn</b></a>\n'
           f'  &nbsp;&nbsp;·&nbsp;&nbsp;\n'
           f'  <a href="mailto:{LINKS["email"]}"><b>{LINKS["email"]}</b></a>\n'
           f'</p>\n']
    for key, *_ in SECTIONS:
        out += [section_md(key), body[key]()]
    out.append('<sub>Kept in sync with <a href="https://rogertito.com">'
               'rogertito.com</a>: <a href="assets/gen_cards.py"><code>'
               'assets/gen_cards.py</code></a> reads the site\'s '
               '<code>profile.json</code> every day and redraws these cards.'
               '</sub>\n')
    return "\n".join(out)


# ═══════════════════════════════════════════════════════════════════════════

def main():
    FONT_PATHS.update(ensure_fonts())
    jobs = [("hero.svg", build_hero)]
    for key, num, label, aside, tint in SECTIONS:
        for mode in ("light", "dark"):
            jobs.append((f"section-{key}-{mode}.svg",
                         lambda a=(key, num, label, aside, tint, mode == "dark"):
                         build_section(*a)))
    jobs += [("experience.svg", build_experience)]
    jobs += [(f"work-{p['slug']}.svg", lambda p=p: build_project(p))
             for p in PROJECTS]
    jobs += [("ai-engineering.svg", build_ai), ("stack.svg", build_stack),
             ("contact.svg", build_contact)]
    for name, build in jobs:
        svg = build().render()
        (HERE / name).write_text(svg, encoding="utf-8")
        print(f"wrote assets/{name:<34} {len(svg.encode()) / 1024:6.1f} KB")
    made = {name for name, _ in jobs}
    for old in HERE.glob("*.svg"):
        if old.name not in made:
            old.unlink()
            print(f"removed assets/{old.name}")
    (ROOT / "README.md").write_text(build_readme(), encoding="utf-8")
    print("wrote README.md")


if __name__ == "__main__":
    main()
