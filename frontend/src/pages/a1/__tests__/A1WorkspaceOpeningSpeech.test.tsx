/**
 * 开场语前端同源守门测试（波次三 T3，拍3-1）
 *
 * 覆盖（施工单 QA：开场渲染断言新语）：
 * 1. 一句话开始（custom_idea → seed.description 分支）→ 新开场语
 *    「接下来我会一次问你一个问题…」在文档中（与 interviewer.py 同源）
 * 2. 旧语「我将围绕…引导你展开世界观」清零
 *
 * 渲染模式沿用 A1WorkspaceImpulseSend.test.tsx（stub fetch，无 fake timers）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
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
    if (u.includes('/api/a1/session/start')) {
      return new Response(JSON.stringify({
        session_id: 's-1',
        file_id: 'f-1',
        ip_code: 'IP-1',
        // 一句话开始路径：seed 无 name 有 description → L649 新开场语分支
        seed: { description: '一个失忆钟表匠的悬疑世界' },
        first_question: {
          section: 'story_line',
          section_label: '剧情',
          question: '主角是谁？',
        },
        file: {},
      }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 200 });
  }));
}

describe('A1Workspace 开场语同源（波次三 T3）', () => {
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
  });

  it('一句话开始 → 新开场语渲染（与 interviewer.py 同源），旧语清零', async () => {
    render(<A1Workspace />);

    // 冲动卡入口 → 选剧情卡 → 确认（触发 session/start）
    fireEvent.click(screen.getByTestId('impulse-card-plot'));
    fireEvent.click(screen.getByTestId('impulse-confirm'));

    // 新开场语在（后端 cadfcb3 同源句）
    expect(await screen.findByText(/接下来我会一次问你一个问题/)).toBeTruthy();
    expect(screen.getByText(/帮你把它变成一个完整的世界/)).toBeTruthy();
    // 旧语清零（施工单验收：grep「我将围绕」= 0）
    expect(screen.queryByText(/我将围绕/)).toBeNull();
  });
});
