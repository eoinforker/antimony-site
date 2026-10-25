"""Writes ../wide/index.html: the 64 thumbnails, numbered, for choosing."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from wide import T
ROOTS = {"Refining": "Antimony purified gold: everything reduced until the gold is left.",
         "The wolf": "Alchemists called antimony the wolf of metals: it devoured the dross so the king, gold, came out pure.",
         "Metal": "Ingots and hallmarks: the stamp that proves a metal is pure.",
         "The library": "Borges's library of hexagons; books that lean on each other.",
         "Crystal": "Stibnite's needles, the lattice, antimony's layered structure.",
         "Monograms": "A, Sb and 51.",
         "Fire": "The athanor: the furnace that never goes out.",
         "Emblems": "Power without menace: enclosed, symmetric, few parts."}
secs = ""; n = 0
for name, items in T:
    cells = ""
    for it in items:
        n += 1; cells += f'<figure><div class="m">{it}</div><figcaption>{n}</figcaption></figure>'
    secs += f'<section><div class="h"><h2>{name}</h2><p>{ROOTS[name]}</p></div><div class="g">{cells}</div></section>'
html = f'''<title>Antimony, Sixty Four</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* A contact sheet: every thumbnail the same size, the same ink, numbered, so the drawing is judged on its own. */
:root {{ --ink: #0B0D0C; --paper: #F4F3EE; --rule: rgba(11,13,12,.12); --dim: #5C6461; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 15px/1.5 "Helvetica Neue", Arial, sans-serif; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 40px 64px; }}
.in {{ max-width: 1160px; margin-inline: auto; display: grid; gap: 34px; }}
h1 {{ font: 400 clamp(32px, 5vw, 56px)/1.02 Georgia, serif; letter-spacing: -.015em; max-width: 16em; text-wrap: balance; }}
header p {{ max-width: 40em; color: var(--dim); margin-top: 12px; }}
section {{ display: grid; gap: 14px; border-top: 1px solid var(--rule); padding-top: 18px; }}
.h {{ display: flex; gap: 16px; align-items: baseline; flex-wrap: wrap; }}
h2 {{ font: 600 14px/1.2 ui-monospace, Menlo, monospace; letter-spacing: .06em; text-transform: uppercase; }}
.h p {{ color: var(--dim); font-size: 14px; }}
.g {{ display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 12px; }}
figure {{ display: grid; gap: 6px; justify-items: center; min-width: 0; }}
.m {{ width: 100%; aspect-ratio: 1; max-width: 100%; background: #FBFAF6; border: 1px solid var(--rule); padding: 16%; }}
.m svg {{ width: 100%; height: 100%; display: block; }}
figcaption {{ font: 600 12px ui-monospace, Menlo, monospace; color: var(--dim); font-variant-numeric: tabular-nums; }}
@media (max-width: 760px) {{ .g {{ grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }} }}
</style>
<div class="in">
  <header><h1>Sixty four roughs. Pick the ones with a pulse.</h1>
  <p>Eight territories, eight each. All rough, all the same size and ink, no colour and no stories, so you are judging the drawing alone. Send me the numbers that have any life in them, even partly, and anything you would combine. Only those get refined.</p></header>
  {secs}
</div>'''
open("../wide/index.html", "w").write(html); print(n)
