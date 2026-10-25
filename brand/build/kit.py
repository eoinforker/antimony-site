"""Shared drawing helpers for every export. Reads geo.json."""
import json, os
G = json.load(open(os.path.join(os.path.dirname(__file__), "geo.json")))
INK, PAPER, COBALT, SKY = "#0B0D0C", "#F4F3EE", "#2448FF", "#94E6FF"
LINE_D, LINE_L = "#1A2120", "#E2E1DA"          # quiet lattice tones on ink and on paper
FONTS = "file:///home/user/antimony-site/assets/fonts/"
WM = G["wordmark"]

def nucleus_for(ground): return SKY if ground == INK else COBALT
def bond_paths(fill, nuc):
    b = G["bond"]; return f'<path d="{b["ink"]}" fill="{fill}"/><path d="{b["nuc"]}" fill="{nuc}"/>'
def bond_svg(fill=INK, nuc=COBALT, cls="", style=""):
    return f'<svg class="{cls}" style="{style}" viewBox="0 0 100 100" role="img" aria-label="Antimony">{bond_paths(fill, nuc)}</svg>'
def seal_svg(fill=INK, nuc=COBALT):
    s = G["seal"]; r = s["ring"]
    return (f'<svg viewBox="0 0 100 100" role="img" aria-label="Antimony"><circle cx="{r["cx"]}" cy="{r["cy"]}" r="{r["r"]}" fill="none" stroke="{fill}" stroke-width="{r["w"]}"/>'
            f'<path d="{s["ink"]}" fill="{fill}"/><path d="{s["nuc"]}" fill="{nuc}"/></svg>')
# The wordmark's own box: from just above the cap height to the descender, with the overshoots kept.
WM_Y0, WM_Y1 = WM["asc"] - WM["cap"] - 40, WM["asc"] + WM["desc"] - 20
def wordmark_svg(fill=INK, dot=None, style=""):
    dot = dot or fill
    return (f'<svg style="{style}" viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" role="img" aria-label="Antimony">'
            f'<path d="{WM["letters"]}" fill="{fill}"/><path d="{WM["dot"]}" fill="{dot}"/></svg>')
def lockup_svg(fill=INK, nuc=COBALT, dot=None, stacked=False, style=""):
    """The emblem stands 1.5 cap heights tall, centred on the cap height; the gap is one atom across."""
    cap, base = WM["cap"], WM["asc"]
    eh = cap * 1.5; s = eh / 93.0                 # the emblem is 93 units tall inside its square
    dot = dot or nuc
    if not stacked:
        ex, ey = 0, base - cap / 2 - eh / 2 - 1 * s
        gap = 2 * G["R"] * s * 1.15
        wx = 100 * s - 3.5 * s + gap - 15
        w = wx + WM["w"]; y0 = min(ey + s * 1, WM_Y0); y1 = WM_Y1
        return (f'<svg style="{style}" viewBox="{-3.5*s:.0f} {y0:.0f} {w + 3.5*s:.0f} {y1 - y0:.0f}" role="img" aria-label="Antimony">'
                f'<g transform="translate({ex} {ey:.1f}) scale({s:.4f})">{bond_paths(fill, nuc)}</g>'
                f'<g transform="translate({wx:.1f} 0)"><path d="{WM["letters"]}" fill="{fill}"/><path d="{WM["dot"]}" fill="{dot}"/></g></svg>')
    eh = cap * 2.4; s = eh / 93.0
    ex = WM["w"] / 2 - 50 * s; ey = WM_Y0 - eh - cap * 0.75
    return (f'<svg style="{style}" viewBox="-10 {ey:.0f} {WM["w"] + 20:.0f} {WM_Y1 - ey:.0f}" role="img" aria-label="Antimony">'
            f'<g transform="translate({ex:.1f} {ey - s:.1f}) scale({s:.4f})">{bond_paths(fill, nuc)}</g>'
            f'<path d="{WM["letters"]}" fill="{fill}"/><path d="{WM["dot"]}" fill="{dot}"/></svg>')
def lattice_svg(w, h, unit, tone, lit=None, nuc=SKY, ox=0, oy=0, lit_tone=None, only=None):
    """the emblem repeated as a crystal. unit is one emblem's size in px. lit = (i, j) of the one molecule in full colour"""
    b = G["bond"]; out = []
    sx, sy = unit * 1.12, unit * 1.12
    j = 0; y = oy - unit
    while y < h + unit:
        x = ox - unit + (j % 2) * sx / 2; i = 0
        while x < w + unit:
            on = lit == (i, j)
            if only is not None and only != (i, j): x += sx; i += 1; continue
            out.append(f'<g transform="translate({x:.1f} {y:.1f}) scale({unit/100:.4f})"><path d="{b["ink"]}" fill="{lit_tone if on else tone}"/><path d="{b["nuc"]}" fill="{nuc if on else tone}"/></g>')
            x += sx; i += 1
        y += sy; j += 1
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="position:absolute;inset:0" aria-hidden="true">{"".join(out)}</svg>'
def page(w, h, body, bg=INK, css=""):
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Timeless Serif"; src: url({FONTS}TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; }}
@font-face {{ font-family: "Timeless Sans"; src: url({FONTS}timeless-sans-400.woff2) format("woff2"); font-weight: 400; }}
@font-face {{ font-family: "Timeless Sans"; src: url({FONTS}timeless-sans-500.woff2) format("woff2"); font-weight: 500; }}
@font-face {{ font-family: "Commit Mono"; src: url({FONTS}CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {w}px; height: {h}px; overflow: hidden; background: {bg}; -webkit-font-smoothing: antialiased; }}
body {{ position: relative; }}
svg {{ display: block; }}
{css}
</style></head><body>{body}</body></html>'''
