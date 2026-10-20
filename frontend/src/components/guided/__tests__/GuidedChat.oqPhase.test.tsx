/**
 * a1-oq-phase T4 红测：GuidedChat 相位驱动
 * 1. oq_phase 激活 → 输入框 placeholder = 当前待问问题文本
 * 2. ✦ 待问卡成为对话主体（相位高亮 data-phase="active"）
 * 3. proposal 横幅：提案在场 → 顶部横幅，输入框保持可用（F2 短指令可消解）
 * 4. 非相位态：placeholder 维持默认（旧行为逐字节不变）
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GuidedChat } from '../GuidedChat';
import type { A1Proposal } from '../../../types/a1';

const Q = '这个世界的纪年是什么？';

const proposal: A1Proposal = {
  key: 'k1',
  module: 'IP定位',
  subfield: 'name',
  old: '旧值',
  new: '新值',
  conflict_note: null,
  merge_preview: '旧值；新值',
};

describe('GuidedChat oq_phase 相位驱动（a1-oq-phase T4）', () => {
  it('相位激活 → placeholder 绑定当前待问问题文本', () => {
    render(
      <GuidedChat
        messages={[]}
        onSend={vi.fn()}
        pendingQuestion={{ id: 'oq-001', question: Q }}
        pendingQuestionsCount={1}
        oqPhaseActive
      />
    );
    const textarea = screen.getByPlaceholderText(Q) as HTMLTextAreaElement;
    expect(textarea).toBeTruthy();
  });

  it('相位激活 → ✦ 待问卡为对话主体（data-phase="active" 高亮）', () => {
    render(
      <GuidedChat
        messages={[]}
        onSend={vi.fn()}
        pendingQuestion={{ id: 'oq-001', question: Q }}
        pendingQuestionsCount={1}
        oqPhaseActive
      />
    );
    const card = screen.getByTestId('pending-question-card');
    expect(card.getAttribute('data-phase')).toBe('active');
    expect(card.textContent).toContain(Q);
  });

  it('提案在场 → 顶部横幅渲染，输入框保持可用（F2 短指令可消解）', () => {
    render(
      <GuidedChat
        messages={[]}
        onSend={vi.fn()}
        proposals={[proposal]}
        oqPhaseActive
        pendingQuestion={{ id: 'oq-001', question: Q }}
      />
    );
    expect(screen.getByTestId('proposal-banner').textContent).toContain(
      '有一条待确认修改待处理'
    );
    const textarea = screen.getByPlaceholderText(Q) as HTMLTextAreaElement;
    expect(textarea.disabled).toBe(false);
  });

  it('非相位态 → placeholder 维持默认（旧行为零改动）', () => {
    render(
      <GuidedChat
        messages={[]}
        onSend={vi.fn()}
        pendingQuestion={{ id: 'oq-001', question: Q }}
        pendingQuestionsCount={1}
      />
    );
    expect(screen.getByPlaceholderText('Type your message...')).toBeTruthy();
  });
});
