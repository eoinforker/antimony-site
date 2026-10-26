// A spray can, simulated on 2D canvas: grain, pressure, overspray, drips that run and pool.
// Everything here is procedural. Colours are sRGB strings; the shader decodes them.

const TAU = Math.PI * 2;

export function rng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
export function noise1(seed) {
  const r = rng(seed), v = new Float32Array(1024);
  for (let i = 0; i < 1024; i++) v[i] = r();
  return x => { const i = Math.floor(x), f = x - i, a = v[i & 1023], b = v[(i + 1) & 1023], u = f * f * (3 - 2 * f); return a + (b - a) * u; };
}
function gauss(r) { return Math.sqrt(-2 * Math.log(r() + 1e-9)) * Math.cos(TAU * r()); }
export function canvas(w, h) { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; }

// ---------- sprites: the can's spray pattern, tinted once per colour ----------
const cans = new Map();
function speckSprite(colour, seed, size = 128, n = 1700) {
  const c = canvas(size, size), x = c.getContext('2d'), r = rng(seed), R = size / 2;
  // a faint flat core so heavy passes reach full coverage
  const g = x.createRadialGradient(R, R, 0, R, R, R * 0.66);
  g.addColorStop(0, colour); g.addColorStop(0.75, colour); g.addColorStop(1, 'rgba(0,0,0,0)');
  x.globalAlpha = 0.62; x.fillStyle = g; x.fillRect(0, 0, size, size);
  x.fillStyle = colour;
  for (let i = 0; i < n; i++) {
    let d;
    if (r() < 0.7) d = Math.sqrt(r()) * 0.62; else d = 0.62 + Math.abs(gauss(r)) * 0.15;
    if (d > 0.98) d = 0.98;
    const a = r() * TAU, px = R + Math.cos(a) * d * R, py = R + Math.sin(a) * d * R;
    const dr = (0.35 + r() * r() * 1.25) * size / 128;
    x.globalAlpha = (0.3 + 0.7 * r()) * (d > 0.62 ? 0.55 : 1);
    x.beginPath(); x.arc(px, py, dr, 0, TAU); x.fill();
  }
  return c;
}
function softSprite(colour, size = 64) {
  const c = canvas(size, size), x = c.getContext('2d'), R = size / 2;
  const g = x.createRadialGradient(R, R, 0, R, R, R);
  g.addColorStop(0, colour); g.addColorStop(0.35, colour); g.addColorStop(1, 'rgba(0,0,0,0)');
  x.fillStyle = g; x.globalAlpha = 1;
  // gaussian-ish: draw twice with different radii
  x.fillRect(0, 0, size, size);
  return c;
}
export function can(colour) {
  if (cans.has(colour)) return cans.get(colour);
  const k = { colour, specks: [0, 1, 2, 3].map(i => speckSprite(colour, 77 + i * 131)), soft: softSprite(colour), mist: speckSprite(colour, 991, 128, 420) };
  cans.set(colour, k);
  return k;
}

function stamp(ctx, img, x, y, size, rot, alpha) {
  if (alpha <= 0.002) return;
  const c = Math.cos(rot), s = Math.sin(rot);
  ctx.globalAlpha = Math.min(1, alpha);
  ctx.setTransform(c, s, -s, c, x, y);
  ctx.drawImage(img, -size / 2, -size / 2, size, size);
}
function reset(ctx) { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; }

// ---------- a painter: a canvas mapped onto a surface in metres ----------
// u to the right, v up. Canvas y runs down from v1.
export class Painter {
  constructor({ u0, v0, u1, v1, pxm, drips = true, ledges = [] }) {
    Object.assign(this, { u0, v0, u1, v1, pxm });
    this.W = Math.min(4096, Math.round((u1 - u0) * pxm));
    this.H = Math.min(4096, Math.round((v1 - v0) * pxm));
    this.pxm = this.W / (u1 - u0);
    this.c = canvas(this.W, this.H); this.ctx = this.c.getContext('2d');
    if (drips) { this.p = canvas(this.W, this.H); this.pctx = this.p.getContext('2d'); }
    this.ledges = ledges.map(v => this.y(v)).sort((a, b) => a - b);
  }
  x(u) { return (u - this.u0) * this.pxm; }
  y(v) { return (this.v1 - v) * this.pxm; }
  m(px) { return px / this.pxm; }
}

// ---------- strokes ----------
function resample(pts, step) {
  const out = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const [ax, ay] = pts[i], [bx, by] = pts[i + 1];
    const d = Math.hypot(bx - ax, by - ay), n = Math.max(1, Math.ceil(d / step));
    for (let k = 0; k < n; k++) out.push([ax + (bx - ax) * k / n, ay + (by - ay) * k / n]);
  }
  out.push(pts[pts.length - 1]);
  return out;
}
export function catmull(pts, seg = 10, closed = false) {
  const out = [], n = pts.length;
  const P = i => closed ? pts[(i + n) % n] : pts[Math.max(0, Math.min(n - 1, i))];
  const last = closed ? n : n - 1;
  for (let i = 0; i < last; i++) {
    const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
    for (let k = 0; k < seg; k++) {
      const t = k / seg, t2 = t * t, t3 = t2 * t;
      out.push([0, 1].map(j => 0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)));
    }
  }
  out.push(closed ? P(n) : P(n - 1));
  return out;
}

// pts in canvas px. o: { col, r (px), flow, drip (chance), dripLen [min,max] metres, seed, halo }
export function spray(P, pts, o) {
  const ctx = P.ctx, k = can(o.col), r = o.r, R = rng(o.seed || 1);
  const nA = noise1((o.seed || 1) * 7 + 3), nB = noise1((o.seed || 1) * 13 + 5), nW = noise1((o.seed || 1) * 17 + 11);
  const step = Math.max(0.6, r * 0.16);
  // hand wobble: a slow drift perpendicular to the path
  const raw = resample(pts, step);
  const L = raw.length * step, wob = (o.wobble ?? 0.12) * r;
  const sp = raw.map((p, i) => {
    const a = raw[Math.max(0, i - 2)], b = raw[Math.min(raw.length - 1, i + 2)];
    let tx = b[0] - a[0], ty = b[1] - a[1]; const l = Math.hypot(tx, ty) || 1; tx /= l; ty /= l;
    const w = (nW(i * step / (r * 9)) - 0.5) * 2 * wob;
    return [p[0] - ty * w, p[1] + tx * w, tx, ty];
  });
  const flow = o.flow ?? 0.5;
  let load = 0;
  for (let i = 0; i < sp.length; i++) {
    const [x, y] = sp[i], s = i * step;
    const dn = nA(s / (r * 5)), pr = nB(s / (r * 2.2));
    const rr = r * (0.82 + 0.42 * dn);
    let a = flow * (1.12 - 0.5 * dn) * (0.72 + 0.28 * pr) * 0.3;
    const e0 = s / (r * 1.4), e1 = (L - s) / (r * 1.1);
    if (e0 < 1) a *= 1 + (1 - e0) * 1.3;          // the can spits as it starts
    if (e1 < 1) a *= 0.35 + 0.65 * Math.max(0, e1); // and trails off
    const spr = k.specks[(i + (o.seed | 0)) & 3];
    stamp(ctx, spr, x, y, rr / 0.31, R() * TAU, a * 1.9);
    if ((i & 1) === 0) stamp(ctx, k.soft, x, y, rr * 2.1, 0, a * 0.18);
    if (o.halo !== false && i % 5 === 0) {
      stamp(ctx, k.soft, x, y, rr * 6.5, 0, a * 0.05);
      stamp(ctx, k.mist, x + (R() - 0.5) * rr, y + (R() - 0.5) * rr, rr * 4.2, R() * TAU, a * 0.5);
    }
    // paint load: slow, heavy spots and ends run
    load += a * step / r * (e0 < 1 || e1 < 1 ? 3.2 : 1);
    if (P.pctx && o.drip && load > 0.6 && R() < o.drip * a * step / r * 6) {
      const len = (o.dripLen[0] + (o.dripLen[1] - o.dripLen[0]) * Math.pow(R(), 1.6)) * P.pxm;
      drip(P, x + (R() - 0.5) * rr * 1.1, y + rr * (0.35 + R() * 0.3), rr * (o.dripW ?? 1) * (0.16 + 0.2 * R()), len, o.col, R, o.dripOff ?? 0);
      load = 0;
    }
  }
  reset(ctx);
}

// A drip: runs down, thins, beads at the end, may pool on a transom ledge.
export function drip(P, x, y, w, len, col, R = Math.random, off = 0) {
  const ctx = P.ctx, pc = P.pctx, nx = noise1(Math.floor(R() * 1e6));
  ctx.fillStyle = col; reset(ctx);
  const maxM = 3.2, o2 = off + R() * 0.12;
  let cx = x, end = len, pooled = false;
  for (const ly of P.ledges) { if (ly > y + 2 && ly < y + len) { if (R() < 0.55) { end = ly - y; pooled = true; } break; } }
  for (let s = 0; s < end; s += 0.75) {
    const t = s / Math.max(end, 1);
    const ww = Math.max(0.7, w * (1 - 0.42 * t) * (0.85 + 0.3 * nx(s * 0.06)));
    cx += (nx(s * 0.013 + 9) - 0.5) * 0.05;
    ctx.globalAlpha = 0.5;
    ctx.fillRect(cx - ww / 2, y + s, ww, 1.1);
    if (pc) {
      const g = Math.min(1, o2 + Math.pow(P.m(s) / maxM, 1.25) * (1 - o2));
      pc.fillStyle = `rgb(255,${Math.round(g * 255)},0)`;
      pc.fillRect(cx - ww / 2 - 0.5, y + s, ww + 1, 1.1);
    }
  }
  const ey = y + end, g = Math.min(1, o2 + Math.pow(P.m(end) / maxM, 1.25) * (1 - o2));
  ctx.globalAlpha = 0.95;
  if (pooled) {
    // paint gathers along the ledge and spreads sideways
    // a tapered smear along the ledge, heavier on one side
    const pw = w * (1.2 + R() * 2.2), ph = Math.max(1, w * 0.42), sk = (R() - 0.5) * pw * 0.6;
    const smear = c => { c.beginPath(); c.moveTo(cx - pw + sk, ey); c.quadraticCurveTo(cx + sk * 0.5, ey - ph * 2.2, cx + pw + sk, ey); c.quadraticCurveTo(cx, ey + ph * 0.6, cx - pw + sk, ey); c.fill(); };
    smear(ctx);
    if (pc) { pc.fillStyle = `rgb(255,${Math.round(g * 255)},0)`; smear(pc); }
  } else {
    const br = Math.max(1, w * (0.62 + R() * 0.25));
    ctx.beginPath(); ctx.ellipse(cx, ey, br, br * 1.25, 0, 0, TAU); ctx.fill();
    if (pc) { pc.fillStyle = `rgb(255,${Math.round(g * 255)},0)`; pc.beginPath(); pc.arc(cx, ey, br + 1, 0, TAU); pc.fill(); }
  }
  reset(ctx);
}

// ---------- hand letters: single-stroke skeletons, height 1, y down ----------
const E = (cx, cy, rx, ry, a0, a1, n = 26) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return [cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]; });
export const GLYPHS = {
  A: { w: 0.8, s: [[[0, 1], [0.4, 0], [0.8, 1]], [[0.14, 0.63], [0.7, 0.6]]] },
  N: { w: 0.74, s: [[[0.02, 1], [0, 0.02], [0.72, 0.98], [0.71, 0]]] },
  T: { w: 0.72, s: [[[-0.02, 0.03], [0.74, 0]], [[0.37, 0.02], [0.35, 1]]] },
  I: { w: 0.2, s: [[[0.1, 0], [0.09, 1]]] },
  M: { w: 0.96, s: [[[0, 1], [0.06, 0.02], [0.48, 0.64], [0.9, 0], [0.96, 1]]] },
  O: { w: 0.82, s: [E(0.41, 0.5, 0.41, 0.5, -Math.PI * 0.62, Math.PI * 1.5)] },
  Y: { w: 0.76, s: [[[0, 0], [0.38, 0.52]], [[0.77, 0], [0.38, 0.52], [0.36, 1]]] },
  S: { w: 0.64, s: [catmull([[0.62, 0.12], [0.44, 0.0], [0.16, 0.03], [0.03, 0.22], [0.14, 0.42], [0.5, 0.56], [0.63, 0.77], [0.48, 0.97], [0.18, 0.99], [0, 0.86]], 8)] },
  E: { w: 0.62, s: [[[0.64, 0.01], [0, 0], [0.01, 1], [0.64, 0.99]], [[0.01, 0.5], [0.5, 0.49]]] },
};

// lay a word out as hand strokes; returns { strokes: [[ [x,y],... ]], width } in px
export function handWord(word, x, top, h, opt = {}) {
  const R = rng(opt.seed || 9), lean = opt.lean ?? 0.13, gap = opt.gap ?? 0.1;
  const strokes = [];
  let cx = x;
  for (let i = 0; i < word.length; i++) {
    const g = GLYPHS[word[i]];
    if (!g) { cx += h * 0.45; continue; }
    const sc = h * (1 + (R() - 0.5) * (opt.vary ?? 0.14)), rot = (R() - 0.5) * (opt.rot ?? 0.1);
    const dy = (opt.slope || 0) * (cx - x) + (R() - 0.5) * h * (opt.bounce ?? 0.09);
    const sx = opt.squash ?? 1;
    for (const st of g.s) {
      const pts = st.map(([u, v]) => {
        let px = u * sc * sx + (1 - v) * lean * sc, py = v * sc;
        const qx = px * Math.cos(rot) - py * Math.sin(rot), qy = px * Math.sin(rot) + py * Math.cos(rot);
        return [cx + qx, top + dy + qy + (h - sc)];
      });
      // overshoot the ends slightly, the way a fast arm does
      const ext = (a, b, k) => [a[0] + (a[0] - b[0]) * k, a[1] + (a[1] - b[1]) * k];
      const n = pts.length;
      if (n > 1) { pts[0] = ext(pts[0], pts[1], 0.03 + R() * 0.05); pts[n - 1] = ext(pts[n - 1], pts[n - 2], 0.02 + R() * 0.06); }
      strokes.push(pts);
    }
    cx += (g.w * sx + gap) * h * (1 + (R() - 0.5) * 0.08);
  }
  return { strokes, width: cx - x - gap * h };
}
export function wordWidth(word, h, gap = 0.1) {
  let w = 0; for (const c of word) w += ((GLYPHS[c] || { w: 0.35 }).w + gap) * h; return w - gap * h;
}

// ---------- an old tag: a fast, squashed handstyle, thin and illegible ----------
export function scribble(P, x, y, w, h, col, seed, r) {
  const R = rng(seed), pool = 'AMNTOSYE', n = 3 + Math.floor(R() * 3);
  let word = ''; for (let i = 0; i < n; i++) word += pool[Math.floor(R() * pool.length)];
  const { strokes } = handWord(word, x, y, h, { seed, lean: 0.45, gap: -0.08, squash: 0.55, vary: 0.35, rot: 0.25, bounce: 0.3 });
  const sc = w / Math.max(1, strokes.reduce((m, st) => Math.max(m, ...st.map(p => p[0])), x) - x);
  strokes.forEach((st, i) => spray(P, catmull(st.map(([a, b]) => [x + (a - x) * Math.min(1.4, sc), b]), 5), { col, r: r || h * 0.06, flow: 0.6, drip: 0.6, dripLen: [0.1, 0.8], seed: seed * 7 + i, wobble: 0.4 }));
  // the underline flourish every writer adds
  const yy = y + h * 1.08;
  spray(P, catmull([[x - h * 0.2, yy + h * 0.1], [x + w * 0.4, yy], [x + w * 0.95, yy - h * 0.15], [x + w * 1.05, yy - h * 0.4]], 8), { col, r: (r || h * 0.06) * 0.8, flow: 0.55, drip: 0.3, dripLen: [0.1, 0.5], seed: seed + 3, wobble: 0.3 });
}

// ---------- the buff: corporate grey rolled over old paint ----------
export function buff(P, x, y, w, h, seed, tone = [34, 36, 40]) {
  const ctx = P.ctx, R = rng(seed), roll = Math.max(6, P.pxm * 0.24);
  reset(ctx);
  for (let yy = y; yy < y + h; yy += roll * 0.82) {
    const j0 = (R() - 0.5) * roll * 1.6, j1 = (R() - 0.5) * roll * 1.6, t = (R() - 0.5) * 6;
    ctx.globalAlpha = 0.82 + R() * 0.14;
    ctx.fillStyle = `rgb(${tone[0] + t},${tone[1] + t},${tone[2] + t})`;
    ctx.fillRect(x + j0, yy, w + j1 - j0, roll);
  }
  // roller grain
  const k = can(`rgb(${tone[0] - 10},${tone[1] - 10},${tone[2] - 9})`);
  for (let i = 0; i < (w * h) / (roll * roll) * 0.4; i++) stamp(ctx, k.mist, x + R() * w, y + R() * h, roll * 3, R() * TAU, 0.18);
  reset(ctx);
}

// ---------- stencils: crisp edges, bridges, overspray, the ghost of the board ----------
const BRIDGE = { O: 0.5, Q: 0.5, '0': 0.5, A: 0.5, B: 0.56, D: 0.56, P: 0.56, R: 0.5, '4': 0.6, '6': 0.5, '8': 0.5, '9': 0.5 };
export function stencil(P, text, x, y, h, col, o = {}) {
  const track = o.track ?? 0.08, sy = o.stretch || 1, weight = o.weight || 640;
  const font = `${weight} ${h}px "Timeless Serif", Georgia, serif`;
  const mctx0 = canvas(4, 4).getContext('2d'); mctx0.font = font;
  const widths = [...text].map(c => mctx0.measureText(c).width);
  const tw = widths.reduce((a, b) => a + b + track * h, 0) - track * h;
  if (o.center) x -= tw / 2;
  const pad = Math.ceil(h * 0.5), W = Math.ceil(tw + pad * 2), H = Math.ceil(h * sy * 1.1 + pad * 2);
  const M = canvas(W, H), m = M.getContext('2d');
  m.font = font; m.fillStyle = '#fff'; m.textBaseline = 'alphabetic';
  m.setTransform(1, 0, 0, sy, 0, 0);
  let cx = pad;
  const cuts = [];
  [...text].forEach((c, i) => {
    m.fillText(c, cx, (pad + h * 0.86 * sy) / sy);
    const b = BRIDGE[c]; if (b) cuts.push(cx + widths[i] * b);
    cx += widths[i] + track * h;
  });
  m.setTransform(1, 0, 0, 1, 0, 0);
  m.globalCompositeOperation = 'destination-out';
  for (const cxp of cuts) m.fillRect(cxp - h * 0.028, 0, h * 0.056, H);
  if (o.cutLine) m.fillRect(0, pad + h * sy * 0.47, W, h * 0.05 * sy);
  m.globalCompositeOperation = 'source-over';
  // the paint layer: uneven horizontal sweeps
  const L = canvas(W, H), l = L.getContext('2d'), k = can(col), R = rng(o.seed || 3), nz = noise1(o.seed || 3);
  l.fillStyle = col; l.globalAlpha = 0.55; l.fillRect(0, 0, W, H);
  const sz = h * 0.9;
  for (let yy = 0; yy < H; yy += sz * 0.28) for (let xx = 0; xx < W; xx += sz * 0.2) {
    stamp(l, k.specks[(xx + yy) & 3], xx + (R() - 0.5) * sz * 0.3, yy, sz, R() * TAU, 0.5 + 0.6 * nz(xx / sz * 0.5 + yy * 0.01));
  }
  reset(l);
  l.globalCompositeOperation = 'destination-in'; l.drawImage(M, 0, 0);
  const ctx = P.ctx, ox = x - pad, oy = y - pad - h * 0.86 * sy;
  reset(ctx);
  // overspray under the board's edge
  ctx.save(); ctx.filter = `blur(${Math.max(1, h * 0.05)}px)`; ctx.globalAlpha = 0.22;
  const T = canvas(W, H), t = T.getContext('2d'); t.drawImage(M, 0, 0); t.globalCompositeOperation = 'source-in'; t.fillStyle = col; t.fillRect(0, 0, W, H);
  ctx.drawImage(T, ox + h * 0.02, oy + h * 0.03); ctx.restore();
  // mist that settled on the board's surround: a faint rectangle with a hard edge
  if (o.board !== false) {
    const bx = ox + pad * 0.45, by = oy + pad * 0.5, bw = W - pad * 0.9, bh = H - pad * 1.0;
    ctx.save(); ctx.beginPath(); ctx.rect(bx, by, bw, bh); ctx.clip();
    for (let i = 0; i < (bw * bh) / (sz * sz) * 1.6; i++) stamp(ctx, k.mist, bx + R() * bw, by + R() * bh, sz * 1.4, R() * TAU, 0.05 + R() * 0.05);
    reset(ctx); ctx.restore();
  }
  ctx.drawImage(L, ox, oy);
  // a few runs where the can lingered
  if (P.pctx && o.drips) {
    let px = x;
    [...text].forEach((c, i) => {
      if (c !== ' ' && R() < o.drips) drip(P, px + widths[i] * (0.25 + R() * 0.5), y - h * 0.04, h * (0.025 + R() * 0.03), h * sy * (0.4 + R() * 1.6), col, R, 0.15);
      px += widths[i] + track * h;
    });
  }
  reset(ctx);
  return tw;
}

// a stencilled shape (Path2D in 100 units), placed at x,y with size s px
export function stencilShape(P, paths, x, y, s, col, o = {}) {
  const W = Math.ceil(s * 1.5), pad = s * 0.25;
  const M = canvas(W, W), m = M.getContext('2d');
  m.setTransform(s / 100, 0, 0, s / 100, pad, pad);
  m.fillStyle = '#fff';
  m.fill(paths.fill);
  if (paths.cut) { m.globalCompositeOperation = 'destination-out'; for (const c of paths.cut) m.fill(c); }
  m.setTransform(1, 0, 0, 1, 0, 0); m.globalCompositeOperation = 'source-over';
  const L = canvas(W, W), l = L.getContext('2d'), k = can(col), R = rng(o.seed || 5);
  l.fillStyle = col; l.globalAlpha = o.base ?? 0.6; l.fillRect(0, 0, W, W);
  const sz = s * 0.11, nz = noise1(o.seed || 5);
  // sweeps of the can across the stencil, a little uneven
  for (let yy = 0; yy < W; yy += sz * 0.3) for (let xx = 0; xx < W; xx += sz * 0.3) stamp(l, k.specks[(xx + yy) & 3], xx + (R() - 0.5) * sz * 0.5, yy + (R() - 0.5) * sz * 0.5, sz, R() * TAU, (o.flow ?? 0.5) * (0.25 + 0.5 * nz(xx / s * 3 + yy / s * 0.7)));
  reset(l);
  l.globalCompositeOperation = 'destination-in'; l.drawImage(M, 0, 0);
  const ctx = P.ctx; reset(ctx);
  ctx.save(); ctx.filter = `blur(${Math.max(1, s * 0.012)}px)`; ctx.globalAlpha = 0.25;
  const T = canvas(W, W), t = T.getContext('2d'); t.drawImage(M, 0, 0); t.globalCompositeOperation = 'source-in'; t.fillStyle = col; t.fillRect(0, 0, W, W);
  ctx.drawImage(T, x - pad + s * 0.008, y - pad + s * 0.01); ctx.restore();
  if (o.board) {
    ctx.save(); ctx.beginPath(); ctx.rect(x - s * 0.1, y - s * 0.1, s * 1.2, s * 1.2); ctx.clip();
    for (let i = 0; i < 260; i++) stamp(ctx, k.mist, x - s * 0.1 + R() * s * 1.2, y - s * 0.1 + R() * s * 1.2, sz * 1.3, R() * TAU, 0.06);
    reset(ctx); ctx.restore();
  }
  ctx.drawImage(L, x - pad, y - pad);
  reset(ctx);
}

// ---------- live paint: what the visitor sprays, with drips that run in real time ----------
export class LiveLayer {
  constructor(P) {
    this.P = P; this.ctx = P.ctx; this.k = can('#94E6FF'); this.drips = []; this.dirty = false;
    this.R = rng(4242); this.last = null; this.load = 0; this.lastSpray = -1e9; this.lastFade = 0; this.used = false;
  }
  dab(x, y, r, a) {
    const ctx = this.ctx, k = this.k, R = this.R;
    const j = r * 0.25;
    stamp(ctx, k.specks[(R() * 4) | 0], x + (R() - 0.5) * j, y + (R() - 0.5) * j, r * (0.85 + R() * 0.4) / 0.31, R() * TAU, a * 0.8);
    stamp(ctx, k.specks[(R() * 4) | 0], x + (R() - 0.5) * j * 2, y + (R() - 0.5) * j * 2, r * 0.7 / 0.31, R() * TAU, a * 0.5);
    stamp(ctx, k.soft, x, y, r * 1.8, 0, a * 0.05);
    if (R() < 0.35) { stamp(ctx, k.soft, x, y, r * 6, 0, a * 0.03); stamp(ctx, k.mist, x + (R() - 0.5) * r, y + (R() - 0.5) * r, r * 4.5, R() * TAU, a * 0.55); }
  }
  // spray from the last point to this one; dt in seconds, now in seconds
  sprayTo(x, y, r, dt, now) {
    const R = this.R;
    const prev = this.last;
    let speed = 0;
    if (prev && now - prev.t < 0.2) {
      const d = Math.hypot(x - prev.x, y - prev.y); speed = d / Math.max(dt, 1e-3);
      const n = Math.min(60, Math.ceil(d / (r * 0.18)));
      for (let i = 1; i <= n; i++) this.dab(prev.x + (x - prev.x) * i / n, prev.y + (y - prev.y) * i / n, r * (0.9 + R() * 0.2), 0.11);
    } else { for (let i = 0; i < 3; i++) this.dab(x, y, r, 0.16); } // first puff
    this.dab(x, y, r, 0.06 * Math.min(1, dt * 60));
    this.load += dt * 2.2 / (1 + speed / (r * 6));
    if (this.load > 0.55 + R() * 0.5) {
      this.load = 0;
      this.drips.push({ x: x + (R() - 0.5) * r * 1.1, y: y + r * 0.45, y0: y + r * 0.45, w: r * (0.08 + R() * 0.1), len: this.P.pxm * (0.3 + Math.pow(R(), 1.5) * 2.4), v: this.P.pxm * (0.18 + R() * 0.25), n: noise1((R() * 1e6) | 0) });
    }
    this.last = { x, y, t: now }; this.dirty = true; this.used = true; this.lastSpray = now;
  }
  lift() { this.last = null; }
  step(dt, now) {
    const ctx = this.ctx;
    if (this.drips.length) {
      ctx.fillStyle = '#94E6FF';
      for (let i = this.drips.length - 1; i >= 0; i--) {
        const d = this.drips[i];
        const ds = d.v * dt; d.v *= Math.exp(-dt * 0.45);
        const s0 = d.y - d.y0, s1 = Math.min(d.len, s0 + ds);
        let s = s0;
        for (; s < s1; s += 0.8) {
          const t = s / d.len, ww = Math.max(0.8, d.w * (1 - 0.4 * t) * (0.85 + 0.3 * d.n(s * 0.07)));
          ctx.globalAlpha = 0.55; ctx.fillRect(d.x - ww / 2, d.y0 + s, ww, 1.1);
          let hit = false;
          for (const ly of this.P.ledges) if (ly > d.y0 + s && ly <= d.y0 + s + 0.8) { if (this.R() < 0.5) hit = true; break; }
          if (hit) { d.len = s; d.pool = true; break; }
        }
        d.y = d.y0 + Math.min(s, s1);
        if (s1 >= d.len || d.v < this.P.pxm * 0.012) {
          ctx.globalAlpha = 0.9; ctx.beginPath();
          if (d.pool) ctx.ellipse(d.x, d.y, d.w * (2 + this.R() * 4), Math.max(1, d.w * 0.6), 0, 0, TAU);
          else ctx.ellipse(d.x, d.y, d.w * 0.7, d.w * 0.9, 0, 0, TAU);
          ctx.fill(); this.drips.splice(i, 1);
        }
        this.dirty = true;
      }
      ctx.globalAlpha = 1;
    }
    // slow fade: the corporation's cleaners are always on their way
    if (this.used && now - this.lastFade > 1) {
      this.lastFade = now;
      ctx.globalCompositeOperation = 'destination-out'; ctx.globalAlpha = 1; ctx.fillStyle = 'rgba(0,0,0,0.03)';
      ctx.fillRect(0, 0, this.P.W, this.P.H); ctx.globalCompositeOperation = 'source-over';
      this.dirty = true;
      if (now - this.lastSpray > 150 && !this.drips.length) { ctx.clearRect(0, 0, this.P.W, this.P.H); this.used = false; }
    }
  }
}
