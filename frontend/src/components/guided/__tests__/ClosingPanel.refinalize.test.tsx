/**
 * a1-oq-phase T4 红测：ClosingPanel variant 抽参（二次收尾面板复用）
 * - variant="refinalize"：标题/动作按钮为重定稿语义
 * - 默认（first）：既有文案字节不变
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ClosingPanel } from '../ClosingPanel';

describe('ClosingPanel variant（a1-oq-phase T4）', () => {
  it('默认（first）→ 既有文案字节不变', () => {
    render(
      <ClosingPanel
        triggered
        consumers={[]}
        onFinalize={vi.fn()}
        onContinue={vi.fn()}
      />
    );
    expect(screen.getByText('快到收尾的时候了')).toBeTruthy();
    expect(screen.getByTestId('closing-action-finalize').textContent).toBe(
      '生成文档'
    );
  });

  it('variant="refinalize" → 重定稿产物语义（标题 + 动作按钮）', () => {
    render(
      <ClosingPanel
        triggered
        consumers={[]}
        onFinalize={vi.fn()}
        onContinue={vi.fn()}
        variant="refinalize"
      />
    );
    expect(screen.getByText('开放问题答完了——重新定稿你的文档')).toBeTruthy();
    expect(screen.getByTestId('closing-action-finalize').textContent).toBe(
      '重新定稿并更新文档'
    );
  });
});
