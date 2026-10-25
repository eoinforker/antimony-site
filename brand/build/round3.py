"""Writes ../round3/index.html: three marks held to one test, shown in the places they will live."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from kit import G, WM, WM_Y0, WM_Y1
INK, PAPER, COBALT, SKY = "#0B0D0C", "#F4F3EE", "#2448FF", "#94E6FF"
N = [0]
def uid(): N[0] += 1; return N[0]
# The And: one stroke at 45 and 90 degrees, a diamond loop with an atom in it, an octagonal bowl, a crossing tail
AND1, AND2 = "M90 96 L38 44 L52 30 L38 16 L24 30 L36 42", "M36 42 L18 60 L18 78 L34 94 L56 94 L86 64"
def and_svg(fill=INK, gem=COBALT, sw=9.5, style=""):
    i = uid(); g = f'<path d="M38 23L45 30L38 37L31 30Z" fill="{gem}"/>' if gem else ""
    return (f'<svg viewBox="8 6 88 92" style="{style}" aria-hidden="true"><defs><clipPath id="a{i}"><rect x="0" y="0" width="100" height="94"/></clipPath></defs>'
            f'<g clip-path="url(#a{i})" fill="none" stroke="{fill}" stroke-width="{sw}" stroke-linejoin="miter" stroke-miterlimit="10"><path d="{AND1}"/><path d="{AND2}"/></g>{g}</svg>')
def arch_svg(fill=INK, tie=None, sw=11, style=""):
    foot, top, base, ty = 14, 5, 95, 62; span = 50 - foot; h = base - top
    cx = (span * span + h * h) / (2 * span) + foot; r = cx - foot; xl = cx - math.sqrt(r * r - (base - ty) ** 2)
    return (f'<svg viewBox="0 0 100 100" style="{style}" aria-hidden="true"><path d="M{foot} {base} A{r:.2f} {r:.2f} 0 0 1 50 {top} A{r:.2f} {r:.2f} 0 0 1 {100-foot} {base}" fill="none" stroke="{fill}" stroke-width="{sw}" stroke-linejoin="miter" stroke-miterlimit="30"/>'
            f'<path d="M{xl - sw/2 + 1:.2f} {ty}H{100 - xl + sw/2 - 1:.2f}" stroke="{tie or fill}" stroke-width="{sw - 1}"/></svg>')
def bondline_svg(fill=INK, nuc=COBALT, bg=PAPER, sw=5, style=""):
    A = G["atoms"]; R = G["R"] - 1
    lines = "".join(f'<path d="M{A[a][0]} {A[a][1]}L{A[b][0]} {A[b][1]}"/>' for a, b in G["bonds"])
    d = "".join(f'<path d="M{x} {y-R}L{x+R} {y}L{x} {y+R}L{x-R} {y}Z"/>' for k, (x, y) in A.items() if k != "nucleus")
    x, y = A["nucleus"]
    return (f'<svg viewBox="0 0 100 100" style="{style}" aria-hidden="true"><g fill="{bg}" stroke="{fill}" stroke-width="{sw}" stroke-linejoin="miter">{lines}{d}</g>'
            f'<path d="M{x} {y-R}L{x+R} {y}L{x} {y+R}L{x-R} {y}Z" fill="{nuc}"/></svg>')
def wm(fill=INK, dot=None, style=""):
    return (f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="{style}" role="img" aria-label="Antimony">'
            f'<path d="{WM["letters"]}" fill="{fill}"/><path d="{WM["dot"]}" fill="{dot or fill}"/></svg>')
def avatar(inner, bg, pad="16%"): return f'<span class="av" style="background:{bg};padding:{pad}">{inner}</span>'
def row(av, name): return f'<div class="row">{av}<div><b>{name}</b><span>Software Development</span></div></div>'
GHOST = '<div class="row ghost"><span class="av"></span><div><b></b><span></span></div></div>'
def tattoo(svg_inner):
    return f'<div class="skin">{svg_inner}</div>'
def pattern_and():
    cells = ""
    for j in range(5):
        for i in range(9):
            lit = (i, j) == (6, 2)
            cells += f'<span>{and_svg(INK if not lit else COBALT, COBALT if lit else None, style="width:100%")}</span>'
    return f'<div class="pat">{cells}</div>'

MARKS = [
 ("and", "The And", "Recommended",
  "Antimony is often read as anti monos: not alone. The oldest sign for not alone is the ampersand, first scratched as a joined e and t on the walls of Pompeii nearly two thousand years ago. Ours is drawn in one continuous line, on the same 45 degree lattice as a crystal, with a single atom held in its upper loop.",
  ["An and: never alone, in one character.", "The diamond: antimony's crystal, the atom at its heart.", "One line: a promise made without lifting the pen.", "Two thousand years old as a sign; new as a drawing."],
  and_svg, lambda: and_svg(SKY, PAPER, style="width:100%"), lambda: and_svg(PAPER, SKY, style="width:100%")),
 ("arch", "The Arch", "Alternative",
  "A lancet arch drawn as an A. Each side is an arc struck from the other side's foot, so neither stands without the other: the way cathedrals stood for eight hundred years. It reads as a doorway, which is the opposite of a fortress.",
  ["An A for Antimony.", "Two sides that hold each other up.", "A door: a way in for the people who make the work.", "Built the way things that last are built."],
  arch_svg, lambda: arch_svg(SKY, PAPER, style="width:100%"), lambda: arch_svg(PAPER, SKY, style="width:100%")),
 ("bond", "The Bond, in line", "Continuity",
  "The molecule from the last round, drawn at one line weight in the way Perplexity draws its mark. Lighter, more precise and less like an emblem than the solid version.",
  ["Five electrons around a nucleus.", "An A, or a person standing.", "A bond: a promise kept.", "A lattice that tiles into patterns."],
  bondline_svg, lambda: bondline_svg(SKY, PAPER, INK, style="width:100%"), lambda: bondline_svg(PAPER, SKY, COBALT, style="width:100%")),
]
TESTS = ["Drawn from memory after one look", "Reads in one colour", "Reads at 16 px", "Its meaning is true", "Feels hopeful, not ominous", "Nobody else's", "Could be tattooed in one sitting"]
SCORES = {"and": ["Yes", "Yes", "Yes", "Yes", "Yes", "Yes", "Yes, in one line"],
          "arch": ["Yes", "Yes", "Yes", "Yes", "Yes", "Partly: pointed A forms exist", "Yes"],
          "bond": ["Partly", "Yes", "Partly", "Yes", "Yes", "Yes", "Yes"]}

secs = ""
for key, name, tag, story, readings, svgf, av_ink, av_cob in MARKS:
    big = svgf(style="width:100%")
    secs += f'''
<section class="band{' lead' if key == 'and' else ''}" id="{key}"><div class="in">
  <div class="head"><span class="eyebrow">{tag}</span><h2>{name}</h2></div>
  <div class="two">
    <div class="hero">{big}</div>
    <div class="txt"><p class="lede">{story}</p><ol class="reads">{"".join(f"<li>{r}</li>" for r in readings)}</ol></div>
  </div>
  <div class="four">
    <figure><div class="tile ink">{av_ink()}</div><figcaption>Avatar: sky on ink.</figcaption></figure>
    <figure><div class="tile cob">{av_cob()}</div><figcaption>On cobalt.</figcaption></figure>
    <figure><div class="list">{row(avatar(av_ink(), INK, "7px"), "Antimony")}{GHOST}{GHOST}</div><figcaption>In a list, at real size.</figcaption></figure>
    <figure><div class="sizes">{"".join(f'<span style="width:{s}px">{svgf(style="width:100%")}</span>' for s in (16, 24, 32, 48))}</div><figcaption>16, 24, 32 and 48 px.</figcaption></figure>
  </div>
  <div class="two">
    <figure><div class="lock">{svgf(style="height:64px;width:auto")}{wm(INK, COBALT, "height:46px;width:auto")}</div><figcaption>With the wordmark.</figcaption></figure>
    <figure>{tattoo(svgf(fill="#23282A", **({"gem": None} if key == "and" else {"tie": None} if key == "arch" else {"nuc": "#23282A", "bg": "none"}), sw=(3.2 if key != "bond" else 2.2), style="width:42%"))}<figcaption>Fine line, on skin.</figcaption></figure>
  </div>
</div></section>'''

table = "<table><thead><tr><th></th>" + "".join(f"<th>{n}</th>" for _, n, *_ in MARKS) + "</tr></thead><tbody>" + "".join(
    f"<tr><th>{t}</th>" + "".join(f"<td>{SCORES[k][i]}</td>" for k, *_ in MARKS) + "</tr>" for i, t in enumerate(TESTS)) + "</tbody></table>"

html = f'''<title>Antimony Mark, Round Three</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Light and open: paper ground, ink line, one atom of cobalt. Each mark gets the same treatment so they can be judged fairly. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-500.woff2) format("woff2"); font-weight: 500; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --ink: {INK}; --paper: {PAPER}; --cobalt: {COBALT}; --sky: {SKY}; --rule: rgba(11,13,12,.13); --dim: #5C6461;
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --sans: "Timeless Sans", "Helvetica Neue", Arial, sans-serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 16px/1.55 var(--sans); -webkit-font-smoothing: antialiased; }}
.band {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 64px; border-bottom: 1px solid var(--rule); }}
.band.lead {{ background: #FBFAF6; }}
.in {{ max-width: 1120px; margin-inline: auto; display: grid; gap: 30px; }}
.eyebrow {{ font: 500 11.5px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--dim); }}
h1 {{ font: 400 clamp(40px, 6vw, 76px)/1 var(--serif); letter-spacing: -.02em; text-wrap: balance; max-width: 15em; }}
h2 {{ font: 400 clamp(34px, 4.6vw, 56px)/1 var(--serif); letter-spacing: -.015em; }}
.head {{ display: grid; gap: 10px; }}
p {{ max-width: 38em; }} .dim {{ color: var(--dim); }}
.lede {{ font: 400 clamp(18px, 1.9vw, 21px)/1.5 var(--serif); }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 36px; align-items: center; }}
.four {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; align-items: start; }}
.hero {{ width: min(100%, 380px); justify-self: center; }}
.txt {{ display: grid; gap: 18px; }}
.reads {{ padding-left: 1.3em; display: grid; gap: 6px; font-size: 15.5px; }}
figure {{ display: grid; gap: 10px; min-width: 0; }} figcaption {{ font-size: 14px; color: var(--dim); }}
.tile {{ aspect-ratio: 1; max-width: 100%; display: grid; place-items: center; padding: 22%; }}
.tile.ink {{ background: var(--ink); }} .tile.cob {{ background: var(--cobalt); }}
.av {{ width: 48px; height: 48px; display: block; flex: none; border-radius: 4px; background: #DCDDD7; }}
.av svg {{ width: 100%; height: 100%; display: block; }}
.list {{ background: #fff; border: 1px solid var(--rule); border-radius: 10px; padding: 4px 14px; }}
.row {{ display: flex; gap: 12px; align-items: center; padding: 11px 0; border-bottom: 1px solid rgba(11,13,12,.08); }} .row:last-child {{ border-bottom: 0; }}
.row b {{ display: block; font: 500 15px/1.25 var(--sans); color: #191919; }} .row span {{ font-size: 12.5px; color: #666; }}
.row.ghost b {{ width: 100px; height: 10px; background: #E3E3DF; border-radius: 3px; margin-bottom: 7px; }} .row.ghost span {{ display: block; width: 64px; height: 8px; background: #EDEDEA; border-radius: 3px; }}
.sizes {{ display: flex; flex-wrap: wrap; align-items: end; gap: 14px; min-height: 84px; padding: 18px; border: 1px solid var(--rule); }}
.sizes span {{ display: block; }} .sizes svg {{ display: block; }}
.lock {{ display: flex; align-items: center; gap: 22px; padding: 34px 28px; border: 1px solid var(--rule); background: #fff; flex-wrap: wrap; }}
.lock svg {{ display: block; max-width: 100%; }}
.skin {{ aspect-ratio: 16 / 10; max-width: 100%; display: grid; place-items: center; border-radius: 4px;
  background: radial-gradient(120% 90% at 40% 30%, #E7B998 0%, #D59F7E 60%, #C48C6C 100%); }}
.skin svg {{ filter: blur(.35px); opacity: .9; }}
.pat {{ display: grid; grid-template-columns: repeat(9, minmax(0, 1fr)); gap: 18px; padding: 26px; background: #fff; border: 1px solid var(--rule); }}
.pat span {{ display: block; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14.5px; }}
th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
thead th {{ font: 500 12px var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--dim); }}
tbody th {{ font-weight: 500; }}
.scroll {{ overflow-x: auto; }}
@media (max-width: 860px) {{ .two {{ grid-template-columns: 1fr; }} .four {{ grid-template-columns: 1fr 1fr; }} .band {{ padding-block: 48px; }} .pat {{ grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }} .four figure:last-child {{ grid-column: 1 / -1; }} }}
</style>

<section class="band"><div class="in">
  <span class="eyebrow">Antimony, the mark, round three</span>
  <h1>Hopeful, ours, and simple enough to carry for a lifetime.</h1>
  <p class="lede">No emblems, no dark plates, no flowers, stars or orbs. Three marks, each from a true root of the name, each held to the same seven tests, each shown where it will live: a list, an avatar, a lockup, and on skin.</p>
</div></section>
{secs}
<section class="band"><div class="in">
  <span class="eyebrow">A seed</span>
  <h2>The And repeats into a pattern; one lit.</h2>
  {pattern_and()}
  <p class="dim">Because every stroke sits on the 45 degree lattice, the mark tiles, scales into a grid for layouts, and gives the type its ornaments. The lattice is the system; the And is its smallest sentence.</p>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">The tests</span>
  <h2>How each one does.</h2>
  <div class="scroll">{table}</div>
  <p>My recommendation is the And. It is the only one that says the name's meaning out loud, it is drawn in one line, and it is versatile in a way letters are not: Orbe &amp; Antimony, you &amp; us, the work &amp; the people who make it.</p>
</div></section>
'''
open("../round3/index.html", "w").write(html); print(len(html))
