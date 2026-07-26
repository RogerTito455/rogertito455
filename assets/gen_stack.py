#!/usr/bin/env python3
"""Generate the stack card (dark + light) for the profile README.

Chips are laid out by measuring monospace text, so adding a technology to
TIERS below and re-running this is enough — no manual coordinates.

    python3 assets/gen_stack.py
"""

W = 880
PAD = 44
CHIP_X = 250          # chips start here; label column sits to the left
CHIP_H = 30
CHIP_GAP = 8
LINE_H = 38
FS = 13               # chip label size
CHAR_W = FS * 0.6     # monospace advance width
DOT_DX = 15
TEXT_DX = 28
CHIP_PAD_R = 15

MONO = ("ui-monospace, SFMono-Regular, Menlo, Consolas, "
        "&apos;Liberation Mono&apos;, monospace")

# (label, brand colour) — the dot colour is the only per-chip variation.
# A brand whose colour vanishes on one background (Next.js is black) can pass
# {"dark": ..., "light": ...} instead of a single hex.
TIERS = [
    ("core", "without thinking", [
        ("Claude", "#D97757"), ("HTML", "#E34F26"), ("CSS", "#1572B6"),
    ]),
    ("working", "i ship with it", [
        ("TypeScript", "#3178C6"), ("JavaScript", "#F7DF1E"),
        ("Node.js", "#5FA04E"), ("Next.js", {"dark": "#FFFFFF", "light": "#000000"}),
        ("Astro", "#FF5D01"), ("n8n", "#EA4B71"),
        ("Linux", "#E95420"), ("Docker", "#2496ED"), ("Traefik", "#24A1C1"),
        ("Cloudflare", "#F38020"), ("Git", "#F05032"), ("MySQL", "#4479A1"),
        ("SQL", "#8B949E"), ("Java", "#ED8B00"),
    ]),
    ("exploring", "learning where it fits", [
        ("OpenAI API", "#10A37F"), ("Python", "#3776AB"),
    ]),
]

THEMES = {
    "dark": dict(
        bg0="#0d1117", bg1="#151a22", card="#161b22", border="#30363d",
        rule="#21262d", text="#e6edf3", muted="#6e7681", dots="#ffffff",
        dots_op="0.03", chip_bg="#ffffff", chip_bg_op="0.045",
        chip_border="#30363d",
        accents={"core": "#3fb950", "working": "#2f81f7",
                 "exploring": "#a371f7"},
    ),
    "light": dict(
        bg0="#ffffff", bg1="#f4f6f9", card="#ffffff", border="#d0d7de",
        rule="#e1e6eb", text="#1f2328", muted="#818b98", dots="#1f2328",
        dots_op="0.045", chip_bg="#1f2328", chip_bg_op="0.035",
        chip_border="#d8dee4",
        accents={"core": "#1a7f37", "working": "#0969da",
                 "exploring": "#8250df"},
    ),
}


def chip_w(label):
    return TEXT_DX + len(label) * CHAR_W + CHIP_PAD_R


def wrap(chips, avail):
    """Greedy-pack chips into lines that fit `avail` pixels."""
    lines, line, used = [], [], 0.0
    for label, colour in chips:
        w = chip_w(label)
        extra = w if not line else w + CHIP_GAP
        if line and used + extra > avail:
            lines.append(line)
            line, used = [(label, colour)], w
        else:
            line.append((label, colour))
            used += extra
    if line:
        lines.append(line)
    return lines


def build(theme_name):
    t = THEMES[theme_name]
    avail = W - PAD - CHIP_X
    out, y = [], 40

    rows = []
    for name, definition, chips in TIERS:
        lines = wrap(chips, avail)
        block_h = len(lines) * LINE_H - (LINE_H - CHIP_H)
        rows.append((name, definition, lines, block_h))

    total = 40 + sum(h + 40 for _, _, _, h in rows) + 26
    body = []

    for i, (name, definition, lines, block_h) in enumerate(rows):
        accent = t["accents"][name]
        label_y = y + 20
        body.append(
            f'  <text x="{PAD}" y="{label_y}" fill="{accent}" font-size="19" '
            f'font-weight="700" letter-spacing="0.4" font-family="{MONO}">{name}</text>'
        )
        body.append(
            f'  <text x="{PAD}" y="{label_y + 19}" fill="{t["muted"]}" '
            f'font-size="11" letter-spacing="0.4" font-family="{MONO}">{definition}</text>'
        )
        for li, line in enumerate(lines):
            cx, cy = CHIP_X, y + li * LINE_H
            for label, colour in line:
                if isinstance(colour, dict):
                    colour = colour[theme_name]
                w = chip_w(label)
                body.append(
                    f'  <rect x="{cx:.0f}" y="{cy}" width="{w:.0f}" height="{CHIP_H}" '
                    f'rx="{CHIP_H // 2}" fill="{t["chip_bg"]}" '
                    f'fill-opacity="{t["chip_bg_op"]}" stroke="{t["chip_border"]}"/>'
                )
                body.append(
                    f'  <circle cx="{cx + DOT_DX:.0f}" cy="{cy + CHIP_H / 2:.0f}" '
                    f'r="3.5" fill="{colour}"/>'
                )
                body.append(
                    f'  <text x="{cx + TEXT_DX:.0f}" y="{cy + CHIP_H / 2 + 4.5:.0f}" '
                    f'fill="{t["text"]}" font-size="{FS}" letter-spacing="0.2" '
                    f'font-family="{MONO}">{label}</text>'
                )
                cx += w + CHIP_GAP
        y += block_h + 40
        if i < len(rows) - 1:
            body.append(
                f'  <rect x="{PAD}" y="{y - 22}" width="{W - 2 * PAD}" '
                f'height="1" fill="{t["rule"]}"/>'
            )

    body.append(
        f'  <text x="{PAD}" y="{total - 18}" fill="{t["muted"]}" font-size="12" '
        f'letter-spacing="0.2" font-family="{MONO}">coursework fundamentals — '
        f'deliberately ai-free</text>'
    )

    alt = "Stack in three tiers. " + " ".join(
        f"{n} ({d}): " + ", ".join(c[0] for c in ch) + "."
        for n, d, ch in TIERS
    )
    s = theme_name[0]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {total}" width="{W}" height="{total}" role="img" aria-label="{alt}">
  <defs>
    <linearGradient id="sb{s}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{t['bg0']}"/><stop offset="100%" stop-color="{t['bg1']}"/>
    </linearGradient>
    <pattern id="sd{s}" width="18" height="18" patternUnits="userSpaceOnUse">
      <circle cx="1.2" cy="1.2" r="1.2" fill="{t['dots']}" fill-opacity="{t['dots_op']}"/>
    </pattern>
    <clipPath id="sc{s}"><rect width="{W}" height="{total}" rx="12"/></clipPath>
  </defs>
  <g clip-path="url(#sc{s})">
    <rect width="{W}" height="{total}" fill="url(#sb{s})"/>
    <rect width="{W}" height="{total}" fill="url(#sd{s})"/>
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{total - 1}" rx="12" fill="none" stroke="{t['border']}"/>
{chr(10).join(body)}
</svg>
'''


if __name__ == "__main__":
    import pathlib
    here = pathlib.Path(__file__).parent
    for name in THEMES:
        path = here / f"stack-{name}.svg"
        path.write_text(build(name), encoding="utf-8")
        print(f"wrote {path.name}")
