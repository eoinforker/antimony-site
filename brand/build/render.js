// Renders every page in pages/manifest.json to ../exports at its true size (and 2x where set); cards also to PDF.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
(async () => {
  const man = JSON.parse(fs.readFileSync('pages/manifest.json')); const b = await chromium.launch();
  for (const m of man) {
    const ctx = await b.newContext({ viewport: { width: m.w, height: m.h }, deviceScaleFactor: m.scale });
    const p = await ctx.newPage(); await p.goto('file://' + path.resolve('pages', m.name + '.html'));
    await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(150);
    const out = path.resolve('../exports', m.name + '.png'); fs.mkdirSync(path.dirname(out), { recursive: true });
    await p.screenshot({ path: out });
    if (m.pdf) await p.pdf({ path: out.replace('.png', '.pdf'), width: m.pdf[0] + 'mm', height: m.pdf[1] + 'mm', printBackground: true, pageRanges: '1', scale: (m.pdf[0] * 96 / 25.4) / m.w });
    await ctx.close();
  }
  await b.close(); console.log('rendered', man.length);
})();
