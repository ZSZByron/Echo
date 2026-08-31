/**
 * TopNav Component
 *
 * Top navigation bar for switching between A1/A2/A3/Lobby sections.
 * Starry theme with glassmorphism design.
 */

import "../theme.css";

export type NavSection = "a1" | "a2" | "a3" | "lobby";

export interface TopNavProps {
  current: NavSection;
  onNavigate?: (section: NavSection) => void;
  className?: string;
}

const NAV_ITEMS = [
  { id: "lobby" as const, label: "Lobby", icon: "◈" },
  { id: "a1" as const, label: "世界观工坊", icon: "✦" },
  { id: "a2" as const, label: "分区工坊", icon: "◉" },
  { id: "a3" as const, label: "场景工坊", icon: "✶" },
] as const;

export function TopNav({
  current,
  onNavigate,
  className = "",
}: TopNavProps) {
  return (
    <nav className={`glass-panel border-b border-white/5 ${className}`}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <div className="flex items-center gap-3">
            <div className="text-stardust-400 text-2xl animate-twinkle">✦</div>
            <span className="text-stardust-300 text-lg font-medium glow-starlight">
              UGC Platform
            </span>
          </div>

          {/* Navigation Items */}
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                onClick={() => onNavigate?.(item.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  current === item.id
                    ? "bg-stardust-400 text-space-950 glow-starlight"
                    : "text-void-400 hover:text-stardust-300 hover:bg-white/5"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>

          {/* User Info/Actions */}
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-stardust-300 text-sm font-medium">Explorer</div>
              <div className="text-void-500 text-xs font-mono">Session Active</div>
            </div>
            <div className="w-8 h-8 rounded-full bg-nebula-500/20 border border-nebula-400/30 flex items-center justify-center">
              <span className="text-nebula-400 text-sm">E</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
