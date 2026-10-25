"""Writes ../../x/home-pebble/index.html: the Antimony home page, after Pebblebed and Zeromatter. Plain words, one picture."""
import os, sys, random
sys.path.insert(0, os.path.dirname(__file__))
from prism2 import M, crystal, P
from kit import WM, WM_Y0, WM_Y1
INK, COB, PAPER = "#1B1C1A", "#2448FF", "#EEECE6"
mk = lambda ink=INK, gold=COB, style="": M["prism_tip"][2](ink, gold, style)
word = f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="height:15px;width:auto;display:block" role="img" aria-label="Antimony"><path d="{WM["letters"]}" fill="{INK}"/><path d="{WM["dot"]}" fill="{INK}"/></svg>'
rng = random.Random(51)
noise = "".join(rng.choice(["·", ":", "▪", " ", " ", "▫", "⁘", "·", "▴"]) for _ in range(900))
MD = """# Antimony

Software for the people who make the work.

Creators do the work. Then they do the work around the work: the briefs, the contracts, the invoices, the chasing. We build software that takes the second part away, so what is left is theirs.

Our first product is [Orbe](https://eoinforker.github.io/orbe-site/), the creator's side of every sponsorship deal. It holds the money until the work is delivered.

Antimony is a metal. It was used to refine gold: melted with it, it took up everything that was not gold. Alchemists called it the wolf of metals. We liked that.
"""
html = f'''<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Antimony</title><meta name="claude:viewport-fit-sides" content="cover">
<style>
/* After Pebblebed and Zeromatter: warm grey paper, a mono for structure and a serif for voice, one rendered picture, plain words. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --paper: {PAPER}; --ink: {INK}; --dim: #6C6B66; --cob: {COB}; --rule: rgba(27,28,26,.12); color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 13.5px/1.6 "Commit Mono", ui-monospace, Menlo, monospace; -webkit-font-smoothing: antialiased; }}
a {{ color: var(--cob); text-decoration: none; }} a:hover {{ text-decoration: underline; text-underline-offset: 3px; }}
:focus-visible {{ outline: 1px solid var(--cob); outline-offset: 3px; }}
.wrap {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
header {{ display: flex; justify-content: space-between; align-items: start; gap: 20px; padding-block: 22px 0; }}
.brand {{ display: grid; gap: 4px; }}
.brand h1 {{ font: 400 clamp(22px, 2.2vw, 28px)/1.1 "Timeless Serif", Georgia, serif; letter-spacing: -.01em; }}
.brand span {{ color: var(--dim); }}
.lock {{ display: flex; align-items: center; gap: 8px; }} .lock .m {{ width: 16px; height: 16px; display: block; }}
nav {{ display: grid; gap: 2px; text-transform: uppercase; letter-spacing: .04em; font-size: 12px; justify-items: start; margin-top: 18px; }}
nav a {{ color: var(--ink); }}
.cols {{ display: grid; grid-template-columns: repeat(3, minmax(0, 18em)); gap: 32px; padding-block: 64px 40px; padding-left: clamp(0px, 4vw, 60px); }}
.cols p {{ max-width: 34ch; }}
.ask {{ font: 400 clamp(19px, 1.8vw, 23px)/1.4 "Timeless Serif", Georgia, serif; padding-left: clamp(0px, 4vw, 60px); padding-bottom: 56px; max-width: 40em; }}
.hero {{ position: relative; margin-inline: max(16px, env(safe-area-inset-left, 0px)) max(16px, env(safe-area-inset-right, 0px)); border-radius: 14px; overflow: hidden; aspect-ratio: 2400 / 1400; max-width: 100%; background: #14110E; }}
.hero img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.hero .t {{ position: absolute; left: 4%; bottom: 8%; right: 40%; color: #EDE6D6; transition: opacity .4s ease; }}
.hero .t b {{ display: block; font: 400 clamp(26px, 3.6vw, 52px)/1.05 "Timeless Serif", Georgia, serif; letter-spacing: -.015em; }}
.hero .t b em {{ font-style: normal; color: #9BE7FF; }}
.hero.hide .t {{ opacity: 0; }}
.hero button {{ position: absolute; right: 2.2%; bottom: 5%; font: inherit; font-size: 12px; color: #EDE6D6; background: rgba(20,17,14,.55); border: 1px solid rgba(237,230,214,.25); border-radius: 30px; padding: 6px 12px; cursor: pointer; }}
.cap {{ color: var(--dim); padding: 10px max(16px, env(safe-area-inset-left, 0px)) 0; padding-left: calc(max(16px, env(safe-area-inset-left, 0px)) + 4px); }}
.facts {{ display: grid; grid-template-columns: 9em minmax(0, 1fr); gap: 0; padding-block: 64px; padding-left: clamp(0px, 4vw, 60px); max-width: 860px; }}
.facts h2 {{ grid-column: 1 / -1; font: 400 26px/1.1 "Timeless Serif", Georgia, serif; margin-bottom: 14px; }}
.facts span {{ padding: 9px 0; border-top: 1px solid var(--rule); }} .facts span:nth-child(even) {{ color: var(--dim); text-transform: uppercase; font-size: 11.5px; letter-spacing: .05em; padding-top: 11px; }}
footer {{ padding-block: 40px 28px; }}
.noise {{ color: #A8A69F; font-size: 11px; line-height: 1.15; letter-spacing: .1em; overflow: hidden; height: 3.5em; word-break: break-all; }}
.fine {{ display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-top: 14px; color: var(--dim); font-size: 12px; }}
.fine button {{ font: inherit; color: var(--cob); background: none; border: 0; padding: 0; cursor: pointer; text-transform: uppercase; letter-spacing: .05em; }}
.fine button[aria-pressed="true"] {{ color: var(--ink); text-decoration: underline; }}
#md {{ white-space: pre-wrap; font: 400 14px/1.65 "Commit Mono", monospace; max-width: 72ch; padding-block: 40px; }}
body.md main {{ display: none; }} body:not(.md) #md {{ display: none; }}
@media (max-width: 820px) {{ .hero button {{ top: 4%; bottom: auto; }} .cols {{ grid-template-columns: 1fr; gap: 18px; padding-block: 40px 28px; }} .hero .t {{ right: 6%; }} .facts {{ grid-template-columns: 7.5em minmax(0, 1fr); }} }}
@media (prefers-reduced-motion: reduce) {{ .hero .t {{ transition: none; }} }}
</style></head><body>
<div class="wrap"><header>
  <div class="brand"><h1>Antimony.</h1><span>Software for the people who make the work.</span></div>
  <div style="display:grid;justify-items:end"><span class="lock">{mk(style="width:16px;height:16px;display:block")}{word}</span>
  <nav aria-label="Main"><a href="https://eoinforker.github.io/orbe-site/">Orbe</a><a href="#facts">About</a><span style="color:var(--dim)">Letters, soon</span></nav></div>
</header></div>
<main>
  <div class="wrap"><div class="cols">
    <p>Creators do the work. Then they do the work around the work: the briefs, the contracts, the invoices, the chasing. We build software that takes the second part away.</p>
    <p>Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator's side of every sponsorship deal. It holds the money until the work is delivered.</p>
    <p>Antimony is a metal. It was used to refine gold: melted with it, it took up everything that was not gold. Alchemists called it the wolf of metals. We liked that.</p>
  </div>
  <p class="ask">What is left, once the work around the work is gone, is yours.</p></div>
  <div class="hero" id="hero"><img src="img/hero.webp" alt="A spray of stibnite crystals, antimony's ore, rendered and lit warm from the left"><div class="t"><b>Take away everything that is not <em>the work</em>.</b></div><button type="button" id="hide" aria-pressed="false">Hide text</button></div>
  <p class="cap">Yes, this is a rendered crystal. Stibnite, antimony's ore, really does grow like this.</p>
  <div class="wrap"><div class="facts" id="facts"><h2>Facts</h2>
    <span>Element</span><span>51, Sb, from the Latin stibium</span>
    <span>Found as</span><span>Stibnite, long grey prisms with pointed tips</span>
    <span>Used for</span><span>Refining gold, for about as long as people have refined gold</span>
    <span>Rarely</span><span>Found alone</span>
    <span>We make</span><span><a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, and what comes after it</span>
  </div></div>
</main>
<div class="wrap" id="md" aria-label="This page as Markdown">{MD}</div>
<div class="wrap"><footer><div class="noise" aria-hidden="true">{noise}</div>
  <div class="fine"><span>© 2026 Antimony</span><span><button type="button" id="b-render" aria-pressed="true">Render</button> / <button type="button" id="b-md" aria-pressed="false">Markdown</button></span></div></footer></div>
<script>
(() => {{ "use strict";
  const hero = document.getElementById("hero"), hb = document.getElementById("hide");
  hb.addEventListener("click", () => {{ const on = hero.classList.toggle("hide"); hb.textContent = on ? "Show text" : "Hide text"; hb.setAttribute("aria-pressed", on); }});
  const r = document.getElementById("b-render"), m = document.getElementById("b-md");
  const set = md => {{ document.body.classList.toggle("md", md); r.setAttribute("aria-pressed", !md); m.setAttribute("aria-pressed", md); }};
  r.addEventListener("click", () => set(false)); m.addEventListener("click", () => set(true));
}})();
</script></body></html>'''
open("../../x/home-pebble/index.html", "w").write(html); print(len(html))
