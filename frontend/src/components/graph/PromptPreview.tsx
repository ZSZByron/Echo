/**
 * PromptPreview component for displaying fused prompt content.
 *
 * Shows the 3-section prompt structure used for asset generation:
 * 1. 【生成主体】 - Node's own visual description
 * 2. 【关联衔接描述】 - Visual relationship descriptions from completed parent nodes
 * 3. 【背景光影】 - Background node description for context
 *
 * Supports collapsible sections for long text with cyberpunk styling.
 */

import { useState } from "react";

interface PromptPreviewProps {
  /** Main subject description (node's own description) */
  subject: string;
  /** Relationship descriptions from completed parent nodes */
  relations: string[];
  /** Background context description */
  background: string;
  /** Optional CSS class name for styling overrides */
  className?: string;
  /** Maximum length before collapsing (default: 200) */
  collapseThreshold?: number;
}

export function PromptPreview({
  subject,
  relations,
  background,
  className = "",
  collapseThreshold = 200,
}: PromptPreviewProps) {
  const [expanded, setExpanded] = useState(false);

  // Check if content is long enough to warrant collapsing
  const totalLength = (subject + relations.join("") + background).length;
  const shouldCollapse = totalLength > collapseThreshold;

  const fullContent = (
    <div className={`space-y-4 ${className}`}>
      {/* Section 1: 生成主体 */}
      {subject && (
        <div className="border-l-2 border-neon-green pl-4 py-2">
          <div className="text-neon-green font-mono text-xs font-bold uppercase tracking-wider mb-2 text-glow-green">
            【生成主体】
          </div>
          <div className="text-gray-300 font-mono text-sm leading-relaxed whitespace-pre-wrap">
            {subject}
          </div>
        </div>
      )}

      {/* Section 2: 关联衔接描述 */}
      {relations.length > 0 && (
        <div className="border-l-2 border-neon-cyan pl-4 py-2">
          <div className="text-neon-cyan font-mono text-xs font-bold uppercase tracking-wider mb-2 text-glow-cyan">
            【关联衔接描述】
          </div>
          <div className="text-gray-300 font-mono text-sm leading-relaxed space-y-2">
            {relations.map((relation, index) => (
              <div key={index} className="whitespace-pre-wrap">
                {relation}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 3: 背景光影 */}
      {background && (
        <div className="border-l-2 border-yellow-500 pl-4 py-2">
          <div className="text-yellow-500 font-mono text-xs font-bold uppercase tracking-wider mb-2">
            【背景光影】
          </div>
          <div className="text-gray-300 font-mono text-sm leading-relaxed whitespace-pre-wrap">
            {background}
          </div>
        </div>
      )}
    </div>
  );

  // If content is short or already expanded, show full content
  if (!shouldCollapse || expanded) {
    return (
      <div className="relative">
        {fullContent}
        {shouldCollapse && (
          <button
            onClick={() => setExpanded(false)}
            className="mt-4 text-neon-cyan font-mono text-xs uppercase tracking-wider hover:text-white transition-colors"
          >
            ▲ Collapse
          </button>
        )}
      </div>
    );
  }

  // Show collapsed preview
  return (
    <div className={`relative ${className}`}>
      {/* Preview indicator */}
      <div className="bg-black/50 border border-neon-cyan border-opacity-30 rounded-sm p-4 backdrop-blur-sm">
        <div className="text-gray-400 font-mono text-sm mb-3">
          <span className="text-neon-cyan">▸</span> Fused prompt structure
          ({[subject, relations.length > 0, background].filter(Boolean).length}{" "}
          sections)
        </div>

        {/* Section indicators */}
        <div className="space-y-1">
          {subject && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-neon-green" />
              <span className="text-gray-400 font-mono text-xs">
                Subject: {subject.slice(0, 40)}
                {subject.length > 40 ? "..." : ""}
              </span>
            </div>
          )}
          {relations.length > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-neon-cyan" />
              <span className="text-gray-400 font-mono text-xs">
                Relations: {relations.length} connection
                {relations.length > 1 ? "s" : ""}
              </span>
            </div>
          )}
          {background && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-yellow-500" />
              <span className="text-gray-400 font-mono text-xs">
                Background: {background.slice(0, 40)}
                {background.length > 40 ? "..." : ""}
              </span>
            </div>
          )}
        </div>

        {/* Expand button */}
        <button
          onClick={() => setExpanded(true)}
          className="mt-3 text-neon-cyan font-mono text-xs uppercase tracking-wider hover:text-white transition-colors"
        >
          ▼ Expand full prompt
        </button>
      </div>
    </div>
  );
}
