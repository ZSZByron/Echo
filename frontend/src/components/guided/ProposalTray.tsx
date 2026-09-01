/**
 * ProposalTray Component
 *
 * Right-bottom tray for storing pending proposals.
 * Shows flag icon with red dot counter.
 * Opens to display list of proposals that can be processed.
 * 
 * Part of the guided review flow (Task 8: A1前端提案卡片+托盘+模糊响应重述+单问句铁律)
 */

import { useState } from 'react';
import type { A1Proposal } from '../../types/a1';
import { ProposalCard } from './ProposalCard';

export interface ProposalTrayProps {
  /** List of pending proposals in tray */
  proposals: A1Proposal[];
  /** Session ID for API calls */
  sessionId: string;
  /** Callback when a proposal is resolved (removed from list) */
  onResolved: (key: string) => void;
  /** Callback to restore a proposal from tray to card view */
  onRestore?: (key: string) => void;
}

export function ProposalTray({
  proposals,
  sessionId,
  onResolved,
  onRestore,
}: ProposalTrayProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Note: onRestore is prepared for future functionality
  // Currently unused but kept for API compatibility
  void onRestore;

  if (proposals.length === 0) {
    return null;
  }

  return (
    <>
      {/* Tray toggle button (fixed position) */}
      <div className="fixed bottom-6 right-6 z-40">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="relative glass-panel px-4 py-3 rounded-lg border border-stardust-400/40 hover:border-stardust-400 transition-all shadow-lg backdrop-blur-sm"
          title={`${proposals.length} 个待处理提案`}
        >
          <span className="text-stardust-400 text-xl">⚑</span>
          {proposals.length > 0 && (
            <span className="absolute -top-2 -right-2 bg-cosmos-error text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
              {proposals.length}
            </span>
          )}
        </button>
      </div>

      {/* Tray panel (slide-up drawer) */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-space-950/60 backdrop-blur-sm z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Tray content */}
          <div className="fixed bottom-0 right-0 left-0 z-50 max-h-[60vh] overflow-y-auto starry-scroll">
            <div className="glass-panel border-t border-stardust-400/40 p-6">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-stardust-400 text-xl">⚑</span>
                  <h3 className="text-stardust-300 text-lg font-medium">
                    提案托盘
                  </h3>
                  <span className="text-nebula-400 text-sm">
                    {proposals.length} 个待处理
                  </span>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-void-400 hover:text-stardust-300 transition-colors"
                >
                  ✕
                </button>
              </div>

              {/* Proposals list */}
              <div className="space-y-4">
                {proposals.map((proposal) => (
                  <ProposalCard
                    key={proposal.key}
                    proposal={proposal}
                    sessionId={sessionId}
                    onResolved={onResolved}
                    fieldLabel={`${proposal.module}.${proposal.subfield}`}
                  />
                ))}
              </div>

              {/* Bottom hint */}
              <div className="text-void-400 text-xs mt-4 text-center italic">
                处理完提案后可继续访谈，提案会自动进入托盘
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
