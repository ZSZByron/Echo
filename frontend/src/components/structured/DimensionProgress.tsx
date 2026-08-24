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
  // Calculate overall progress including sub-items
  let totalSubItems = 0;
  let completedSubItems = 0;
  
  sections.forEach((section) => {
    if (section.subs && section.subs.length > 0) {
      totalSubItems += section.subs.length;
      completedSubItems += section.subs.filter(sub => sub.done).length;
    }
  });

  const completedCount = sections.filter((s) => s.done).length;
  const totalCount = sections.length;
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  // Each of the 10 cells directly corresponds to a module (section)
  // Index 0 = first module, Index 1 = second module, etc.
  const gridCells = sections.slice(0, 10).map((section, index) => {
    // Calculate sub-item progress for this section
    const sectionSubs = section.subs || [];
    const doneSubs = sectionSubs.filter(sub => sub.done).length;
    
    return {
      index,
      label: section.label,
      filled: section.done,
      doneFields: doneSubs,
      totalFields: sectionSubs.length,
    };
  });

  // Fill remaining cells if less than 10 modules
  while (gridCells.length < 10) {
    gridCells.push({
      index: gridCells.length,
      label: "",
      filled: false,
      doneFields: 0,
      totalFields: 0,
    });
  }

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

      {/* 10-Grid Progress Display - One cell per module */}
      <div className="grid grid-cols-10 gap-2 mb-4">
        {gridCells.map((cell) => (
          <div
            key={cell.index}
            className="group relative"
          >
            <div
              className={`aspect-square rounded-sm transition-all ${
                cell.filled
                  ? "bg-stardust-400 shadow-glow-strong cursor-pointer"
                  : "bg-space-800 border border-white/5 cursor-pointer"
              } hover:border-nebula-400/30`}
              aria-label={
                cell.filled
                  ? `${cell.label || `Module ${cell.index + 1}`} - Completed`
                  : `${cell.label || `Module ${cell.index + 1}`} - Incomplete`
              }
            />
            {/* Tooltip on hover */}
            {cell.label && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 
                bg-space-900 border border-white/10 rounded text-xs text-stardust-300 whitespace-nowrap
                opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                {cell.label}
                {cell.totalFields > 0 && (
                  <span className="text-void-400 ml-2">
                    ({cell.doneFields || 0}/{cell.totalFields})
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Section Labels with sub-item progress */}
      <div className="space-y-2 mt-4 pt-4 border-t border-white/5">
        {sections.map((section) => {
          const sectionSubs = section.subs || [];
          const doneSubs = sectionSubs.filter(sub => sub.done).length;
          
          return (
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
              <div className="flex-1">
                <span
                  className={`${
                    section.done ? "text-gray-200" : "text-void-500"
                  }`}
                >
                  {section.label}
                </span>
                {/* Show sub-item progress if available */}
                {sectionSubs.length > 0 && (
                  <span className="text-void-400 text-xs ml-2">
                    ({doneSubs}/{sectionSubs.length} sub-items)
                  </span>
                )}
              </div>
              {section.done && (
                <span className="text-cosmos-success text-xs">✓</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
