// F3a final QA replay — scenarios 1-6, API fully mocked, per-scenario 90s budget.
// Evidence written incrementally to H:/UGC/.sisyphus/evidence/final-qa/
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const EVID = 'H:/UGC/.sisyphus/evidence/final-qa';
const UPLOAD_FILE = 'C:/Users/Administrator/AppData/Local/Temp/opencode/f3a/world.txt';
const BASE = 'http://localhost:5173';

const SEEDS_RESPONSE = {
  seeds: ['深渊低语','霓虹窃案','腐化深渊','灰烬之路','碎天录','群星彼岸','破晓之剑','鸩酒与玫瑰'].map((name, i) => ({
    id: String(i + 1), name, genre: '预设', description: `${name}——预设种子世界`, dimension_defaults: {},
  })),
};
const SESSION_START_RESPONSE = {
  session_id: 'sess-e2e', file_id: 'file-e2e', ip_code: 'A1-E2E-0001', seed: null,
  file: { status: 'draft', sections: [] },
  first_question: { section: 'opening', section_label: '开场', question: '这个世界叫什么名字？' },
};
const CHAT_RESPONSE = { reply: '收到，我们继续。', progress: { sections: [], finalizable: false } };
const FILE_STATE_RESPONSE = {
  status: 'draft', sections: [], open_questions: [],
  edge_stats: { semantic_total: 0, semantic_confirmed: 0, rule_total: 0, structure_total: 0, pending_review: 0 },
  confirmed_edges: {}, rejected_edges: {},
};
const UPLOAD_PARSED_RESPONSE = {
  status: 'parsed', upload_id: 'up-e2e', session_id: 'sess-upload', file_id: 'file-upload',
  ip_code: 'A1-E2E-0002', seed: null, answers: { world_name: '艾欧尼亚' }, innovations: [],
  file: { status: 'draft', sections: [{ id: 'world_core', label: '世界内核', done: true,
    subs: [{ id: 'core_a', label: '世界名称', done: true }, { id: 'core_b', label: '基本面貌', done: true }] }] },
};

async function installMocks(page, capture) {
  await page.route('**/api/a1/seeds', r => r.fulfill({ json: SEEDS_RESPONSE }));
  await page.route('**/api/a1/session/start', async r => {
    capture.start = r.request().postDataJSON();
    await r.fulfill({ json: SESSION_START_RESPONSE });
  });
  await page.route('**/api/a1/chat', r => r.fulfill({ json: CHAT_RESPONSE }));
  await page.route('**/api/a1/file/**', r => r.fulfill({ json: FILE_STATE_RESPONSE }));
  await page.route('**/api/a1/upload', r => r.fulfill({ json: UPLOAD_PARSED_RESPONSE }));
}

const results = [];
async function runScenario(n, name, fn) {
  const t0 = Date.now();
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const capture = {};
    await installMocks(page, capture);
    const ok = await Promise.race([
      fn(page, capture).then(() => 'PASS'),
      new Promise((_, rej) => setTimeout(() => rej(new Error('SCENARIO_TIMEOUT_90s')), 88000)),
    ]);
    results.push({ n, name, status: ok, ms: Date.now() - t0 });
  } catch (e) {
    const status = String(e.message).includes('SCENARIO_TIMEOUT') ? 'TIMEOUT' : 'FAIL';
    results.push({ n, name, status, ms: Date.now() - t0, err: String(e.message).slice(0, 500) });
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(EVID, `scenario-${n}-${results[results.length - 1].status.toLowerCase()}.txt`),
    `Scenario ${n}: ${results[results.length - 1].status} (${results[results.length - 1].ms}ms)\n${results[results.length - 1].err || ''}`);
  console.log(`Scenario ${n} [${name}]: ${results[results.length - 1].status} (${results[results.length - 1].ms}ms)`);
}

async function freshVisit(page) {
  await page.goto(BASE + '/a1');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByTestId('impulse-cards').waitFor({ timeout: 15000 });
}
const telemetry = (page) => page.evaluate(() => JSON.parse(localStorage.getItem('a1_telemetry_v1') || '[]'));
const shot = (page, name) => page.screenshot({ path: path.join(EVID, name), fullPage: false });

// ---- Scenario 1: new user full chain（E0.1：剧情+爱情 → 直达访谈 custom_idea）----
await runScenario(1, 'new-user-full-chain', async (page, capture) => {
  await freshVisit(page);
  const cards = page.locator('[data-testid^="impulse-card-"]');
  if (await cards.count() !== 9) throw new Error(`expected 9 cards, got ${await cards.count()}`);
  await shot(page, 'scenario-1-cards.png');
  await page.getByTestId('impulse-card-plot').click();
  await page.getByTestId('impulse-card-romance').click();
  await page.getByTestId('impulse-confirm').click();
  // E0.1: 故事侧直达访谈——entryNotice 可见 + 聊天输入框出现
  await page.getByTestId('impulse-entry-notice').waitFor({ timeout: 10000 });
  await page.locator('input[placeholder="Type your message..."]').waitFor({ timeout: 10000 });
  await shot(page, 'scenario-1-interview.png');
  for (let i = 0; i < 40 && !capture.start; i++) await page.waitForTimeout(250);
  if (!capture.start) throw new Error('session/start never fired');
  const ci = String(capture.start.custom_idea || '');
  if (!ci.includes('我想看故事开场') || !ci.includes('其次')) throw new Error(`custom_idea wrong: ${ci}`);
  fs.writeFileSync(path.join(EVID, 'scenario-1-start-body.json'), JSON.stringify(capture.start, null, 2));
  const tel = await telemetry(page);
  const shown = tel.find(e => e.event === 'impulse_card_shown');
  const sel = tel.find(e => e.event === 'impulse_card_selected');
  if (!shown) throw new Error('no impulse_card_shown');
  if (!sel || sel.data?.primary !== 'plot' || sel.data?.secondary !== 'romance')
    throw new Error(`selected event wrong: ${JSON.stringify(sel)}`);
  fs.writeFileSync(path.join(EVID, 'scenario-1-telemetry.json'), JSON.stringify(tel, null, 2));
});

// ---- Scenario 1b: builder type（设定-重度）仍走分组种子页（E0.1）----
await runScenario('1b', 'builder-seeds-page', async (page, capture) => {
  await freshVisit(page);
  await page.getByTestId('impulse-card-setting_heavy').click();
  await page.getByTestId('impulse-confirm').click();
  await page.getByText('✦ 为你推荐').waitFor({ timeout: 10000 });
  const firstName = await page.locator('div.grid h3').first().textContent();
  if (firstName !== '群星彼岸') throw new Error(`first seed expected 群星彼岸, got ${firstName}`);
  if (capture.start) throw new Error('session/start should not fire for builder types');
  await shot(page, 'scenario-1b-seeds.png');
});

// ---- Scenario 2: skip chain ----
await runScenario(2, 'skip-chain', async (page) => {
  await freshVisit(page);
  await page.getByTestId('impulse-skip').click();
  await page.getByText('✦ 为你推荐').waitFor({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(500);
  const recTitle = await page.getByText('✦ 为你推荐').count();
  if (recTitle > 0) throw new Error('grouped title should NOT appear after skip');
  await shot(page, 'scenario-2-skip-seeds.png');
  const tel = await telemetry(page);
  if (!tel.find(e => e.event === 'impulse_card_skipped')) throw new Error('no impulse_card_skipped event');
});

// ---- Scenario 3: healing direct ----
await runScenario(3, 'healing-direct', async (page, capture) => {
  await freshVisit(page);
  await page.getByTestId('impulse-card-healing').click();
  await page.getByTestId('impulse-confirm').click();
  for (let i = 0; i < 40 && !capture.start; i++) await page.waitForTimeout(250);
  if (!capture.start) throw new Error('session/start never fired');
  if (Number(capture.start.seed_id) !== 7) throw new Error(`seed_id expected 7, got ${JSON.stringify(capture.start)}`);
  await page.getByText(/陪你|一起|轻松|慢慢|不急/).first().waitFor({ timeout: 15000 });
  await shot(page, 'scenario-3-healing.png');
  fs.writeFileSync(path.join(EVID, 'scenario-3-start-body.json'), JSON.stringify(capture.start, null, 2));
});

// ---- Scenario 4: nostalgia route ----
await runScenario(4, 'nostalgia-route', async (page) => {
  await freshVisit(page);
  await page.getByTestId('impulse-card-nostalgia').click();
  await page.getByTestId('impulse-confirm').click();
  await page.waitForTimeout(500);
  const entry = page.getByTestId('upload-entry');
  await entry.waitFor({ timeout: 10000 });
  await shot(page, 'scenario-4-nostalgia-ring.png');
  const cls = await entry.getAttribute('class');
  if (!/ring/.test(cls || '')) throw new Error(`no ring highlight class: ${cls}`);
});

// ---- Scenario 5: upload confirm page ----
await runScenario(5, 'upload-confirm-page', async (page) => {
  await freshVisit(page);
  await page.getByTestId('impulse-skip').click();
  await page.getByTestId('upload-entry').waitFor({ timeout: 10000 });
  await page.locator('input[type="file"]').first().setInputFiles(UPLOAD_FILE);
  await page.getByText('它认出了你的世界').waitFor({ timeout: 15000 });
  await page.getByText(/认出了 1 处|1 处设定/).waitFor({ timeout: 5000 });
  await shot(page, 'scenario-5-confirm.png');
  await page.getByTestId('nostalgia-continue').click();
  await page.locator('input[placeholder="Type your message..."]').waitFor({ timeout: 15000 });
  await shot(page, 'scenario-5-interview.png');
});

// ---- Scenario 6: returning user not hijacked ----
await runScenario(6, 'returning-user', async (page) => {
  await page.goto(BASE + '/a1');
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem('a1_workspace_v1', JSON.stringify({
      workspaceState: 'guided_chat', sessionId: 's1', fileId: 'f1', ipCode: '', seedInfo: null, messages: [],
    }));
  });
  await page.goto(BASE + '/a1');
  await page.waitForTimeout(1500);
  const cards = await page.getByTestId('impulse-cards').count();
  if (cards > 0) throw new Error('impulse cards appeared for returning user');
  // guided_chat visible: chat input or interview present
  await page.locator('textarea, input[type="text"]').first().waitFor({ timeout: 10000 });
  await shot(page, 'scenario-6-returning.png');
});

console.log('\n=== F3a SUMMARY ===');
for (const r of results) console.log(`Scenario ${r.n}: ${r.status} (${r.ms}ms)${r.err ? ' | ' + r.err : ''}`);
const p = results.filter(r => r.status === 'PASS').length;
const f = results.filter(r => r.status === 'FAIL').length;
const t = results.filter(r => r.status === 'TIMEOUT').length;
console.log(`Scenarios 1-6 [${p} pass/${f} fail/${t} timeout]`);
