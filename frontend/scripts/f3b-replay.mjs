// F3b final QA replay — scenarios 7-12. Same infra as f3a-replay.mjs.
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const EVID = 'H:/UGC/.sisyphus/evidence/final-qa';
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
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
    const page = await ctx.newPage();
    const capture = {};
    await installMocks(page, capture);
    const out = await Promise.race([
      fn(page, ctx, capture),
      new Promise((_, rej) => setTimeout(() => rej(new Error('SCENARIO_TIMEOUT_90s')), 88000)),
    ]);
    results.push({ n, name, status: 'PASS', ms: Date.now() - t0, out });
  } catch (e) {
    const status = String(e.message).includes('SCENARIO_TIMEOUT') ? 'TIMEOUT' : 'FAIL';
    results.push({ n, name, status, ms: Date.now() - t0, err: String(e.message).slice(0, 500) });
  } finally {
    await browser.close();
  }
  const r = results[results.length - 1];
  fs.writeFileSync(path.join(EVID, `scenario-${n}-${r.status.toLowerCase()}.txt`),
    `Scenario ${n}: ${r.status} (${r.ms}ms)\n${r.out || r.err || ''}`);
  console.log(`Scenario ${n} [${name}]: ${r.status} (${r.ms}ms)`);
}

async function freshVisit(page) {
  await page.goto(BASE + '/a1');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByTestId('impulse-cards').waitFor({ timeout: 15000 });
}
const telemetry = (page) => page.evaluate(() => JSON.parse(localStorage.getItem('a1_telemetry_v1') || '[]'));
const shot = (page, name) => page.screenshot({ path: path.join(EVID, name) });

async function exportDownload(page, ctx, filename) {
  // 导出按钮仅在卡片屏页脚（data-testid=impulse-export）；若当前在种子页，清持久化态保留遥测后 reload 回卡片屏
  if (await page.getByTestId('impulse-export').count() === 0) {
    await page.evaluate(() => {
      const t = localStorage.getItem('a1_telemetry_v1');
      localStorage.clear();
      if (t) localStorage.setItem('a1_telemetry_v1', t);
    });
    await page.reload();
    await page.getByTestId('impulse-cards').waitFor({ timeout: 15000 });
  }
  const [dl] = await Promise.all([
    page.waitForEvent('download', { timeout: 15000 }),
    page.getByTestId('impulse-export').click(),
  ]);
  const fp = path.join(EVID, filename);
  await dl.saveAs(fp);
  return fp;
}

// ---- Scenario 7: export + metrics script ----
await runScenario(7, 'export-and-metrics', async (page, ctx) => {
  await freshVisit(page);
  await page.getByTestId('impulse-card-plot').click();
  await page.getByTestId('impulse-confirm').click();
  await page.getByText('✦ 为你推荐').waitFor({ timeout: 10000 });
  const f1 = await exportDownload(page, ctx, 'scenario-7-export-selected.json');
  // skip 场景另开 context（独立 localStorage）产生 skipped 事件
  const b2 = await chromium.launch();
  const ctx2 = await b2.newContext({ acceptDownloads: true });
  const p2 = await ctx2.newPage();
  await installMocks(p2, {});
  await freshVisit(p2);
  await p2.getByTestId('impulse-skip').click();
  await p2.waitForTimeout(800);
  const f2 = await exportDownload(p2, ctx2, 'scenario-7-export-skipped.json');
  await b2.close();
  // 指标脚本逐个跑，stdout 合并落盘
  const { execSync } = await import('child_process');
  let out = '';
  for (const f of [f1, f2]) {
    out += `=== node verify-telemetry-metrics.mjs ${path.basename(f)} ===\n`;
    out += execSync(`node frontend/scripts/verify-telemetry-metrics.mjs ${f}`, { cwd: 'H:/UGC', encoding: 'utf8' });
    out += '\n';
  }
  fs.writeFileSync(path.join(EVID, 'scenario-7-metrics.txt'), out);
  if (/=\s*NaN|= undefined/.test(out) || !out.includes('无 NaN')) throw new Error(`metrics bad output:\n${out.slice(-600)}`);
  return out.slice(0, 400);
});

// ---- Scenario 8: cards screen survives reload ----
await runScenario(8, 'cards-reload', async (page) => {
  await freshVisit(page);
  await page.reload();
  await page.getByTestId('impulse-cards').waitFor({ timeout: 10000 });
  const persisted = await page.evaluate(() => localStorage.getItem('a1_workspace_v1'));
  await shot(page, 'scenario-8-reload-cards.png');
  if (persisted && /impulse_cards/.test(persisted)) throw new Error(`impulse_cards was persisted: ${persisted}`);
  return `impulse-cards visible after reload; a1_workspace_v1=${persisted}`;
});

// ---- Scenario 9: seeds API failure, cards still render ----
await runScenario(9, 'seeds-api-failure', async (page) => {
  await page.route('**/api/a1/seeds', r => r.abort());
  await freshVisit(page);
  const count = await page.locator('[data-testid^="impulse-card-"]').count();
  await shot(page, 'scenario-9-seeds-fail.png');
  if (count !== 9) throw new Error(`expected 9 static cards, got ${count}`);
  return `9 cards rendered with seeds API aborted`;
});

// ---- Scenario 10: session/start failure → error UI, no white screen ----
await runScenario(10, 'startsession-failure', async (page) => {
  await page.route('**/api/a1/session/start', r => r.abort()); // script bug fix: installMocks fulfilled start, so it never failed (F3 observed guided_chat, interactive=4)
  await freshVisit(page);
  await page.getByTestId('impulse-card-healing').click();
  await page.getByTestId('impulse-confirm').click();
  await page.waitForTimeout(3000);
  const errText = await page.getByText('Failed to start session. Please try again.').count();
  await shot(page, 'scenario-10-start-fail.png');
  // 不白屏：页面仍有可交互元素
  const interactive = await page.locator('button, a, [data-testid]').count();
  if (interactive < 1) throw new Error('page appears blank (no interactive elements)');
  if (errText === 0) {
    throw new Error('DEFECT: session/start 失败后无任何错误提示可见——A1Workspace error 仅渲染于 seed_selector(:1063)/guided_chat(:1225)/graph_view(:1611)，' +
      `impulse_cards 分支(:1443)不渲染 error；页面未白屏（interactive=${interactive}，停在卡片屏可操作），但违反 T7 QA 预期"错误提示可见"`);
  }
  return `error toast visible, interactive elements=${interactive}`;
});

// ---- Scenario 11: zero-prefill upload honesty fallback ----
await runScenario(11, 'zero-prefill-upload', async (page) => {
  // 覆盖 upload mock：answers 空
  await page.route('**/api/a1/upload', r => r.fulfill({ json: { ...UPLOAD_PARSED_RESPONSE, answers: {} } }));
  await freshVisit(page);
  await page.getByTestId('impulse-skip').click();
  await page.getByTestId('upload-entry').waitFor({ timeout: 10000 });
  // 复用 F3a 上传文件
  await page.locator('input[type="file"]').first().setInputFiles('C:/Users/Administrator/AppData/Local/Temp/opencode/f3a/world.txt');
  await page.getByTestId('nostalgia-confirm').waitFor({ timeout: 15000 });
  await page.getByText('我们读完了你的文档').waitFor({ timeout: 5000 });
  const recognized = await page.getByText(/认出/).count();
  await shot(page, 'scenario-11-zero-prefill.png');
  if (recognized > 0) throw new Error(`"认出" text appeared in zero-prefill branch (${recognized} nodes)`);
  return 'fallback title shown; zero "认出" text';
});

// ---- Scenario 12: dual tab same context (known telemetry race — observe, no FAIL) ----
await runScenario(12, 'dual-tab-observe', async (page, ctx) => {
  await freshVisit(page);
  const p2 = await ctx.newPage();
  await p2.goto(BASE + '/a1');
  await p2.getByTestId('impulse-cards').waitFor({ timeout: 10000 });
  // 两页均可操作卡片
  await p2.getByTestId('impulse-card-plot').click();
  await page.getByTestId('impulse-card-philosophy').click();
  const tel1 = await telemetry(page);
  const tel2 = await telemetry(p2);
  const lines = [
    `tab1 selected cards: impulse_card_selected=${tel1.filter(e => e.event === 'impulse_card_selected').length}`,
    `tab2 selected cards: impulse_card_selected=${tel2.filter(e => e.event === 'impulse_card_selected').length}`,
    `tab1 total events=${tel1.length}, tab2 total events=${tel2.length}`,
    `NOTE: 已知限制（localStorage 遥测竞态，计划 Must-NOT-Have 明示接受）——观察记录，不判 FAIL`,
    `cross-visibility: tab1 sees tab2's event=${tel1.some(e => e.event === 'impulse_card_selected' && e.data?.primary === 'plot')}, tab2 sees tab1's event=${tel2.some(e => e.event === 'impulse_card_selected' && e.data?.primary === 'philosophy')}`,
  ];
  await shot(page, 'scenario-12-dual-tab.png');
  return lines.join('\n');
});

console.log('\n=== F3b SUMMARY ===');
for (const r of results) console.log(`Scenario ${r.n}: ${r.status} (${r.ms}ms)${r.err ? ' | ' + r.err : ''}`);
const p = results.filter(r => r.status === 'PASS').length;
const f = results.filter(r => r.status === 'FAIL').length;
const t = results.filter(r => r.status === 'TIMEOUT').length;
console.log(`Scenarios 7-12 [${p} pass/${f} fail/${t} timeout]`);
