/**
 * P0-6 F4 + P1-5 商业加固批：A1Workspace 卡死防线单测
 * 1. skip 失败可观测：mock fetch reject → 错误条「跳过失败，请重试」+ loading 复位
 * 2. loading 看门狗：请求挂起 125s → 自动解锁 + 错误条（fake timers）
 *
 * 渲染模式沿用 A1WorkspaceRestart.test.tsx / A1WorkspaceImpulseSend.test.tsx
 * （localStorage 预置 guided_chat + stub fetch）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { A1Workspace } from '../A1Workspace';

function seedGuidedChat() {
  localStorage.setItem('a1_workspace_v1', JSON.stringify({
    workspaceState: 'guided_chat',
    sessionId: 's-1',
    fileId: 'f-1',
    ipCode: 'IP-1',
    messages: [],
  }));
  localStorage.setItem('user_id', 'u-test');
}

type FetchImpl = (url: string | URL | Request, init?: RequestInit) => Promise<Response>;

function chatUrl(u: string) {
  return u.includes('/api/a1/chat') && !u.includes('confirm');
}

async function sendFirstMessage() {
  const textarea = screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement;
  fireEvent.change(textarea, { target: { value: '主线是钟表匠找回记忆' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send' }));
  // 等首轮 chat 响应落账（pending_question 卡出现）
  await screen.findByTestId('pending-question-card');
}

describe('A1Workspace skip 失败可观测（P0-6 F4）', () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('skip 请求 reject → 错误条出现 + loading 复位（textarea 解禁）', async () => {
    seedGuidedChat();
    let chatCalls = 0;
    const impl: FetchImpl = async (url) => {
      const u = String(url);
      if (u.includes('/api/a1/seeds')) {
        return new Response(JSON.stringify({ seeds: [] }), { status: 200 });
      }
      if (chatUrl(u)) {
        chatCalls += 1;
        if (chatCalls === 1) {
          // 首轮：正常响应并携带待问开放问题 → 渲染 skip 按钮
          return new Response(JSON.stringify({
            reply: '收到。',
            pending_question: { id: 'oq-001', question: '这个世界的纪年是什么？' },
            pending_questions_count: 1,
            file_diff: [],
            progress: { sections: [], finalizable: false },
          }), { status: 200 });
        }
        // skip 请求（带 skip_question_id）→ 网络故障
        throw new Error('network down');
      }
      return new Response(JSON.stringify({ sections: [] }), { status: 200 });
    };
    vi.stubGlobal('fetch', vi.fn(impl));

    render(<A1Workspace />);
    await sendFirstMessage();

    const textarea = screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement;
    expect(textarea.disabled).toBe(false); // 首轮完成后 loading 已复位

    fireEvent.click(screen.getByTestId('skip-question-btn'));

    expect(await screen.findByText('跳过失败，请重试')).toBeTruthy();
    expect((screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement).disabled).toBe(false);
  });
});

describe('A1Workspace loading 看门狗（P1-5）', () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('请求挂起 125s → 自动解锁 + 错误条「请求超时」', async () => {
    vi.useFakeTimers();
    seedGuidedChat();
    const impl: FetchImpl = async (url) => {
      const u = String(url);
      if (u.includes('/api/a1/seeds')) {
        return new Response(JSON.stringify({ seeds: [] }), { status: 200 });
      }
      if (chatUrl(u)) {
        // 永不 resolve：模拟后端挂死
        return new Promise<Response>(() => {});
      }
      return new Response(JSON.stringify({ sections: [] }), { status: 200 });
    };
    vi.stubGlobal('fetch', vi.fn(impl));

    render(<A1Workspace />);

    const textarea = screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '讲讲大陆的历史' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    // 请求挂起中：loading 态（textarea 禁用）
    expect((screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement).disabled).toBe(true);

    // 未到 125s：不解锁
    await act(async () => { vi.advanceTimersByTime(124_000); });
    expect((screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement).disabled).toBe(true);

    // 125s 到点：看门狗解锁 + 错误条
    await act(async () => { vi.advanceTimersByTime(1_000); });
    expect(screen.getByText('请求超时，已自动解锁，请重试')).toBeTruthy();
    expect((screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement).disabled).toBe(false);
  });
});
