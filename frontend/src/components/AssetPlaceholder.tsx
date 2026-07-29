/**
 * AssetPlaceholder — graceful fallback for missing scene assets.
 *
 * Two modes:
 *  - 'background': full-size gradient + CRT scanlines + "SCENE ASSET PENDING..." text
 *  - 'object':     neon-bordered box showing object name and type label
 *
 * Used by SceneView/SceneObject when an asset is null or img onError fires.
 */

export interface AssetPlaceholderProps {
  mode: 'background' | 'object';
  /** Object name (object mode only). */
  name?: string;
  /** Object type label (object mode only). */
  type?: string;
  /** Additional Tailwind classes merged onto the root element. */
  className?: string;
}

/** CRT scanline overlay matching the global body::after aesthetic. */
const scanlineStyle: React.CSSProperties = {
  backgroundImage:
    'repeating-linear-gradient(0deg, rgba(0,255,65,0.03), rgba(0,255,65,0.03) 1px, transparent 1px, transparent 2px)',
};

export function AssetPlaceholder({
  mode,
  name,
  type,
  className = '',
}: AssetPlaceholderProps) {
  /* ── Background mode ───────────────────────────────────────── */
  if (mode === 'background') {
    return (
      <div
        className={`absolute inset-0 bg-gradient-to-b from-gray-900 to-black overflow-hidden ${className}`}
        aria-label="Scene asset pending"
      >
        {/* CRT scanline overlay */}
        <div className="absolute inset-0 pointer-events-none" style={scanlineStyle} />

        {/* Centered pending text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-neon-cyan font-mono text-sm tracking-widest animate-pulse">
            场景资产等待中...
          </span>
        </div>
      </div>
    );
  }

  /* ── Object mode ──────────────────────────────────────────── */
  return (
    <div
      className={`relative flex flex-col items-center justify-center min-w-20 min-h-20 border-2 border-neon-green bg-black/40 shadow-[inset_0_0_10px_rgba(0,255,65,0.2)] ${className}`}
      aria-label={name ? `资产等待中: ${name}` : '资产等待中'}
    >
      {/* CRT scanline overlay */}
      <div className="absolute inset-0 pointer-events-none" style={scanlineStyle} />

      {name !== undefined && (
        <span className="relative text-neon-green text-xs font-mono truncate max-w-full px-1">
          {name}
        </span>
      )}
      {type !== undefined && (
        <span className="relative text-neon-cyan text-[10px] uppercase font-mono tracking-wider px-1">
          {type}
        </span>
      )}
    </div>
  );
}
