"""Writes pages/sting-<w>x<h>.html: a five second film of the Bond. Driven frame by frame by sting.js."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kit import G, WM, INK, PAPER, SKY, LINE_D, page, WM_Y0, WM_Y1
for w, h in [(1080, 1080), (1920, 1080)]:
    js = f"""
const G = {json.dumps({"atoms": G["atoms"], "bonds": G["bonds"], "R": G["R"], "W": G["W"]})};
const WM = {json.dumps({"letters": WM["letters"], "dot": WM["dot"], "w": WM["w"], "y0": WM_Y0, "y1": WM_Y1, "cap": WM["cap"], "asc": WM["asc"]})};
const W = {w}, H = {h}, c = document.getElementById("c"), x = c.getContext("2d");
c.width = W * 2; c.height = H * 2; x.scale(2, 2);
const letters = new Path2D(WM.letters), dot = new Path2D(WM.dot);
const cl = v => Math.max(0, Math.min(1, v)), eo = t => 1 - Math.pow(1 - t, 3), eio = t => t < .5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3) / 2;
const span = (t, a, b) => cl((t - a) / (b - a));
function diamond(px, py, r) {{ x.beginPath(); x.moveTo(px, py - r); x.lineTo(px + r, py); x.lineTo(px, py + r); x.lineTo(px - r, py); x.closePath(); x.fill(); }}
// one emblem: grow is 0..1 through the build; at 1 it is complete
function emblem(cx, cy, s, grow, ink, nuc) {{
  const A = G.atoms, k = s / 100, P = n => [cx + (A[n][0] - 50) * k, cy + (A[n][1] - 50) * k];
  const nucT = eo(cl(grow / .25)), armT = eio(cl((grow - .2) / .35)), legT = eio(cl((grow - .5) / .3));
  const pop = (t0) => eo(cl((grow - t0) / .2));
  x.fillStyle = ink;
  for (const [a, b] of G.bonds) {{
    const t = a === "nucleus" ? armT : legT; if (t <= 0) continue;
    const [x1, y1] = P(a), [x2, y2] = P(b), ex = x1 + (x2 - x1) * t, ey = y1 + (y2 - y1) * t, w = G.W * k / 2;
    if (x1 === x2) x.fillRect(x1 - w, Math.min(y1, ey), 2 * w, Math.abs(ey - y1)); else x.fillRect(Math.min(x1, ex), y1 - w, Math.abs(ex - x1), 2 * w);
  }}
  for (const n of ["apex", "left", "right"]) {{ const p = pop(.45); if (p > 0) diamond(...P(n), G.R * k * p); }}
  for (const n of ["leg_l", "leg_r"]) {{ const p = pop(.72); if (p > 0) diamond(...P(n), G.R * k * p); }}
  x.fillStyle = nuc; if (nucT > 0) diamond(...P("nucleus"), G.R * k * nucT);
}}
window.at = t => {{
  x.fillStyle = "{INK}"; x.fillRect(0, 0, W, H);
  const big = Math.min(W, H) * .46, small = Math.min(W, H) * .2;
  const pull = eio(span(t, 2.3, 3.4));                    // the camera pulls back: the Bond is one of a lattice
  const lock = eio(span(t, 3.9, 4.7));                    // the lattice falls away and the name arrives
  let s = big + (small - big) * pull; const cx0 = W / 2, cy0 = H / 2;
  // lockup geometry: emblem height 1.5 cap heights; the name sits to its right
  const capPx = small / 1.5 * (93 / 100) , k = capPx / WM.cap, wmW = WM.w * k, gap = small * .22, total = small * .93 + gap + wmW;
  const lx = W / 2 - total / 2 + small * .93 / 2;
  const cx = cx0 + (lx - cx0) * lock, cy = cy0;
  // the lattice
  const lat = span(t, 2.3, 3.1) * (1 - span(t, 3.9, 4.5));
  if (lat > 0) {{
    const step = s * 1.12;
    x.globalAlpha = lat;
    for (let j = -6; j <= 6; j++) for (let i = -9; i <= 9; i++) {{
      if (i === 0 && j === 0) continue;
      const px = cx + i * step + (Math.abs(j) % 2) * step / 2, py = cy + j * step;
      if (px < -s || px > W + s || py < -s || py > H + s) continue;
      emblem(px, py, s, 1, "{LINE_D}", "{LINE_D}");
    }}
    x.globalAlpha = 1;
  }}
  emblem(cx, cy, s, span(t, .35, 2.0), "{PAPER}", "{SKY}");
  // the name, wiped in from the left
  if (lock > 0) {{
    const ox = cx + small * .93 / 2 + gap, baseY = cy + capPx / 2;
    x.save(); x.beginPath(); x.rect(ox - 10, 0, (wmW + 20) * eo(span(t, 4.1, 4.9)), H); x.clip();
    x.translate(ox, baseY - WM.asc * k); x.scale(k, k); x.fillStyle = "{PAPER}"; x.fill(letters); x.fillStyle = "{SKY}"; x.fill(dot); x.restore();
  }}
}};
window.at(0);
"""
    open(f"pages/sting-{w}x{h}.html", "w").write(page(w, h, f'<canvas id="c" style="width:{w}px;height:{h}px"></canvas><script>{js}</script>', INK))
print("ok")
