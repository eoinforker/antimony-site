"""Writes ../standards/: the Antimony standards, one page per chapter. Everything is drawn from mark.py and colours.json."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from mark import *
from crystal_geometry import HEX, TOP, LL, LR, V as HV
COL = json.load(open("colours.json")); SRC = json.load(open("../art/sources.json"))
OUT = "../standards/"
CH = [("index", "Introduction"), ("logo", "Logo"), ("type", "Typography"), ("colour", "Colour"), ("art", "Art direction"),
      ("motion", "Motion"), ("voice", "Voice"), ("use", "Brand in use"), ("downloads", "Downloads")]
CSS = f"""
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-500.woff2) format("woff2"); font-weight: 500; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
/* A standards book in two grounds: paper for the rules, ink for the mark and the work. Chapters are pages; sections are numbered
   only where the order is real. Every measure on these pages is computed from the same geometry the kit was drawn from. */
:root {{ --ink: {INK}; --paper: {PAPER}; --cobalt: {COBALT}; --sky: {SKY}; --rule: rgba(11,13,12,.13); --dim: #5C6461; --card: #FBFAF6;
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --sans: "Timeless Sans", "Helvetica Neue", Arial, sans-serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 16px/1.55 var(--sans); -webkit-font-smoothing: antialiased; }}
a {{ color: inherit; }}
:focus-visible {{ outline: 2px solid var(--cobalt); outline-offset: 3px; }}
body::before {{ content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 10; background: var(--ink); }}
.top {{ position: sticky; top: env(safe-area-inset-top, 0px); z-index: 9; background: var(--ink); color: var(--paper);
  padding: 12px max(16px, env(safe-area-inset-right, 0px)) 12px max(16px, env(safe-area-inset-left, 0px)); display: flex; gap: 22px; align-items: center; }}
.top .home {{ display: flex; align-items: center; gap: 12px; text-decoration: none; flex: none; }}
.top .home svg {{ height: 22px; width: auto; display: block; }}
.top .home span {{ font: 500 11.5px var(--mono); letter-spacing: .08em; text-transform: uppercase; color: #8A9592; }}
.top nav {{ display: flex; gap: 18px; overflow-x: auto; scrollbar-width: none; min-width: 0; margin-left: auto; }}
.top nav a {{ font: 400 13.5px var(--sans); text-decoration: none; color: #C9CFCC; white-space: nowrap; padding-block: 4px; border-bottom: 1px solid transparent; }}
.top nav a:hover {{ color: var(--paper); }} .top nav a[aria-current] {{ color: var(--paper); border-color: var(--sky); }}
.band {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 72px; border-bottom: 1px solid var(--rule); }}
.band.ink {{ background: var(--ink); color: var(--paper); --rule: rgba(244,243,238,.14); --dim: #8A9592; --card: #121716; }}
.in {{ max-width: 1160px; margin-inline: auto; display: grid; gap: 28px; }}
.eyebrow {{ font: 500 11.5px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--dim); }}
.chapter {{ font: 400 clamp(56px, 10vw, 150px)/.92 var(--serif); letter-spacing: -.03em; }}
h1 {{ font: 400 clamp(44px, 7vw, 96px)/.96 var(--serif); letter-spacing: -.025em; text-wrap: balance; }}
h2 {{ font: 400 clamp(30px, 3.8vw, 46px)/1.04 var(--serif); letter-spacing: -.014em; text-wrap: balance; max-width: 19em; }}
h3 {{ font: 500 16px/1.3 var(--sans); }}
p {{ max-width: 38em; }} .dim {{ color: var(--dim); }}
.lede {{ font: 400 clamp(19px, 2vw, 23px)/1.45 var(--serif); max-width: 33em; }}
.sec {{ display: grid; grid-template-columns: minmax(0, 15em) minmax(0, 1fr); gap: 40px; align-items: start; }}
.sec > .head {{ display: grid; gap: 10px; position: sticky; top: 76px; }}
.sec > .body {{ display: grid; gap: 22px; min-width: 0; }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; align-items: start; }}
.three {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; align-items: start; }}
.four {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; align-items: start; }}
figure {{ display: grid; gap: 10px; min-width: 0; }} figcaption {{ font-size: 14px; color: var(--dim); }}
figcaption b {{ display: block; color: var(--ink); font: 500 15px/1.3 var(--sans); margin-bottom: 2px; }}
.band.ink figcaption b {{ color: var(--paper); }}
.tile {{ aspect-ratio: 1; max-width: 100%; display: grid; place-items: center; padding: 22%; background: var(--card); border: 1px solid var(--rule); }}
.tile svg, .tile img {{ width: 100%; height: 100%; display: block; object-fit: contain; }}
.tile.wide {{ aspect-ratio: 2.4; padding: 9% 12%; }} .tile.tall {{ aspect-ratio: 1; padding: 14%; }}
.tile.ink {{ background: var(--ink); border-color: var(--ink); }} .tile.cob {{ background: var(--cobalt); border-color: var(--cobalt); }}
.tile.sky {{ background: var(--sky); border-color: var(--sky); }}
.shot {{ width: 100%; height: auto; display: block; border: 1px solid var(--rule); max-width: 100%; }}
.nums {{ display: grid; gap: 0; }}
.nums div {{ display: grid; grid-template-columns: 5em minmax(0, 1fr); gap: 14px; border-top: 1px solid var(--rule); padding: 12px 0; }}
.nums b {{ font: 500 14.5px var(--mono); color: var(--cobalt); }}
.band.ink .nums b {{ color: var(--sky); }}
.cons {{ width: 100%; height: auto; font: 500 4.2px var(--mono); background: var(--card); border: 1px solid var(--rule); }}
.dont {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
.dont .tile {{ position: relative; }}
.dont .tile::after {{ content: ""; position: absolute; inset: 10px; background: linear-gradient(to top right, transparent calc(50% - .7px), #D9483B calc(50% - .7px), #D9483B calc(50% + .7px), transparent calc(50% + .7px)); opacity: .8; pointer-events: none; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14.5px; }}
th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
thead th {{ font: 500 11.5px var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--dim); }}
td.num, th.num {{ font-variant-numeric: tabular-nums; font-family: var(--mono); font-size: 13.5px; }}
.scroll {{ overflow-x: auto; }}
.sw {{ display: grid; gap: 3px; padding: 14px; min-height: 150px; align-content: end; border: 1px solid var(--rule); }}
.sw b {{ font: 400 24px/1.1 var(--serif); }} .sw span {{ font: 400 12px var(--mono); opacity: .85; }}
.ramp {{ display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); border: 1px solid var(--rule); }}
.ramp div {{ min-height: 86px; padding: 8px; display: grid; align-content: end; font: 400 10.5px/1.3 var(--mono); }}
.prop {{ display: flex; height: 56px; border: 1px solid var(--rule); }}
.contents {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 40px; }}
.contents a {{ display: grid; grid-template-columns: 3em minmax(0, 1fr) auto; gap: 12px; align-items: baseline; padding: 16px 0; border-top: 1px solid var(--rule); text-decoration: none; }}
.contents a span:first-child {{ font: 500 13px var(--mono); color: var(--dim); }} .contents a b {{ font: 400 26px/1.1 var(--serif); }} .contents a i {{ font-style: normal; color: var(--dim); }}
.contents a:hover b {{ color: var(--cobalt); }}
.pn {{ display: flex; justify-content: space-between; gap: 20px; flex-wrap: wrap; }}
.pn a {{ font: 400 clamp(26px, 3vw, 40px)/1.1 var(--serif); text-decoration: none; }} .pn a:hover {{ color: var(--sky); }}
.spec {{ font-size: clamp(22px, 3vw, 34px); line-height: 1.3; word-break: break-word; }}
.bloom {{ position: relative; aspect-ratio: 4 / 3; max-width: 100%; background: var(--paper); cursor: crosshair; overflow: hidden; border: 1px solid var(--rule); }}
.bloom canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.bloom .hint {{ position: absolute; left: 12px; bottom: 10px; font: 500 11px var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--paper); background: rgba(11,13,12,.7); padding: 6px 9px; pointer-events: none; }}
.plates {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
.plates img {{ width: 100%; aspect-ratio: 4 / 5; object-fit: cover; display: block; border: 1px solid var(--rule); max-width: 100%; }}
.profile {{ background: #fff; border: 1px solid var(--rule); border-radius: 10px; overflow: hidden; color: #191919; }}
.profile .ban {{ width: 100%; display: block; aspect-ratio: 1128 / 191; object-fit: cover; }}
.profile .body {{ padding: 0 20px 20px; }} .profile .av {{ width: 96px; height: 96px; margin-top: -48px; border: 4px solid #fff; border-radius: 6px; display: block; }}
.profile b {{ display: block; font: 500 24px/1.2 var(--sans); margin-top: 10px; }} .profile span {{ color: #555; font-size: 15px; }}
.tab {{ display: inline-flex; align-items: center; gap: 8px; background: #fff; border: 1px solid var(--rule); border-bottom: 0; border-radius: 8px 8px 0 0; padding: 9px 16px; font-size: 13px; color: #333; }}
.tab img {{ image-rendering: pixelated; display: block; }}
.sig {{ background: #fff; border: 1px solid var(--rule); padding: 22px; font: 400 14px/1.5 Arial, sans-serif; color: #222; }}
.do {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); border: 1px solid var(--rule); }}
.do div {{ padding: 16px 18px; display: grid; gap: 6px; }} .do div + div {{ border-left: 1px solid var(--rule); }}
.do .k {{ font: 500 11.5px var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--dim); }}
.do .yes .k {{ color: var(--cobalt); }}
.files {{ display: grid; }} .files div {{ display: grid; grid-template-columns: 9em minmax(0, 1fr); gap: 16px; border-top: 1px solid var(--rule); padding: 12px 0; }}
.files code {{ font: 500 14px var(--mono); }}
.strike {{ width: min(100%, 340px); height: auto; display: block; cursor: pointer; }}
.strike .cut {{ animation: cut .32s cubic-bezier(.65,0,.35,1) forwards; }}
.strike .c1 {{ animation-delay: .5s; }} .strike .c2 {{ animation-delay: .95s; }} .strike .c3 {{ animation-delay: 1.4s; }}
.strike .gold {{ opacity: 0; animation: gold .6s cubic-bezier(.2,.7,.2,1) 1.9s forwards; }}
@keyframes cut {{ to {{ stroke-dashoffset: 0; }} }} @keyframes gold {{ to {{ opacity: 1; }} }}
video {{ width: 100%; height: auto; display: block; max-width: 100%; }}
@media (prefers-reduced-motion: reduce) {{ .strike .cut {{ animation: none; stroke-dashoffset: 0; }} .strike .gold {{ animation: none; opacity: 1; }} video {{ display: none; }} }}
@media (max-width: 900px) {{ .sec {{ grid-template-columns: 1fr; gap: 20px; }} .sec > .head {{ position: static; }} .three, .four, .dont, .plates {{ grid-template-columns: 1fr 1fr; }} .contents {{ grid-template-columns: 1fr; }} .band {{ padding-block: 52px; }} }}
@media (max-width: 560px) {{ .two {{ grid-template-columns: 1fr; }} .ramp {{ grid-template-columns: repeat(5, minmax(0, 1fr)); }} .top .home span {{ display: none; }} .do {{ grid-template-columns: 1fr; }} .do div + div {{ border-left: 0; border-top: 1px solid var(--rule); }} }}
"""
HEAD = '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><link rel="icon" href="img/favicon.svg" type="image/svg+xml">'
def nav(slug):
    links = "".join(f'<a href="{s}.html"{" aria-current=\"page\"" if s == slug else ""}>{t}</a>' for s, t in CH)
    return f'<header class="top"><a class="home" href="index.html">{lockup(PAPER, SKY, "height:22px;width:auto")}<span>Standards</span></a><nav aria-label="Chapters">{links}</nav></header>'
def prevnext(slug):
    i = [s for s, _ in CH].index(slug); p = CH[i - 1] if i > 0 else None; n = CH[i + 1] if i < len(CH) - 1 else None
    return (f'<section class="band ink"><div class="in pn">{f"<a href={chr(34)}{p[0]}.html{chr(34)}>&larr; {p[1]}</a>" if p else "<span></span>"}'
            f'{f"<a href={chr(34)}{n[0]}.html{chr(34)}>{n[1]} &rarr;</a>" if n else ""}</div></section>')
def chapter_head(slug, n, lede, sections):
    t = dict(CH)[slug]
    toc = "".join(f'<a href="#{a}">{b}</a>' for a, b in sections)
    return (f'<section class="band ink"><div class="in"><span class="eyebrow">Chapter {n:02d}</span><h1 class="chapter">{t}</h1>'
            f'<p class="lede">{lede}</p><nav class="toc" aria-label="In this chapter" style="display:flex;gap:10px 22px;flex-wrap:wrap;font:400 14px var(--sans)">{toc}</nav></div></section>')
def sec(id_, title, intro, body, ink=False):
    return (f'<section class="band{" ink" if ink else ""}" id="{id_}"><div class="in sec"><div class="head"><span class="eyebrow">{title}</span></div>'
            f'<div class="body">{intro}{body}</div></div></section>')
def write(slug, title, body, scripts="", doctype=True):
    html = (f'<!doctype html><html lang="en-GB"><head>{HEAD}<title>{title}</title><meta name="claude:viewport-fit-sides" content="cover"><style>{CSS}</style></head><body>' if doctype
            else f'<title>{title}</title><meta name="claude:viewport-fit-sides" content="cover"><link rel="icon" href="img/favicon.svg" type="image/svg+xml"><style>{CSS}</style>')
    html += nav(slug) + body + prevnext(slug) + scripts + ("</body></html>" if doctype else "")
    open(OUT + f"{slug}.html", "w").write(html)
    return len(html)

# ---------- shared drawings ----------
BY = PC["bar_y"]; W = PC["W"]
def construction():
    tri = poly([TOP, LR, LL]); inner = mark_paths(INK, INK)
    return (f'<svg viewBox="-16 -12 132 128" class="cons" role="img" aria-label="Construction of the mark">'
            f'<circle cx="50" cy="50" r="50" fill="none" stroke="rgba(11,13,12,.25)" stroke-width=".3" stroke-dasharray="1.2 1.2"/>'
            f'<path d="{poly(HEX)}" fill="none" stroke="{INK}" stroke-width=".35"/>'
            f'<g opacity=".12">{inner}</g><path d="{tri}" fill="none" stroke="{COBALT}" stroke-width=".5"/>'
            f'<line x1="50" y1="50" x2="{HV(1)[0]:.2f}" y2="{HV(1)[1]:.2f}" stroke="{INK}" stroke-width=".4"/><text x="73" y="35" fill="{INK}">R</text>'
            f'<line x1="-7" y1="0" x2="-7" y2="75" stroke="{INK}" stroke-width=".4"/><line x1="-9" y1="{BY}" x2="-5" y2="{BY}" stroke="{INK}" stroke-width=".4"/>'
            f'<text x="-10" y="{BY + 1.4}" text-anchor="end" fill="{INK}">¾</text><text x="-10" y="76.4" text-anchor="end" fill="{INK}">1</text>'
            f'<text x="50" y="114" text-anchor="middle" fill="#5C6461">60°</text><text x="15" y="40" fill="{COBALT}">W</text></svg>')
def clearspace():
    # clear space: the height of the counter on every side of the mark
    ch = PC["counter"][1][1] - PC["counter"][0][1] if False else (BY - W * .45) - (TOP[1] + W / 2 / math.sin(math.radians(30)))
    m = 100; c = ch
    return (f'<svg viewBox="{-c - 4} {-c - 4} {m + 2 * c + 8} {m + 2 * c + 8}" class="cons" role="img" aria-label="Clear space">'
            f'<rect x="{-c}" y="{-c}" width="{m + 2 * c}" height="{m + 2 * c}" fill="none" stroke="{COBALT}" stroke-width=".6" stroke-dasharray="2 1.5"/>'
            f'{mark_paths(INK, COBALT)}'
            f'<path d="{poly([(-c + 2, -c / 2 - 4), (-c + 2 + c * .577 * 1.0, -c / 2 - 4 + 0), (-c + 2 + c * .289, -c / 2 - 4 - c * .5)])}" fill="none"/>'
            f'<text x="{-c / 2}" y="{m / 2 + 2}" text-anchor="middle" fill="{COBALT}" style="font: 500 6px var(--mono)">x</text>'
            f'<text x="{m + c / 2}" y="{m / 2 + 2}" text-anchor="middle" fill="{COBALT}" style="font: 500 6px var(--mono)">x</text>'
            f'<text x="50" y="{-c / 2 + 2}" text-anchor="middle" fill="{COBALT}" style="font: 500 6px var(--mono)">x</text>'
            f'<text x="50" y="{m + c / 2 + 2}" text-anchor="middle" fill="{COBALT}" style="font: 500 6px var(--mono)">x</text></svg>'), round(ch, 1)
def strike_svg(ground=INK, metal=PAPER, gold=SKY):
    t = (BY - TOP[1]) / (LL[1] - TOP[1]); xl = TOP[0] + (LL[0] - TOP[0]) * t
    def ext(p, q, e): L = math.hypot(q[0] - p[0], q[1] - p[1]); return (p[0] - (q[0] - p[0]) / L * e, p[1] - (q[1] - p[1]) / L * e)
    def seg(a, b, cls): L = math.hypot(b[0] - a[0], b[1] - a[1]); return f'<path class="cut {cls}" d="M{f(a[0])} {f(a[1])}L{f(b[0])} {f(b[1])}" stroke-dasharray="{L:.1f}" stroke-dashoffset="{L:.1f}"/>'
    return (f'<svg viewBox="-2 -2 104 104" class="strike" role="img" aria-label="The mark, struck"><path d="{poly(HEX)}" fill="{metal}"/>'
            f'<g fill="none" stroke="{ground}" stroke-width="{W}">{seg(ext(TOP, LL, 8), ext(LL, TOP, 8), "c1")}{seg(ext(TOP, LR, 8), ext(LR, TOP, 8), "c2")}{seg((xl, BY), (100 - xl, BY), "c3")}</g>'
            f'<path class="gold" d="{poly(PC["counter"])}" fill="{gold}" stroke="{gold}" stroke-width=".8" stroke-linejoin="round"/></svg>')
STRIKE_JS = '<script>document.querySelectorAll(".restrike").forEach(b => b.addEventListener("click", () => { const s = b.querySelector("svg"); s.replaceWith(s.cloneNode(true)); }));</script>'
def window(plate, gold=COBALT, outline=INK):
    clip = "".join(f'<path d="{poly(PC[k])}"/>' for k in ("wing_l", "wing_r", "foot")); i = abs(hash(plate)) % 100000
    return (f'<svg viewBox="-1 -1 102 102" aria-hidden="true"><defs><clipPath id="w{i}">{clip}</clipPath></defs>'
            f'<image href="plates/{plate}.webp" x="-1" y="-1" width="102" height="102" preserveAspectRatio="xMidYMid slice" clip-path="url(#w{i})"/>'
            + "".join(f'<path d="{poly(PC[k])}" fill="none" stroke="{outline}" stroke-width=".45" stroke-linejoin="round"/>' for k in ("wing_l", "wing_r", "foot")) +
            f'<path d="{poly(PC["counter"])}" fill="{gold}"/></svg>')
def bloom_js(plates):
    srcs = json.dumps([f"plates/{p}.webp" for p in plates])
    return """<script>
(() => { "use strict";
  document.querySelectorAll(".bloom").forEach(box => {
  const c = box.querySelector("canvas"), gl = c.getContext("webgl", { antialias: false }); if (!gl) return;
  const SRC = """ + srcs + """;
  const vs = "attribute vec2 p; varying vec2 uv; void main() { uv = vec2(p.x * .5 + .5, .5 - p.y * .5); gl_Position = vec4(p, 0., 1.); }";
  const fs = `precision highp float; varying vec2 uv; uniform sampler2D A, B; uniform float t, seed; uniform vec2 o, asp, ca, cb;
  float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float n(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
  float fbm(vec2 p) { float v = 0., a = .5; for (int i = 0; i < 5; i++) { v += a * n(p); p = p * 2.07 + 3.1; a *= .5; } return v; }
  vec2 fit(vec2 u, vec2 c) { return (u - .5) * c + .5; }
  void main() { vec2 d = (uv - o) * asp; float r = length(d); float g = t * 1.12;
    float e = r + (fbm(uv * 3.5 + seed) - .5) * .42 * (.25 + t) + (fbm(uv * 22. + seed * 1.7) - .5) * .045;
    float m = 1. - smoothstep(g - .005, g + .005, e); float rim = exp(-pow((e - g) / .007, 2.)) * (1. - smoothstep(.8, 1., t)) * step(.001, t);
    vec2 push = normalize(d + 1e-5) / asp * rim * .006;
    vec3 a = texture2D(A, fit(uv - push, ca)).rgb, b = texture2D(B, fit(uv + push, cb)).rgb;
    gl_FragColor = vec4(mix(mix(a, b, m), vec3(.043, .051, .047), rim * .9), 1.); }`;
  const sh = (ty, s) => { const x = gl.createShader(ty); gl.shaderSource(x, s); gl.compileShader(x); return x; };
  const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr); gl.useProgram(pr);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const L = gl.getAttribLocation(pr, "p"); gl.enableVertexAttribArray(L); gl.vertexAttribPointer(L, 2, gl.FLOAT, false, 0, 0);
  const U = k => gl.getUniformLocation(pr, k), tex = [], asp = [], still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let cur = 0, nxt = 1, t = 0, busy = false, o = [.5, .5], seed = 0, ready = false;
  const load = i => new Promise(res => { const im = new Image(); im.onload = () => { const tx = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tx);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im); [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.LINEAR));
    [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.CLAMP_TO_EDGE)); tex[i] = tx; asp[i] = im.width / im.height; res(); }; im.src = SRC[i]; });
  const cover = ia => { const a = c.width / c.height; return ia > a ? [a / ia, 1] : [1, ia / a]; };
  const size = () => { const r = box.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1); c.width = r.width * d; c.height = r.height * d; gl.viewport(0, 0, c.width, c.height); };
  const draw = () => { gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex[cur]); gl.uniform1i(U("A"), 0); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, tex[nxt]); gl.uniform1i(U("B"), 1);
    gl.uniform1f(U("t"), t); gl.uniform1f(U("seed"), seed); gl.uniform2f(U("o"), o[0], o[1]); gl.uniform2f(U("asp"), 1, c.height / c.width); gl.uniform2fv(U("ca"), cover(asp[cur])); gl.uniform2fv(U("cb"), cover(asp[nxt])); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); };
  const bloom = (x, y) => { if (busy || !ready) return; busy = true; o = [x, y]; seed = Math.random() * 40; const s0 = performance.now(), dur = still ? 1 : 2600;
    (function step(now) { const k = Math.min(1, (now - s0) / dur); t = 1 - Math.pow(1 - k, 1.7); draw(); if (k < 1) requestAnimationFrame(step); else { cur = nxt; nxt = (nxt + 1) % SRC.length; t = 0; draw(); busy = false; } })(s0); };
  let auto = setInterval(() => bloom(.5, .5), 5600);
  box.addEventListener("pointerdown", e => { const r = box.getBoundingClientRect(); bloom((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height); clearInterval(auto); auto = setInterval(() => bloom(.5, .5), 5600); });
  new ResizeObserver(() => { size(); if (ready) draw(); }).observe(box);
  Promise.all(SRC.map((_, i) => load(i))).then(() => { ready = true; size(); draw(); });
  });
})();
</script>"""

# ---------- 00 Introduction ----------
PRINCIPLES = [("Struck, not drawn", "Everything we make is cut from something solid. We reach a design by taking away what it does not need."),
              ("What is left is gold", "Colour is earned. It marks the counter, a link, one lit crystal: the part that matters. Never decoration."),
              ("Never alone", "The mark tiles into a library. Our products share our metal. Our pictures stand on four hundred years of other people's work."),
              ("Exact", "Every measure has a reason that can be written down. If a choice cannot be explained, it is not finished."),
              ("Built to last", "Choose what will still look right in fifty years: a serif, paper, ink, plain words.")]
intro = f'''
<section class="band ink"><div class="in" style="grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:56px;align-items:center">
  <div style="display:grid;gap:24px"><span class="eyebrow">Antimony standards</span><h1 class="chapter">Standards.</h1>
  <p class="lede">How Antimony looks, sounds and moves, and why. Written so that anyone who builds with it, now or in fifty years, can make something we would recognise as ours.</p></div>
  <div style="width:min(100%,420px);justify-self:center">{mark(PAPER, SKY, "width:100%;height:auto")}</div>
</div></section>
<section class="band"><div class="in sec"><div class="head"><span class="eyebrow">A note</span></div><div class="body">
  <p class="lede">Antimony is a metal that was used to refine gold: melted with it, it took up everything that was not gold and left the gold behind. Our mark is a crystal with an A struck through it, and the piece left in the middle is the gold.</p>
  <p>This is a standard, not a template. Learn the reasons and you can make anything; copy the examples and you will make the same thing twice. Where these pages give a number, use the number. Where they give a reason, use your judgement.</p>
</div></div></section>
<section class="band"><div class="in sec"><div class="head"><span class="eyebrow">Five principles</span></div><div class="body"><div class="nums">
  {"".join(f"<div><b>{i + 1:02d}</b><span><b style='color:var(--ink);font:500 16px var(--sans);display:block'>{a}</b>{b}</span></div>" for i, (a, b) in enumerate(PRINCIPLES))}
</div></div></div></section>
<section class="band"><div class="in"><span class="eyebrow">Contents</span><div class="contents">
  {"".join(f'<a href="{s}.html"><span>{i:02d}</span><b>{t}</b><i>&rarr;</i></a>' for i, (s, t) in enumerate(CH) if s != "index")}
</div></div></section>'''
sizes = {"index": write("index", "Antimony Standards", intro, doctype=False)}

# ---------- 01 Logo ----------
cs_svg, cs_x = clearspace()
READ = [("An A, struck", "Struck through solid metal like a hallmark: the stamp that says a metal has been tested and is true.", mark(INK, INK, "width:100%")),
        ("The crystal", "Antimony crystallises in the trigonal system. Its symmetry is exactly this: a triangle inside a hexagon.",
         f'<svg viewBox="-2 -2 104 104" aria-hidden="true"><path d="{poly(HEX)}" fill="none" stroke="{INK}" stroke-width="2.4"/><path d="{poly([TOP, LR, LL])}" fill="none" stroke="{COBALT}" stroke-width="2.4"/></svg>'),
        ("The library", "Borges imagined a library of hexagonal galleries. Tile the mark and it becomes one.", lattice(4, 3, 100)),
        ("The wolf", "Alchemists called antimony the wolf of metals. Struck through its top corner, the crystal keeps two ears.", mark(INK, INK, "width:100%")),
        ("The gold", "Antimony refined gold by taking up everything else. The counter is what is left, and it is the only colour.", mark("#D7DCDA", COBALT, "width:100%"))]
DONTS = [("Fill the strikes", f'<svg viewBox="-2 -2 104 104"><path d="{poly(HEX)}" fill="{INK}"/><path d="{poly(PC["counter"])}" fill="{COBALT}"/></svg>'),
         ("Rotate it", mark(INK, COBALT, "transform:rotate(30deg)")), ("Gold on the wrong piece", mark_svg := f'<svg viewBox="-2 -2 104 104">{mark_paths(INK, INK)}<path d="{poly(PC["foot"])}" fill="{COBALT}"/></svg>'),
         ("Colour every piece", f'<svg viewBox="-2 -2 104 104"><path d="{poly(PC["wing_l"])}" fill="{COBALT}"/><path d="{poly(PC["wing_r"])}" fill="{SKY}"/><path d="{poly(PC["foot"])}" fill="#D9483B"/><path d="{poly(PC["counter"])}" fill="{INK}"/></svg>'),
         ("Outline it on screen", mark(INK, line=2)), ("Stretch it", mark(INK, COBALT, "transform:scaleX(1.35)")),
         ("Move the bar", f'<svg viewBox="-2 -2 104 104"><path d="{poly(HEX)}" fill="{INK}"/><path d="M50 -2L4 78M50 -2L96 78M20 40H80" stroke="#FBFAF6" stroke-width="9" fill="none"/></svg>'),
         ("Crowd it", f'<svg viewBox="-2 -2 104 104">{mark_paths(INK, COBALT)}<text x="50" y="58" text-anchor="middle" style="font:700 22px Arial" fill="#D9483B">NEW</text></svg>')]
logo = chapter_head("logo", 1, "A crystal with an A struck through it. It appears everywhere, from a 16 pixel browser tab to the front of a building, so it is drawn to be exact at both.",
    [("about", "About the mark"), ("lockup", "Primary lockup"), ("stacked", "Stacked"), ("symbol", "Symbol"), ("wordmark", "Wordmark"), ("construction", "Construction"),
     ("space", "Clear space and size"), ("small", "Small sizes"), ("family", "Our products"), ("others", "Working with others"), ("dont", "What not to do"), ("element", "As a design element")])
logo += sec("about", "About the mark", '<p class="lede">Five readings, each of them true, for anyone who looks for long enough.</p>',
    '<div class="four" style="grid-template-columns:repeat(5,minmax(0,1fr))">' + "".join(f'<figure><div class="tile">{s}</div><figcaption><b>{a}</b>{b}</figcaption></figure>' for a, b, s in READ) + '</div>')
logo += sec("lockup", "Primary lockup", '<p>The mark with the wordmark, for everything from the website header to a letterhead. The mark stands 1.42 cap heights tall, centred on the cap height, with 0.42 of a cap height between them.</p>',
    f'<div class="two"><figure><div class="tile wide">{lockup(INK, COBALT, "width:100%;height:auto")}</div><figcaption><b>Full colour, on paper</b>The gold in cobalt.</figcaption></figure>'
    f'<figure><div class="tile wide ink">{lockup(PAPER, SKY, "width:100%;height:auto")}</div><figcaption><b>Full colour, on ink</b>The gold in sky.</figcaption></figure>'
    f'<figure><div class="tile wide">{lockup(INK, INK, "width:100%;height:auto")}</div><figcaption><b>One colour, ink</b>For busy layouts and anything printed in one ink.</figcaption></figure>'
    f'<figure><div class="tile wide cob">{lockup(PAPER, INK, "width:100%;height:auto")}</div><figcaption><b>On cobalt</b>Paper, the gold in ink.</figcaption></figure></div>')
logo += sec("stacked", "Stacked", '<p>For square and tall spaces. Always centred on the page or the space it sits in.</p>',
    f'<div class="two"><figure><div class="tile">{stacked(INK, COBALT, "width:100%;height:auto")}</div></figure><figure><div class="tile ink">{stacked(PAPER, SKY, "width:100%;height:auto")}</div></figure></div>')
logo += sec("symbol", "Symbol", '<p>On its own wherever the name is already present or there is no room for it: avatars, app icons, the favicon, stamps.</p>',
    f'<div class="four"><figure><div class="tile">{mark(INK, COBALT)}</div><figcaption>On paper</figcaption></figure><figure><div class="tile ink">{mark(PAPER, SKY)}</div><figcaption>On ink</figcaption></figure>'
    f'<figure><div class="tile cob">{mark(PAPER, INK)}</div><figcaption>On cobalt</figcaption></figure><figure><div class="tile sky">{mark(INK, PAPER)}</div><figcaption>On sky, for rare use</figcaption></figure></div>')
logo += sec("wordmark", "Wordmark", '<p>Timeless Serif at weight 420, kerned as the font intends and tracked in 14 units. The dot of the i is a small triangle: the gold, in cobalt when colour is allowed. Use it alone where the symbol already appears nearby, such as a footer.</p>',
    f'<figure><div class="tile wide" style="aspect-ratio:3.4">{wordmark(INK, COBALT, "width:100%;height:auto")}</div></figure>')
logo += sec("construction", "Construction", "",
    f'<div class="two">{construction()}<div class="nums"><div><b>R 50</b><span>The hexagon\'s radius, on a 100 unit square. Every point is on it or found from it.</span></div>'
    f'<div><b>60°</b><span>The legs run from the top corner to the two lower side corners: an equilateral triangle. Nothing is drawn by eye.</span></div>'
    f'<div><b>W 9</b><span>Each strike is 9 units wide, just under a fifth of the radius.</span></div>'
    f'<div><b>¾</b><span>The bar is struck three quarters of the way down the A; the counter holds nine sixteenths of the triangle.</span></div>'
    f'<div><b>4</b><span>Pieces: two wings, the counter and the foot. Corners are softened by 0.4 units so they print and engrave cleanly.</span></div></div></div>')
logo += sec("space", "Clear space and size", f'<p>Keep the height of the counter, x, clear on every side of the mark and the lockup. Nothing else enters it: not type, not other marks, not the edge of the page.</p>',
    f'<div class="two">{cs_svg}<div class="nums"><div><b>x</b><span>The counter\'s height: {cs_x} units on the 100 unit drawing.</span></div>'
    f'<div><b>16 px</b><span>Smallest symbol on screen, using the drawn 16 pixel version.</span></div><div><b>96 px</b><span>Smallest lockup on screen.</span></div>'
    f'<div><b>6 mm</b><span>Smallest symbol in print; 24 mm for the lockup.</span></div></div></div>')
logo += sec("small", "Small sizes", '<p>Below 48 pixels the mark is not shrunk but drawn: every pixel of the 16 and 32 pixel versions was placed on the grid. These are the files in the favicon.</p>',
    f'<div class="two"><div style="display:flex;gap:16px;flex-wrap:wrap">{pixel_svg(PX["16"]).replace("<svg ", "<svg style=\"width:46%;height:auto;border:1px solid var(--rule)\" ", 1)}{pixel_svg(PX["32"]).replace("<svg ", "<svg style=\"width:46%;height:auto;border:1px solid var(--rule)\" ", 1)}</div>'
    f'<div style="display:flex;gap:24px;align-items:end;flex-wrap:wrap"><span style="display:grid;gap:6px;justify-items:center;font:11px var(--mono);color:var(--dim)">{pixel_svg(PX["16"], grid=False, size=16)}16</span>'
    f'<span style="display:grid;gap:6px;justify-items:center;font:11px var(--mono);color:var(--dim)">{pixel_svg(PX["32"], grid=False, size=32)}32</span>'
    f'<span style="display:grid;gap:6px;justify-items:center;font:11px var(--mono);color:var(--dim)">{mark(INK, COBALT, "width:48px;height:48px")}48</span>'
    f'<span style="display:grid;gap:6px;justify-items:center;font:11px var(--mono);color:var(--dim)">{mark(INK, COBALT, "width:96px;height:96px")}96</span></div></div>')
logo += sec("family", "Our products", '<p>Each product carries its own mark, cut from the same kind of metal: one solid block, one strike. Antimony stands beside it as its maker, never inside it.</p>',
    f'<div class="two"><figure><div class="tile wide" style="display:flex;gap:9%;justify-content:center">{mark(INK, COBALT, "width:30%;height:auto")}<img src="img/orbe-mark.png" alt="The Orbe mark" style="width:30%;height:auto"></div><figcaption><b>Antimony and Orbe</b>A crystal with its A struck through; a block with its orb struck out.</figcaption></figure>'
    f'<figure><div class="tile wide" style="display:flex;gap:14px;align-items:center;justify-content:center;flex-wrap:wrap"><img src="img/orbe-lockup.png" alt="The Orbe lockup" style="width:48%;height:auto;min-width:0"><span style="display:flex;align-items:center;gap:8px;font:400 15px var(--sans);color:var(--dim);border-left:1px solid var(--rule);padding-left:16px">{mark(INK, COBALT, "width:18px;height:18px")}by Antimony</span></div><figcaption><b>The endorsement</b>Where a product needs its maker named: the symbol at one cap height, set in Timeless Sans, after a hairline.</figcaption></figure></div>')
logo += sec("others", "Working with others", "<p>When our name appears with another company's, set the two apart at equal optical size with a hairline and clear space between them, and only where the relationship is real and agreed in writing. Never place a mark so that it implies one company endorses or partners with the other. Never join our mark to anyone else's.</p>", "")
logo += sec("dont", "What not to do", '<p>Beyond the usual rules for any mark (do not warp it, do not add effects), eight that belong to this one.</p>',
    '<div class="dont">' + "".join(f'<figure><div class="tile">{s}</div><figcaption>{t}</figcaption></figure>' for t, s in DONTS) + '</div>')
logo += sec("element", "As a design element", '<p>Two uses beyond the logo itself, and only these two. As a window, the four pieces cut from an archive plate. As a lattice, the mark tiled into Borges\'s library with one counter lit. Never both on one page, and never a third.</p>',
    f'<div class="two"><figure><div class="tile tall">{window("V0025578-two")}</div><figcaption><b>The window</b>The 1763 laboratory, seen through the crystal.</figcaption></figure>'
    f'<figure><div class="tile tall ink" style="padding:0;overflow:hidden">{lattice(5, 5, 100, lit=(2, 2), fill="#1B2321", gold=SKY, lit_fill=PAPER).replace("style=\"display:block\"", "style=\"display:block;width:100%;height:100%\" preserveAspectRatio=\"xMidYMid slice\"")}</div><figcaption><b>The lattice</b>One crystal in paper, one counter lit.</figcaption></figure></div>')
sizes["logo"] = write("logo", "Logo, Antimony Standards", logo, STRIKE_JS)

# ---------- 02 Typography ----------
SCALE = [("Display", 112, "serif", "1.0"), ("Headline 1", 84, "serif", "1.02"), ("Headline 2", 62, "serif", "1.04"), ("Headline 3", 46, "serif", "1.05"),
         ("Title", 34, "serif", "1.1"), ("Lede", 23, "serif", "1.45"), ("Body", 17, "sans", "1.55"), ("Small", 14, "sans", "1.5"), ("Label", 12, "mono", "1.2")]
AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ<br>abcdefghijklmnopqrstuvwxyz<br>0123456789 &amp; ! ? ( ) £ € %"
typ = chapter_head("type", 2, "Three faces, each with one job. Old enough to be trusted, cut well enough to be read at any size.", [("faces", "The faces"), ("scale", "Scale"), ("rules", "Using type"), ("languages", "Other languages")])
typ += sec("faces", "The faces", "",
    f'<div class="nums"><div><b>Primary</b><span><span style="font:400 48px/1.05 var(--serif);display:block;margin-bottom:10px">Timeless Serif</span>Headlines, the wordmark, ledes and anything said with conviction. Licensed to Antimony. Set it large and let it be quiet.<p class="spec" style="font-family:var(--serif);margin-top:14px">{AZ}</p></span></div>'
    f'<div><b>Secondary</b><span><span style="font:500 40px/1.05 var(--sans);display:block;margin-bottom:10px">Timeless Sans</span>Body text, interfaces, captions and anything read at length. Weights 400 and 500 only.<p class="spec" style="font-family:var(--sans);margin-top:14px">{AZ}</p></span></div>'
    f'<div><b>Tertiary</b><span><span style="font:400 34px/1.1 var(--mono);display:block;margin-bottom:10px">Commit Mono</span>Labels, figures, code and anything that has to line up. Open source.<p class="spec" style="font-family:var(--mono);font-size:clamp(17px,2.2vw,24px);margin-top:14px">{AZ}</p></span></div></div>')
typ += sec("scale", "Scale", '<p>Nine steps, on screen in pixels. In print, divide by 1.33 for points.</p>',
    '<div class="scroll"><table><thead><tr><th>Step</th><th class="num">Size</th><th class="num">Leading</th><th>Sample</th></tr></thead><tbody>' + "".join(
        f'<tr><th>{n}</th><td class="num">{s}</td><td class="num">{l}</td><td style="font:{"500" if fam == "mono" else "400"} {min(s, 62)}px/{l} var(--{fam});{"letter-spacing:.06em;text-transform:uppercase;" if fam == "mono" else ""}white-space:nowrap">Antimony</td></tr>' for n, s, fam, l in SCALE) + '</tbody></table></div>')
typ += sec("rules", "Using type", "",
    '<div class="nums"><div><b>Balance</b><span>Set the main headline either clearly larger or clearly smaller than the wordmark beside it, never the same size. Two things the same size compete.</span></div>'
    '<div><b>Grid</b><span>Twelve columns with 24 pixel gutters on screen, 5 mm in print. Type starts on a column.</span></div>'
    '<div><b>Break it</b><span>Once per layout, and only for a reason: a headline that hangs into the margin, a line that steps over a column. Never twice.</span></div>'
    '<div><b>Case</b><span>Sentence case everywhere, including headlines and buttons. Capitals only for Commit Mono labels, tracked out by 6 to 8 per cent.</span></div>'
    '<div><b>Figures</b><span>Tables and prices in Commit Mono or in tabular figures, so columns line up.</span></div>'
    '<div><b>Punctuation</b><span>British spelling. Curly quotation marks. No em or en dashes: a colon, a comma or a full stop does the work, and "to" for ranges.</span></div></div>')
typ += sec("languages", "Other languages", '<p>Timeless covers Latin scripts. For others, use Noto Serif and Noto Sans in the matching script, and Source Han Serif and Sans for Chinese, Japanese and Korean, set at the same optical size as the Latin beside them.</p>', "")
sizes["type"] = write("type", "Typography, Antimony Standards", typ)

# ---------- 03 Colour ----------
def rgb(h): return ", ".join(str(int(h[i:i + 2], 16)) for i in (1, 3, 5))
core = COL["core"]; ok = COL["oklch"]
ROLE = {"Ink": "Grounds, type, the mark", "Paper": "Grounds, type, the mark", "Cobalt": "The gold on paper; links", "Sky": "The gold on ink"}
col = chapter_head("colour", 3, "Ink and paper carry everything. Colour is kept for the gold: the part that is left when everything else has been taken away.", [("core", "Core colours"), ("scales", "Tones"), ("gold", "The gold"), ("contrast", "Contrast"), ("proportion", "Proportion")])
col += sec("core", "Core colours", "",
    '<div class="four">' + "".join(f'<div class="sw" style="background:{h};color:{INK if n in ("Paper", "Sky") else PAPER}"><b>{n}</b><span>{h}</span><span>RGB {rgb(h)}</span><span>OKLCH {ok[n][0]} {ok[n][1]} {ok[n][2]}</span><span>{ROLE[n]}</span></div>' for n, h in core.items()) + '</div>'
    '<p class="dim">These are screen values. For print, match each to a drawdown on the stock being used; do not convert by formula.</p>')
def ramp(name, sc):
    return (f'<figure><figcaption><b>{name}</b></figcaption><div class="ramp">' + "".join(
        f'<div style="background:{h};color:{INK if int(k) < 500 else PAPER}">{k}<br>{h}</div>' for k, h in sc.items()) + '</div></figure>')
col += sec("scales", "Tones", '<p>Two scales of ten, built in OKLCH so each step is an even step to the eye. Cobalt itself sits exactly at 600; paper is the neutral 50. Use tones for interfaces and charts; never for the mark.</p>', ramp("Cobalt", COL["cobalt"]) + ramp("Neutral", COL["neutral"]))
col += sec("gold", "The gold", '<p>One rule decides the only colour in the mark: the counter takes the gold of the ground it sits on.</p>',
    f'<div class="three"><figure><div class="tile">{mark(INK, COBALT)}</div><figcaption><b>On paper</b>Cobalt.</figcaption></figure><figure><div class="tile ink">{mark(PAPER, SKY)}</div><figcaption><b>On ink</b>Sky.</figcaption></figure><figure><div class="tile cob">{mark(PAPER, INK)}</div><figcaption><b>On cobalt</b>Ink.</figcaption></figure></div>')
col += sec("contrast", "Contrast", '<p>Every pairing, measured with the WCAG 2 formula.</p>',
    '<div class="scroll"><table><thead><tr><th>Ground</th><th>Colour</th><th class="num">Ratio</th><th>Use</th></tr></thead><tbody>' + "".join(
        f'<tr><td>{p["ground"]}</td><td><span style="display:inline-block;width:12px;height:12px;background:{core[p["colour"]]};border:1px solid var(--rule);vertical-align:-1px;margin-right:8px"></span>{p["colour"]}</td><td class="num">{p["ratio"]:.2f} : 1</td><td>{p["text"]}</td></tr>' for p in COL["pairs"]) +
    '</tbody></table></div><p class="dim">AAA and AA: any text. AA large: text above 24 pixels, and marks. Never: sky on paper is not used for anything.</p>')
pr = COL["proportion"]
col += sec("proportion", "Proportion", '<p>Across a body of work, roughly this much of each. The gold is rare on purpose.</p>',
    '<div class="prop">' + "".join(f'<div style="flex:{v};background:{core[k]};border-right:1px solid var(--rule)" title="{k} {v}%"></div>' for k, v in pr.items()) + '</div>'
    '<div style="display:flex;gap:20px;flex-wrap:wrap;font:400 13px var(--mono);color:var(--dim)">' + "".join(f'<span>{k} {v}%</span>' for k, v in pr.items()) + '</div>')
sizes["colour"] = write("colour", "Colour, Antimony Standards", col)

# ---------- 04 Art direction ----------
FAM = {"matter": "Matter", "method": "Method", "makers": "Makers"}
plates_by = {k: [s for s in SRC if s["family"] == k] for k in FAM}
art = chapter_head("art", 4, "We do not make pictures of the future. We stand on four hundred years of people making things, and print it again in our own ink.", [("archive", "The archive"), ("treatment", "The print"), ("window", "The window"), ("bloom", "The ink bloom"), ("rules", "Rules"), ("sources", "Sources")])
art += sec("archive", "The archive", '<p>Engravings from the Wellcome Collection, all in the public domain, in three families. Matter: crystals, minerals, the old symbols. Method: laboratories, furnaces, the table of what bonds with what. Makers: people at work with their hands.</p>',
    "".join(f'<h3>{FAM[k]}</h3><div class="plates">' + "".join(f'<img src="plates/{s["id"]}-two.webp" alt="{s["title"][:110]}" loading="lazy">' for s in plates_by[k][:4]) + '</div>' for k in FAM))
art += sec("treatment", "The print", '<p>Every plate is printed as if on a two drum risograph: ink for the engraved line, cobalt for the tone, a hair out of register, with the grain of a real print. Four printings.</p>',
    '<div class="four">' + "".join(f'<figure><img class="shot" src="plates/V0025147EL-{v}.webp" alt="" loading="lazy"><figcaption><b>{n}</b>{d}</figcaption></figure>' for v, n, d in [
        ("two", "Two colour", "The default."), ("ink", "Ink", "For one colour print and quiet pages."), ("cobalt", "Cobalt", "For a single loud moment."), ("night", "Night", "On ink. Diagrams and matter only; never people.")]) + '</div>')
art += sec("window", "The window", '<p>The mark\'s four pieces cut from a plate, the counter left as gold. The one way imagery and the mark meet.</p>',
    f'<div class="three"><figure><div class="tile tall">{window("V0025578-two")}</div><figcaption>The laboratory, 1763.</figcaption></figure><figure><div class="tile tall">{window("V0039777EL-ink")}</div><figcaption>The gold beater.</figcaption></figure><figure><div class="tile tall ink">{window("V0025147ER-night", SKY, PAPER)}</div><figcaption>Crystallography, 1802, night.</figcaption></figure></div>')
art += sec("bloom", "The ink bloom", '<p>Plates change by spreading into each other like ink into paper, leaving a thin ink line at the edge. It is two still images and a shader, not a video. Tap it.</p>',
    '<div class="bloom"><canvas aria-label="Archive plates changing with an ink bloom"></canvas><span class="hint">Tap to bloom</span></div>')
art += sec("rules", "Rules", "",
    '<div class="nums"><div><b>Credit</b><span>Every plate carries its credit: title, date if known, and "Wellcome Collection, public domain".</span></div>'
    '<div><b>People</b><span>Never colourise a person, never print a person night side, never let a strike cross a face.</span></div>'
    '<div><b>Truth</b><span>Never make new pictures that imitate the archive and present them as old. If we commission work, it is credited as ours.</span></div>'
    '<div><b>One</b><span>One plate per layout. The archive is a source, not a collage.</span></div></div>')
art += sec("sources", "Sources", f'<p>{len(SRC)} plates, each from the Wellcome Collection under the Public Domain Mark.</p>',
    '<div class="scroll"><table><thead><tr><th>Family</th><th>Plate</th><th>Reference</th></tr></thead><tbody>' + "".join(
        f'<tr><td>{FAM[s["family"]]}</td><td>{s["title"][:120]}</td><td class="num"><a href="{s["work"]}">{s["id"]}</a></td></tr>' for s in SRC) + '</tbody></table></div>')
sizes["art"] = write("art", "Art direction, Antimony Standards", art, bloom_js(["V0025578-two", "V0040548ETR-two", "V0025147EL-two", "V0039777EL-ink"]))

# ---------- 05 Motion ----------
mot = chapter_head("motion", 5, "Nothing is drawn on. It is cut out, struck, and what is left lights up.", [("strike", "The strike"), ("film", "The film"), ("timing", "Timing"), ("rules", "Rules")])
mot += sec("strike", "The strike", '<p>A solid crystal, struck three times: the left leg, the right leg, the bar. Then the counter turns to gold. Every reveal, loader and transition in the system is a strike. Tap it.</p>',
    f'<button class="restrike" style="all:unset;cursor:pointer;display:block" aria-label="Strike the mark again">{strike_svg(PAPER, INK, COBALT)}</button>')
mot += sec("film", "The film", '<p>Six seconds, for the start and end of films, talks and posts. Square and 16 by 9 versions are in the kit.</p>',
    '<video src="img/strike-1920x1080.mp4" autoplay muted loop playsinline aria-label="The strike film"></video>', ink=True)
TIM = [("Strike", "320 ms", "cubic-bezier(.65, 0, .35, 1)", "Each cut: fast through the middle, firm at the ends."), ("Between strikes", "130 ms", "", "A beat, so each strike is heard."),
       ("Gold", "600 ms", "cubic-bezier(.2, .7, .2, 1)", "The counter lights, and settles."), ("Ink bloom", "2600 ms", "ease out, power 1.7", "Plates change."),
       ("Interface", "180 to 240 ms", "cubic-bezier(.2, .7, .2, 1)", "Hovers, menus, small changes."), ("Page", "480 ms", "cubic-bezier(.65, 0, .35, 1)", "Between pages; never longer.")]
mot += sec("timing", "Timing", "", '<div class="scroll"><table><thead><tr><th>Move</th><th class="num">Duration</th><th class="num">Easing</th><th>Why</th></tr></thead><tbody>' + "".join(
    f'<tr><th>{a}</th><td class="num">{b}</td><td class="num">{c}</td><td>{d}</td></tr>' for a, b, c, d in TIM) + '</tbody></table></div>')
mot += sec("rules", "Rules", "", '<div class="nums"><div><b>Once</b><span>A strike plays once per visit. It is never a loop, except as a loader.</span></div><div><b>Still</b><span>With reduced motion on, show the final frame.</span></div><div><b>No bounce</b><span>Nothing overshoots, wobbles or springs. Metal does not bounce.</span></div></div>')
sizes["motion"] = write("motion", "Motion, Antimony Standards", mot, STRIKE_JS)

# ---------- 06 Voice ----------
PAIRS = [("Revolutionising the creator economy with AI.", "Orbe holds the money until the work is delivered."), ("Seamless, end to end brand partnerships.", "Every deal in one place: the brief, the contract, the payment."),
         ("We're on a mission to empower creators!", "We sit on the creator's side of the table."), ("Leverage our cutting edge platform to unlock value.", "Send a brief. Get paid when the work is done.")]
voice = chapter_head("voice", 6, "Plain, exact and on their side. We write the way a good craftsperson talks about their work.", [("principles", "How we write"), ("pairs", "Before and after"), ("words", "Words"), ("names", "Names")])
voice += sec("principles", "How we write", "", '<div class="nums"><div><b>Plain</b><span>Short sentences, common words. If a word needs explaining, choose another.</span></div><div><b>Exact</b><span>Say what happens: who pays whom, when, for what. A number beats an adjective.</span></div>'
    '<div><b>On their side</b><span>Write from the creator\'s side of the screen, about their work, in their terms.</span></div><div><b>Calm</b><span>No exclamation marks, no hype, no countdowns. Confidence is quiet.</span></div><div><b>British</b><span>British spelling and punctuation; no em or en dashes.</span></div></div>')
voice += sec("pairs", "Before and after", "", "".join(f'<div class="do"><div><span class="k">Not this</span><span>{a}</span></div><div class="yes"><span class="k">This</span><span>{b}</span></div></div>' for a, b in PAIRS))
voice += sec("words", "Words", "", '<div class="two"><div class="nums"><div><b>Use</b><span>work, make, deal, brief, paid, on time, yours, together</span></div></div><div class="nums"><div><b>Avoid</b><span>revolutionise, seamless, leverage, unlock, empower, game changing, ecosystem, operating system</span></div></div></div>')
voice += sec("names", "Names", '<p>Antimony is the company. Orbe is our first product. Write "Antimony, makers of Orbe" where both are needed. Never call either an operating system. Describe other companies and their products factually, and never suggest a partnership or endorsement that does not exist in writing.</p>', "")
sizes["voice"] = write("voice", "Voice, Antimony Standards", voice)

# ---------- 07 Brand in use ----------
use = chapter_head("use", 7, "Where people meet Antimony first. Every image here is an export in the kit, at the size the platform asks for.", [("linkedin", "LinkedIn"), ("social", "Social"), ("deck", "Presentations"), ("print", "Print"), ("web", "Web and app"), ("email", "Email")])
use += sec("linkedin", "LinkedIn", "", f'<div class="profile"><img class="ban" src="img/linkedin-company-cover.webp" alt="Company cover"><div class="body"><img class="av" src="img/avatar-ink.webp" alt="Avatar"><b>Antimony</b><span>Software for the people who make the work.</span></div></div>'
    f'<figure><img class="shot" src="img/linkedin-personal-banner.webp" alt="Personal banner" loading="lazy"><figcaption><b>Personal banner</b>1584 by 396. The left stays quiet for the profile photo; one crystal is lit.</figcaption></figure>')
use += sec("social", "Social", "", f'<div class="three"><figure><img class="shot" src="img/post-mark.webp" alt="" loading="lazy"><figcaption><b>The mark</b>1080 square.</figcaption></figure><figure><img class="shot" src="img/post-archive.webp" alt="" loading="lazy"><figcaption><b>From the archive</b>1080 by 1350, the window.</figcaption></figure><figure><img class="shot" src="img/og-image.webp" alt="" loading="lazy"><figcaption><b>Link card</b>1200 by 630.</figcaption></figure></div>'
    f'<figure><img class="shot" src="img/x-header.webp" alt="X header" loading="lazy"><figcaption><b>X header</b>1500 by 500.</figcaption></figure>')
use += sec("deck", "Presentations", "", f'<div class="three"><figure><img class="shot" src="img/01-title.webp" alt="" loading="lazy"><figcaption><b>Title</b></figcaption></figure><figure><img class="shot" src="img/02-content.webp" alt="" loading="lazy"><figcaption><b>Content</b>One plate, one idea.</figcaption></figure><figure><img class="shot" src="img/03-close.webp" alt="" loading="lazy"><figcaption><b>Close</b></figcaption></figure></div>')
use += sec("print", "Print", "", f'<div class="three"><figure><img class="shot" src="img/card-front.webp" alt="" loading="lazy"><figcaption><b>Card, front</b>85 by 55 mm.</figcaption></figure><figure><img class="shot" src="img/card-back.webp" alt="" loading="lazy"><figcaption><b>Card, back</b></figcaption></figure><figure><img class="shot" src="img/letterhead.webp" alt="" loading="lazy" style="max-width:260px"><figcaption><b>Letterhead</b>A4.</figcaption></figure></div>')
use += sec("web", "Web and app", "", f'<div class="two"><figure><div><span class="tab"><img src="img/favicon-16.png" width="16" height="16" alt="">Antimony</span><div style="height:110px;background:#fff;border:1px solid var(--rule)"></div></div><figcaption><b>The favicon</b>The drawn 16 pixel mark in a browser tab.</figcaption></figure>'
    f'<figure><img class="shot" src="img/app-512.webp" alt="" loading="lazy" style="max-width:180px;border-radius:40px"><figcaption><b>App icon</b>The mark on ink, inside the platform mask.</figcaption></figure></div>')
use += sec("email", "Email", "", f'<div class="sig"><b style="font-weight:700">Name Surname</b><br>Antimony, makers of Orbe<br><span style="color:#666">name@antimony.inc</span><div style="margin-top:12px">{lockup(INK, COBALT, "height:18px;width:auto")}</div></div><p class="dim">Plain text with the lockup at 18 pixels. No banners, no quotes, no social icons.</p>')
sizes["use"] = write("use", "Brand in use, Antimony Standards", use)

# ---------- 08 Downloads ----------
FILES = [("logo/", "The mark, lockup, stacked lockup and wordmark, on paper, ink and cobalt, as PNG at up to 2400 px."), ("icons/", "favicon.svg, favicon.ico with the drawn 16 and 32 px, and app icons at 180, 192, 512 and 1024."),
         ("social/", "Avatars, LinkedIn company cover and personal banner, X header, the link card and two posts."), ("deck/", "Title, content and closing slides at 1920 by 1080."),
         ("print/", "Business card front and back, and letterhead, as PDF at true size with bleed."), ("motion/", "The strike film, square and 16 by 9, MP4."),
         ("source", "The geometry the whole system is drawn from, so any of it can be rebuilt exactly.")]
dl = chapter_head("downloads", 8, "Everything on these pages, as files.", [("kit", "The kit")])
dl += sec("kit", "The kit", '<p>The kit is sent as one archive. Ask for it from the brand owner; the folders are:</p>', '<div class="files">' + "".join(f'<div><code>{a}</code><span>{b}</span></div>' for a, b in FILES) + '</div>')
sizes["downloads"] = write("downloads", "Downloads, Antimony Standards", dl)
print(sizes)
