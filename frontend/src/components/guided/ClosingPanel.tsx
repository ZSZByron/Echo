/**
 * ClosingPanel Component (D21-08, T9)
 *
 * 收尾三连问面板 — appears in the A1Workspace fixed footer when the closing
 * flow triggers (triggered = closing_step > 0 && not settled, persisted
 * server-side so a refresh re-renders the panel directly).
 *
 * ⓪ Preview zone: read-only list of generatable outputs (human names, no
 *   download/export affordances — producing them happens after finalize).
 * ①-③ The three closing questions themselves are NOT hardcopied here —
 *   the backend interjects plain-language questions into the chat reply
 *   stream, and user answers may also flow through the normal chat input
 *   (closing_flow parses natural language). The panel only adds three
 *   explicit ACTION entries and coexists with chat input, no exclusivity.
 *
 * 「改天继续」 shows a static hint only — no new session, no new entry
 * point, no route change.
 */

import { useState } from 'react';
import type { ConsumerArtifact } from '../../types/a1';

/**
 * Human label for a consumer artifact id (plainQuestion-style pure fallback).
 * Backend CONSUMER_ARTIFACTS carry internal snake_case ids (world_bible …);
 * the panel must never show module identifiers, so known ids map to fixed
 * human names and unknown ids degrade to a generic phrase.
 */
export function consumerLabel(id: string): string {
  const KNOWN: Readonly<Record<string, string>> = Object.freeze({
    world_bible: '世界观圣经',
    character_codex: '角色图鉴',
    story_outline: '故事大纲',
    dice_projection: '跑团投影',
    character_projection: '角色投影',
  });
  return KNOWN[id] ?? '一份设定产出';
}

export interface ClosingPanelProps {
  /** Closing flow active (closing-state triggered OR chat closing signal). */
  triggered: boolean;
  /** Generatable outputs from closing-state preview.consumers (read-only). */
  consumers: ConsumerArtifact[];
  /** 「生成文档」→ parent injects its existing finalize flow. */
  onFinalize: () => void;
  /** 「继续访谈录入设定」→ parent closes the panel, chat continues. */
  onContinue: () => void;
  /**
   * a1-oq-phase T4: 收尾变体（additive，缺省 "first" 字节不变）。
   * - "first"：首次收尾（预设问完）——既有文案。
   * - "refinalize"：二次收尾（开放问题清结）——产物语义 = 重定稿 + 文档再生成。
   *   三问文案本体仍由后端 chat reply 流式下发，本组件只换标题/动作措辞。
   */
  variant?: 'first' | 'refinalize';
}

const PANEL_COPY = {
  first: {
    title: '快到收尾的时候了',
    finalizeAction: '生成文档',
  },
  refinalize: {
    title: '开放问题答完了——重新定稿你的文档',
    finalizeAction: '重新定稿并更新文档',
  },
} as const;

export function ClosingPanel({
  triggered,
  consumers,
  onFinalize,
  onContinue,
  variant = 'first',
}: ClosingPanelProps) {
  // 「改天继续」is purely local: static hint, no API calls, no navigation.
  const [laterHint, setLaterHint] = useState(false);
  const copy = PANEL_COPY[variant];

  if (!triggered) return null;

  return (
    <div
      data-testid="closing-panel"
      data-variant={variant}
      className="glass-panel p-5 border border-nebula-400/25"
    >
      <h3 className="text-stardust-300 text-lg font-medium mb-3 flex items-center gap-2">
        <span>✦</span>
        {copy.title}
      </h3>

      {/* ⓪ Preview: read-only generatable outputs (human names, no downloads) */}
      {consumers.length > 0 && (
        <div className="mb-4">
          <p className="text-void-400 text-xs mb-2">定稿后可以生成：</p>
          <ul className="space-y-1">
            {consumers.map((c) => (
              <li
                key={c.id}
                data-testid="closing-preview-item"
                className="text-gray-300 text-sm flex items-center gap-2"
              >
                <span className="text-nebula-400">·</span>
                {consumerLabel(c.id)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ①-③ Three explicit action entries (questions stream via chat reply) */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          data-testid="closing-action-finalize"
          onClick={onFinalize}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-stardust-400 text-space-950 hover:bg-stardust-300 glow-starlight transition-all"
        >
          {copy.finalizeAction}
        </button>
        <button
          type="button"
          data-testid="closing-action-continue"
          onClick={onContinue}
          className="px-4 py-2 rounded-lg text-sm border border-nebula-400/30 text-void-400 hover:text-stardust-300 hover:border-nebula-400/60 transition-colors"
        >
          继续访谈录入设定
        </button>
        <button
          type="button"
          data-testid="closing-action-later"
          onClick={() => setLaterHint(true)}
          className="px-4 py-2 rounded-lg text-sm border border-white/10 text-void-400 hover:text-gray-300 transition-colors"
        >
          改天继续
        </button>
      </div>

      {laterHint && (
        <p
          data-testid="closing-later-hint"
          className="text-void-400 text-xs mt-3"
        >
          好的，进度都保存在这个会话里，随时回来
        </p>
      )}
    </div>
  );
}
