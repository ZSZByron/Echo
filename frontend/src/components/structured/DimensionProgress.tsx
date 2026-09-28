/**
 * DimensionProgress Component
 *
 * Count-based progress indicator: plain-language main line (聊聊你的世界 done/total)
 * plus one cell per section. Module-name labels are intentionally NOT rendered
 * (T5, D21-11) — data still flows in via props, only label text is dropped.
 */

import "../theme.css";
import { plainProgressLabel } from "../../labels/plainProgress";

export interface Section {
  id: string;
  label: string;
  done: boolean;
  done_fields?: number;
  total_fields?: number;
  subs?: Array<{
    id: string;
    label: string;
    done: boolean;
  }>;
}

export interface DimensionProgressProps {
  sections: Section[];
  className?: string;
}

export function DimensionProgress({
  sections,
  className = "",
}: DimensionProgressProps) {
  const completedCount = sections.filter((s) => s.done).length;
  const totalCount = sections.length;

  // One cell per section — total derived from sections.length, never hardcoded.
  const gridCells = sections.map((section, index) => ({
    index,
    filled: section.done,
  }));

  return (
    <div className={`glass-panel p-6 ${className}`}>
      {/* Plain-language count line */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-stardust-300 text-lg font-medium">
          {plainProgressLabel(completedCount, totalCount)}
        </h3>
        <div
          className="text-2xl font-bold text-stardust-400 glow-starlight"
          aria-label={plainProgressLabel(completedCount, totalCount)}
        >
          {completedCount}/{totalCount}
        </div>
      </div>

      {/* Progress cells — one per section, done-state styling only (no label text) */}
      <div
        className="grid gap-2 mb-4"
        style={{
          gridTemplateColumns: `repeat(${Math.max(totalCount, 1)}, minmax(0, 1fr))`,
        }}
      >
        {gridCells.map((cell) => (
          <div
            key={cell.index}
            data-progress-cell={cell.index}
            className={`aspect-square rounded-sm transition-all ${
              cell.filled
                ? "bg-stardust-400 shadow-glow-strong"
                : "bg-space-800 border border-white/5"
            } hover:border-nebula-400/30`}
            aria-label={
              cell.filled
                ? `第 ${cell.index + 1} 项已完成`
                : `第 ${cell.index + 1} 项未完成`
            }
          />
        ))}
      </div>
    </div>
  );
}
