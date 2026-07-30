/**
 * WaveDivider component for visually separating generation waves.
 *
 * Displays "Wave N" labels to clearly distinguish different waves
 * in the asset generation timeline. Uses cyberpunk styling with
 * neon colors and scanline effects.
 *
 * Waves represent groups of nodes that can be generated concurrently
 * in the serial generation schedule (nodes with no dependencies on each other).
 */

interface WaveDividerProps {
  /** Wave number (1-indexed) */
  waveNumber: number;
  /** Optional CSS class name for styling overrides */
  className?: string;
  /** Optional label override (defaults to "Wave N") */
  label?: string;
}

export function WaveDivider({
  waveNumber,
  className = "",
  label,
}: WaveDividerProps) {
  const displayLabel = label || `Wave ${waveNumber}`;

  return (
    <div
      className={`relative flex items-center justify-center py-6 ${className}`}
    >
      {/* Scanline effect overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/20 to-transparent pointer-events-none" />

      {/* Left line */}
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-neon-cyan to-transparent opacity-50" />

      {/* Wave badge */}
      <div className="mx-4 px-6 py-2 bg-black border border-neon-cyan border-opacity-40 rounded-sm">
        <span className="text-neon-cyan font-mono text-sm font-bold uppercase tracking-widest text-glow-cyan">
          {displayLabel}
        </span>
      </div>

      {/* Right line */}
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-neon-cyan to-transparent opacity-50" />

      {/* Corner accents */}
      <div className="absolute left-4 top-1/2 w-2 h-2 border-l border-t border-neon-cyan opacity-60 -translate-y-1/2" />
      <div className="absolute right-4 top-1/2 w-2 h-2 border-r border-b border-neon-cyan opacity-60 -translate-y-1/2" />
    </div>
  );
}
