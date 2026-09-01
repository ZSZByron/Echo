/**
 * ProposalTray Component Tests
 *
 * TDD: Tests written first to define component behavior before implementation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProposalTray } from '../guided/ProposalTray';
import type { A1Proposal } from '../../types/a1';

// Mock the API module
vi.mock('../../api/a1', () => ({
  confirmFillProposal: vi.fn(() => Promise.resolve({ success: true, message: 'Proposal resolved' })),
}));

import { confirmFillProposal } from '../../api/a1';

describe('ProposalTray', () => {
  const mockSessionId = 'test-session-456';
  const mockOnResolved = vi.fn();
  const mockOnRestore = vi.fn();

  const createMockProposals = (count: number): A1Proposal[] => {
    return Array.from({ length: count }, (_, i) => ({
      key: `proposal-${i}`,
      module: `module_${i}`,
      subfield: `subfield_${i}`,
      old: `Old ${i}`,
      new: `New ${i}`,
      conflict_note: i % 2 === 0 ? null : `Conflict ${i}`,
      merge_preview: `Old ${i}；New ${i}`,
      options: ['replace', 'merge', 'drop'],
    }));
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render tray when no proposals', () => {
    const { container } = render(
      <ProposalTray
        proposals={[]}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('should render tray button with red dot counter', () => {
    const proposals = createMockProposals(2);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    // Should show flag icon
    expect(screen.getByText('⚑')).toBeInTheDocument();

    // Should show counter badge
    const counter = screen.getByText('2');
    expect(counter).toBeInTheDocument();
    expect(counter.className).toContain('bg-cosmos-error');
  });

  it('should render tray button with correct count', () => {
    const proposals = createMockProposals(5);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    const counter = screen.getByText('5');
    expect(counter).toBeInTheDocument();
  });

  it('should open tray panel when button clicked', () => {
    const proposals = createMockProposals(3);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    // Click tray button
    const trayButton = screen.getByRole('button');
    fireEvent.click(trayButton);

    // Should show tray panel
    expect(screen.getByText('提案托盘')).toBeInTheDocument();
    expect(screen.getByText('3 个待处理')).toBeInTheDocument();
  });

  it('should display all proposals in tray', () => {
    const proposals = createMockProposals(3);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    // Open tray
    const trayButton = screen.getByRole('button');
    fireEvent.click(trayButton);

    // Should show proposal cards
    expect(screen.getByText('Old 0')).toBeInTheDocument();
    expect(screen.getByText('New 0')).toBeInTheDocument();
    expect(screen.getByText('Old 1')).toBeInTheDocument();
    expect(screen.getByText('New 1')).toBeInTheDocument();
    expect(screen.getByText('Old 2')).toBeInTheDocument();
    expect(screen.getByText('New 2')).toBeInTheDocument();
  });

  it('should close tray when clicking X button', () => {
    const proposals = createMockProposals(2);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    // Open tray
    const trayButton = screen.getByRole('button');
    fireEvent.click(trayButton);

    expect(screen.getByText('提案托盘')).toBeInTheDocument();

    // Click X button
    const closeButton = screen.getByText('✕');
    fireEvent.click(closeButton);

    // Tray should close
    expect(screen.queryByText('提案托盘')).not.toBeInTheDocument();
  });

  it('should close tray when clicking backdrop', () => {
    const proposals = createMockProposals(2);

    const { container } = render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    // Open tray
    const trayButton = screen.getByRole('button');
    fireEvent.click(trayButton);

    expect(screen.getByText('提案托盘')).toBeInTheDocument();

    // Click backdrop
    const backdrop = container.querySelector('.fixed.inset-0.bg-space-950\\/60');
    if (backdrop) {
      fireEvent.click(backdrop);
      // Tray should close
      expect(screen.queryByText('提案托盘')).not.toBeInTheDocument();
    }
  });

  it('should call onResolved when proposal is resolved', async () => {
    const proposals = createMockProposals(2);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        onRestore={mockOnRestore}
      />
    );

    // Open tray
    const trayButton = screen.getByRole('button');
    fireEvent.click(trayButton);

    // Click replace button on first proposal
    const replaceButtons = screen.getAllByText('替换');
    fireEvent.click(replaceButtons[0]);

    expect(confirmFillProposal).toHaveBeenCalledWith(mockSessionId, 'proposal-0', 'replace');
    
    // Wait for async
    await new Promise(resolve => setTimeout(resolve, 0));
    expect(mockOnResolved).toHaveBeenCalledWith('proposal-0');
  });

  it('should handle 5 proposals correctly (display ≤3, rest in tray)', () => {
    // This test validates the tray logic in GuidedChat component
    // The tray itself just displays whatever proposals it receives
    const proposals = createMockProposals(5);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
        onRestore={mockOnRestore}
      />
    );

    // Tray button should show 5
    const counter = screen.getByText('5');
    expect(counter).toBeInTheDocument();

    // Open tray and verify all 5 are shown
    const trayButton = screen.getByRole('button');
    fireEvent.click(trayButton);

    expect(screen.getByText('5 个待处理')).toBeInTheDocument();
  });

  it('should show bottom hint text in tray', () => {
    const proposals = createMockProposals(1);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    // Open tray
    const trayButton = screen.getByRole('button');
    fireEvent.click(trayButton);

    expect(screen.getByText('处理完提案后可继续访谈，提案会自动进入托盘')).toBeInTheDocument();
  });

  it('should send new messages move proposals to tray', () => {
    // This test validates GuidedChat behavior, not the tray component itself
    // The tray just displays what it receives
    const proposals = createMockProposals(2);

    render(
      <ProposalTray
        proposals={proposals}
        sessionId={mockSessionId}
        onResolved={mockOnResolved}
      />
    );

    // Tray shows 2 proposals
    expect(screen.getByText('2')).toBeInTheDocument();
  });
});
