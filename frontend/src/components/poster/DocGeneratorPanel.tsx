/**
 * DocGeneratorPanel Component
 *
 * 「生成文档」 panel for the IP poster page: 6 artifact buttons + a modal
 * viewer for generated products (markdown docs / structured templates).
 *
 * Honest error handling: 409 pending_finalize / missing_dice_template are
 * surfaced verbatim in the modal, never swallowed.
 *
 * TC hard dependency: a 409 {detail: "missing_dice_template"} triggers one
 * automatic dice-template generation then a single retry.
 */

import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import {
  generateDoc,
  fetchDocMarkdown,
  generateWorldBible,
  fetchWorldBibleMarkdown,
  generateCharacterCodex,
  fetchCharacterCodexMarkdown,
  generateStoryOutline,
  fetchStoryOutlineMarkdown,
  generateDiceTemplate,
  generateCharacterTemplate,
} from '../../api/a1';
import type {
  DocArtifactResponse,
  TemplateArtifactResponse,
  WarningLedgerEntry,
} from '../../types/a1';
import '../theme.css';

// ---------------------------------------------------------------------------
// Button registry — endpoint contract per artifact (backend a1_routes.py)
// ---------------------------------------------------------------------------

type ArtifactKind = 'markdown' | 'template';

interface ArtifactButton {
  key: string;
  label: string;
  stage: string;
  kind: ArtifactKind;
  filename: string;
}

const ARTIFACTS: ArtifactButton[] = [
  { key: 'doc', label: '主模组', stage: 'M', kind: 'markdown', filename: 'main-module' },
  { key: 'world-bible', label: '世界圣经', stage: 'B', kind: 'markdown', filename: 'world-bible' },
  { key: 'character-codex', label: '人物志', stage: 'C', kind: 'markdown', filename: 'character-codex' },
  { key: 'story-outline', label: '故事大纲', stage: 'O', kind: 'markdown', filename: 'story-outline' },
  { key: 'dice-template', label: '骰子模板', stage: 'TD', kind: 'template', filename: 'dice-template' },
  { key: 'character-template', label: '角色模板', stage: 'TC', kind: 'template', filename: 'character-template' },
];

// ---------------------------------------------------------------------------
// Viewer state
// ---------------------------------------------------------------------------

type ViewerState =
  | { status: 'loading'; title: string }
  | { status: 'error'; title: string; message: string }
  | { status: 'markdown'; title: string; code: string; content: string }
  | {
      status: 'template';
      title: string;
      code: string;
      template: Record<string, unknown>;
      warnings: WarningLedgerEntry[];
    };

/** Extract `detail` string from an ApiError body ({detail: "..." } contract). */
function detailOf(body: unknown): string | null {
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    const d = (body as { detail?: unknown }).detail;
    if (typeof d === 'string') return d;
  }
  return null;
}

/** Human-readable error message — honest, contract-aware, never silent. */
function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = detailOf(err.body);
    if (err.status === 409 && detail === 'pending_finalize') {
      return '尚未定稿（pending_finalize）——请先回到世界观工坊完成定稿，再生成文档。';
    }
    if (detail) {
      return `${fallback}：${detail} (HTTP ${err.status})`;
    }
    return `${fallback} (HTTP ${err.status})`;
  }
  return '网络错误，请检查后端服务是否可用。';
}

// ---------------------------------------------------------------------------
// Lightweight markdown renderer (no external dep — styled line blocks)
// ---------------------------------------------------------------------------

function MarkdownView({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <div className="space-y-2 text-gray-200 text-sm leading-relaxed">
      {lines.map((line, i) => {
        if (line.startsWith('# ')) {
          return (
            <h1 key={i} className="text-stardust-300 text-xl font-medium mt-4 mb-2 glow-starlight">
              {line.slice(2)}
            </h1>
          );
        }
        if (line.startsWith('## ')) {
          return (
            <h2 key={i} className="text-nebula-300 text-lg font-medium mt-3 mb-1">
              {line.slice(3)}
            </h2>
          );
        }
        if (line.startsWith('### ')) {
          return (
            <h3 key={i} className="text-stardust-400 text-base font-medium mt-2">
              {line.slice(4)}
            </h3>
          );
        }
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={i} className="flex gap-2 pl-2">
              <span className="text-stardust-400 shrink-0">✦</span>
              <span>{line.slice(2)}</span>
            </div>
          );
        }
        if (/^\d+\.\s/.test(line)) {
          return (
            <div key={i} className="flex gap-2 pl-2">
              <span className="text-nebula-400 shrink-0 font-mono text-xs pt-0.5">
                {line.match(/^\d+/)?.[0]}
              </span>
              <span>{line.replace(/^\d+\.\s/, '')}</span>
            </div>
          );
        }
        if (line.trim() === '---' || line.trim() === '***') {
          return <hr key={i} className="border-white/10 my-3" />;
        }
        if (line.trim() === '') {
          return <div key={i} className="h-1" />;
        }
        return <p key={i}>{line}</p>;
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Structured template renderer — key/value cards, never raw JSON dump
// ---------------------------------------------------------------------------

function TemplateNode({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-void-500">—</span>;
  }
  if (typeof value !== 'object') {
    return <span className="text-gray-100">{String(value)}</span>;
  }
  if (Array.isArray(value)) {
    return (
      <div className="space-y-1">
        {value.map((item, i) => (
          <div key={i} className="flex gap-2 pl-2">
            <span className="text-stardust-400 shrink-0 text-xs pt-0.5">▸</span>
            {typeof item === 'object' && item !== null ? (
              <div className="flex-1 glass-panel p-2 bg-white/5 border-white/5">
                <TemplateNode value={item} />
              </div>
            ) : (
              <span className="text-gray-200 text-sm">{String(item)}</span>
            )}
          </div>
        ))}
      </div>
    );
  }
  const entries = Object.entries(value as Record<string, unknown>);
  return (
    <div className="space-y-1.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-3 items-start">
          <span className="text-nebula-300 text-xs font-medium shrink-0 pt-1 min-w-20">
            {k}
          </span>
          {typeof v === 'object' && v !== null ? (
            <div className="flex-1 glass-panel p-3 bg-white/5 border-white/5">
              <TemplateNode value={v} />
            </div>
          ) : (
            <span className="text-gray-100 text-sm flex-1">
              {v === null || v === undefined ? '—' : String(v)}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DocGeneratorPanel({ fileId }: { fileId: string | null }) {
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [viewer, setViewer] = useState<ViewerState | null>(null);
  const [copied, setCopied] = useState<'idle' | 'ok' | 'failed'>('idle');

  // Close on ESC
  useEffect(() => {
    if (!viewer) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setViewer(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [viewer]);

  const closeViewer = useCallback(() => {
    setViewer(null);
    setCopied('idle');
  }, []);

  const generateMarkdown = useCallback(
    async (
      btn: ArtifactButton,
      generate: (id: string) => Promise<DocArtifactResponse>,
      fetchMd: (id: string) => Promise<string>
    ) => {
      if (!fileId) return;
      setViewer({ status: 'loading', title: btn.label });
      try {
        const res = await generate(fileId);
        const md = await fetchMd(fileId);
        setViewer({
          status: 'markdown',
          title: btn.label,
          code: res.doc_code ?? res.bible_code ?? res.codex_code ?? res.outline_code ?? '',
          content: md,
        });
      } catch (err) {
        setViewer({
          status: 'error',
          title: btn.label,
          message: errorMessage(err, `${btn.label}生成失败`),
        });
      }
    },
    [fileId]
  );

  const generateTemplate = useCallback(
    async (
      btn: ArtifactButton,
      generate: (id: string) => Promise<TemplateArtifactResponse>
    ) => {
      if (!fileId) return;
      setViewer({ status: 'loading', title: btn.label });
      try {
        const res = await generate(fileId);
        setViewer({
          status: 'template',
          title: btn.label,
          code: res.graph_code,
          template: res.template,
          warnings: res.warnings ?? [],
        });
      } catch (err) {
        setViewer({
          status: 'error',
          title: btn.label,
          message: errorMessage(err, `${btn.label}生成失败`),
        });
      }
    },
    [fileId]
  );

  // TC hard dependency: 409 missing_dice_template → auto-generate dice
  // template once, then retry character-template exactly once.
  const generateCharacter = useCallback(async () => {
    const btn = ARTIFACTS.find((a) => a.key === 'character-template');
    if (!btn || !fileId) return;
    setViewer({ status: 'loading', title: btn.label });
    try {
      let res: TemplateArtifactResponse;
      try {
        res = await generateCharacterTemplate(fileId);
      } catch (err) {
        if (
          err instanceof ApiError &&
          err.status === 409 &&
          detailOf(err.body) === 'missing_dice_template'
        ) {
          await generateDiceTemplate(fileId);
          res = await generateCharacterTemplate(fileId);
        } else {
          throw err;
        }
      }
      setViewer({
        status: 'template',
        title: btn.label,
        code: res.graph_code,
        template: res.template,
        warnings: res.warnings ?? [],
      });
    } catch (err) {
      setViewer({
        status: 'error',
        title: btn.label,
        message: errorMessage(err, '角色模板生成失败：自动补齐骰子模板后重试仍失败'),
      });
    }
  }, [fileId]);

  const handleGenerate = useCallback(
    (btn: ArtifactButton) => {
      if (busyKey) return;
      setBusyKey(btn.key);
      setCopied('idle');
      const run = async () => {
        try {
          switch (btn.key) {
            case 'doc':
              await generateMarkdown(btn, generateDoc, fetchDocMarkdown);
              break;
            case 'world-bible':
              await generateMarkdown(btn, generateWorldBible, fetchWorldBibleMarkdown);
              break;
            case 'character-codex':
              await generateMarkdown(btn, generateCharacterCodex, fetchCharacterCodexMarkdown);
              break;
            case 'story-outline':
              await generateMarkdown(btn, generateStoryOutline, fetchStoryOutlineMarkdown);
              break;
            case 'dice-template':
              await generateTemplate(btn, generateDiceTemplate);
              break;
            case 'character-template':
              await generateCharacter();
              break;
          }
        } finally {
          setBusyKey(null);
        }
      };
      void run();
    },
    [busyKey, generateMarkdown, generateTemplate, generateCharacter]
  );

  const handleCopy = useCallback(async () => {
    if (!viewer || viewer.status === 'loading' || viewer.status === 'error') return;
    const text =
      viewer.status === 'markdown' ? viewer.content : JSON.stringify(viewer.template, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setCopied('ok');
    } catch {
      // Clipboard API unavailable/denied → manual-select fallback hint
      setCopied('failed');
    }
  }, [viewer]);

  const handleDownload = useCallback(() => {
    if (!viewer || viewer.status !== 'markdown' || !fileId) return;
    const blob = new Blob([viewer.content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const btn = ARTIFACTS.find((x) => x.label === viewer.title);
    a.href = url;
    a.download = `${btn?.filename ?? 'document'}-${fileId}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }, [viewer, fileId]);

  return (
    <div className="glass-panel p-5" data-testid="doc-generator-panel">
      <div className="flex items-center gap-2 mb-4">
        <div className="text-stardust-400 text-lg animate-twinkle">✦</div>
        <h2 className="text-stardust-300 text-base font-medium">生成文档</h2>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {ARTIFACTS.map((btn) => (
          <button
            key={btn.key}
            onClick={() => handleGenerate(btn)}
            disabled={busyKey !== null}
            aria-label={btn.label}
            className="group flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg border border-white/10 bg-white/5 hover:bg-stardust-400/10 hover:border-stardust-400/40 transition-all text-left disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="text-stardust-300 text-sm group-hover:text-stardust-200 transition-colors">
              {busyKey === btn.key ? (
                <span className="flex items-center gap-2">
                  <span className="w-3 h-3 border-2 border-stardust-400 border-t-transparent rounded-full animate-spin" />
                  生成中...
                </span>
              ) : (
                btn.label
              )}
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-void-800/60 text-void-400 border border-white/5">
              {btn.stage}
            </span>
          </button>
        ))}
      </div>

      {/* Modal Viewer */}
      {viewer && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-space-950/80 backdrop-blur-sm"
          data-testid="doc-viewer-backdrop"
          onClick={closeViewer}
        >
          <div
            role="dialog"
            aria-label={viewer.title}
            className="glass-panel w-full max-w-3xl max-h-[85vh] flex flex-col bg-space-900/95 border-stardust-400/20"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between gap-4 px-6 py-4 border-b border-white/10 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <div className="text-stardust-400 text-lg animate-twinkle shrink-0">✦</div>
                <h3 className="text-stardust-300 text-lg font-medium truncate">{viewer.title}</h3>
                {'code' in viewer && viewer.code && (
                  <span
                    data-testid="doc-graph-code"
                    className="text-[10px] font-mono px-2 py-0.5 rounded bg-stardust-400/10 text-stardust-300 border border-stardust-400/30 whitespace-nowrap"
                  >
                    {viewer.code}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {viewer.status === 'markdown' && (
                  <>
                    <button
                      onClick={handleCopy}
                      className="text-xs px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-stardust-400/10 hover:border-stardust-400/40 text-stardust-300 transition-all"
                    >
                      {copied === 'ok' ? '已复制 ✓' : copied === 'failed' ? '复制失败' : '复制'}
                    </button>
                    <button
                      onClick={handleDownload}
                      className="text-xs px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-stardust-400/10 hover:border-stardust-400/40 text-stardust-300 transition-all"
                    >
                      下载 .md
                    </button>
                  </>
                )}
                {viewer.status === 'template' && (
                  <button
                    onClick={handleCopy}
                    className="text-xs px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-stardust-400/10 hover:border-stardust-400/40 text-stardust-300 transition-all"
                  >
                    {copied === 'ok' ? '已复制 ✓' : copied === 'failed' ? '复制失败' : '复制 JSON'}
                  </button>
                )}
                <button
                  onClick={closeViewer}
                  aria-label="关闭"
                  className="w-8 h-8 rounded-lg border border-white/10 bg-white/5 hover:bg-cosmos-error/20 hover:border-cosmos-error/40 text-stardust-300 hover:text-cosmos-error transition-all flex items-center justify-center"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Copy fallback hint */}
            {copied === 'failed' && (
              <div className="px-6 py-2 text-xs text-cosmos-warning bg-cosmos-warning/10 shrink-0">
                剪贴板不可用——请在下方内容区手动选中文本复制。
              </div>
            )}

            {/* Body */}
            <div className="px-6 py-4 overflow-y-auto max-h-[70vh]">
              {viewer.status === 'loading' && (
                <div className="flex flex-col items-center justify-center py-16 gap-4">
                  <div className="w-12 h-12 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin" />
                  <p className="text-stardust-300 text-sm">生成中...（LLM 调用可能需要数秒）</p>
                </div>
              )}

              {viewer.status === 'error' && (
                <div className="p-4 rounded-lg bg-cosmos-error/10 border border-cosmos-error/30">
                  <p className="text-cosmos-error text-sm leading-relaxed">{viewer.message}</p>
                </div>
              )}

              {viewer.status === 'markdown' && <MarkdownView content={viewer.content} />}

              {viewer.status === 'template' && (
                <div className="space-y-4">
                  {viewer.warnings.length > 0 && (
                    <div className="p-3 rounded-lg bg-cosmos-warning/10 border border-cosmos-warning/30">
                      <p className="text-cosmos-warning text-xs font-medium mb-1">警告账本</p>
                      {viewer.warnings.map((w, i) => (
                        <p key={i} className="text-cosmos-warning/80 text-xs">
                          [{w.source}] {w.detail}
                          {w.count > 1 ? ` ×${w.count}` : ''}
                        </p>
                      ))}
                    </div>
                  )}
                  <TemplateNode value={viewer.template} />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
