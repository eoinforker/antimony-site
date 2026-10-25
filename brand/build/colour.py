"""The colour system, computed. Tonal scales are built in OKLCH so each step is an even step to the eye; every contrast
ratio is calculated with the WCAG 2 formula, not judged. Writes colours.json."""
import json, math
def srgb_to_lin(c): return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
def lin_to_srgb(c): c = max(0, min(1, c)); return 12.92 * c if c <= .0031308 else 1.055 * c ** (1 / 2.4) - .055
def hex2rgb(h): return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
def rgb2hex(r): return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02X}" for v in r)
def to_oklch(h):
    r, g, b = map(srgb_to_lin, hex2rgb(h))
    l = .4122214708 * r + .5363325363 * g + .0514459929 * b; m = .2119034982 * r + .6806995451 * g + .1073969566 * b; s = .0883024619 * r + .2817188376 * g + .6299787005 * b
    l, m, s = (v ** (1 / 3) for v in (l, m, s))
    L = .2104542553 * l + .7936177850 * m - .0040720468 * s; a = 1.9779984951 * l - 2.4285922050 * m + .4505937099 * s; bb = .0259040371 * l + .7827717662 * m - .8086757660 * s
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360
def from_oklch(L, C, H):
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l = (L + .3963377774 * a + .2158037573 * b) ** 3; m = (L - .1055613458 * a - .0638541728 * b) ** 3; s = (L - .0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + .2309699292 * s; g = -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s; bl = -.0041960863 * l - .7034186147 * m + 1.7076147010 * s
    return rgb2hex([lin_to_srgb(v) for v in (r, g, bl)])
def in_gamut(L, C, H):
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l = (L + .3963377774 * a + .2158037573 * b) ** 3; m = (L - .1055613458 * a - .0638541728 * b) ** 3; s = (L - .0894841775 * a - 1.2914855480 * b) ** 3
    rgb = [4.0767416621 * l - 3.3077115913 * m + .2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s, -.0041960863 * l - .7034186147 * m + 1.7076147010 * s]
    return all(-1e-4 <= v <= 1 + 1e-4 for v in rgb)
def lum(h): r, g, b = map(srgb_to_lin, hex2rgb(h)); return .2126 * r + .7152 * g + .0722 * b
def contrast(a, b): la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)
CORE = {"Ink": "#0B0D0C", "Paper": "#F4F3EE", "Cobalt": "#2448FF", "Sky": "#94E6FF"}
STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]
LIGHT = [.975, .945, .89, .82, .73, .62, .52, .43, .34, .25]
def scale(base, chroma_peak, hue, peak_at=500):
    out = {}
    for s, L in zip(STEPS, LIGHT):
        # chroma rises to the middle of the scale and falls at both ends, then is pulled back inside sRGB
        k = 1 - abs((STEPS.index(s) - STEPS.index(peak_at)) / 5) ** 1.6
        C = max(.004, chroma_peak * max(.12, k))
        while not in_gamut(L, C, hue) and C > 0: C -= .002
        out[s] = from_oklch(L, C, hue)
    return out
Lc, Cc, Hc = to_oklch(CORE["Cobalt"])
cobalt = scale(CORE["Cobalt"], Cc, Hc, 600); cobalt[600] = CORE["Cobalt"]      # the core cobalt sits at 600, exactly
Li, Ci, Hi = to_oklch(CORE["Ink"])
neutral = {s: from_oklch(L, .006, Hi) for s, L in zip(STEPS, LIGHT)}             # the neutrals keep ink's faint green bias
neutral[50] = CORE["Paper"]
grounds = {"Paper": CORE["Paper"], "Ink": CORE["Ink"], "Cobalt": CORE["Cobalt"]}
pairs = []
for gname, g in grounds.items():
    for fname, fc in CORE.items():
        if fc == g: continue
        c = contrast(g, fc); pairs.append({"ground": gname, "colour": fname, "ratio": round(c, 2), "text": "AAA" if c >= 7 else "AA" if c >= 4.5 else "AA large" if c >= 3 else "Marks only" if c >= 1.6 else "Never"})
out = {"core": CORE, "cobalt": cobalt, "neutral": neutral, "pairs": pairs,
       "oklch": {k: [round(v, 3) for v in to_oklch(h)] for k, h in CORE.items()},
       "proportion": {"Paper": 62, "Ink": 30, "Cobalt": 6, "Sky": 2}}
json.dump(out, open("colours.json", "w"), indent=1)
print(json.dumps({"cobalt": cobalt, "neutral": neutral}, indent=0)); print(pairs)
