import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { NostalgiaConfirmPage } from '../NostalgiaConfirmPage';

describe('NostalgiaConfirmPage — 有预填分支（happy path）', () => {
  it('渲染确认标题 + 预填计数 + 文件名语境 + 继续按钮可用', () => {
    const onContinue = vi.fn();
    render(
      <NostalgiaConfirmPage prefillCount={23} seedName="明华修仙.txt" onContinue={onContinue} />
    );

    expect(screen.getByText('它认出了你的世界')).toBeInTheDocument();
    expect(screen.getByText(/23 处设定/)).toBeInTheDocument();
    expect(screen.getByText(/来自《明华修仙\.txt》/)).toBeInTheDocument();

    const btn = screen.getByTestId('nostalgia-continue');
    expect(btn).toBeEnabled();
    fireEvent.click(btn);
    expect(onContinue).toHaveBeenCalledTimes(1);
  });

  it('根节点带 nostalgia-confirm testid（T8 E2E 依赖）', () => {
    render(<NostalgiaConfirmPage prefillCount={1} seedName="a.txt" onContinue={vi.fn()} />);
    expect(screen.getByTestId('nostalgia-confirm')).toBeInTheDocument();
  });
});

describe('NostalgiaConfirmPage — 零预填诚实降级（核心纪律）', () => {
  it('绝不渲染"认出"类文案，降级标题出现，流程不阻断', () => {
    const onContinue = vi.fn();
    render(
      <NostalgiaConfirmPage prefillCount={0} seedName="空白.txt" onContinue={onContinue} />
    );

    // 断言级：零预填分支"认出"字样零渲染
    expect(screen.queryByText(/认出/)).toBeNull();
    expect(screen.queryByText('它认出了你的世界')).toBeNull();

    // 降级标题与引导语
    expect(screen.getByText('我们读完了你的文档')).toBeInTheDocument();

    // onContinue 仍可用
    const btn = screen.getByTestId('nostalgia-continue');
    expect(btn).toBeEnabled();
    fireEvent.click(btn);
    expect(onContinue).toHaveBeenCalledTimes(1);
  });
});
