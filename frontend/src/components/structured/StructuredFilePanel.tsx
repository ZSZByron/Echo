/**
 * StructuredFilePanel Component
 *
 * Displays structured file information with diff highlighting for field changes.
 * Starry theme with glassmorphism design.
 */

import "../theme.css";
import { DiffHighlight } from "./DiffHighlight";

export interface DiffChange {
  field: string;
  old: string;
  new: string;
}

export interface StructuredFile {
  id: string;
  name: string;
  path: string;
  type: string;
  sections?: Array<{
    id: string;
    label: string;
    content: string;
    done: boolean;
  }>;
  status?: "draft" | "finalized";
  size?: string;
  modified?: string;
}

export interface StructuredFilePanelProps {
  file: StructuredFile;
  diff?: DiffChange[];
  className?: string;
}

export function StructuredFilePanel({
  file,
  diff,
  className = "",
}: StructuredFilePanelProps) {
  return (
    <div className={`glass-panel ${className}`}>
      {/* File Header */}
      <div className="flex items-start gap-4 p-6 border-b border-white/5">
        <div className="text-nebula-400 text-3xl animate-twinkle">◉</div>
        <div className="flex-1">
          <h3 className="text-stardust-300 text-xl font-medium mb-1">
            {file.name}
          </h3>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-void-400 text-sm font-mono">
            <span className="text-nebula-400">{file.type}</span>
            <span>{file.path}</span>
            {file.size && <span>{file.size}</span>}
            {file.modified && <span>Modified: {file.modified}</span>}
          </div>
        </div>
        {file.status && (
          <span
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              file.status === "finalized"
                ? "bg-cosmos-success/20 text-cosmos-success border border-cosmos-success/30"
                : "bg-cosmos-warning/20 text-cosmos-warning border border-cosmos-warning/30"
            }`}
          >
            {file.status}
          </span>
        )}
      </div>

      {/* Diff Changes */}
      {diff && diff.length > 0 && (
        <div className="p-6 space-y-3">
          <div className="text-stardust-400 text-sm font-medium uppercase tracking-wider mb-3">
            Changes
          </div>
          {diff.map((change, index) => (
            <div
              key={index}
              className="bg-space-800/40 border border-white/5 rounded-lg p-4 hover:border-nebula-400/20 transition-all"
            >
              <div className="text-stardust-300 text-sm font-medium mb-2">
                {change.field}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-void-500 text-xs font-mono mb-1">
                    BEFORE
                  </div>
                  <DiffHighlight oldText={change.old} newText={change.new} />
                </div>
                <div>
                  <div className="text-cosmos-success text-xs font-mono mb-1">
                    AFTER
                  </div>
                  <div className="text-gray-200 text-sm font-mono">
                    {change.new}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sections */}
      {file.sections && file.sections.length > 0 && (
        <div className="p-6 pt-0 space-y-4">
          {file.sections.map((section) => (
            <div
              key={section.id}
              className={`glass-card p-4 ${
                section.done
                  ? "border-cosmos-success/30"
                  : "border-white/5"
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <h4 className="text-gray-200 font-medium">{section.label}</h4>
                {section.done && (
                  <span className="text-cosmos-success text-sm">✓</span>
                )}
              </div>
              <p className="text-gray-300 text-sm leading-relaxed">
                {section.content || (
                  <span className="text-void-500 italic">Not yet filled</span>
                )}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
