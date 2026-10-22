/**
 * 重新开始（返回当前版本入口）按钮 —— UX 补丁测试
 *
 * 覆盖：
 * 1. 点击「重新开始」→ 弹出确认对话框（含取消/确认，标题按版本：v1=返回种子选择 / v2=返回冲动入口）
 * 2. 确认 → workspaceState 回当前版本入口（v1=seed_selector / v2=impulse_cards）
 *    + a1_workspace_v1 / a1_return_intent 清除 + user_id 保留 + restart_to_entry 埋点落库
 * 3. 取消 → 状态不变（仍在种子选择页，持久化键保留）
 *
 * 路由拆分后种子屏的合法入口是 /a1v1（默认路径与 /a1v2 一律落冲动卡屏，
 * 持久化入口态不再跨版本恢复），故 v1 场景统一在 /a1v1 下渲染；
 * 另设 /a1v2 用例锁定冲动卡入口回归。
 * 渲染模式沿用 A1WorkspaceImpulseSend.test.tsx（mock fetch，无 fake timers）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { A1Workspace } from '../../A1Workspace';

const SEED = {
  id: '1',
  name: '星渊回响',
  genre: '科幻',
  description: 'desc',
  dimension_defaults: {},
};

function stubFetch() {
  vi.stubGlobal('fetch', vi.fn(async (url: string | URL | Request) => {
    const u = String(url);
    if (u.includes('/api/a1/seeds')) {
      return new Response(JSON.stringify({ seeds: [SEED] }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 200 });
  }));
}

/** 预置持久化工作区状态（返回用户场景：restore 进 seed_selector） */
function seedPersistedWorkspace() {
  localStorage.setItem('a1_workspace_v1', JSON.stringify({
    workspaceState: 'seed_selector',
    sessionId: 's-old',
    messages: [],
  }));
  localStorage.setItem('user_id', 'u-test');
}

function readTelemetryEvents(): Array<{ event: string }> {
  const raw = localStorage.getItem('a1_telemetry_v1');
  return raw ? (JSON.parse(raw) as Array<{ event: string }>) : [];
}

describe('A1Workspace 重新开始（返回冲动入口）', () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    stubFetch();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    window.history.pushState(null, '', '/');
  });

  it('点击重新开始 → 确认对话框出现（含取消与确认，v1 标题为返回种子选择）', () => {
    window.history.pushState(null, '', '/a1v1');
    seedPersistedWorkspace();
    render(<A1Workspace />);

    fireEvent.click(screen.getByTestId('restart-to-entry'));

    const dialog = screen.getByTestId('restart-confirm-dialog');
    expect(dialog).toBeTruthy();
    expect(screen.getByText('返回种子选择？')).toBeTruthy();
    expect(screen.getByText(/当前创作进度与本地状态将被清除/)).toBeTruthy();
    expect(screen.getByTestId('restart-cancel')).toBeTruthy();
    expect(screen.getByTestId('restart-confirm')).toBeTruthy();
  });

  it('v1 确认 → 回到种子选择页（不落冲动卡）+ 本地工作区键清除 + user_id 保留 + 埋点', async () => {
    window.history.pushState(null, '', '/a1v1');
    seedPersistedWorkspace();
    localStorage.setItem('a1_return_intent', 'chat');
    render(<A1Workspace />);

    fireEvent.click(screen.getByTestId('restart-to-entry'));
    fireEvent.click(screen.getByTestId('restart-confirm'));

    // v1 重启回种子选择页：冲动卡屏不出现，种子卡片渲染
    expect(screen.queryByTestId('impulse-card-plot')).toBeNull();
    expect(await screen.findByText('星渊回响')).toBeTruthy();
    // v1 重启后持久化 effect 会回写"干净"入口态记录（seed_selector，无会话数据）——
    // 断言语义契约：不得残留任何工作进度；身份键保留
    const raw = localStorage.getItem('a1_workspace_v1');
    const rec = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    expect(rec.sessionId ?? null).toBeNull();
    expect(rec.fileId ?? null).toBeNull();
    expect(Array.isArray(rec.messages) ? rec.messages : []).toEqual([]);
    expect(localStorage.getItem('a1_return_intent')).toBeNull();
    expect(localStorage.getItem('user_id')).toBe('u-test');
    // 埋点：restart_to_entry 落库；埋点历史不受影响（本条之前的事件仍在）
    const events = readTelemetryEvents();
    expect(events.some(e => e.event === 'restart_to_entry')).toBe(true);
  });

  it('v2 确认（自 guided_chat）→ 回到冲动卡入口（现状回归锁定）', async () => {
    window.history.pushState(null, '', '/a1v2');
    seedPersistedWorkspace();
    localStorage.setItem('a1_return_intent', 'chat');
    render(<A1Workspace />);

    fireEvent.click(screen.getByTestId('restart-to-entry'));
    // v2 对话框标题为返回冲动入口
    expect(screen.getByText('返回冲动入口？')).toBeTruthy();
    fireEvent.click(screen.getByTestId('restart-confirm'));

    expect(await screen.findByTestId('impulse-card-plot')).toBeTruthy();
    // 持久化工作区键清除；身份键保留
    expect(localStorage.getItem('a1_workspace_v1')).toBeNull();
    expect(localStorage.getItem('a1_return_intent')).toBeNull();
    expect(localStorage.getItem('user_id')).toBe('u-test');
    // 埋点：restart_to_entry 落库；埋点历史不受影响（本条之前的事件仍在）
    const events = readTelemetryEvents();
    expect(events.some(e => e.event === 'restart_to_entry')).toBe(true);
  });

  it('取消 → 状态不变：仍在种子选择页，持久化键保留', async () => {
    window.history.pushState(null, '', '/a1v1');
    seedPersistedWorkspace();
    render(<A1Workspace />);

    fireEvent.click(screen.getByTestId('restart-to-entry'));
    fireEvent.click(screen.getByTestId('restart-cancel'));

    expect(screen.queryByTestId('restart-confirm-dialog')).toBeNull();
    // 仍在种子选择页（重新开始按钮仍在 + 种子卡片渲染；seeds 为异步加载，用 findBy）
    expect(screen.getByTestId('restart-to-entry')).toBeTruthy();
    expect(await screen.findByText('星渊回响')).toBeTruthy();
    // 持久化状态未被清除
    expect(localStorage.getItem('a1_workspace_v1')).not.toBeNull();
    // 未打点
    expect(readTelemetryEvents().some(e => e.event === 'restart_to_entry')).toBe(false);
  });
});
