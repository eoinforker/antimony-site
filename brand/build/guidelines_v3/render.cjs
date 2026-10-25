/* Renders a list of jobs with Playwright: node render.cjs jobs.json
   job: { url, w, h, out, scale?: 1, omit?: false, wait?: ms, pdf?: {width, height} } */
const { chromium } = require("playwright");
const fs = require("fs");
(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const ctxs = {};
  let n = 0;
  for (const j of jobs) {
    const key = (j.scale || 1);
    if (!ctxs[key]) ctxs[key] = await b.newContext({ deviceScaleFactor: key });
    const p = await ctxs[key].newPage();
    p.on("pageerror", e => console.error("pageerror", j.out, e.message));
    p.on("console", m => { if (m.type() === "error") console.error("console", j.out, m.text()); });
    await p.setViewportSize({ width: j.w, height: j.h });
    await p.goto(j.url, { waitUntil: "load" });
    if (j.waitTitle) await p.waitForFunction(() => document.title === "done", null, { timeout: 120000 });
    await p.evaluate(() => document.fonts && document.fonts.ready);
    await p.waitForTimeout(j.wait || 150);
    if (j.pdf) await p.pdf({ path: j.out, width: j.pdf.width, height: j.pdf.height, printBackground: true, pageRanges: "1" });
    else await p.screenshot({ path: j.out, omitBackground: !!j.omit, type: j.out.endsWith(".jpg") ? "jpeg" : "png", quality: j.out.endsWith(".jpg") ? 90 : undefined, clip: { x: 0, y: 0, width: j.clipW || j.w, height: j.clipH || j.h } });
    await p.close(); n++;
  }
  await b.close();
  console.log("rendered", n);
})();
