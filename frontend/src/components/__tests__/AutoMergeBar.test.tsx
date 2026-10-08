/**
 * AutoMergeBar Component Tests (D23)
 *
 * Disclosure text + inline undo button; undo calls mergeUndo and hides the bar.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AutoMergeBar } from '../guided/AutoMergeBar';
import type { AutoMergeDisclosure } from '../../types/a1';

vi.mock('../../api/a1', () => ({
  mergeUndo: vi.fn(() => Promise.resolve({ restored: true })),
}));

import { mergeUndo } from '../../api/a1';

const merge = (overrides?: Partial<AutoMergeDisclosure>): AutoMergeDisclosure => ({
  token: 'tok-1',
  field_key: 'world.history',
  label: '历史纪元',
  old: '旧纪元',
  new: '新纪元设定内容',
  merged: '合并结果',
  kind: 'semantic_merge',
  ...overrides,
});

describe('AutoMergeBar', () => {
  const onUndone = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the disclosure text and an undo button', () => {
    render(<AutoMergeBar merges={[merge()]} sessionId="s1" onUndone={onUndone} />);

    expect(screen.getByTestId('auto-merge-bar')).toBeInTheDocument();
    expect(screen.getByText(/已把『新纪元设定内容』并入【历史纪元】/)).toBeInTheDocument();
    expect(screen.getByText('撤销')).toBeInTheDocument();
  });

  it('truncates the merged fragment to 20 chars', () => {
    const long = '一'.repeat(30);
    render(<AutoMergeBar merges={[merge({ new: long })]} sessionId="s1" />);

    expect(screen.getByText(/已把『一{20}…』并入/)).toBeInTheDocument();
  });

  it('calls mergeUndo on undo click and hides the bar on success', async () => {
    render(<AutoMergeBar merges={[merge()]} sessionId="s1" onUndone={onUndone} />);

    fireEvent.click(screen.getByText('撤销'));

    await waitFor(() => {
      expect(mergeUndo).toHaveBeenCalledWith('s1', 'tok-1');
    });
    await waitFor(() => {
      expect(screen.queryByTestId('auto-merge-bar')).not.toBeInTheDocument();
    });
    expect(onUndone).toHaveBeenCalledWith('tok-1');
  });

  it('renders nothing when merges is empty', () => {
    render(<AutoMergeBar merges={[]} sessionId="s1" />);
    expect(screen.queryByTestId('auto-merge-bar')).not.toBeInTheDocument();
  });
});
