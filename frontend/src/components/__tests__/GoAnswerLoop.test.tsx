/**
 * 去回答闭环 + stale fileId 404 自动恢复
 *
 * - deriveOldestPendingQuestion: open_questions → 最老 pending/asked 卡片 + 角标数
 * - isNotFoundError: ApiError.status=404 / 降级 message 含 404
 * - GraphViewContent: loadFileData 404 → onFileMissing（父级切 seed_selector + 提示条）
 *
 * 说明：A1Workspace 页面本体挂载需 mock 全部端点（seeds/chat/file），重而脆；
 * 故闭环派生逻辑抽为纯函数单测 + GraphViewContent 组件级断言 404 恢复路径。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import {
  GraphViewContent,
  deriveOldestPendingQuestion,
  isNotFoundError,
  type OpenQuestionRecord,
} from '../../pages/a1/A1Workspace';

// ResizeObserver stub for jsdom (A1GraphSection → React Flow)
class ResizeObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

beforeEach(() => {
  window.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
});

vi.mock('../../api/client', () => ({
  fetchJson: vi.fn(),
  ApiError: class extends Error {
    status: number;
    body: unknown;
    constructor(status: number, body: unknown) {
      super(`HTTP ${status}`);
      this.name = 'ApiError';
      this.status = status;
      this.body = body;
    }
  },
}));

vi.mock('../../api/a1', () => ({
  confirmEdge: vi.fn(() => Promise.resolve({ success: true, message: 'ok' })),
}));

import { fetchJson, ApiError } from '../../api/client';

describe('deriveOldestPendingQuestion（去回答闭环）', () => {
  it('returns the oldest pending/asked record and its count', () => {
    const questions: OpenQuestionRecord[] = [
      { id: 'q1', question: '最早的问题', status: 'answered' },
      { id: 'q2', question: '最老的待问', status: 'pending' },
      { id: 'q3', question: '第二老的待问', status: 'asked' },
      { id: 'q4', question: '已跳过', status: 'skipped' },
    ];

    const derived = deriveOldestPendingQuestion(questions);
    expect(derived.question).toEqual({ id: 'q2', question: '最老的待问' });
    expect(derived.count).toBe(2);
  });

  it('returns null when nothing is pending/asked', () => {
    const questions: OpenQuestionRecord[] = [
      { id: 'q1', question: 'a', status: 'answered' },
      { id: 'q2', question: 'b', status: 'skipped' },
    ];

    const derived = deriveOldestPendingQuestion(questions);
    expect(derived.question).toBeNull();
    expect(derived.count).toBe(0);
  });
});

describe('isNotFoundError（stale fileId 识别）', () => {
  it('matches ApiError with status 404', () => {
    expect(isNotFoundError(new ApiError(404, {}))).toBe(true);
  });

  it('does not match other ApiError statuses', () => {
    expect(isNotFoundError(new ApiError(500, {}))).toBe(false);
    expect(isNotFoundError(new ApiError(409, {}))).toBe(false);
  });

  it('matches plain Error messages containing 404 (legacy fetch path)', () => {
    expect(isNotFoundError(new Error('HTTP 404'))).toBe(true);
    expect(isNotFoundError(new Error('network down'))).toBe(false);
  });
});

describe('GraphViewContent - stale fileId 404 恢复', () => {
  const baseProps = {
    returnToChat: vi.fn(),
    graphCode: 'graph_v1',
    fileStatus: 'finalized' as const,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls onFileMissing when file data fetch returns 404', async () => {
    vi.mocked(fetchJson).mockRejectedValue(new ApiError(404, { detail: 'not found' }));
    const onFileMissing = vi.fn();

    render(
      <GraphViewContent fileId="stale-file" {...baseProps} onFileMissing={onFileMissing} />
    );

    await waitFor(() => {
      expect(onFileMissing).toHaveBeenCalledTimes(1);
    });
  });

  it('does NOT call onFileMissing for non-404 errors (retry screen stays)', async () => {
    vi.mocked(fetchJson).mockRejectedValue(new ApiError(500, {}));
    const onFileMissing = vi.fn();

    render(
      <GraphViewContent fileId="some-file" {...baseProps} onFileMissing={onFileMissing} />
    );

    await waitFor(() => {
      // loadGraph 也失败，但不应触发 stale 恢复
      expect(vi.mocked(fetchJson)).toHaveBeenCalled();
    });
    expect(onFileMissing).not.toHaveBeenCalled();
  });
});
