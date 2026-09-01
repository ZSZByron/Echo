/**
 * ProposalCard Component Tests
 *
 * TDD: Tests written first to define component behavior before implementation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProposalCard } from '../guided/ProposalCard';
import type { A1Proposal } from '../../types/a1';

// Mock the API module
vi.mock('../../api/a1', () => ({
  confirmFillProposal: vi.fn(() => Promise.resolve({ success: true, message: 'Proposal resolved' })),
}));

import { confirmFillProposal } from '../../api/a1';

describe('ProposalCard', () => {
  const mockSessionId = 'test-session-123';
  const mockOnResolved = vi.fn();

  const createMockProposal = (overrides?: Partial<A1Proposal>): A1Proposal => ({
    key: 'test-key',
    module: 'test_module',
    subfield: 'test_subfield',
    old: 'Old value',
    new: 'New value',
    conflict_note: null,
    merge_preview: 'Old value；New value',
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render proposal card with conflict_note', () => {
    const proposal = createMockProposal({
      conflict_note: 'This conflicts with existing content',
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    // Should show conflict warning
    expect(screen.getByText('⚠')).toBeInTheDocument();
    expect(screen.getByText('与已有设定重叠')).toBeInTheDocument();
    expect(screen.getByText('This conflicts with existing content')).toBeInTheDocument();
  });

  it('should render proposal card without conflict_note', () => {
    const proposal = createMockProposal({
      conflict_note: null,
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    // Should not show conflict warning
    expect(screen.queryByText('⚠')).not.toBeInTheDocument();
    expect(screen.queryByText('与已有设定重叠')).not.toBeInTheDocument();
  });

  it('should show old and new values in comparison boxes', () => {
    const proposal = createMockProposal({
      old: 'Original content here',
      new: 'New suggested content',
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    expect(screen.getByText('Original content here')).toBeInTheDocument();
    expect(screen.getByText('New suggested content')).toBeInTheDocument();
  });

  it('should show merge preview when merge is available', () => {
    const proposal = createMockProposal({
      merge_preview: 'Original；New',
      options: ['replace', 'merge', 'drop'],
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    expect(screen.getByText('Original；New')).toBeInTheDocument();
  });

  it('should call confirmFillProposal with merge when merge button clicked', async () => {
    const proposal = createMockProposal({
      key: 'proposal-abc',
      options: ['replace', 'merge', 'drop'],
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    const mergeButton = screen.getByText('合并保留两者 ✓');
    fireEvent.click(mergeButton);

    expect(confirmFillProposal).toHaveBeenCalledWith(mockSessionId, 'proposal-abc', 'merge');
    // Wait for async and then check callback
    await new Promise(resolve => setTimeout(resolve, 0));
    expect(mockOnResolved).toHaveBeenCalledWith('proposal-abc');
  });

  it('should call confirmFillProposal with replace when replace button clicked', async () => {
    const proposal = createMockProposal({
      key: 'proposal-xyz',
      options: ['replace', 'merge', 'drop'],
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    const replaceButton = screen.getByText('替换');
    fireEvent.click(replaceButton);

    expect(confirmFillProposal).toHaveBeenCalledWith(mockSessionId, 'proposal-xyz', 'replace');
    await new Promise(resolve => setTimeout(resolve, 0));
    expect(mockOnResolved).toHaveBeenCalledWith('proposal-xyz');
  });

  it('should call confirmFillProposal with drop when drop button clicked', async () => {
    const proposal = createMockProposal({
      key: 'proposal-drop',
      options: ['replace', 'merge', 'drop'],
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    const dropButton = screen.getByText('放弃');
    fireEvent.click(dropButton);

    expect(confirmFillProposal).toHaveBeenCalledWith(mockSessionId, 'proposal-drop', 'drop');
    await new Promise(resolve => setTimeout(resolve, 0));
    expect(mockOnResolved).toHaveBeenCalledWith('proposal-drop');
  });

  it('should disable merge button when merge not in options', () => {
    const proposal = createMockProposal({
      key: 'proposal-no-merge',
      options: ['replace', 'drop'], // No merge option
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    const mergeButton = screen.getByText('合并保留两者 ✓');
    expect(mergeButton).toBeDisabled();
    expect(mergeButton).toHaveClass('cursor-not-allowed');
  });

  it('should show bottom hint about skipping', () => {
    const proposal = createMockProposal();

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        fieldLabel="Test Field"
      />
    );

    expect(screen.getByText('输入"跳过"将跳过当前问题而非处理提案')).toBeInTheDocument();
  });

  it('should use default field label when none provided', () => {
    const proposal = createMockProposal({
      module: 'Geography',
      subfield: 'special_geo',
    });

    render(
      <ProposalCard
        proposal={proposal}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    expect(screen.getByText('字段：Geography.special_geo')).toBeInTheDocument();
  });
});
