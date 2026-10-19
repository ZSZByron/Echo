/**
 * P0-2 商业加固批：ErrorBoundary 单测
 * 1. 子组件抛错 → fallback 错误卡可见（绝不白屏）
 * 2. 点重试 → state 复位，子组件恢复渲染
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary';

function Bomb({ explode }: { explode: boolean }) {
  if (explode) throw new Error('boom-render-crash');
  return <div data-testid="bomb-fine">一切正常</div>;
}

describe('ErrorBoundary（P0-2 商业加固批）', () => {
  beforeEach(() => {
    cleanup();
    // React 会把组件树抛错打到 console.error——测试里静音
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    (console.error as unknown as ReturnType<typeof vi.spyOn>).mockRestore();
  });

  it('子组件抛错 → fallback 错误卡可见（含标题与错误摘要）', () => {
    render(
      <ErrorBoundary>
        <Bomb explode />
      </ErrorBoundary>,
    );

    expect(screen.getByTestId('error-boundary')).toBeTruthy();
    expect(screen.getByText('这块区域出了点问题')).toBeTruthy();
    expect(screen.getByText(/boom-render-crash/)).toBeTruthy();
    expect(screen.getByTestId('error-boundary-retry')).toBeTruthy();
  });

  it('点重试 → state 复位，子组件恢复渲染', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <Bomb explode />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId('error-boundary')).toBeTruthy();

    // 先换上不炸的子组件（hasError 期间 children 不渲染，不会再次抛错），
    // 再点重试复位 state → 正常渲染，错误卡退场
    rerender(
      <ErrorBoundary>
        <Bomb explode={false} />
      </ErrorBoundary>,
    );
    fireEvent.click(screen.getByTestId('error-boundary-retry'));

    expect(screen.queryByTestId('error-boundary')).toBeNull();
    expect(screen.getByTestId('bomb-fine')).toBeTruthy();
  });
});
