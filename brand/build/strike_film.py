"""Writes pages2/strike-<w>x<h>.html: six seconds. A crystal appears, is struck three times, its counter turns to gold,
and the name arrives. Driven frame by frame by strike_film.js."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from mark import PC, HEX, TOP, LL, LR, DOT, WM, INK, PAPER, SKY, poly
from kit import page
by = PC["bar_y"]; W = PC["W"]
t = (by - TOP[1]) / (LL[1] - TOP[1]); xl = TOP[0] + (LL[0] - TOP[0]) * t
def ext(p, q, e):
    L = math.hypot(q[0] - p[0], q[1] - p[1]); return [p[0] - (q[0] - p[0]) / L * e, p[1] - (q[1] - p[1]) / L * e]
CUTS = [[ext(TOP, LL, 8), ext(LL, TOP, 8)], [ext(TOP, LR, 8), ext(LR, TOP, 8)], [[xl, by], [100 - xl, by]]]
for w, h in [(1080, 1080), (1920, 1080)]:
    js = f"""
const W = {w}, H = {h}, c = document.getElementById("c"), x = c.getContext("2d"); c.width = W * 2; c.height = H * 2; x.scale(2, 2);
const HEXP = new Path2D("{poly(HEX)}"), GOLD = new Path2D("{poly(PC['counter'])}"), LET = new Path2D("{WM['letters']}"), DOTP = new Path2D("{DOT}");
const CUTS = {json.dumps(CUTS)}, SW = {W}, CAP = {WM['cap']}, ASC = {WM['asc']}, WMW = {WM['w']};
const cl = v => Math.max(0, Math.min(1, v)), eo = t => 1 - Math.pow(1 - t, 3), eio = t => t < .5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3) / 2, sp = (t, a, b) => cl((t - a) / (b - a));
window.at = t => {{
  x.fillStyle = "{INK}"; x.fillRect(0, 0, W, H);
  const big = Math.min(W, H) * .42, small = Math.min(W, H) * .17;
  const lock = eio(sp(t, 3.7, 4.5));
  const s = big + (small - big) * lock;
  const capPx = small / 1.42, k = capPx / CAP, wmW = WMW * k, gap = capPx * .42, total = small + gap + wmW;
  const cx = W / 2 + ((W / 2 - total / 2 + small / 2) - W / 2) * lock, cy = H / 2;
  const appear = eo(sp(t, .35, 1.0));
  x.save(); x.translate(cx, cy); x.scale(s / 100 * (.92 + .08 * appear), s / 100 * (.92 + .08 * appear)); x.translate(-50, -50);
  x.globalAlpha = appear; x.fillStyle = "{PAPER}"; x.fill(HEXP); x.globalAlpha = 1;
  // three strikes, each a fast cut along its line
  const starts = [1.2, 1.65, 2.1];
  x.strokeStyle = "{INK}"; x.lineWidth = SW; x.lineCap = "butt";
  CUTS.forEach(([[ax, ay], [bx, by]], i) => {{
    const p = eio(sp(t, starts[i], starts[i] + .32)); if (p <= 0) return;
    x.beginPath(); x.moveTo(ax, ay); x.lineTo(ax + (bx - ax) * p, ay + (by - ay) * p); x.stroke();
  }});
  const g = eo(sp(t, 2.6, 3.2)); if (g > 0) {{ x.globalAlpha = g; x.fillStyle = "{SKY}"; x.fill(GOLD); x.globalAlpha = 1; }}
  x.restore();
  if (lock > 0) {{
    const ox = cx + small / 2 + gap, base = cy + capPx / 2;
    x.save(); x.beginPath(); x.rect(ox - 10, 0, (wmW + 20) * eo(sp(t, 3.95, 4.8)), H); x.clip();
    x.translate(ox, base - ASC * k); x.scale(k, k); x.fillStyle = "{PAPER}"; x.fill(LET); x.fillStyle = "{SKY}"; x.fill(DOTP); x.restore();
  }}
}};
window.at(0);
"""
    open(f"pages2/strike-{w}x{h}.html", "w").write(page(w, h, f'<canvas id="c" style="width:{w}px;height:{h}px"></canvas><script>{js}</script>', INK))
print("ok")
