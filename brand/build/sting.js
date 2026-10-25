// Renders the sting frame by frame at 30 fps and encodes MP4 with ffmpeg.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const { execSync } = require('child_process');
(async () => {
  const b = await chromium.launch();
  for (const [w, h] of [[1080, 1080], [1920, 1080]]) {
    const dir = `/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/frames-${w}`; fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
    const p = await b.newPage({ viewport: { width: w, height: h } });
    await p.goto('file://' + path.resolve(`pages/sting-${w}x${h}.html`)); await p.evaluate(() => document.fonts.ready);
    const N = 6.2 * 30;
    for (let i = 0; i < N; i++) { await p.evaluate(t => window.at(t), i / 30); await p.screenshot({ path: `${dir}/f${String(i).padStart(4, '0')}.png` }); }
    fs.mkdirSync('../exports/motion', { recursive: true });
    execSync(`ffmpeg -y -loglevel error -framerate 30 -i ${dir}/f%04d.png -c:v libx264 -pix_fmt yuv420p -crf 16 -movflags +faststart ../exports/motion/bond-sting-${w}x${h}.mp4`);
    await p.close();
  }
  await b.close(); console.log('ok');
})();
