/**
 * AlignmentCard Component Tests
 *
 * D21 T10: 对齐推测卡 — in-message-flow card for AI-inferred worldview alignments.
 * TDD: Tests written first to define component behavior before implementation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AlignmentCard, ACTION_LABELS } from '../guided/AlignmentCard';
import { GuidedChat } from '../guided/GuidedChat';
import type { AlignmentItem } from '../../types/a1';

// Mock the API module (GuidedChat-level resolve goes through resolveAlignment)
vi.mock('../../api/a1', () => ({
  confirmFillProposal: vi.fn(() => Promise.resolve({ success: true, message: 'ok' })),
  resolveAlignment: vi.fn(() => Promise.resolve({ applied: true, accept: true })),
}));

import { resolveAlignment } from '../../api/a1';

const mockOnResolve = vi.fn(() => Promise.resolve());

function makeItem(overrides?: Partial<AlignmentItem>): AlignmentItem {
  return {
    key: 'align-1',
    action: 'link',
    content: '你提到的月城与已有的浮空都市是同一个设定',
    quote: '月城其实就漂浮在那片海之上',
    stale_warning: [],
    ...overrides,
  };
}

describe('AlignmentCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the corresponding badge label for each of the four actions (closed set)', () => {
    const actions = ['link', 'dedupe', 'contradict', 'update'] as const;
    const expected = ['关联', '去重', '矛盾', '更新'];

    actions.forEach((action, i) => {
      const { unmount } = render(
        <AlignmentCard item={makeItem({ action })} onResolve={mockOnResolve} />
      );
      expect(screen.getByTestId('alignment-action-badge')).toHaveTextContent(expected[i]);
      unmount();
    });
    // Closed set: exactly four labels
    expect(Object.keys(ACTION_LABELS).sort()).toEqual(['contradict', 'dedupe', 'link', 'update']);
  });

  it('content contains no internal key forms and no node-id prefixes', () => {
    render(<AlignmentCard item={makeItem()} onResolve={mockOnResolve} />);

    const text = document.body.textContent || '';
    // No module.subfield internal-key form
    expect(text).not.toMatch(/[a-z_]+\.[a-z_]+/);
    // No node-id forms (term: prefix or lone colon-prefixed ids)
    expect(text).not.toMatch(/term:/);
    expect(text).not.toMatch(/:\s*[a-z_]+/);
  });

  it('clicking 采纳 calls onResolve(key, true)', async () => {
    render(<AlignmentCard item={makeItem()} onResolve={mockOnResolve} />);

    fireEvent.click(screen.getByRole('button', { name: '采纳' }));

    await waitFor(() => {
      expect(mockOnResolve).toHaveBeenCalledWith('align-1', true);
    });
  });

  it('clicking 不是这样 calls onResolve(key, false)', async () => {
    render(<AlignmentCard item={makeItem()} onResolve={mockOnResolve} />);

    fireEvent.click(screen.getByRole('button', { name: '不是这样' }));

    await waitFor(() => {
      expect(mockOnResolve).toHaveBeenCalledWith('align-1', false);
    });
  });

  it('renders each stale_warning entry as its own amber line', () => {
    render(
      <AlignmentCard
        item={makeItem({ stale_warning: ['将使概念「月城」过期', '将使关系「月城-潮汐」过期'] })}
        onResolve={mockOnResolve}
      />
    );

    const lines = screen.getAllByTestId('alignment-stale-warning');
    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(line).toHaveClass('text-cosmos-warning');
    }
    expect(lines[0]).toHaveTextContent('将使概念「月城」过期');
    expect(lines[1]).toHaveTextContent('将使关系「月城-潮汐」过期');
  });

  it('does not render quote marks when quote is empty', () => {
    render(<AlignmentCard item={makeItem({ quote: '' })} onResolve={mockOnResolve} />);

    expect(screen.queryByTestId('alignment-quote')).not.toBeInTheDocument();
  });

  it('renders quote as styled citation when present', () => {
    render(<AlignmentCard item={makeItem()} onResolve={mockOnResolve} />);

    const quote = screen.getByTestId('alignment-quote');
    expect(quote).toHaveTextContent('月城其实就漂浮在那片海之上');
  });

  it('disables both buttons while resolve is in flight (double-click guard)', async () => {
    let resolvePromise: (v: void) => void = () => {};
    const slowResolve = vi.fn(
      () => new Promise<void>((r) => { resolvePromise = r; })
    );
    render(<AlignmentCard item={makeItem()} onResolve={slowResolve} />);

    fireEvent.click(screen.getByRole('button', { name: '采纳' }));
    expect(screen.getByRole('button', { name: '采纳' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '不是这样' })).toBeDisabled();

    resolvePromise();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '采纳' })).not.toBeDisabled();
    });
  });
});

describe('GuidedChat alignment integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderChat(alignments: AlignmentItem[]) {
    return render(
      <GuidedChat
        messages={[{ id: 'm1', type: 'assistant', text: '我注意到一个关联' }]}
        onSend={() => {}}
        alignments={alignments}
        fileId="file-1"
      />
    );
  }

  it('renders N cards for a pending_alignments array', () => {
    renderChat([
      makeItem({ key: 'k1' }),
      makeItem({ key: 'k2', action: 'dedupe' }),
    ]);

    expect(screen.getAllByTestId('alignment-card')).toHaveLength(2);
    expect(screen.getByText('关联')).toBeInTheDocument();
    expect(screen.getByText('去重')).toBeInTheDocument();
  });

  it('removes the card after resolve', async () => {
    renderChat([makeItem({ key: 'k1' })]);

    fireEvent.click(screen.getByRole('button', { name: '采纳' }));

    await waitFor(() => {
      expect(resolveAlignment).toHaveBeenCalledWith('file-1', 'k1', true);
    });
    await waitFor(() => {
      expect(screen.queryByTestId('alignment-card')).not.toBeInTheDocument();
    });
  });

  it('removes card and shows inline hint on not_found (no error popup)', async () => {
    vi.mocked(resolveAlignment).mockResolvedValueOnce({
      applied: false,
      accept: true,
      error: 'not_found',
    });
    renderChat([makeItem({ key: 'k1' })]);

    fireEvent.click(screen.getByRole('button', { name: '采纳' }));

    await waitFor(() => {
      expect(screen.queryByTestId('alignment-card')).not.toBeInTheDocument();
    });
    expect(screen.getByTestId('alignment-stale-hint')).toHaveTextContent('这条已经处理过了');
  });
});
