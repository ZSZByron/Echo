/**
 * PosterBoard Component
 *
 * Full-screen atmospheric display with gradient overlay and floating panels.
 * Starry theme with glassmorphism design.
 */

import "../theme.css";

export interface Panel {
  id: string;
  title: string;
  content: string;
  position?: { x: number; y: number };
}

export interface PosterBoardProps {
  panels: Panel[];
  backgroundImage?: string;
  className?: string;
  onPanelClick?: (panelId: string) => void;
}

export function PosterBoard({
  panels,
  backgroundImage,
  className = "",
  onPanelClick,
}: PosterBoardProps) {
  return (
    <div
      className={`relative min-h-screen starry-gradient overflow-hidden ${className}`}
      style={
        backgroundImage
          ? {
              backgroundImage: `url(${backgroundImage})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
            }
          : {}
      }
    >
      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-space-950/80 via-space-900/60 to-space-950/90 backdrop-blur-[2px]" />

      {/* Ambient Stars */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-[10%] left-[20%] w-1 h-1 bg-stardust-400 rounded-full animate-twinkle" />
        <div className="absolute top-[15%] right-[30%] w-1.5 h-1.5 bg-stardust-300 rounded-full animate-twinkle delay-100" />
        <div className="absolute top-[25%] left-[40%] w-1 h-1 bg-nebula-400 rounded-full animate-twinkle delay-200" />
        <div className="absolute bottom-[30%] right-[20%] w-1.5 h-1.5 bg-stardust-400 rounded-full animate-twinkle delay-300" />
        <div className="absolute bottom-[20%] left-[30%] w-1 h-1 bg-nebula-300 rounded-full animate-twinkle delay-150" />
      </div>

      {/* Content Container */}
      <div className="relative z-10 min-h-screen p-8 flex items-center justify-center">
        <div className="max-w-7xl w-full">
          {/* Floating Panels Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {panels.map((panel, index) => (
              <div
                key={panel.id}
                onClick={() => onPanelClick?.(panel.id)}
                className="glass-panel p-6 animate-float-glow cursor-pointer hover:border-stardust-400/30 transition-all"
                style={{
                  animationDelay: `${index * 0.2}s`,
                  transform: `translateY(${Math.sin(index * 0.5) * 10}px)`,
                }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="text-stardust-400 text-lg">✦</div>
                  <h3 className="text-stardust-300 text-lg font-medium">
                    {panel.title}
                  </h3>
                </div>
                <p className="text-gray-200 text-sm leading-relaxed">
                  {panel.content}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Gradient Fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-space-950 to-transparent" />
    </div>
  );
}
