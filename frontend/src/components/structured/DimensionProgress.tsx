/**
 * DimensionProgress Component
 *
 * 10-grid progress indicator showing completion status across multiple sections.
 * Starry theme with glowing completed cells.
 */

import "../theme.css";

export interface Section {
  id: string;
  label: string;
  done: boolean;
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
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  // Always normalize to exactly 10 cells for the visual grid
  const gridCells = Array.from({ length: 10 }, (_, i) => {
    // Map 10 cells to actual section count
    const sectionIndex = Math.floor((i / 10) * totalCount);
    const section = sections[sectionIndex];
    return {
      index: i,
      filled: section?.done || false,
      partial: !section?.done && sectionIndex < completedCount,
    };
  });

  return (
    <div className={`glass-panel p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-stardust-300 text-lg font-medium">
          Dimension Progress
        </h3>
        <div className="text-right">
          <div className="text-2xl font-bold text-stardust-400 glow-starlight">
            {completedCount}/{totalCount}
          </div>
          <div className="text-void-500 text-xs font-mono">
            {progress.toFixed(0)}% Complete
          </div>
        </div>
      </div>

      {/* 10-Grid Progress Display */}
      <div className="grid grid-cols-10 gap-2 mb-4">
        {gridCells.map((cell) => (
          <div
            key={cell.index}
            className={`aspect-square rounded-sm transition-all ${
              cell.filled
                ? "bg-stardust-400 shadow-glow-strong"
                : cell.partial
                ? "bg-stardust-400/30"
                : "bg-space-800 border border-white/5"
            }`}
            aria-label={
              cell.filled
                ? "Completed section"
                : cell.partial
                ? "Partial progress"
                : "Incomplete section"
            }
          />
        ))}
      </div>

      {/* Section Labels */}
      <div className="space-y-2 mt-4 pt-4 border-t border-white/5">
        {sections.map((section) => (
          <div
            key={section.id}
            className="flex items-center gap-3 text-sm"
          >
            <div
              className={`w-2 h-2 rounded-full ${
                section.done
                  ? "bg-cosmos-success glow-success"
                  : "bg-void-600"
              }`}
            />
            <span
              className={`${
                section.done ? "text-gray-200" : "text-void-500"
              }`}
            >
              {section.label}
            </span>
            {section.done && (
              <span className="text-cosmos-success text-xs">✓</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
