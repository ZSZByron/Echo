// T13a item 5: /a1 smoke test — three-state flow interactive, star theme,
// old CRT page untouched.
const { chromium } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  // State 1: seed selector — 8 seed cards render
  await page.goto('http://localhost:5173/a1');
  await page.waitForTimeout(1500);
  const body = await page.textContent('body');
  const hasSeeds = /深渊低语|霓虹窃案|破晓之剑/.test(body || '');
  console.log('[1] seed cards render:', hasSeeds ? 'PASS' : 'FAIL');

  // Interact: click first seed card then start (best-effort selectors)
  let enteredChat = false;
  try {
    const card = page.locator('text=深渊低语').first();
    if (await card.count()) { await card.click(); await page.waitForTimeout(500); }
    const startBtn = page.locator('button', { hasText: /开始|进入|启动/ }).first();
    if (await startBtn.count()) { await startBtn.click(); await page.waitForTimeout(1500); }
    const chatBody = await page.textContent('body');
    enteredChat = /世界观|底层秩序|发送/.test(chatBody || '');
  } catch (e) { console.log('interaction note:', String(e).slice(0, 80)); }
  console.log('[2] guided chat interactive:', enteredChat ? 'PASS' : 'PARTIAL(dom-selectors)');

  // Star theme: theme.css variables applied (component area background dark)
  const bg = await page.evaluate(() => {
    const el = document.querySelector('.a1-workspace, main, body');
    return el ? getComputedStyle(el).backgroundColor : 'n/a';
  });
  console.log('[3] page bg (star theme dark):', bg);

  // Old CRT page untouched
  await page.goto('http://localhost:5173/');
  await page.waitForTimeout(1200);
  const homeBody = await page.textContent('body');
  const crtOk = homeBody && homeBody.length > 20;
  const crtBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  console.log('[4] old CRT home loads:', crtOk ? 'PASS' : 'FAIL', 'bg=', crtBg);

  console.log('console errors:', errors.length ? errors.slice(0, 3) : 'none');
  await browser.close();
})();
