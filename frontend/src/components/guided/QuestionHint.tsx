/**
 * QuestionHint Component
 *
 * Displays a question with an optional collapsible hint for guided exploration.
 * Starry theme with glassmorphism design.
 */

import { useState } from "react";
import "../theme.css";

export interface QuestionHintProps {
  question: string;
  hint?: string;
  className?: string;
}

export function QuestionHint({ question, hint, className = "" }: QuestionHintProps) {
  const [showHint, setShowHint] = useState(false);

  return (
    <div className={`glass-panel p-6 ${className}`}>
      {/* Question */}
      <div className="flex items-start gap-3">
        <div className="text-stardust-400 text-2xl animate-twinkle">✦</div>
        <div className="flex-1">
          <h3 className="text-gray-100 text-lg font-medium leading-relaxed">
            {question}
          </h3>
        </div>
      </div>

      {/* Hint Toggle */}
      {hint && (
        <div className="mt-4 pt-4 border-t border-white/5">
          <button
            onClick={() => setShowHint(!showHint)}
            className="flex items-center gap-2 text-stardust-300 hover:text-stardust-200 transition-colors text-sm font-medium"
          >
            <span className={showHint ? "rotate-180" : ""}>▼</span>
            {showHint ? "Hide hint" : "Show hint"}
          </button>

          {showHint && (
            <div className="mt-3 p-4 bg-space-800/50 border border-nebula-400/20 rounded-lg">
              <div className="flex items-start gap-2">
                <div className="text-nebula-400 text-sm">💡</div>
                <p className="text-gray-300 text-sm leading-relaxed">
                  {hint}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
