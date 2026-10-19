import { test, expect, Page } from '@playwright/test';

/**
 * Playwright E2E —— 波次三前端批四幕（a1-wave3-frontend 施工单 T6 验收）
 *
 * 四幕（路由 mock 全部 A1 端点，零 LLM 依赖——a1-impulse-entry.spec 先例）：
 *  1. 开场语：冲动入口 → 一句话开始 → 新开场语（与 interviewer.py cadfcb3 同源）可见
 *  2. 图谱边：graph_view 直达 → migration/linkage/未知边三类渲染（真浏览器 SVG 可断言；
 *     jsdom 不可——vitest 侧以 edgeVisualStyle 纯函数守门）
 *  3. 活地图：图谱页「活地图」tab → 七大陆渲染 + 已答亮起
 *  4. 灵感架：活地图 tab 下 RackPanel 存量可见 + [安家] 点击 → 既有 /api/a1/chat 投递
 */

// ---- 共享 mock 载荷 ----

const SEEDS_RESPONSE = {
  seeds: [
    {
      id: '1',
      name: '深渊低语',
      genre: '预设',
      description: '深渊低语是一个预设世界观种子',
      dimension_defaults: {},
    },
  ],
};

const SESSION_START_RESPONSE = {
  session_id: 'sess-e2e',
  file_id: 'file-e2e',
  ip_code: 'A1-E2E-0001',
  // 一句话开始路径：seed 无 name 有 description → 新开场语分支（L649）
  seed: { description: '一个失忆钟表匠的悬疑世界' },
  first_question: {
    section: 'story_line',
    section_label: '剧情',
    question: '故事的核心两难是什么？',
  },
  file: { status: 'draft', sections: [] },
};

const CHAT_RESPONSE = {
  reply: '收到，已记下你的想法。',
  progress: { sections: [], finalizable: false },
};

const GRAPH_RESPONSE = {
  scene_id: 'sess-e2e',
  background_node_id: 'bg',
  nodes: {
    bg: { id: 'bg', serial_number: '1', level: 1, description: 'World Background', status: 'completed' },
    'm-1-1': { id: 'm-1-1', serial_number: '1-1', level: 2, description: '地理模块', status: 'completed', continent: 'worldview' },
    'm-2-1': { id: 'm-2-1', serial_number: '2-1', level: 2, description: '文化模块', status: 'completed', continent: 'worldview' },
    'e-1-1-1': { id: 'e-1-1-1', serial_number: '1-1-1', level: 3, description: '地理: 环形群岛', status: 'completed' },
  },
  edges: [
    { from_node_id: 'bg', to_node_id: 'm-1-1', edge_type: 'tree', visual_description: '' },
    { from_node_id: 'bg', to_node_id: 'm-2-1', edge_type: 'tree', visual_description: '' },
    { from_node_id: 'm-1-1', to_node_id: 'e-1-1-1', edge_type: 'tree', visual_description: '' },
    {
      from_node_id: 'm-1-1',
      to_node_id: 'm-2-1',
      edge_type: 'migration',
      visual_description: '从战后废墟到重建之城',
      relation: '迁移',
      confidence: '',
      confirmed: true,
    },
    {
      from_node_id: 'bg',
      to_node_id: 'e-1-1-1',
      edge_type: 'linkage',
      visual_description: '威望·上升',
      relation: '衔接',
      confidence: '',
      confirmed: true,
    },
    {
      from_node_id: 'm-2-1',
      to_node_id: 'e-1-1-1',
      edge_type: 'warp',
      visual_description: '跃迁',
      relation: '',
      confidence: '',
    },
  ],
};

const FILE_STATE_RESPONSE = {
  file_id: 'file-e2e',
  status: 'finalized',
  session_id: 'sess-e2e',
  answers: {},
  answers_tree: {},
  graph_code: 'G1',
  sections: [],
  open_questions: [],
  edge_stats: {
    semantic_total: 0,
    semantic_confirmed: 0,
    rule_total: 0,
    structure_total: 3,
    pending_review: 0,
  },
  confirmed_edges: {},
  rejected_edges: {},
  concept_terms: [],
  proposed_relations: [],
  finalize_warnings: [],
  warnings: [],
  dead_edges: [],
  material_pool: [
    { text: '主角的怀表能倒转七秒', home: '命运' },
  ],
};

// P0-7（商业加固批）：closing-state 专用正常载荷——带完整 preview
// （历史缺陷：通配 file 路由遮蔽了 closing-state → 载荷无 preview →
//  `closingState?.preview.consumers` 整树崩溃）。
const CLOSING_STATE_RESPONSE = {
  file_id: 'file-e2e',
  triggered: false,
  closing_step: 0,
  settled: false,
  preview: {
    consumers: [],
    modules: [],
    missing_modules: [],
    finalize_ready: false,
  },
};

// 幕五专用：故意畸形的 closing-state 载荷（模拟端点演进/降级异常形状）——
// triggered=true + preview.consumers 非数组 → ClosingPanel 渲染必然抛错，
// 用于验证 ErrorBoundary 崩溃降级（错误卡可见 + 页面存活，绝不白屏）。
const CLOSING_STATE_MALFORMED_RESPONSE = {
  file_id: 'file-e2e',
  triggered: true,
  closing_step: 1,
  settled: false,
  preview: {
    consumers: 'not-an-array',
  },
};

interface ChatCapture {
  bodies: Array<Record<string, unknown>>;
}

/** 装全套 A1 路由 mock；返回 chat 请求捕获器 */
async function mockA1Endpoints(page: Page): Promise<ChatCapture> {
  const capture: ChatCapture = { bodies: [] };
  await page.route('**/api/a1/seeds', (route) => route.fulfill({ json: SEEDS_RESPONSE }));
  await page.route('**/api/a1/session/start', (route) => route.fulfill({ json: SESSION_START_RESPONSE }));
  await page.route('**/api/a1/chat', async (route) => {
    const req = route.request();
    try {
      capture.bodies.push(req.postDataJSON() as Record<string, unknown>);
    } catch {
      /* body 非 JSON 时忽略 */
    }
    await route.fulfill({ json: CHAT_RESPONSE });
  });
  // 注意注册顺序：Playwright 后注册者优先——专用路由必须晚于通配 file 路由注册
  await page.route('**/api/a1/file/**', (route) => route.fulfill({ json: FILE_STATE_RESPONSE }));
  await page.route('**/api/a1/file/**/graph', (route) => route.fulfill({ json: GRAPH_RESPONSE }));
  // P0-7：closing-state 专用 mock —— 后注册，抢在通配 file 路由之前命中
  // （此前被遮蔽 → closingState 收到无 preview 的载荷 → 渲染崩溃）
  await page.route('**/api/a1/file/**/closing-state', (route) => route.fulfill({ json: CLOSING_STATE_RESPONSE }));
  return capture;
}

/** 预置持久化工作区状态：直达 graph_view（graph 幕共用） */
async function seedGraphViewStorage(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('a1_workspace_v1', JSON.stringify({
      workspaceState: 'graph_view',
      sessionId: 'sess-e2e',
      fileId: 'file-e2e',
      messages: [],
    }));
    localStorage.setItem('user_id', 'u-e2e');
  });
}

/** 预置持久化工作区状态：直达 guided_chat（崩溃降级幕共用） */
async function seedGuidedChatStorage(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('a1_workspace_v1', JSON.stringify({
      workspaceState: 'guided_chat',
      sessionId: 'sess-e2e',
      fileId: 'file-e2e',
      ipCode: 'A1-E2E-0001',
      messages: [],
    }));
    localStorage.setItem('user_id', 'u-e2e');
  });
}

test.describe('波次三前端四幕（路由 mock，零 LLM）', () => {
  test('幕一 开场语：一句话开始 → 新开场语同源可见，旧语缺席', async ({ page }) => {
    await mockA1Endpoints(page);
    await page.goto('/a1');

    // 冲动入口 → 剧情卡 → 确认（一句话开始路径）
    await page.getByTestId('impulse-card-plot').click();
    await page.getByTestId('impulse-confirm').click();

    // 新开场语（与 interviewer.py cadfcb3 同源）
    await expect(page.getByText(/接下来我会一次问你一个问题/)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/帮你把它变成一个完整的世界/)).toBeVisible();
    // 旧语清零
    await expect(page.getByText(/我将围绕/)).toHaveCount(0);
  });

  test('幕二 图谱边：migration/linkage/未知边三类渲染', async ({ page }) => {
    await mockA1Endpoints(page);
    await seedGraphViewStorage(page);
    await page.goto('/a1');

    // 图谱画布渲染（真浏览器 React Flow）
    await expect(page.locator('.react-flow__node').first()).toBeVisible({ timeout: 15000 });

    // 三类边：迁移（橙红）/衔接（青）/未知（灰降级 + 标签）
    await expect(page.locator('.react-flow__edge.edge-migration')).toHaveCount(1);
    await expect(page.locator('.react-flow__edge.edge-linkage')).toHaveCount(1);
    await expect(page.locator('.react-flow__edge.edge-unknown')).toHaveCount(1);
    await expect(page.getByText(/未知边类型/).first()).toBeVisible();
  });

  test('幕三 活地图：图谱页「活地图」tab → 七大陆渲染 + 已答亮起', async ({ page }) => {
    await mockA1Endpoints(page);
    await seedGraphViewStorage(page);
    await page.goto('/a1');

    await page.getByRole('button', { name: '活地图' }).click();

    // 七大陆在 + 点亮计数（serial 1-1/2-1 两处 L2）
    await expect(page.getByTestId('continent-worldview')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('continent-ip')).toBeVisible();
    await expect(page.getByText(/已点亮 2 处/)).toBeVisible();
    await expect(page.getByTestId('continent-worldview').getByText(/文化模块/)).toBeVisible();
  });

  test('幕四 灵感架：存量可见 + [安家] 点击 → 既有 chat 投递通道', async ({ page }) => {
    const capture = await mockA1Endpoints(page);
    await seedGraphViewStorage(page);
    await page.goto('/a1');

    await page.getByRole('button', { name: '活地图' }).click();
    await expect(page.getByTestId('rack-panel')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/还放着 1 个想法/)).toBeVisible();
    await expect(page.getByText(/主角的怀表能倒转七秒/)).toBeVisible();

    // 安家操作入口：点击 → POST /api/a1/chat（既有投递端点，session_id 来自 file 端点）
    await page.getByTestId('rack-item-stow').first().click();
    await expect
      .poll(() => capture.bodies.length, { timeout: 15000 })
      .toBeGreaterThanOrEqual(1);
    const body = capture.bodies[capture.bodies.length - 1];
    expect(body.session_id).toBe('sess-e2e');
    expect(String(body.message)).toContain('安家');
    expect(String(body.message)).toContain('主角的怀表能倒转七秒');
  });

  test('幕五 崩溃降级：畸形 closing-state 载荷 → error-boundary 可见 + 页面存活', async ({ page }) => {
    await mockA1Endpoints(page);
    // 幕五专用：用畸形载荷覆写 closing-state mock（后注册优先）
    await page.route('**/api/a1/file/**/closing-state', (route) => route.fulfill({ json: CLOSING_STATE_MALFORMED_RESPONSE }));
    await seedGuidedChatStorage(page);
    await page.goto('/a1');

    // 崩溃被 ErrorBoundary 拦截：错误卡可见（绝非整树卸载白屏）
    await expect(page.getByTestId('error-boundary')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('error-boundary-retry')).toBeVisible();
    // 页面存活：root 仍有渲染内容（历史缺陷：崩溃后 childElementCount = 0）
    const childCount = await page.evaluate(() => document.getElementById('root')?.childElementCount ?? 0);
    expect(childCount).toBeGreaterThan(0);
    // 重试入口可用（点击不抛未捕获异常、错误卡仍在——载荷持续畸形时降级稳定）
    await page.getByTestId('error-boundary-retry').click();
    await expect(page.getByTestId('error-boundary')).toBeVisible({ timeout: 15000 });
  });
});
