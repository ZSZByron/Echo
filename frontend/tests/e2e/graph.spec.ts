import { test, expect, Page } from '@playwright/test';

/**
 * Playwright E2E Tests for Graph Editor and Asset Generation Pages
 *
 * Test Coverage:
 * 1. Graph Editor Basic Functionality
 *    - Page loading and initialization
 *    - Adding new nodes
 *    - Editing node information
 *    - Connecting nodes to create edges
 *    - Deleting nodes and edges
 *
 * 2. LLM Extraction Functionality
 *    - Input scene description trigger extraction
 *    - Verify extracted graph structure correctness
 *    - Verify error handling
 *
 * 3. Graph Validation and Saving
 *    - Validate valid graphs
 *    - Detect cycles and display warnings
 *    - Save graphs to database
 *    - Load saved graphs
 *
 * 4. Asset Generation Page
 *    - Select graphs
 *    - Trigger serial generation
 *    - Verify generation progress display
 *    - Verify wave order correctness
 *    - Verify status badge display
 *    - Verify prompt preview functionality
 *
 * 5. Responsive Design
 *    - UI adaptation for different screen sizes
 *    - Mobile basic functionality availability
 */

// Test utilities
const GRAPH_EDITOR_URL = '/admin/graph-editor';
const ASSET_REVIEW_URL = '/admin/graph-assets';

/**
 * Navigate to graph editor page and wait for initialization
 */
async function gotoGraphEditor(page: Page) {
  await page.goto(GRAPH_EDITOR_URL);
  await expect(page.locator('h1:has-text("图谱编辑器")')).toBeVisible();
  await expect(page.locator('button:has-text("+ 节点")')).toBeVisible();
}

/**
 * Navigate to asset review page and wait for initialization
 */
async function gotoAssetReview(page: Page) {
  await page.goto(ASSET_REVIEW_URL);
  await expect(page.locator('h1:has-text("资产生成页面变体")')).toBeVisible();
}

/**
 * Fill and submit the add node form
 */
async function addNode(page: Page, options: {
  serialNumber: string;
  description: string;
  level: string;
  parentId?: string;
}) {
  // Click add node button
  await page.click('button:has-text("+ 节点")');
  await expect(page.locator('text=添加节点')).toBeVisible();

  // Fill form fields
  await page.fill('input[placeholder*="例如: 1-1-2"]', options.serialNumber);
  await page.fill('textarea[placeholder*="视觉描述..."]', options.description);
  await page.fill('input[type="number"]', options.level);

  if (options.parentId) {
    await page.fill('input[placeholder*="父节点 ID"]', options.parentId);
  }

  // Submit form
  await page.click('button:has-text("添加")');

  // Wait for dialog to close
  await expect(page.locator('text=添加节点')).not.toBeVisible();
}

/**
 * Open AI extraction dialog and input scene description
 */
async function openExtractDialog(page: Page, description: string) {
  await page.click('button:has-text("AI 提取")');
  await expect(page.locator('text=AI 提取图谱')).toBeVisible();

  await page.fill('textarea[placeholder*="描述你的场景..."]', description);
}

// ==========================================
// TEST SUITE 1: Graph Editor Basic Functionality
// ==========================================

test.describe('Graph Editor Basic Functionality', () => {
  test('should load and initialize graph editor page', async ({ page }) => {
    await gotoGraphEditor(page);

    // Verify header is visible
    await expect(page.locator('h1:has-text("图谱编辑器")')).toBeVisible();

    // Verify main buttons are present
    await expect(page.locator('button:has-text("+ 节点")')).toBeVisible();
    await expect(page.locator('button:has-text("AI 提取")')).toBeVisible();
    await expect(page.locator('button:has-text("验证")')).toBeVisible();
    await expect(page.locator('button:has-text("保存")')).toBeVisible();
    await expect(page.locator('button:has-text("生成")')).toBeVisible();

    // Verify React Flow canvas is present
    await expect(page.locator('.react-flow')).toBeVisible();
  });

  test('should add new node to graph', async ({ page }) => {
    await gotoGraphEditor(page);

    // Add a new node
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Ancient stone pillar with hieroglyphics',
      level: '1',
    });

    // Wait for node to appear in canvas
    await expect(page.locator('.react-flow-node').filter({ hasText: '1-1' })).toBeVisible();

    // Verify node content
    const node = page.locator('.react-flow-node').filter({ hasText: '1-1' });
    await expect(node.locator('text=[1-1]')).toBeVisible();
    await expect(node.locator('text=Ancient stone pillar')).toBeVisible();
  });

  test('should edit existing node information', async ({ page }) => {
    await gotoGraphEditor(page);

    // Add a node first
    await addNode(page, {
      serialNumber: '1-2',
      description: 'Mysterious altar',
      level: '2',
    });

    // Click on the node to select it
    await page.click('.react-flow-node').filter({ hasText: '1-2' });

    // Wait for edit dialog to appear
    await expect(page.locator('text=编辑节点')).toBeVisible();

    // Update description
    await page.fill('textarea', 'Sacred altar with offerings');
    await page.click('button:has-text("保存")');

    // Wait for dialog to close
    await expect(page.locator('text=编辑节点')).not.toBeVisible();

    // Verify node was updated
    const node = page.locator('.react-flow-node').filter({ hasText: '1-2' });
    await expect(node.locator('text=Sacred altar')).toBeVisible();
  });

  test('should create edge between two nodes', async ({ page }) => {
    await gotoGraphEditor(page);

    // Add two nodes
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Background scene',
      level: '1',
    });

    await addNode(page, {
      serialNumber: '2-1',
      description: 'Foreground object',
      level: '2',
    });

    // Get node positions for connection
    const firstNode = page.locator('.react-flow-node').filter({ hasText: '1-1' }).first();
    const secondNode = page.locator('.react-flow-node').filter({ hasText: '2-1' }).first();

    // Drag from first node to second node to create edge
    await firstNode.dragTo(secondNode);

    // Wait for edge to be created
    await expect(page.locator('.react-flow-edge')).toBeVisible();

    // Verify edge exists and is visible
    await expect(page.locator('.react-flow-edge')).toHaveCount(1);
  });

  test('should delete selected node', async ({ page }) => {
    await gotoGraphEditor(page);

    // Add a node
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Temporary node',
      level: '1',
    });

    // Click on the node to select it
    await page.click('.react-flow-node').filter({ hasText: '1-1' });

    // Verify delete button appears
    await expect(page.locator('button:has-text("删除")')).toBeVisible();

    // Click delete button
    await page.click('button:has-text("删除")');

    // Verify node was removed
    await expect(page.locator('.react-flow-node').filter({ hasText: '1-1' })).not.toBeVisible();
  });

  test('should delete selected edge', async ({ page }) => {
    await gotoGraphEditor(page);

    // Add two nodes and create an edge
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Node 1',
      level: '1',
    });

    await addNode(page, {
      serialNumber: '2-1',
      description: 'Node 2',
      level: '2',
    });

    // Create edge
    const firstNode = page.locator('.react-flow-node').filter({ hasText: '1-1' }).first();
    const secondNode = page.locator('.react-flow-node').filter({ hasText: '2-1' }).first();
    await firstNode.dragTo(secondNode);

    // Click on the edge to select it
    await page.click('.react-flow-edge');

    // Verify delete button appears
    await expect(page.locator('button:has-text("删除")')).toBeVisible();

    // Click delete button
    await page.click('button:has-text("删除")');

    // Verify edge was removed
    await expect(page.locator('.react-flow-edge')).toHaveCount(0);
  });
});

// ==========================================
// TEST SUITE 2: LLM Extraction Functionality
// ==========================================

test.describe('LLM Extraction Functionality', () => {
  test('should open extraction dialog and accept input', async ({ page }) => {
    await gotoGraphEditor(page);

    await openExtractDialog(page, 'Ancient Egyptian temple entrance with massive stone doors');

    // Verify dialog is open and has content
    await expect(page.locator('textarea')).toHaveValue('Ancient Egyptian temple entrance with massive stone doors');
  });

  test('should close extraction dialog on cancel', async ({ page }) => {
    await gotoGraphEditor(page);

    await openExtractDialog(page, 'Some description');

    // Click cancel button
    await page.click('button:has-text("取消")');

    // Verify dialog is closed
    await expect(page.locator('text=AI 提取图谱')).not.toBeVisible();
  });

  test('should show validation error for empty extraction input', async ({ page }) => {
    await gotoGraphEditor(page);

    // Open dialog with empty text
    await openExtractDialog(page, '');

    // Click extract button
    await page.click('button:has-text("提取图谱")');

    // Verify error message appears
    await expect(page.locator('text=Please enter a scene description').or(page.locator('text=请输入场景描述'))).toBeVisible();
  });

  test('should handle extraction failure gracefully', async ({ page }) => {
    await gotoGraphEditor(page);

    // Mock API failure scenario
    await page.route('**/api/graph/extract', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'LLM service unavailable' }),
      });
    });

    await openExtractDialog(page, 'Test scene description');

    // Click extract button
    await page.click('button:has-text("提取图谱")');

    // Wait for loading state
    await expect(page.locator('button:has-text("提取中...")')).toBeVisible();

    // Verify error message appears
    await expect(page.locator('text=Extraction failed').or(page.locator('text=提取失败'))).toBeVisible();
  });
});

// ==========================================
// TEST SUITE 3: Graph Validation and Saving
// ==========================================

test.describe('Graph Validation and Saving', () => {
  test('should validate graph with no cycles', async ({ page }) => {
    await gotoGraphEditor(page);

    // Create a valid DAG (Directed Acyclic Graph)
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Background',
      level: '1',
    });

    await addNode(page, {
      serialNumber: '2-1',
      description: 'Object 1',
      level: '2',
    });

    // Click validate button
    await page.click('button:has-text("验证")');

    // Verify success message
    await expect(page.locator('text=Graph is valid').or(page.locator('text=图谱有效'))).toBeVisible();
  });

  test('should detect cycles and display warnings', async ({ page }) => {
    await gotoGraphEditor(page);

    // Create nodes for a cycle
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Node A',
      level: '1',
    });

    await addNode(page, {
      serialNumber: '1-2',
      description: 'Node B',
      level: '2',
    });

    await addNode(page, {
      serialNumber: '1-3',
      description: 'Node C',
      level: '3',
    });

    // Mock cycle detection API response
    await page.route('**/api/graph/validate', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          is_valid: false,
          cycles: [['1-1', '1-2', '1-3', '1-1']],
        }),
      });
    });

    // Click validate button
    await page.click('button:has-text("验证")');

    // Verify cycle warning is displayed
    await expect(page.locator('text=Cycles detected').or(page.locator('text=环检测警告'))).toBeVisible();
    await expect(page.locator('text=环 1')).toBeVisible();
  });

  test('should save graph successfully', async ({ page }) => {
    await gotoGraphEditor(page);

    // Create a simple graph
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Test node',
      level: '1',
    });

    // Mock save API response
    await page.route('**/api/graph/save', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ scene_id: 'scene-1234567890' }),
      });
    });

    // Click save button
    await page.click('button:has-text("保存")');

    // Verify success message
    await expect(page.locator('text=Graph saved').or(page.locator('text=图谱已保存'))).toBeVisible();
    await expect(page.locator('text=scene-')).toBeVisible();
  });

  test('should handle save failure with cycles', async ({ page }) => {
    await gotoGraphEditor(page);

    // Create nodes
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Node A',
      level: '1',
    });

    // Mock save API response with validation error
    await page.route('**/api/graph/save', route => {
      route.fulfill({
        status: 422,
        body: JSON.stringify({ detail: 'Graph contains cycles and cannot be saved' }),
      });
    });

    // Click save button
    await page.click('button:has-text("保存")');

    // Verify error message
    await expect(page.locator('text=Save failed').or(page.locator('text=保存失败'))).toBeVisible();
  });
});

// ==========================================
// TEST SUITE 4: Asset Generation Page
// ==========================================

test.describe('Asset Generation Page', () => {
  test('should load asset generation page', async ({ page }) => {
    await gotoAssetReview(page);

    // Verify main elements
    await expect(page.locator('h1:has-text("资产生成页面变体")')).toBeVisible();
    await expect(page.locator('text=GRAPH SELECTION')).toBeVisible();
    await expect(page.locator('button:has-text("生成所有")')).toBeVisible();
  });

  test('should display available graphs for selection', async ({ page }) => {
    await gotoAssetReview(page);

    // Verify graph selection buttons
    await expect(page.locator('text=赛博朋克神庙废墟')).toBeVisible();
    await expect(page.locator('text=量子实验室核心区')).toBeVisible();
    await expect(page.locator('text=数据流废墟入口')).toBeVisible();
  });

  test('should load graph when selected', async ({ page }) => {
    await gotoAssetReview(page);

    // Mock load graph API response
    await page.route('**/api/graph/*', route => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            scene_id: 'scene_001',
            background_node_id: 'bg-1',
            nodes: {
              'bg-1': {
                id: 'bg-1',
                serial_number: '0',
                level: 1,
                description: 'Background scene',
                status: 'pending' as const,
              },
            },
            edges: [],
          }),
        });
      }
    });

    // Click on first graph
    await page.click('button:has-text("赛博朋克神庙废墟")');

    // Wait for loading to complete
    await expect(page.locator('text=加载图谱中…')).not.toBeVisible();

    // Verify graph info is displayed
    await expect(page.locator('text=scene_001')).toBeVisible();
  });

  test('should trigger serial generation', async ({ page }) => {
    await gotoAssetReview(page);

    // Mock APIs
    await page.route('**/api/graph/*', route => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            scene_id: 'scene_001',
            background_node_id: 'bg-1',
            nodes: {
              'bg-1': {
                id: 'bg-1',
                serial_number: '0',
                level: 1,
                description: 'Background',
                status: 'pending' as const,
              },
            },
            edges: [],
          }),
        });
      }
    });

    await page.route('**/api/graph/generate', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          total: 1,
          succeeded: 1,
          failed: 0,
          order: ['bg-1'],
        }),
      });
    });

    // Select graph
    await page.click('button:has-text("赛博朋克神庙废墟")');
    await expect(page.locator('text=scene_001')).toBeVisible();

    // Click generate button
    await page.click('button:has-text("生成所有")');

    // Verify generation state
    await expect(page.locator('text=生成中…').or(page.locator('text=生成中'))).toBeVisible();
  });

  test('should display generation progress', async ({ page }) => {
    await gotoAssetReview(page);

    // Mock APIs
    await page.route('**/api/graph/*', route => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            scene_id: 'scene_001',
            background_node_id: 'bg-1',
            nodes: {
              'bg-1': {
                id: 'bg-1',
                serial_number: '0',
                level: 1,
                description: 'Background scene',
                status: 'generating' as const,
              },
            },
            edges: [],
          }),
        });
      }
    });

    // Select and generate
    await page.click('button:has-text("赛博朋克神庙废墟")');
    await page.click('button:has-text("生成所有")');

    // Verify progress indicators
    await expect(page.locator('text=Generating…').or(page.locator('text=生成中'))).toBeVisible();
  });

  test('should display wave order correctly', async ({ page }) => {
    await gotoAssetReview(page);

    // Mock API with multi-wave graph
    await page.route('**/api/graph/*', route => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            scene_id: 'scene_001',
            background_node_id: 'bg-1',
            nodes: {
              'bg-1': {
                id: 'bg-1',
                serial_number: '0',
                level: 1,
                description: 'Background',
                status: 'pending' as const,
              },
              '1-1': {
                id: '1-1',
                serial_number: '1',
                level: 2,
                description: 'Object 1',
                status: 'pending' as const,
              },
            },
            edges: [
              {
                from_node_id: 'bg-1',
                to_node_id: '1-1',
                edge_type: 'tree' as const,
                visual_description: '',
              },
            ],
          }),
        });
      }
    });

    // Select graph
    await page.click('button:has-text("赛博朋克神庙废墟")');

    // Verify wave display
    await expect(page.locator('text=Wave 0').or(page.locator('text=Wave 1'))).toBeVisible();
  });

  test('should display status badges correctly', async ({ page }) => {
    await gotoAssetReview(page);

    // Mock API with different node statuses
    await page.route('**/api/graph/*', route => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            scene_id: 'scene_001',
            background_node_id: 'bg-1',
            nodes: {
              'bg-1': {
                id: 'bg-1',
                serial_number: '0',
                level: 1,
                description: 'Completed node',
                status: 'completed' as const,
              },
              '1-1': {
                id: '1-1',
                serial_number: '1',
                level: 2,
                description: 'Failed node',
                status: 'failed' as const,
              },
            },
            edges: [],
          }),
        });
      }
    });

    // Select graph
    await page.click('button:has-text("赛博朋克神庙废墟")');

    // Verify status badges
    await expect(page.locator('text=完成').or(page.locator('text=Completed'))).toBeVisible();
    await expect(page.locator('text=失败').or(page.locator('text=Failed'))).toBeVisible();
  });

  test('should display prompt preview', async ({ page }) => {
    await gotoAssetReview(page);

    // Mock API
    await page.route('**/api/graph/*', route => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            scene_id: 'scene_001',
            background_node_id: 'bg-1',
            nodes: {
              'bg-1': {
                id: 'bg-1',
                serial_number: '0',
                level: 1,
                description: 'Background scene with detailed description',
                status: 'pending' as const,
              },
            },
            edges: [],
          }),
        });
      }
    });

    // Select graph and generate
    await page.click('button:has-text("赛博朋克神庙废墟")');
    await page.click('button:has-text("生成所有")');

    // Verify prompt preview sections
    await expect(page.locator('text=【生成主体】').or(page.locator('text=Subject'))).toBeVisible();
  });
});

// ==========================================
// TEST SUITE 5: Responsive Design
// ==========================================

test.describe('Responsive Design', () => {
  test('should adapt layout for tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    await gotoAssetReview(page);

    // Verify layout adaptation
    await expect(page.locator('h1:has-text("资产生成页面变体")')).toBeVisible();

    // Sidebar should still be visible
    await expect(page.locator('text=GRAPH SELECTION')).toBeVisible();
  });

  test('should adapt layout for mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await gotoAssetReview(page);

    // Verify main elements still accessible
    await expect(page.locator('h1:has-text("资产生成页面变体")')).toBeVisible();

    // Navigation should work
    await expect(page.locator('button:has-text("← 返回游戏")')).toBeVisible();
  });

  test('should maintain basic functionality on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await gotoGraphEditor(page);

    // Verify core functionality works
    await expect(page.locator('button:has-text("+ 节点")')).toBeVisible();
    await expect(page.locator('button:has-text("AI 提取")')).toBeVisible();

    // Test adding node on mobile
    await addNode(page, {
      serialNumber: '1-1',
      description: 'Mobile test node',
      level: '1',
    });

    // Verify node was added
    await expect(page.locator('.react-flow-node').filter({ hasText: '1-1' })).toBeVisible();
  });

  test('should handle landscape mobile orientation', async ({ page }) => {
    // Set mobile landscape
    await page.setViewportSize({ width: 667, height: 375 });

    await gotoGraphEditor(page);

    // Verify basic functionality
    await expect(page.locator('h1:has-text("图谱编辑器")')).toBeVisible();
    await expect(page.locator('.react-flow')).toBeVisible();
  });
});