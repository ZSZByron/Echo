import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AssetPlaceholder } from '../../components/shared/AssetPlaceholder';
import {
  approveAsset,
  type Asset,
  type AssetStatus,
  type AssetType,
  bulkApprove,
  generateAll,
  generateAsset,
  getAssetStatus,
  listAssets,
  rejectAsset,
  updatePrompt,
} from '../../api/assets';

type FilterType = 'all' | AssetStatus;

const STATUS_COLORS: Record<AssetStatus, string> = {
  pending: 'bg-gray-500',
  generating: 'bg-neon-cyan animate-pulse',
  completed: 'bg-neon-cyan',
  approved: 'bg-neon-green',
  rejected: 'bg-neon-red',
  failed: 'bg-neon-red opacity-60',
};

const STATUS_TEXT_COLORS: Record<AssetStatus, string> = {
  pending: 'text-gray-500',
  generating: 'text-neon-cyan animate-pulse',
  completed: 'text-neon-cyan',
  approved: 'text-neon-green',
  rejected: 'text-neon-red',
  failed: 'text-neon-red opacity-60',
};

const STATUS_BORDER_COLORS: Record<AssetStatus, string> = {
  pending: 'border-gray-500',
  generating: 'border-neon-cyan',
  completed: 'border-neon-cyan',
  approved: 'border-neon-green',
  rejected: 'border-neon-red',
  failed: 'border-neon-red',
};

const FILTERS: { label: string; value: FilterType }[] = [
  { label: '全部', value: 'all' },
  { label: '等待中', value: 'pending' },
  { label: '生成中', value: 'generating' },
  { label: '已完成', value: 'completed' },
  { label: '已批准', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
  { label: '失败', value: 'failed' },
];

const TYPE_ICON: Record<AssetType, string> = {
  background: '▦',
  object: '◈',
};

/** Statuses for which GENERATE / REGENERATE is enabled. */
const GENERATABLE_STATUSES: ReadonlySet<AssetStatus> = new Set([
  'pending',
  'completed',
  'rejected',
  'failed',
]);

/** Interval (ms) for polling generating assets. */
const POLL_INTERVAL_MS = 3000;
const ASSETS_CHANGED_EVENT = 'echo-assets-changed';

/** Dispatch a window event so any open SceneView can refresh. */
function dispatchAssetsChanged(): void {
  window.dispatchEvent(new CustomEvent(ASSETS_CHANGED_EVENT));
}

export function AssetReview() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [activeLod, setActiveLod] = useState<'far' | 'mid' | 'near'>('near');

  // Editable prompt fields (local working copy until SAVE)
  const [promptDraft, setPromptDraft] = useState<string>('');
  const [negativeDraft, setNegativeDraft] = useState<string>('');
  const [promptDirty, setPromptDirty] = useState<boolean>(false);
  const [savingPrompt, setSavingPrompt] = useState<boolean>(false);

  // In-flight action tracking (per-asset id set)
  const [busyIds, setBusyIds] = useState<ReadonlySet<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const list = await listAssets();
      setAssets(list);
      setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '批准失败');
      } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Pre-select first asset once loaded (if none selected)
  useEffect(() => {
    if (selectedId === null && assets.length > 0) {
      setSelectedId(assets[0].id);
    }
  }, [assets, selectedId]);

  const filteredAssets = useMemo(
    () => (filter === 'all' ? assets : assets.filter((a) => a.status === filter)),
    [assets, filter],
  );

  const selectedAsset = useMemo(
    () => (selectedId ? assets.find((a) => a.id === selectedId) ?? null : null),
    [assets, selectedId],
  );

  // Sync editable prompt drafts whenever selection changes or asset updates
  useEffect(() => {
    if (selectedAsset) {
      // If asset has LOD views and active LOD is set, use LOD-specific prompt
      if (selectedAsset.views && selectedAsset.views[activeLod]) {
        const lodView = selectedAsset.views[activeLod] as Record<string, unknown>;
        const lodPrompt = (lodView.prompt as string | undefined) ?? selectedAsset.prompt;
        const lodNegativePrompt = (lodView.negative_prompt as string | undefined) ?? selectedAsset.negative_prompt;
        
        setPromptDraft(lodPrompt);
        setNegativeDraft(lodNegativePrompt);
      } else {
        // Use base asset prompt
        setPromptDraft(selectedAsset.prompt);
        setNegativeDraft(selectedAsset.negative_prompt);
      }
      setPromptDirty(false);
    }
  }, [selectedAsset?.id, selectedAsset?.prompt, selectedAsset?.negative_prompt, selectedAsset?.views, activeLod]);

  // Detect manual edits to drafts
  useEffect(() => {
    if (!selectedAsset) return;
    if (
      promptDraft !== selectedAsset.prompt ||
      negativeDraft !== selectedAsset.negative_prompt
    ) {
      setPromptDirty(true);
    } else {
      setPromptDirty(false);
    }
  }, [promptDraft, negativeDraft, selectedAsset]);

  // ── Polling: poll any asset in 'generating' status ─────────────────────
  const generatingIds = useMemo(
    () => assets.filter((a) => a.status === 'generating').map((a) => a.id),
    [assets],
  );

  const assetsRef = useRef<Asset[]>(assets);
  assetsRef.current = assets;

  useEffect(() => {
    if (generatingIds.length === 0) return;

    let cancelled = false;

    const pollOnce = async () => {
      const ids = assetsRef.current
        .filter((a) => a.status === 'generating')
        .map((a) => a.id);
      if (ids.length === 0) return;

      let needsRefresh = false;
      await Promise.all(
        ids.map(async (id) => {
          try {
            const status = await getAssetStatus(id);
            if (status.status !== 'generating') {
              needsRefresh = true;
            }
          } catch {
            // swallow — next tick will retry
          }
        }),
      );

      if (!cancelled && needsRefresh) {
        dispatchAssetsChanged();
        await refresh();
      }
    };

    const interval = setInterval(() => {
      void pollOnce();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [generatingIds, refresh]);

  // ── Action helpers ─────────────────────────────────────────────────────
  const markBusy = useCallback((id: string) => {
    setBusyIds((prev) => new Set(prev).add(id));
  }, []);

  const unmarkBusy = useCallback((id: string) => {
    setBusyIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const flashNotice = useCallback((msg: string) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(null), 3500);
  }, []);

  const handleGenerate = useCallback(
    async (id: string) => {
      markBusy(id);
      try {
        await generateAsset(id);
        flashNotice(`▶ 开始生成: ${id}`);
        dispatchAssetsChanged();
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : '生成失败');
      } finally {
        unmarkBusy(id);
      }
    },
    [markBusy, unmarkBusy, refresh, flashNotice],
  );

  const handleApprove = useCallback(
    async (id: string) => {
      markBusy(id);
      try {
        await approveAsset(id);
        flashNotice(`✓ 已批准: ${id}`);
        dispatchAssetsChanged();
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : '批准失败');
      } finally {
        unmarkBusy(id);
      }
    },
    [markBusy, unmarkBusy, refresh, flashNotice],
  );

  const handleReject = useCallback(
    async (id: string) => {
      markBusy(id);
      try {
        await rejectAsset(id);
        flashNotice(`✗ 已拒绝: ${id}`);
        dispatchAssetsChanged();
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : '生成失败');
      } finally {
        unmarkBusy(id);
      }
    },
    [markBusy, unmarkBusy, refresh, flashNotice],
  );

  const handleSavePrompt = useCallback(
    async (id: string) => {
      if (!selectedAsset) return;
      setSavingPrompt(true);
      try {
        await updatePrompt(id, promptDraft, negativeDraft);
        flashNotice(`▼ 提示词已保存: ${id}`);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : '批准失败');
      } finally {
        setSavingPrompt(false);
      }
    },
    [selectedAsset, promptDraft, negativeDraft, refresh, flashNotice],
  );

  const handleGenerateAll = useCallback(async () => {
    try {
      const result = await generateAll();
        flashNotice(`▶▶ 触发了 ${result.triggered} 个生成任务`);
      dispatchAssetsChanged();
      await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : '批量生成失败');
      }
  }, [refresh, flashNotice]);

  const handleBulkApprove = useCallback(async () => {
    try {
      const result = await bulkApprove();
        flashNotice(`✓✓ 批量批准了 ${result.approved} 个资产`);
      dispatchAssetsChanged();
      await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : '批量生成失败');
      }
  }, [refresh, flashNotice]);

  const isBusy = selectedId !== null && busyIds.has(selectedId);

  // ── Derived flags for the currently selected asset ────────────────────
  const canGenerate =
    selectedAsset !== null &&
    GENERATABLE_STATUSES.has(selectedAsset.status) &&
    !isBusy;
  const canApprove =
    selectedAsset !== null && selectedAsset.status === 'completed' && !isBusy;
  const canReject =
    selectedAsset !== null && selectedAsset.status === 'completed' && !isBusy;

  const hasGenerating = assets.some((a) => a.status === 'generating');

  return (
    <div className="h-screen w-screen bg-black text-neon-green font-mono overflow-hidden flex flex-col">
      {/* Top Bar */}
      <header className="flex justify-between items-center px-6 py-3 border-b-2 border-neon-green shrink-0">
        <div className="flex items-baseline gap-4">
          <h1 className="text-2xl text-neon-cyan text-glow-cyan tracking-widest">
            资产审核 // 回声
          </h1>
          {hasGenerating && (
            <span className="text-xs text-neon-cyan animate-pulse tracking-widest">
              ⟳ 轮询中…
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {notice && (
            <span className="text-xs text-neon-green/80 tracking-widest">
              {notice}
            </span>
          )}
          <a
            href="/"
            className="text-neon-green text-sm border border-neon-green px-3 py-1 hover:bg-neon-green hover:text-black transition-colors"
          >
            ← 返回游戏
          </a>
          <button
            type="button"
            onClick={() => void handleGenerateAll()}
            className="text-neon-red text-sm border border-neon-red px-3 py-1 hover:bg-neon-red hover:text-black transition-colors"
          >
            生成所有待处理
          </button>
          <button
            type="button"
            onClick={() => void handleBulkApprove()}
            className="text-neon-green text-sm border border-neon-green px-3 py-1 hover:bg-neon-green hover:text-black transition-colors"
          >
            批量批准
          </button>
        </div>
      </header>

      {error && (
        <div className="px-6 py-2 bg-neon-red/10 border-b border-neon-red text-neon-red text-xs tracking-widest flex justify-between items-center">
          <span>⚠ {error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-neon-red/70 hover:text-neon-red underline"
          >
            关闭
          </button>
        </div>
      )}

      {/* Three-column body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Column — Asset List */}
        <aside className="w-80 border-r-2 border-neon-green flex flex-col overflow-hidden">
          <div className="p-3 border-b border-neon-green">
            <div className="text-xs text-neon-green mb-2 opacity-70">FILTER</div>
            <div className="flex flex-wrap gap-1">
              {FILTERS.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => setFilter(f.value)}
                  className={`text-xs px-2 py-1 border transition-colors ${
                    filter === f.value
                      ? 'border-neon-cyan text-neon-cyan bg-neon-cyan/10'
                      : 'border-neon-green/50 text-neon-green/70 hover:border-neon-cyan hover:text-neon-cyan'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {loading && (
              <div className="text-neon-cyan text-xs p-4 text-center animate-pulse">
                加载资产中…
              </div>
            )}
            {!loading && filteredAssets.length === 0 && (
              <div className="text-neon-green/50 text-xs p-4 text-center">
                无符合筛选条件的资产
              </div>
            )}
            {filteredAssets.map((asset) => {
              const isSelected = asset.id === selectedId;
              return (
                <button
                  key={asset.id}
                  type="button"
                  onClick={() => setSelectedId(asset.id)}
                  title={
                    asset.status === 'failed' && asset.error_message
                      ? asset.error_message
                      : undefined
                  }
                  className={`w-full text-left p-2 border-2 bg-black flex items-center gap-3 transition-colors ${
                    isSelected
                      ? 'border-neon-cyan bg-neon-cyan/5'
                      : `border-neon-green/30 hover:border-neon-green ${STATUS_BORDER_COLORS[asset.status]}/0`
                  }`}
                >
                  <span
                    className={`w-2.5 h-2.5 rounded-full shrink-0 ${STATUS_COLORS[asset.status]}`}
                  />
                  <span className="text-neon-cyan text-base shrink-0" aria-hidden>
                    {TYPE_ICON[asset.type]}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-sm text-neon-green truncate">
                      {asset.name}
                    </span>
                    <span className="block text-xs opacity-60 uppercase">
                      {asset.type}
                    </span>
                  </span>
                  <span
                    className={`text-xs uppercase shrink-0 ${STATUS_TEXT_COLORS[asset.status]}`}
                  >
                    {asset.status}
                  </span>
                </button>
              );
            })}
          </div>
        </aside>

        {/* Center Column — Preview */}
        <section className="flex-1 flex items-center justify-center p-6 overflow-hidden">
          {selectedAsset ? (
            <div
              className={`relative w-full h-full border-2 border-dashed ${STATUS_BORDER_COLORS[selectedAsset.status]} flex flex-col items-center justify-center bg-black overflow-hidden`}
            >
              <div className="absolute top-3 left-3 text-xs text-neon-green/60 tracking-widest z-10">
                预览区域
              </div>
              <div className="absolute top-3 right-3 text-xs uppercase tracking-widest z-10">
                <span className="opacity-60">类型: </span>
                <span className="text-neon-cyan">{selectedAsset.type}</span>
              </div>

              {/* LOD Tabs - show only when asset has views */}
              {selectedAsset.views && (
                <div className="absolute top-12 left-3 right-3 z-10">
                  <div className="flex gap-1 mb-2 border-b border-gray-700">
                    <button
                      type="button"
                      onClick={() => setActiveLod('far')}
                      className={`px-3 py-1 text-xs font-mono transition-colors ${
                        activeLod === 'far'
                          ? 'text-neon-cyan border-b-2 border-neon-cyan'
                          : 'text-gray-500 hover:text-neon-cyan'
                      }`}
                    >
                      远 (Far)
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveLod('mid')}
                      className={`px-3 py-1 text-xs font-mono transition-colors ${
                        activeLod === 'mid'
                          ? 'text-neon-cyan border-b-2 border-neon-cyan'
                          : 'text-gray-500 hover:text-neon-cyan'
                      }`}
                    >
                      中 (Mid)
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveLod('near')}
                      className={`px-3 py-1 text-xs font-mono transition-colors ${
                        activeLod === 'near'
                          ? 'text-neon-cyan border-b-2 border-neon-cyan'
                          : 'text-gray-500 hover:text-neon-cyan'
                      }`}
                    >
                      近 (Near)
                    </button>
                  </div>
                </div>
              )}

              {(() => {
                // Determine which image to display based on LOD state
                let imageUrl: string | null | undefined = selectedAsset.url;
                let showImage = selectedAsset.url !== null &&
                  (selectedAsset.status === 'approved' || selectedAsset.status === 'completed');
                
                // If asset has LOD views and active LOD is set, try to get LOD-specific image
                if (selectedAsset.views && selectedAsset.views[activeLod]) {
                  const lodView = selectedAsset.views[activeLod] as Record<string, unknown>;
                  const lodFilePath = lodView.file_path as string | null | undefined;
                  
                  if (lodFilePath) {
                    // Convert file_path to URL like the backend does
                    imageUrl = `/assets/${lodFilePath.split('/').pop()}`;
                    showImage = true;
                  }
                }
                
                return showImage && imageUrl ? (
                  <img
                    src={imageUrl}
                    alt={`${selectedAsset.name} (${activeLod})`}
                    className="max-w-full max-h-full object-contain"
                    onError={(e) => {
                      // Hide broken image — placeholder fallback handled by conditional,
                      // but guard runtime 404s on stale paths.
                      (e.currentTarget as HTMLImageElement).style.display = 'none';
                    }}
                  />
                ) : (
                  <div className="relative w-full h-full flex items-center justify-center">
                    <AssetPlaceholder
                      mode={selectedAsset.type === 'background' ? 'background' : 'object'}
                      name={selectedAsset.name}
                      type={selectedAsset.type}
                      className="static max-w-md max-h-md"
                    />
                  </div>
                );
              })()}

              <div className="absolute bottom-3 left-3 text-xs text-neon-green/60 uppercase tracking-widest z-10">
                编号: {selectedAsset.id}
              </div>
              {selectedAsset.seed !== null && (
                <div className="absolute bottom-3 right-3 text-xs text-neon-cyan/70 uppercase tracking-widest z-10">
                  种子: {selectedAsset.seed}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center text-neon-green/50">
              <div className="text-6xl mb-4 opacity-30" aria-hidden>
                ◇
              </div>
              <div className="text-xl tracking-widest">选择资产</div>
            </div>
          )}
        </section>

        {/* Right Column — Properties */}
        <aside className="w-96 border-l-2 border-neon-green flex flex-col overflow-y-auto">
          {selectedAsset ? (
            <div className="p-4 space-y-5">
              <div>
                 <div className="text-xs text-neon-green/70 mb-1 tracking-widest">名称</div>
                 <div className="text-lg text-neon-green">{selectedAsset.name}</div>
               </div>

               <div>
                 <div className="text-xs text-neon-green/70 mb-1 tracking-widest">状态</div>
                <span
                  className={`inline-block text-sm uppercase tracking-widest px-3 py-1 border-2 ${STATUS_BORDER_COLORS[selectedAsset.status]} ${STATUS_TEXT_COLORS[selectedAsset.status]}`}
                >
                  ● {selectedAsset.status}
                </span>
              </div>

               <div>
                 <div className="text-xs text-neon-green/70 mb-1 tracking-widest">类型</div>
                 <div className="text-sm text-neon-cyan uppercase">{selectedAsset.type}</div>
               </div>

               {selectedAsset.status === 'failed' && selectedAsset.error_message && (
                 <div className="border-2 border-neon-red bg-neon-red/10 p-3">
                   <div className="text-xs text-neon-red tracking-widest mb-1">
                     ⚠ 错误
                   </div>
                  <div className="text-xs text-neon-red/90 break-words">
                    {selectedAsset.error_message}
                  </div>
                </div>
              )}

               {selectedAsset.reviewer_note && (
                 <div>
                   <div className="text-xs text-neon-green/70 mb-1 tracking-widest">
                     审核备注
                   </div>
                  <div className="text-xs text-neon-green/80 italic">
                    {selectedAsset.reviewer_note}
                  </div>
                </div>
              )}

               <div className="border-t border-neon-green/30 pt-4">
                 <div className="flex items-center justify-between mb-2">
                   <label
                     htmlFor="prompt"
                     className="block text-xs text-neon-green/70 tracking-widest"
                   >
                     提示词
                     {selectedAsset.views && (
                       <span className="ml-2 text-neon-cyan/80 text-xs uppercase">
                         ({activeLod})
                       </span>
                     )}
                   </label>
                  <button
                    type="button"
                    onClick={() => void handleSavePrompt(selectedAsset.id)}
                    disabled={!promptDirty || savingPrompt}
                    className={`text-xs px-2 py-0.5 border tracking-widest transition-colors ${
                      promptDirty && !savingPrompt
                        ? 'border-neon-cyan text-neon-cyan hover:bg-neon-cyan hover:text-black'
                        : 'border-neon-green/30 text-neon-green/40 cursor-not-allowed'
                    }`}
                  >
                    {savingPrompt ? '保存中…' : '保存'}
                  </button>
                </div>
                <textarea
                  id="prompt"
                  value={promptDraft}
                  onChange={(e) => setPromptDraft(e.target.value)}
                  rows={5}
                  className="w-full text-sm text-neon-green bg-black border border-neon-green/50 p-2 resize-none focus:outline-none focus:border-neon-cyan"
                />
              </div>

              <div>
                <label
                  htmlFor="negative-prompt"
                  className="block text-xs text-neon-green/70 mb-2 tracking-widest"
                >
                  负面提示词
                </label>
                <textarea
                  id="negative-prompt"
                  value={negativeDraft}
                  onChange={(e) => setNegativeDraft(e.target.value)}
                  rows={3}
                  className="w-full text-sm text-neon-red/90 bg-black border border-neon-red/40 p-2 resize-none focus:outline-none focus:border-neon-red"
                />
              </div>

              <div className="border-t border-neon-green/30 pt-4 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => void handleGenerate(selectedAsset.id)}
                  disabled={!canGenerate}
                  className={`text-sm border py-2 transition-colors ${
                    canGenerate
                      ? 'border-neon-cyan text-neon-cyan hover:bg-neon-cyan hover:text-black'
                      : 'border-neon-cyan/40 text-neon-cyan/40 cursor-not-allowed'
                  }`}
                >
                  生成
                </button>
                <button
                  type="button"
                  onClick={() => void handleApprove(selectedAsset.id)}
                  disabled={!canApprove}
                  className={`text-sm border py-2 transition-colors ${
                    canApprove
                      ? 'border-neon-green text-neon-green hover:bg-neon-green hover:text-black'
                      : 'border-neon-green/40 text-neon-green/40 cursor-not-allowed'
                  }`}
                >
                  批准
                </button>
                <button
                  type="button"
                  onClick={() => void handleReject(selectedAsset.id)}
                  disabled={!canReject}
                  className={`text-sm border py-2 transition-colors ${
                    canReject
                      ? 'border-neon-red text-neon-red hover:bg-neon-red hover:text-black'
                      : 'border-neon-red/40 text-neon-red/40 cursor-not-allowed'
                  }`}
                >
                  拒绝
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (
                      window.confirm(
                        `重新生成 "${selectedAsset.name}"？这将覆盖当前图像。`,
                      )
                    ) {
                      void handleGenerate(selectedAsset.id);
                    }
                  }}
                  disabled={!canGenerate}
                  className={`text-sm border py-2 transition-colors ${
                    canGenerate
                      ? 'border-neon-cyan text-neon-cyan hover:bg-neon-cyan hover:text-black'
                      : 'border-neon-cyan/40 text-neon-cyan/40 cursor-not-allowed'
                  }`}
                >
                  重新生成
                </button>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-6">
              <div className="text-neon-green/50 text-sm tracking-widest text-center">
                未选择资产
                <br />
                <span className="opacity-60">— 属性已禁用 —</span>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
