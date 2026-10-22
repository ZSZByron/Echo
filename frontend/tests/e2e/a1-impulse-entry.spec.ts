import { test, expect, Page, Request } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { IMPULSE_CARDS, type ImpulseTypeId } from '../../src/pages/a1/impulse/impulseCards.config';
import { TYPE_SEED_NAMES } from '../../src/pages/a1/impulse/seedGrouping';

/**
 * Playwright E2E — E0 冲动承接入口（计划 e0-impulse-entry T8）
 *
 * 覆盖：
 *  - 9 卡路由矩阵（8 型推荐分组首位逐字 + nostalgia 上传高亮 + healing seed_id=7 + unsure 故事侧首位）
 *  - 主+次多选 telemetry 断言
 *  - skip 路径
 *  - 三条既有路径回归（skip 后种子直选 / custom_idea 一句话开始 / a1_return_intent 直达 guided_chat）
 *  - 埋点导出下载（schema_version=1）+ module_completed 轻量链路（上传确认页）
 *
 * API 策略：沿用 graph.spec 惯例——page.route mock 全部 A1 端点（零 LLM 依赖、零后端依赖），
 * 种子名单逐字取自 src 配置（TYPE_SEED_NAMES 与 preset_loader 名单在 T4 单测中已对齐）。
 * LLM 依赖层面：只断言"请求已发 + body 正确"，不断言 LLM 响应内容。
 */

// ---- 种子 mock：8 预设种子（名单与 backend preset_loader 一致，顺序 id 1-8）----
const PRESET_SEED_NAMES = [
  '深渊低语', '霓虹窃案', '腐化深渊', '灰烬之路',
  '碎天录', '群星彼岸', '破晓之剑', '鸩酒与玫瑰',
] as const;

const SEEDS_RESPONSE = {
  seeds: PRESET_SEED_NAMES.map((name, i) => ({
    id: String(i + 1),
    name,
    genre: '预设',
    description: `${name}——预设种子世界`,
    dimension_defaults: {},
  })),
};

const SESSION_START_RESPONSE = {
  session_id: 'sess-e2e',
  file_id: 'file-e2e',
  ip_code: 'A1-E2E-0001',
  seed: null,
  file: { status: 'draft', sections: [] },
  first_question: {
    section: 'opening',
    section_label: '开场',
    question: '这个世界叫什么名字？',
  },
};

const CHAT_RESPONSE = {
  reply: '收到，我们继续。',
  progress: { sections: [], finalizable: false },
};

const FILE_STATE_RESPONSE = {
  status: 'draft',
  sections: [],
  open_questions: [],
  edge_stats: { semantic_total: 0, semantic_confirmed: 0, rule_total: 0, structure_total: 0, pending_review: 0 },
  confirmed_edges: {},
  rejected_edges: {},
};

const UPLOAD_PARSED_RESPONSE = {
  status: 'parsed',
  upload_id: 'up-e2e',
  session_id: 'sess-upload',
  file_id: 'file-upload',
  ip_code: 'A1-E2E-0002',
  seed: null,
  answers: { world_name: '艾欧尼亚' },
  innovations: [],
  file: {
    status: 'draft',
    sections: [
      {
        id: 'world_core',
        label: '世界内核',
        done: true,
        subs: [
          { id: 'core_a', label: '世界名称', done: true },
          { id: 'core_b', label: '基本面貌', done: true },
        ],
      },
    ],
  },
};

type StartCapture = { url: string; body: Record<string, unknown> | null };

/** 安装 A1 API mock；session/start 的请求 body 捕获进 capture（healing/custom_idea 断言用） */
async function installApiMocks(page: Page, capture: { start?: StartCapture }) {
  await page.route('**/api/a1/seeds', (route) => route.fulfill({ json: SEEDS_RESPONSE }));
  await page.route('**/api/a1/session/start', async (route) => {
    const req: Request = route.request();
    capture.start = { url: req.url(), body: req.postDataJSON() as Record<string, unknown> };
    await route.fulfill({ json: SESSION_START_RESPONSE });
  });
  await page.route('**/api/a1/chat', (route) => route.fulfill({ json: CHAT_RESPONSE }));
  // 会话状态水合（fileId 变更触发）：404 会触发 stale-session 回退，必须 mock 成合法态
  await page.route('**/api/a1/file/**', (route) => route.fulfill({ json: FILE_STATE_RESPONSE }));
  await page.route('**/api/a1/upload', (route) => route.fulfill({ json: UPLOAD_PARSED_RESPONSE }));
}

/** 每用例前置：mock 安装后进 /a1v2 清 localStorage 再刷新（新用户 → 卡片屏） */
async function freshVisit(page: Page) {
  await page.goto('/a1v2');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await expect(page.getByTestId('impulse-cards')).toBeVisible();
}

async function readTelemetry(page: Page): Promise<Array<Record<string, unknown>>> {
  return page.evaluate(() => JSON.parse(localStorage.getItem('a1_telemetry_v1') || '[]'));
}

async function pickAndConfirm(page: Page, type: ImpulseTypeId) {
  await page.getByTestId(`impulse-card-${type}`).click();
  await page.getByTestId('impulse-confirm').click();
}

const readMe = (page: Page) => page.locator('div.grid h3').first(); // 种子网格首位卡名

// ==========================================
// SUITE 1: 9 卡路由矩阵
// ==========================================

test.describe('9 卡路由矩阵（E0.1 分流：故事侧直达访谈 / 设定侧种子分组 + 型特化路由）', () => {
  // E0.1 故事侧 5 型：确认后直达访谈（custom_idea 通道）
  const STORY_SIDE: ImpulseTypeId[] = ['plot', 'romance', 'philosophy', 'unsure', 'character_driven'];
  for (const card of IMPULSE_CARDS) {
    if (!STORY_SIDE.includes(card.id)) continue;
    test(`型 ${card.id} → 直达访谈（entryNotice + custom_idea 含 tagline）`, async ({ page }) => {
      const capture: { start?: StartCapture } = {};
      await installApiMocks(page, capture);
      await freshVisit(page);

      await pickAndConfirm(page, card.id);

      // 引导横幅可见（含该型 tagline 文本）
      await expect(page.getByTestId('impulse-entry-notice')).toBeVisible();
      await expect(page.getByTestId('impulse-entry-notice')).toContainText(card.tagline);
      // 直达 guided_chat（聊天输入框可见，不落种子页）
      await expect(page.locator('input[placeholder="Type your message..."]')).toBeVisible();
      // session/start body.custom_idea 含 tagline 关键词；unsure 特殊断言含"说不清"引导文本
      expect(capture.start).toBeDefined();
      const customIdea = String(capture.start!.body!.custom_idea);
      expect(customIdea).toContain(card.tagline);
      if (card.id === 'unsure') expect(customIdea).toContain('说不清');
    });
  }

  // 设定侧 2 型：保持分组种子页（世界观模板是他们的真实需求）
  for (const card of IMPULSE_CARDS) {
    if (card.id !== 'setting_heavy' && card.id !== 'exploration') continue;
    test(`型 ${card.id} → 推荐首位「${TYPE_SEED_NAMES[card.id][0]}」`, async ({ page }) => {
      const capture: { start?: StartCapture } = {};
      await installApiMocks(page, capture);
      await freshVisit(page);

      await pickAndConfirm(page, card.id);

      // 推荐分组标题 + matched 首位名称逐字
      await expect(page.getByText('✦ 为你推荐')).toBeVisible();
      await expect(readMe(page)).toHaveText(TYPE_SEED_NAMES[card.id][0]);
    });
  }

  test('nostalgia → 停在种子页 + 上传入口高亮（ring 3 秒）', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await freshVisit(page);

    await pickAndConfirm(page, 'nostalgia');

    const uploadEntry = page.getByTestId('upload-entry');
    await expect(uploadEntry).toBeVisible();
    await expect(uploadEntry).toHaveClass(/ring-2/, { timeout: 3000 });
    // 卡片屏已退场、未发 session/start（怀旧不走种子直达）
    await expect(page.getByTestId('impulse-cards')).toHaveCount(0);
    expect(capture.start).toBeUndefined();
  });

  test('healing → POST /api/a1/session/start body seed_id=7 + 陪伴横幅', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await freshVisit(page);

    await pickAndConfirm(page, 'healing');

    await expect(page.getByText('知道了')).toBeVisible(); // healingNotice 横幅关闭钮
    expect(capture.start).toBeDefined();
    // 前端发字符串 '7'，后端 Pydantic 强转整数——按数值语义断言
    expect(Number(capture.start!.body!.seed_id)).toBe(7);
    await expect(page.locator('input[placeholder="Type your message..."]')).toBeVisible();
  });
});

// ==========================================
// SUITE 2: 主+次多选 + skip
// ==========================================

test.describe('主+次多选与 skip', () => {
  test('选主+次确认 → telemetry 记录 primary/secondary', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await freshVisit(page);

    await page.getByTestId('impulse-card-plot').click();
    await expect(page.getByTestId('impulse-card-plot')).toHaveAttribute('data-selected', 'primary');
    await page.getByTestId('impulse-card-romance').click();
    await expect(page.getByTestId('impulse-card-romance')).toHaveAttribute('data-selected', 'secondary');

    await page.getByTestId('impulse-confirm').click();

    const events = await readTelemetry(page);
    const selected = events.find((e) => e.event === 'impulse_card_selected');
    expect(selected).toBeDefined();
    expect((selected!.data as Record<string, unknown>).primary).toBe('plot');
    expect((selected!.data as Record<string, unknown>).secondary).toBe('romance');
    expect(selected!.schema_version).toBe(1);
  });

  test('skip → 落 seed_selector 平铺视图 + telemetry 记录 skipped', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await freshVisit(page);

    const skipBtn = page.getByTestId('impulse-skip');
    await expect(skipBtn).toBeVisible();
    await expect(skipBtn).toBeEnabled(); // 不选卡也可跳过（D2-③ 常驻）
    await skipBtn.click();

    await expect(page.getByRole('heading', { name: '世界观工坊' })).toBeVisible();
    await expect(page.getByText('✦ 为你推荐')).toHaveCount(0); // 平铺无分组标题
    await expect(page.getByTestId('upload-entry')).toBeVisible();

    const events = await readTelemetry(page);
    expect(events.some((e) => e.event === 'impulse_card_skipped')).toBe(true);
    expect(capture.start).toBeUndefined();
  });
});

// ==========================================
// SUITE 3: 三条既有路径回归
// ==========================================

test.describe('既有路径回归', () => {
  test('skip 后种子直选 → guided_chat（不经卡片确认按钮）', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await freshVisit(page);

    await page.getByTestId('impulse-skip').click();
    await page.getByText('霓虹窃案').first().click();

    await expect(page.locator('input[placeholder="Type your message..."]')).toBeVisible();
    expect(capture.start).toBeDefined();
    expect(capture.start!.body!.seed_id).toBeDefined();
  });

  test('custom_idea 中文一句话开始 → 请求含 custom_idea + 首答埋点', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await freshVisit(page);

    await page.getByTestId('impulse-skip').click();
    await expect(page.getByRole('heading', { name: '或者，从一个念头开始' })).toBeVisible();

    await page.fill('input[placeholder*="一句话描述"]', '一个雨永远下不停的港口城市');
    await page.getByRole('button', { name: '开始' }).click();

    expect(capture.start).toBeDefined();
    expect(capture.start!.body!.custom_idea).toBe('一个雨永远下不停的港口城市');
    await expect(page.locator('input[placeholder="Type your message..."]')).toBeVisible();

    // 首答埋点在发送时打点（不依赖 LLM 响应）：发出第一条消息即应记录
    await page.fill('input[placeholder="Type your message..."]', '这座城市叫雾锚港');
    await page.getByRole('button', { name: 'Send' }).click();

    const events = await readTelemetry(page);
    const first = events.find((e) => e.event === 'first_question_answered');
    expect(first).toBeDefined();
    expect(typeof (first!.data as Record<string, unknown>).elapsed_ms).toBe('number');
  });

  test('a1_return_intent=chat 预置 → 直达 guided_chat，卡片屏不劫持', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await page.addInitScript(() => {
      localStorage.setItem(
        'a1_workspace_v1',
        JSON.stringify({
          workspaceState: 'guided_chat',
          sessionId: 'sess-return',
          messages: [{ id: '1', type: 'assistant', text: '欢迎回来。' }],
        }),
      );
      localStorage.setItem('a1_return_intent', 'chat');
    });

    await page.goto('/a1v2');

    await expect(page.locator('input[placeholder="Type your message..."]')).toBeVisible();
    await expect(page.getByTestId('impulse-cards')).toHaveCount(0);
    expect(capture.start).toBeUndefined();
  });
});

// ==========================================
// SUITE 4: 埋点导出 + module_completed 轻量链路
// ==========================================

test.describe('埋点导出与模块完成', () => {
  test('多事件积累后导出 → 下载 JSON schema_version=1（并落盘供 R1 指标脚本）', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await freshVisit(page);

    // 真实事件流：shown → selected(plot，E0.1 直达访谈) → 首答
    await page.getByTestId('impulse-card-plot').click();
    await page.getByTestId('impulse-confirm').click();
    await page.locator('input[placeholder="Type your message..."]').waitFor({ timeout: 10000 });
    await page.fill('input[placeholder="Type your message..."]', '山叫负岳');
    await page.getByRole('button', { name: 'Send' }).click();

    const beforeExport = await readTelemetry(page);
    expect(beforeExport.some((e) => e.event === 'impulse_card_shown')).toBe(true);
    expect(beforeExport.some((e) => e.event === 'impulse_card_selected')).toBe(true);
    expect(beforeExport.some((e) => e.event === 'first_question_answered')).toBe(true);

    // 回到卡片屏（impulse_cards 不持久化 → 清持久化态重载），保留遥测，再补一次 skip
    const keep = () => page.evaluate(() => {
      const t = localStorage.getItem('a1_telemetry_v1');
      localStorage.clear();
      if (t) localStorage.setItem('a1_telemetry_v1', t);
    });
    await keep();
    await page.reload();
    await expect(page.getByTestId('impulse-cards')).toBeVisible();
    await page.getByTestId('impulse-skip').click();
    await expect(page.getByRole('heading', { name: '世界观工坊' })).toBeVisible();

    // 再次回卡片屏导出
    await keep();
    await page.reload();
    await expect(page.getByTestId('impulse-cards')).toBeVisible();

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('impulse-export').click(),
    ]);

    const outPath = path.join(process.cwd(), 'test-results', 'telemetry-export.json');
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    await download.saveAs(outPath);

    const exported = JSON.parse(fs.readFileSync(outPath, 'utf-8')) as Array<Record<string, unknown>>;
    expect(Array.isArray(exported)).toBe(true);
    expect(exported.length).toBeGreaterThan(0);
    expect(exported[0].schema_version).toBe(1);
    // 导出 = 存储全量（导出不清空）
    const afterExport = await readTelemetry(page);
    expect(afterExport.length).toBe(exported.length);
  });

  test('上传链 → 确认页"它认出了你的世界" → 继续 → module_completed 记录', async ({ page }) => {
    const capture: { start?: StartCapture } = {};
    await installApiMocks(page, capture);
    await freshVisit(page);

    await page.getByTestId('impulse-skip').click();
    await page
      .getByTestId('upload-entry')
      .locator('input[type="file"]')
      .setInputFiles(path.resolve(process.cwd(), 'tests', 'e2e', 'fixtures', 'world.txt'));

    // 预填确认页（answers 有 1 个有效值 → 有预填文案）
    await expect(page.getByTestId('nostalgia-confirm')).toBeVisible();
    await expect(page.getByRole('heading', { name: '它认出了你的世界' })).toBeVisible();
    await page.getByTestId('nostalgia-continue').click();

    await expect(page.locator('input[placeholder="Type your message..."]')).toBeVisible();

    // mock sections world_core 2/2 done ≥50% → module_completed 事件（轻量验证重链路埋点）
    const events = await readTelemetry(page);
    const mod = events.find((e) => e.event === 'module_completed');
    expect(mod).toBeDefined();
    expect((mod!.data as Record<string, unknown>).module_id).toBe('world_core');
  });
});
