/**
 * AlignmentCard Component
 *
 * D21 T10: 对齐推测卡 — in-message-flow card letting the user accept/reject
 * AI's inferred worldview alignments. Renders the action badge (closed set:
* 关联/去重/矛盾/更新), a human-readable summary, the user's quoted words,
 * optional amber stale warnings, and two adjudication buttons (采纳/不是这样).
 * The backend resolve endpoint is boolean two-value — no third button.
 */

import { useState } from 'react';
import type { AlignmentItem } from '../../types/a1';

/** Frozen action→label map (closed set — do not add or change). */
export const ACTION_LABELS: Readonly<
  Record<AlignmentItem['action'], string>
> = Object.freeze({
  link: '关联',
  dedupe: '去重',
  contradict: '矛盾',
  update: '更新',
});

export interface AlignmentCardProps {
  item: AlignmentItem;
  /**
   * Adjudication callback. May return a promise — the card disables both
   * buttons until it settles (double-click guard).
   */
  onResolve: (key: string, accept: boolean) => void | Promise<void>;
}

export function AlignmentCard({ item, onResolve }: AlignmentCardProps) {
  const [resolving, setResolving] = useState(false);

  const handleClick = async (accept: boolean) => {
    if (resolving) return;
    setResolving(true);
    try {
      await onResolve(item.key, accept);
    } finally {
      setResolving(false);
    }
  };

  return (
    <div
      data-testid="alignment-card"
      className="glass-panel mt-3 mb-3 p-4 border border-nebula-400/20"
    >
      {/* Action badge + header */}
      <div className="flex items-center gap-2 mb-2">
        <span
          data-testid="alignment-action-badge"
          className="text-xs font-medium px-2 py-0.5 rounded-full bg-nebula-400/15 text-nebula-400 border border-nebula-400/30"
        >
          {ACTION_LABELS[item.action]}
        </span>
        <span className="text-stardust-300 text-sm font-medium">
          我的一个推测
        </span>
      </div>

      {/* Human-readable summary (no internal keys / node ids) */}
      <div className="text-gray-300 text-sm leading-relaxed mb-2">
        {item.content}
      </div>

      {/* User's quoted words — styled citation, omitted when empty */}
      {item.quote && (
        <div
          data-testid="alignment-quote"
          className="border-l-2 border-nebula-400/40 pl-3 my-2"
        >
          <span className="text-void-400 text-lg leading-none">“</span>
          <span className="text-void-400 text-sm italic">{item.quote}</span>
          <span className="text-void-400 text-lg leading-none">”</span>
        </div>
      )}

      {/* Stale warnings — one amber line per entry */}
      {item.stale_warning.map((w, idx) => (
        <div
          key={idx}
          data-testid="alignment-stale-warning"
          className="text-cosmos-warning text-xs mt-1"
        >
          <span aria-hidden="true">⚠ </span>
          <span>{w}</span>
        </div>
      ))}

      {/* Adjudication — boolean two-value (accept / reject) */}
      <div className="flex gap-2 mt-3">
        <button
          type="button"
          onClick={() => handleClick(true)}
          disabled={resolving}
          className="flex-1 px-4 py-2 rounded text-sm font-medium bg-cosmos-success/20 text-cosmos-success border border-cosmos-success/50 hover:bg-cosmos-success/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          采纳
        </button>
        <button
          type="button"
          onClick={() => handleClick(false)}
          disabled={resolving}
          className="flex-1 px-4 py-2 rounded text-sm font-medium bg-space-700 text-gray-300 border border-white/10 hover:bg-space-600 hover:text-stardust-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          不是这样
        </button>
      </div>
    </div>
  );
}
