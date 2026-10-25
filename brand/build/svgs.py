"""Writes the master SVG files into ../exports/svg."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from kit import *
os.makedirs("../exports/svg", exist_ok=True)
X = lambda s: s.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1).replace(' class=""', "").replace(' style=""', "")
files = {
 "bond.svg": bond_svg(INK, COBALT), "bond-reversed.svg": bond_svg(PAPER, SKY), "bond-one-colour.svg": bond_svg(INK, INK),
 "bond-one-colour-white.svg": bond_svg("#FFFFFF", "#FFFFFF"), "seal.svg": seal_svg(INK, COBALT), "seal-reversed.svg": seal_svg(PAPER, SKY),
 "wordmark.svg": wordmark_svg(INK, COBALT), "wordmark-reversed.svg": wordmark_svg(PAPER, SKY), "wordmark-one-colour.svg": wordmark_svg(INK, INK),
 "lockup.svg": lockup_svg(INK, COBALT), "lockup-reversed.svg": lockup_svg(PAPER, SKY), "lockup-stacked.svg": lockup_svg(INK, COBALT, stacked=True),
 "lockup-stacked-reversed.svg": lockup_svg(PAPER, SKY, stacked=True),
}
for n, s in files.items(): open(f"../exports/svg/{n}", "w").write(X(s))
# the favicon: the emblem on paper with a little air, so it reads in dark and light browser tabs
open("../exports/icons/favicon.svg", "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="18" fill="{PAPER}"/><g transform="translate(9 9) scale(.82)">{bond_paths(INK, COBALT)}</g></svg>')
print(len(files) + 1, "svg")
