/* Captures the beats of the Blend C opening, the water under the pointer and the chipped stone, for the Motion chapter. */
const { chromium } = require("playwright");
const fs = require("fs");
const OUT = process.argv[2];
const URL = "http://localhost:8811/directions/blend-c/index.html";
(async () => {
  const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  p.on("pageerror", e => console.error("pageerror", e.message));
  await p.goto(URL + "?t=0&debug"); await p.waitForTimeout(1500);
  const T = await p.evaluate(() => window.__T);
  fs.writeFileSync(OUT + "/timeline.json", JSON.stringify(T, null, 1));
  const beats = [["typed", T.typed + .12], ["wall", T.g0 + .2], ["gather", T.g0 + .75], ["cells", T.sn0 + .32], ["split", T.e0 + T.ed + .25],
    ["join", T.j0 + .62], ["flare", T.j1 + .04], ["ground", T.d0 + .42]];
  for (const [n, t] of beats) { await p.evaluate(s => window.__seek(s), t); await p.waitForTimeout(250); await p.screenshot({ path: `${OUT}/beat-${n}.png` }); }
  await p.goto(URL + "?rest&debug"); await p.waitForTimeout(1800);
  await p.screenshot({ path: `${OUT}/beat-rest.png` });
  const box = await p.evaluate(() => { const r = document.getElementById("mark").getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width }; });
  fs.writeFileSync(OUT + "/markbox.json", JSON.stringify(box));
  const K = box.w / 100, at = (u, v) => [box.x + u * K, box.y + v * K];
  const clip = (m) => ({ x: Math.round(box.x - box.w * m), y: Math.round(box.y - box.w * m), width: Math.round(box.w * (1 + 2 * m)), height: Math.round(box.w * (1 + 2 * m)) });
  /* the water: the pointer sweeps across the crystal */
  const cx = box.x + box.w / 2, cy = box.y + box.w * .515;
  await p.mouse.move(cx - box.w * 1.3, cy);
  await p.waitForTimeout(400);
  await p.screenshot({ path: `${OUT}/water-0.png`, clip: clip(.12) });
  for (let i = 0; i <= 10; i++) { await p.mouse.move(cx - box.w * 1.3 + i * box.w * .26, cy - i * 2); await p.waitForTimeout(16); }
  let last = 0;
  for (const [k, ms] of [80, 320, 800, 3200].entries()) { await p.waitForTimeout(ms - last); last = ms; await p.screenshot({ path: `${OUT}/water-${k + 1}.png`, clip: clip(.12) }); }
  /* the chipped stone: a fracture under the pointer, a chip, the shard turning, the heal */
  await p.mouse.move(10, 10); await p.waitForTimeout(2500);
  const [hx, hy] = at(20, 32);
  await p.mouse.move(hx, hy); await p.waitForTimeout(500);
  await p.screenshot({ path: `${OUT}/chip-0.png`, clip: clip(1.15) });
  await p.mouse.down(); await p.mouse.up();
  last = 0;
  for (const [k, ms] of [120, 500, 1700].entries()) { await p.waitForTimeout(ms - last); last = ms; await p.screenshot({ path: `${OUT}/chip-${k + 1}.png`, clip: clip(1.15) }); }
  const [h2x, h2y] = at(80, 70); await p.mouse.move(h2x, h2y); await p.waitForTimeout(200); await p.mouse.down(); await p.mouse.up();
  const [h3x, h3y] = at(82, 26); await p.mouse.move(h3x, h3y); await p.waitForTimeout(200); await p.mouse.down(); await p.mouse.up();
  await p.mouse.move(box.x + box.w * 3, box.y + box.w * 1.8); await p.waitForTimeout(1900);
  await p.screenshot({ path: `${OUT}/chip-3up.png`, clip: clip(1.15) });
  await p.mouse.down(); await p.mouse.up();
  await p.waitForTimeout(1150);
  await p.screenshot({ path: `${OUT}/chip-heal.png`, clip: clip(1.15) });
  await b.close();
  console.log(JSON.stringify(T));
})();
