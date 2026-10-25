"""Writes /home/user/antimony-site/index.html. One screen. The stone at the scale of a building, running off the edge of the
page, a print seen through the crystal, and a few lines of type."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from three import break_parts, CONT
HERE = os.path.dirname(os.path.abspath(__file__))
Q = break_parts()
vb, WMB = open(os.path.join(HERE, "../../x/edge/wm.txt")).read().split("\n", 1)
INK, PAPER, SKY = "#0B0C0C", "#EEEAE0", "#94E6FF"
PRINT = "18972"   # Hiroshige, Autumn Moon over Ishiyama Temple, 1857

stone = f'''<svg class="stone" viewBox="0 0 100 100" aria-hidden="true">
<defs>
  <clipPath id="t">{CONT["tile"]}</clipPath><clipPath id="g"><path d="{Q["gem"]}"/></clipPath>
  <mask id="m"><rect width="100" height="100" fill="#fff"/><path d="{Q["seam"]}" fill="#000"/><path d="{Q["cav"]}" fill="#000"/></mask>
  <filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="2.4" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .05 0"/><feComposite in2="SourceGraphic" operator="in"/></filter>
  <linearGradient id="fall" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1C1B19"/><stop offset=".55" stop-color="#141311"/><stop offset="1" stop-color="#0F0F0E"/></linearGradient>
</defs>
<g clip-path="url(#t)">
  <g mask="url(#m)"><rect width="100" height="100" fill="url(#fall)"/><rect width="100" height="100" fill="#fff" filter="url(#grain)"/></g>
  <g clip-path="url(#g)"><g class="print"><image href="assets/prints/{PRINT}.webp" x="24" y="14" width="52" height="76.4" preserveAspectRatio="xMidYMid slice"/></g>
    <path d="{Q["facet"]}" fill="#fff" fill-opacity=".07"/></g>
</g>
</svg>'''

html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{INK}"><meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: {INK}; height: 100%; }}
body {{ color: {PAPER}; font: 400 17px/1.55 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; overflow: hidden; }}
a {{ color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .22em; text-decoration-color: rgba(238,234,224,.3); transition: text-decoration-color .3s ease; }}
a:hover {{ text-decoration-color: currentColor; }}
:focus-visible {{ outline: 1px solid {SKY}; outline-offset: 4px; }}
::selection {{ background: {SKY}; color: {INK}; }}
/* the stone, at the scale of a building: taller than the screen, its right side off the page */
.stone {{ position: fixed; height: 132vh; width: 132vh; top: -17vh; left: calc(74vw - 66vh); display: block; }}
.print {{ transition: transform 2.4s cubic-bezier(.2,.7,.2,1); transform-origin: 50px 52px; }}
.page {{ position: relative; height: 100%; display: grid; grid-template-rows: auto 1fr auto; padding: max(34px, env(safe-area-inset-top, 0px)) 0 max(30px, env(safe-area-inset-bottom, 0px)); padding-inline: max(48px, env(safe-area-inset-left, 0px)) max(48px, env(safe-area-inset-right, 0px)); }}
header svg {{ height: 22px; width: auto; display: block; color: {PAPER}; --lit: {SKY}; }}
main {{ align-self: center; max-width: 25em; }}
h1 {{ font-weight: 400; font-size: clamp(36px, 3.8vw, 60px); line-height: 1.04; letter-spacing: -.022em; text-wrap: balance; margin-bottom: 30px; }}
main p {{ color: rgba(238,234,224,.66); max-width: 23em; text-wrap: pretty; }} main p + p {{ margin-top: .7em; }}
footer {{ display: flex; gap: 36px; font-size: 14px; color: rgba(238,234,224,.42); }}
footer .credit {{ margin-left: auto; text-align: right; max-width: 26em; }}
@media (max-width: 760px) {{
  body {{ overflow: auto; }}
  .stone {{ height: 118vw; width: 118vw; top: -8vw; left: 12vw; position: absolute; }}
  .page {{ min-height: 100%; height: auto; padding-inline: 24px; grid-template-rows: auto 1fr auto; }}
  main {{ align-self: end; padding-top: 92vw; margin-bottom: 44px; }}
  h1 {{ font-size: 36px; margin-bottom: 20px; }}
  footer {{ flex-wrap: wrap; gap: 8px 24px; }} footer .credit {{ margin-left: 0; text-align: left; flex-basis: 100%; }}
}}
@media (prefers-reduced-motion: reduce) {{ .print {{ transition: none; }} }}
</style></head>
<body>
{stone}
<div class="page">
  <header><svg viewBox="{vb}" role="img" aria-label="Antimony">{WMB}</svg></header>
  <main>
    <h1>Software for the people who make the work.</h1>
    <p>Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator&#39;s side of every sponsorship deal.</p>
    <p>We sit on their side of the table, and we mean to stay there for a long time.</p>
  </main>
  <footer><span>London</span><a href="https://eoinforker.github.io/orbe-site/">Orbe</a><span class="credit">In the stone: Utagawa Hiroshige, <i>Autumn Moon over Ishiyama Temple</i>, 1857. Art Institute of Chicago.</span></footer>
</div>
<script>
// the print sits behind the crystal like a view through glass: it shifts a little, the other way, as you move
(() => {{ if (matchMedia("(prefers-reduced-motion: reduce)").matches || !matchMedia("(pointer: fine)").matches) return;
  const p = document.querySelector(".print");
  addEventListener("pointermove", e => {{ const x = e.clientX / innerWidth - .5, y = e.clientY / innerHeight - .5; p.style.transform = `translate(${{-x * 1.4}}px, ${{-y * 1.4}}px) scale(1.04)`; }});
}})();
</script>
</body></html>'''
open(os.path.join(HERE, "../../index.html"), "w").write(html); print(len(html))
