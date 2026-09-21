/**
 * E1-Lite T4：A1Workspace impulse 结构化上送单测
 *
 * 路径断言：
 * 1. happy：plot 主 + romance 次 → start 请求体含 impulse_primary/impulse_secondary
 * 2. 次冲动为空 → 请求体无 impulse_secondary 键（缺省语义）
 * 3. skip / nostalgia → 不发 session/start（无 profile，默认序，不上送）
 * 附：设定侧 2 型 → 暂存 pendingImpulseRef，分组种子页点种子时随请求体上送
 *
 * 惯例：不用 fake timers / waitFor；mock fetch 断言请求体。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { A1Workspace } from '../../A1Workspace';
import type { ImpulseTypeId } from '../impulseCards.config';

const card = (id: ImpulseTypeId) => screen.getByTestId(`impulse-card-${id}`);

type StartBody = Record<string, unknown>;

const SEED = {
  id: '1',
  name: '深渊低语',
  genre: '哲理',
  description: 'desc',
  dimension_defaults: {},
};

/** 装一个捕获 session/start 请求体的 fetch stub，返回捕获数组 */
function stubFetch() {
  const startBodies: StartBody[] = [];
  const impl = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
    const u = String(url);
    if (u.includes('/api/a1/seeds')) {
      return new Response(JSON.stringify({ seeds: [SEED] }), { status: 200 });
    }
    if (u.includes('/api/a1/session/start')) {
      startBodies.push(JSON.parse(String(init?.body ?? '{}')) as StartBody);
      return new Response(JSON.stringify({
        session_id: 's-1', file_id: 'f-1', ip_code: 'IP-1',
        first_question: null, file: {},
      }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 200 });
  });
  vi.stubGlobal('fetch', impl);
  return startBodies;
}

describe('A1Workspace impulse 结构化上送（E1-Lite T4）', () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    localStorage.setItem('user_id', 'u-test');
    localStorage.removeItem('a1_telemetry_v1');
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('happy：plot 主 + romance 次 → 请求体含 impulse_primary/impulse_secondary + custom_idea', async () => {
    const startBodies = stubFetch();
    render(<A1Workspace />);

    fireEvent.click(card('plot'));
    fireEvent.click(card('romance'));
    fireEvent.click(screen.getByTestId('impulse-confirm'));

    expect(startBodies).toHaveLength(1);
    const body = startBodies[0];
    expect(body.impulse_primary).toBe('plot');
    expect(body.impulse_secondary).toBe('romance');
    expect(typeof body.custom_idea).toBe('string');
  });

  it('次冲动为空 → 请求体无 impulse_secondary 键（缺省语义）', async () => {
    const startBodies = stubFetch();
    render(<A1Workspace />);

    fireEvent.click(card('plot'));
    fireEvent.click(screen.getByTestId('impulse-confirm'));

    expect(startBodies).toHaveLength(1);
    const body = startBodies[0];
    expect(body.impulse_primary).toBe('plot');
    expect('impulse_secondary' in body).toBe(false);
  });

  it('skip 路径 → 不发 session/start，请求体不含 impulse 键', async () => {
    const startBodies = stubFetch();
    render(<A1Workspace />);

    fireEvent.click(screen.getByTestId('impulse-skip'));
    expect(startBodies).toHaveLength(0);
  });

  it('nostalgia 路径 → 不发 session/start（无 profile，默认序）', async () => {
    const startBodies = stubFetch();
    render(<A1Workspace />);

    fireEvent.click(card('nostalgia'));
    fireEvent.click(screen.getByTestId('impulse-confirm'));
    expect(startBodies).toHaveLength(0);
  });

  it('设定侧 2 型：确认后暂存，分组种子页点种子时随请求体上送 primary', async () => {
    const startBodies = stubFetch();
    render(<A1Workspace />);

    fireEvent.click(card('setting_heavy'));
    fireEvent.click(screen.getByTestId('impulse-confirm'));
    expect(startBodies).toHaveLength(0);

    // 分组种子页出现种子卡片，点击触发 startSession
    fireEvent.click(await screen.findByText('深渊低语'));
    expect(startBodies).toHaveLength(1);
    const body = startBodies[0];
    expect(body.seed_id).toBe(SEED.id);
    expect(body.impulse_primary).toBe('setting_heavy');
    expect('impulse_secondary' in body).toBe(false);
  });
});
