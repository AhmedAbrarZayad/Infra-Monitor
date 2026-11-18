// usage: node render.js stills 0.5,2.5,...   |  node render.js all
const path = require('path');
const { chromium } = require('C:/Users/ahmed/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core');
const FPS = 30, DUR = 21;
(async () => {
  const mode = process.argv[2];
  const browser = await chromium.launch({ channel: 'chrome' });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file:///' + path.join(__dirname, 'video.html').replace(/\\/g, '/'));
  await page.evaluate(() => window.ready);
  const shot = async (t, file) => {
    await page.evaluate(t => window.render(t), t);
    await page.screenshot({ path: file, type: 'jpeg', quality: 93 });
  };
  if (mode === 'stills') {
    for (const s of process.argv[3].split(',')) await shot(+s, path.join(__dirname, 'stills', `t${(+s).toFixed(2)}.jpg`));
  } else {
    const n = FPS * DUR;
    for (let f = 0; f < n; f++) {
      await shot(f / FPS, path.join(__dirname, 'frames', String(f).padStart(4, '0') + '.jpg'));
      if (f % 60 === 0) console.log('frame', f);
    }
  }
  await browser.close();
})();
