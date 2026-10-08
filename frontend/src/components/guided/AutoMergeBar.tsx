/**
 * AutoMergeBar Component (D23)
 *
 * Inline chat-flow disclosure for semantic auto-merges. When the backend
 * merges a user utterance into an existing field, each merge shows up here
 * as a one-line bar in the message flow (NOT a modal): what was merged,
 * where it went, and an undo button. Undo is idempotent — the bar is
 * removed on success (or on a restored:false reply, which means it was
 * already handled elsewhere).
 */

import { useState } from 'react';
import { mergeUndo } from '../../api/a1';
import type { AutoMergeDisclosure } from '../../types/a1';

export interface AutoMergeBarProps {
  /** Auto-merges from the latest chat response (`auto_merges`). */
  merges: AutoMergeDisclosure[];
  /** Session ID for the undo API call. */
  sessionId: string;
  /** Optional callback after a successful undo (parent may refetch file). */
  onUndone?: (token: string) => void;
}

/** First 20 chars of the merged fragment, for the one-line disclosure. */
function truncate(text: string, max = 20): string {
  const trimmed = text.trim();
  return trimmed.length > max ? `${trimmed.slice(0, max)}…` : trimmed;
}

export function AutoMergeBar({ merges, sessionId, onUndone }: AutoMergeBarProps) {
  // Locally hidden tokens — removed after a successful undo (optimistic UI).
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<string | null>(null);

  if (merges.length === 0) return null;

  const handleUndo = async (token: string) => {
    if (!sessionId || pending) return;
    setPending(token);
    try {
      await mergeUndo(sessionId, token);
      setHidden((prev) => new Set(prev).add(token));
      onUndone?.(token);
    } catch (err) {
      console.error('Failed to undo merge:', err);
    } finally {
      setPending(null);
    }
  };

  const visible = merges.filter((m) => !hidden.has(m.token));
  if (visible.length === 0) return null;

  return (
    <div className="space-y-2" data-testid="auto-merge-bar">
      {visible.map((merge) => (
        <div
          key={merge.token}
          data-testid={`auto-merge-item-${merge.token}`}
          className="max-w-2xl rounded-lg px-4 py-2 bg-slate-800/60 border border-nebula-400/20 flex items-center gap-2"
        >
          <span className="text-nebula-400 text-sm">✧</span>
          <span className="text-slate-300 text-sm flex-1">
            已把『{truncate(merge.new)}』并入【{merge.label}】——不对就说一声。
          </span>
          <button
            type="button"
            data-testid={`auto-merge-undo-${merge.token}`}
            onClick={() => handleUndo(merge.token)}
            disabled={pending !== null}
            className="text-void-400 hover:text-stardust-300 text-xs transition-colors disabled:opacity-50 flex-shrink-0"
          >
            撤销
          </button>
        </div>
      ))}
    </div>
  );
}
