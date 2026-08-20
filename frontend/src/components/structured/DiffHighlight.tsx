/**
 * DiffHighlight Component
 *
 * Highlights differences between old and new text with cosmic theme styling.
 * Shows removed content in error red and added content in success green.
 */

import "../theme.css";

export interface DiffHighlightProps {
  oldText: string;
  newText: string;
  className?: string;
}

export function DiffHighlight({
  oldText,
  newText,
  className = "",
}: DiffHighlightProps) {
  // Simple diff algorithm: highlight removed characters in red, added in green
  const highlightDiff = (oldStr: string, newStr: string) => {
    const oldLines = oldStr.split("\n");
    const newLines = newStr.split("\n");
    const maxLines = Math.max(oldLines.length, newLines.length);

    const elements = [];

    for (let i = 0; i < maxLines; i++) {
      const oldLine = oldLines[i] || "";
      const newLine = newLines[i] || "";

      if (oldLine !== newLine) {
        // Lines are different - show both
        if (oldLine) {
          elements.push(
            <div
              key={`${i}-old`}
              className="text-cosmos-error text-sm font-mono bg-cosmos-error/10 px-2 py-1 rounded"
            >
              − {oldLine}
            </div>
          );
        }
        if (newLine) {
          elements.push(
            <div
              key={`${i}-new`}
              className="text-cosmos-success text-sm font-mono bg-cosmos-success/10 px-2 py-1 rounded"
            >
              + {newLine}
            </div>
          );
        }
      } else if (oldLine) {
        // Lines are the same
        elements.push(
          <div
            key={i}
            className="text-gray-400 text-sm font-mono px-2 py-1"
          >
            {oldLine}
          </div>
        );
      }
    }

    return elements;
  };

  return (
    <div className={`space-y-1 ${className}`}>
      {highlightDiff(oldText, newText)}
    </div>
  );
}
