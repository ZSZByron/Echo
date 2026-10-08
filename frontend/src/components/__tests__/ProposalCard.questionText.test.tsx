/**
 * ProposalCard question_text tests (D23)
 *
 * When proposal.question_text is non-empty it replaces the generic field
 * copy; otherwise the existing 字段 line stays untouched.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProposalCard } from '../guided/ProposalCard';
import type { A1Proposal } from '../../types/a1';

vi.mock('../../api/a1', () => ({
  confirmFillProposal: vi.fn(() => Promise.resolve({ success: true })),
}));

const baseProposal: A1Proposal = {
  key: 'k1',
  module: 'world',
  subfield: 'history',
  old: '旧',
  new: '新',
  conflict_note: null,
  merge_preview: '旧；新',
};

describe('ProposalCard question_text', () => {
  const onResolved = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows question_text instead of the generic field line when present', () => {
    render(
      <ProposalCard
        proposal={{ ...baseProposal, question_text: '这个世界的历史到底该怎么算？' }}
        sessionId="s1"
        onResolved={onResolved}
        fieldLabel="world.history"
      />
    );

    expect(screen.getByText('这个世界的历史到底该怎么算？')).toBeInTheDocument();
    expect(screen.queryByText(/字段：world\.history/)).not.toBeInTheDocument();
    // Three action buttons stay
    expect(screen.getByText('替换')).toBeInTheDocument();
    expect(screen.getByText('合并保留两者 ✓')).toBeInTheDocument();
    expect(screen.getByText('放弃')).toBeInTheDocument();
  });

  it('falls back to the generic field line when question_text is missing', () => {
    render(
      <ProposalCard
        proposal={baseProposal}
        sessionId="s1"
        onResolved={onResolved}
        fieldLabel="world.history"
      />
    );

    expect(screen.getByText('字段：world.history')).toBeInTheDocument();
  });

  it('falls back to the generic field line when question_text is empty', () => {
    render(
      <ProposalCard
        proposal={{ ...baseProposal, question_text: '' }}
        sessionId="s1"
        onResolved={onResolved}
        fieldLabel="world.history"
      />
    );

    expect(screen.getByText('字段：world.history')).toBeInTheDocument();
  });
});
