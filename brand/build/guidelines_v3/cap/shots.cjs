/* Screenshots every chapter at 1440 x 900 and 390 x 844: the first screen, and the whole page. */
const { chromium } = require("playwright");
const OUT = process.argv[2], only = process.argv[3];
const PAGES = ["index", "logo", "type", "colour", "motion", "art", "use", "downloads"].filter(p => !only || only.split(",").includes(p));
(async () => {
  const b = await chromium.launch();
  for (const [vw, vh, tag] of [[1440, 900, "d"], [390, 844, "m"]]) {
    const ctx = await b.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: tag === "m" ? 2 : 1 });
    for (const p of PAGES) {
      const pg = await ctx.newPage();
      const errs = [];
      pg.on("pageerror", e => errs.push(e.message)); pg.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
      pg.on("requestfailed", r => errs.push("failed " + r.url()));
      await pg.goto(`http://localhost:8811/brand/guidelines/${p}.html`, { waitUntil: "networkidle" });
      await pg.evaluate(() => document.fonts.ready);
      await pg.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); } scrollTo(0, 0); });
      await pg.waitForTimeout(600);
      const sw = await pg.evaluate(() => document.documentElement.scrollWidth);
      await pg.screenshot({ path: `${OUT}/${p}-${tag}-top.png` });
      await pg.screenshot({ path: `${OUT}/${p}-${tag}-full.png`, fullPage: true });
      console.log(p, tag, "scrollWidth", sw, errs.length ? errs.join(" | ") : "");
      await pg.close();
    }
  }
  await b.close();
})();
