/**
 * a1-oq-phase T4 红测：A1Workspace 相位接线
 * 1. 刷新恢复：GET /file 带 oq_phase_active=true → ✦ 卡在 + placeholder=问题
 *    文本 + 定稿按钮禁用（tooltip 说明）
 * 2. chat 响应相位值优先：oq_phase_active=false → 相位退出、定稿解禁
 * 3. 竞态源已删：openQuestions 有 pending 但无相位 → 不派生 ✦ 卡
 *
 * 渲染模式沿用 A1WorkspaceHardening.test.tsx（localStorage 预置 + stub fetch）。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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

const FILE_PHASE_ACTIVE = {
  file_id: 'f-1',
  session_id: 's-1',
  status: 'draft',
  graph_code: 'IP0001-W1-v1',
  answers: {},
  sections: [],
  open_questions: [
    { id: 'oq-001', question: '这个世界的纪年是什么？', status: 'pending' },
  ],
  oq_phase_active: true,
  pending_question: { id: 'oq-001', question: '这个世界的纪年是什么？' },
  pending_questions_count: 1,
};

const FILE_PHASE_OFF = {
  ...FILE_PHASE_ACTIVE,
  oq_phase_active: false,
  pending_question: null,
  pending_questions_count: 0,
};

function stubFile(body: object) {
  vi.stubGlobal('fetch', vi.fn(async (url: string | URL) => {
    const u = String(url);
    if (u.includes('/api/a1/seeds')) {
      return new Response(JSON.stringify({ seeds: [] }), { status: 200 });
    }
    if (u.includes('/api/a1/file/f-1') && !u.includes('closing')) {
      return new Response(JSON.stringify(body), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 200 });
  }));
}

describe('A1Workspace oq_phase 刷新恢复（a1-oq-phase T4）', () => {
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

  it('file 带 oq_phase_active=true → ✦ 卡 + placeholder=问题 + 定稿禁用', async () => {
    seedGuidedChat();
    stubFile(FILE_PHASE_ACTIVE);
    render(<A1Workspace />);

    // ✦ 卡由 file 快照恢复（不再依赖 file 派生 effect）
    const card = await screen.findByTestId('pending-question-card');
    expect(card.getAttribute('data-phase')).toBe('active');
    // placeholder 绑定当前待问问题文本
    const textarea = screen.getByPlaceholderText(
      '这个世界的纪年是什么？'
    ) as HTMLTextAreaElement;
    expect(textarea.disabled).toBe(false);
    // 定稿禁用 + tooltip 说明（sections=[] 使 finalizable=true——禁用只来自相位）
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /定稿/ }) as HTMLButtonElement;
      expect(btn.disabled).toBe(true);
      expect(btn.title).toBe('先答完/跳过开放问题，从收尾处定稿');
    });
  });

  it('file 带 oq_phase_active=false → 无 ✦ 卡、定稿不禁用（默认态零改动）', async () => {
    seedGuidedChat();
    stubFile(FILE_PHASE_OFF);
    render(<A1Workspace />);

    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /定稿/ }) as HTMLButtonElement;
      expect(btn.disabled).toBe(false);
    });
    expect(screen.queryByTestId('pending-question-card')).toBeNull();
  });

  it('竞态源已删：openQuestions 有 pending 但无相位 → 不派生 ✦ 卡', async () => {
    seedGuidedChat();
    stubFile({
      ...FILE_PHASE_OFF,
      open_questions: FILE_PHASE_ACTIVE.open_questions,
    });
    render(<A1Workspace />);

    // 等 hydrate 完成（无相位 → 无卡；派生 effect 已删，旧实现会派生出卡）
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /定稿/ }) as HTMLButtonElement;
      expect(btn.disabled).toBe(false);
    });
    expect(screen.queryByTestId('pending-question-card')).toBeNull();
  });

  it('skip 末题清结 → 二次收尾 ClosingPanel variant=refinalize（T5 bug 修复锁定）', async () => {
    seedGuidedChat();
    // 冷启动带相位 + 待问 1（prevPhase=true）
    stubFile(FILE_PHASE_ACTIVE);
    render(<A1Workspace />);
    await screen.findByTestId('pending-question-card');

    // skip 末题响应：相位闭合 + closing.triggered=true（后端 T3 skip 路径契约）
    vi.stubGlobal('fetch', vi.fn(async (url: string | URL, init?: RequestInit) => {
      const u = String(url);
      if (u.includes('/api/a1/seeds')) {
        return new Response(JSON.stringify({ seeds: [] }), { status: 200 });
      }
      if (u.includes('/api/a1/chat') && !u.includes('confirm')) {
        const body = JSON.parse(String(init?.body ?? '{}'));
        if (body.skip_question_id) {
          return new Response(JSON.stringify({
            reply: '好的，开放问题都答完了。重新定稿后文档会同步更新。想现在生成文档，还是继续访谈、补充设定？',
            oq_phase_active: false,
            pending_question: null,
            pending_questions_count: 0,
            closing: { step: 1, settled: false, triggered: true },
            progress: { sections: [], finalizable: true },
          }), { status: 200 });
        }
        return new Response(JSON.stringify({
          reply: '收到。',
          oq_phase_active: true,
          pending_question: { id: 'oq-001', question: '这个世界的纪年是什么？' },
          pending_questions_count: 1,
          progress: { sections: [], finalizable: true },
        }), { status: 200 });
      }
      if (u.includes('/api/a1/file/f-1/closing-state')) {
        return new Response(JSON.stringify({
          file_id: 'f-1', triggered: true, closing_step: 1, settled: false,
          preview: { consumers: [{ id: 'world_bible', kind: 'd22' }], modules: [], missing_modules: [], finalize_ready: true },
        }), { status: 200 });
      }
      return new Response(JSON.stringify({ sections: [] }), { status: 200 });
    }));

    // 跳过末题（相位内 ✦ 卡上的 skip 按钮）
    fireEvent.click(screen.getByTestId('skip-question-btn'));

    // 二次收尾面板以 refinalize 变体渲染（修复前误渲染 "first"）
    const panel = await screen.findByTestId('closing-panel');
    expect(panel.getAttribute('data-variant')).toBe('refinalize');
  });
});
