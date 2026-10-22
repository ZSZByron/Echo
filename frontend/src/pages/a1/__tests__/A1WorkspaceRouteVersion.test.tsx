/**
 * 路由拆分：初始态按 URL 版本派生（a1v1 种子版 / a1v2 冲动卡版）
 *
 * 规则（在 poster_view 迁移与 a1_return_intent 检查之后）：
 * - 下游态（guided_chat / graph_view）跨刷新照旧恢复（续工作）。
 * - 入口态一律以 URL 为准：/a1v1 → seed_selector，/a1v2 及默认路径 → impulse_cards。
 *   两版本共用存储键 a1_workspace_v1，持久化入口态（如 v1 写入的 seed_selector）
 *   不得污染 v2 入口（病理：访问 v1 后开 v2 显示种子页）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { A1Workspace } from '../A1Workspace';

const SEED = {
  id: '1',
  name: '深渊低语',
  genre: '哲理',
  description: 'desc',
  dimension_defaults: {},
};

function stubFetch() {
  vi.stubGlobal('fetch', vi.fn(async (url: string | URL | Request) => {
    const u = String(url);
    if (u.includes('/api/a1/seeds')) {
      return new Response(JSON.stringify({ seeds: [SEED] }), { status: 200 });
    }
    if (u.includes('/api/a1/file') && u.includes('closing-state')) {
      return new Response(JSON.stringify({ sections: [] }), { status: 200 });
    }
    if (u.includes('/api/a1/file')) {
      return new Response(JSON.stringify({ sections: [] }), { status: 200 });
    }
    if (u.includes('/api/a1/chat')) {
      return new Response(JSON.stringify({
        reply: '收到。',
        pending_question: { id: 'oq-1', question: '主角是谁？' },
        pending_questions_count: 1,
        file_diff: [],
        progress: { sections: [], finalizable: false },
      }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 200 });
  }));
}

function goto(path: string) {
  window.history.pushState(null, '', path);
}

describe('A1Workspace 初始态按 URL 版本派生（路由拆分）', () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    localStorage.setItem('user_id', 'u-test');
    stubFetch();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    goto('/');
  });

  it('/a1v1 无持久化 → seed_selector（种子选择页）', async () => {
    goto('/a1v1');
    render(<A1Workspace />);

    // 冲动卡屏不出现，种子选择页出现
    expect(screen.queryByTestId('impulse-card-plot')).toBeNull();
    expect(await screen.findByText('Choose a seed to start your creative journey')).toBeTruthy();
  });

  it('/a1v1 持久化 guided_chat → 照旧恢复 guided_chat（跨刷新续工作）', async () => {
    goto('/a1v1');
    localStorage.setItem('a1_workspace_v1', JSON.stringify({
      workspaceState: 'guided_chat',
      sessionId: 's-1',
      fileId: 'f-1',
      ipCode: 'IP-1',
      messages: [],
    }));
    render(<A1Workspace />);

    expect(await screen.findByPlaceholderText('Type your message...')).toBeTruthy();
  });

  it('/a1v2 无持久化 → impulse_cards（冲动卡入口）', async () => {
    goto('/a1v2');
    render(<A1Workspace />);

    expect(await screen.findByTestId('impulse-card-plot')).toBeTruthy();
  });

  it('/a1v2 持久化 seed_selector（v1 访问污染）→ URL 压倒入口态 → impulse_cards', async () => {
    goto('/a1v2');
    localStorage.setItem('a1_workspace_v1', JSON.stringify({
      workspaceState: 'seed_selector',
      sessionId: null,
      fileId: null,
      ipCode: null,
      messages: [],
    }));
    render(<A1Workspace />);

    expect(await screen.findByTestId('impulse-card-plot')).toBeTruthy();
  });

  it('默认路径（jsdom 的 /）无持久化 → impulse_cards（现状不变）', async () => {
    goto('/');
    render(<A1Workspace />);

    expect(await screen.findByTestId('impulse-card-plot')).toBeTruthy();
  });
});
