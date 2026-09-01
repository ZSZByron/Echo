/**
 * ProposalCard Component
 *
 * Displays a fill proposal with three action buttons: replace/merge/drop.
 * Shows conflict note, old/new comparison, and field labels.
 * 
 * Part of the guided review flow (Task 8: A1前端提案卡片+托盘+模糊响应重述+单问句铁律)
 */

import { confirmFillProposal } from '../../api/a1';
import type { A1Proposal } from '../../types/a1';

export interface ProposalCardProps {
  /** The proposal to display */
  proposal: A1Proposal;
  /** Session ID for API calls */
  sessionId: string;
  /** Callback when proposal is resolved (removed from list) */
  onResolved: (key: string) => void;
  /** Field label for display (Chinese) */
  fieldLabel?: string;
}

export function ProposalCard({
  proposal,
  sessionId,
  onResolved,
  fieldLabel,
}: ProposalCardProps) {
  const handleChoice = async (choice: 'replace' | 'merge' | 'drop') => {
    try {
      await confirmFillProposal(sessionId, proposal.key, choice);
      onResolved(proposal.key);
    } catch (error) {
      console.error('Failed to confirm proposal:', error);
    }
  };

  // Determine if merge is available (options array without 'merge')
  const canMerge = !proposal.options || proposal.options.includes('merge');
  
  // Determine if replace is available
  const canReplace = !proposal.options || proposal.options.includes('replace');
  
  // Determine if drop is available
  const canDrop = !proposal.options || proposal.options.includes('drop');

  return (
    <div className="glass-panel p-5 border border-nebula-400/30 mt-3 mb-3 shadow-lg backdrop-blur-sm">
      {/* Header with conflict warning if present */}
      <div className="flex items-start gap-2 mb-3">
        {proposal.conflict_note && (
          <span className="text-cosmos-warning text-xl">⚠</span>
        )}
        <div className="flex-1">
          <div className="text-stardust-300 text-sm font-medium mb-1">
            字段：{fieldLabel || `${proposal.module}.${proposal.subfield}`}
          </div>
          {proposal.conflict_note && (
            <div className="text-cosmos-warning text-xs">
              与已有设定重叠
            </div>
          )}
        </div>
      </div>

      {/* Old vs New comparison boxes */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        {/* Old value */}
        <div className="bg-space-800/50 border border-white/10 rounded p-3">
          <div className="text-void-400 text-xs mb-2">原设定</div>
          <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
            {proposal.old || '<空>'}
          </div>
        </div>

        {/* New value */}
        <div className="bg-space-800/50 border border-nebula-400/20 rounded p-3">
          <div className="text-nebula-400 text-xs mb-2">新内容</div>
          <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
            {proposal.new}
          </div>
        </div>
      </div>

      {/* Merge preview (if merge is possible) */}
      {canMerge && proposal.merge_preview && (
        <div className="bg-space-800/30 border border-white/5 rounded p-2 mb-3">
          <div className="text-void-400 text-xs mb-1">合并预览</div>
          <div className="text-stardust-300 text-xs leading-relaxed whitespace-pre-wrap">
            {proposal.merge_preview}
          </div>
        </div>
      )}

      {/* Conflict explanation */}
      {proposal.conflict_note && (
        <div className="bg-cosmos-warning/10 border border-cosmos-warning/30 rounded p-3 mb-3">
          <div className="text-cosmos-warning text-xs mb-1">冲突说明</div>
          <div className="text-gray-300 text-sm leading-relaxed">
            {proposal.conflict_note}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => handleChoice('replace')}
          disabled={!canReplace}
          className={`
            flex-1 px-4 py-2 rounded text-sm font-medium transition-all
            ${canReplace
              ? 'bg-space-700 text-gray-300 hover:bg-space-600 hover:text-stardust-200 border border-white/10'
              : 'bg-space-800/30 text-gray-600 cursor-not-allowed border border-white/5'
            }
          `}
        >
          替换
        </button>

        <button
          onClick={() => handleChoice('merge')}
          disabled={!canMerge}
          className={`
            flex-1 px-4 py-2 rounded text-sm font-medium transition-all border
            ${canMerge
              ? 'bg-cosmos-success/20 text-cosmos-success border-cosmos-success/50 hover:bg-cosmos-success/30 glow-starlight ring-2 ring-cosmos-success/30'
              : 'bg-space-800/30 text-gray-600 cursor-not-allowed border border-white/5'
            }
          `}
        >
          合并保留两者 ✓
        </button>

        <button
          onClick={() => handleChoice('drop')}
          disabled={!canDrop}
          className={`
            flex-1 px-4 py-2 rounded text-sm font-medium transition-all
            ${canDrop
              ? 'bg-space-700 text-gray-300 hover:bg-space-600 hover:text-stardust-200 border border-white/10'
              : 'bg-space-800/30 text-gray-600 cursor-not-allowed border border-white/5'
            }
          `}
        >
          放弃
        </button>
      </div>

      {/* Bottom hint */}
      <div className="text-void-400 text-xs mt-3 italic">
        输入"跳过"将跳过当前问题而非处理提案
      </div>
    </div>
  );
}
