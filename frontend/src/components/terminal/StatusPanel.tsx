import { useGameState } from '../../hooks/useGameState';
import { useEffect, useState, useRef } from 'react';

export function StatusPanel() {
  const { playerState, godWatchLevel } = useGameState();
  const prevStatsRef = useRef({ energy: 0, health: 0, mental: 0 });
  const [flashStates, setFlashStates] = useState({ energy: false, health: false, mental: false });

  useEffect(() => {
    if (!playerState) return;

    const prev = prevStatsRef.current;

    // Check for decreases to trigger red flash
    const newFlashStates = {
      energy: playerState.energy < prev.energy,
      health: playerState.health < prev.health,
      mental: playerState.mental_stability < prev.mental,
    };

    setFlashStates(newFlashStates);
    prevStatsRef.current = {
      energy: playerState.energy,
      health: playerState.health,
      mental: playerState.mental_stability,
    };

    // Clear flash after animation
    const timer = setTimeout(() => {
      setFlashStates({ energy: false, health: false, mental: false });
    }, 1000);

    return () => clearTimeout(timer);
  }, [playerState]);

  if (!playerState) {
    return (
      <div className="h-full w-full p-4 overflow-y-auto">
        <div className="text-neon-cyan text-glow-cyan font-mono mb-4">状态：初始化中...</div>
      </div>
    );
  }

  const getBarColor = (current: number, max: number) => {
    const ratio = current / max;
    if (ratio > 0.6) return 'bg-neon-green';
    if (ratio > 0.3) return 'bg-yellow-400';
    return 'bg-neon-red';
  };

  const getBarWidth = (current: number, max: number) => {
    return `${Math.max(0, Math.min(100, (current / max) * 100))}%`;
  };

  const StatBar = ({
    label,
    current,
    max,
    isFlashing,
  }: {
    label: string;
    current: number;
    max: number;
    isFlashing: boolean;
  }) => (
    <div className="mb-4">
      <div className="flex justify-between mb-1">
        <span className="text-neon-green font-mono text-sm">{label}</span>
        <span className="text-neon-green font-mono text-sm">
          {Math.max(0, current)}/{max}
        </span>
      </div>
      <div className="w-full bg-gray-800 rounded h-4 overflow-hidden">
        <div
          className={`h-full ${getBarColor(current, max)} transition-all duration-500 ${isFlashing ? 'bg-neon-red animate-pulse' : ''}`}
          style={{ width: getBarWidth(current, max) }}
        />
      </div>
    </div>
  );

  return (
    <div className="h-full w-full p-4 overflow-y-auto">
      <h2 className="text-neon-cyan text-glow-cyan font-mono mb-4 text-xl">状态面板</h2>

      <StatBar
        label="能量"
        current={playerState.energy}
        max={playerState.max_energy}
        isFlashing={flashStates.energy}
      />

      <StatBar
        label="生命"
        current={playerState.health}
        max={playerState.max_health}
        isFlashing={flashStates.health}
      />

      <StatBar
        label="精神稳定"
        current={playerState.mental_stability}
        max={100}
        isFlashing={flashStates.mental}
      />

      <div className="mt-6 border-t border-neon-green pt-4">
        <div className="text-neon-green font-mono text-sm mb-2">
          位置：<span className="text-neon-cyan">{playerState.location}</span>
        </div>
        <div className="text-neon-green font-mono text-sm mb-2">
          回声模式：<span className={playerState.echo_mode_enabled ? 'text-neon-green' : 'text-neon-red'}>
            {playerState.echo_mode_enabled ? '已启用' : '已禁用'}
          </span>
        </div>
        <div className="text-neon-green font-mono text-sm">
          力量：{playerState.strength} | 智力：{playerState.intelligence}
        </div>
      </div>

      {playerState.inventory.length > 0 && (
        <div className="mt-4 border-t border-neon-green pt-4">
          <div className="text-neon-green font-mono text-sm mb-2">物品栏：</div>
          <ul className="text-neon-cyan font-mono text-xs list-disc list-inside">
            {playerState.inventory.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {playerState.status && playerState.status !== 'normal' && (
        <div className="mt-4 border-t border-neon-green pt-4">
          <div className="text-neon-green font-mono text-sm mb-2">当前效果：</div>
          <div className="text-warn-yellow font-mono text-xs">
            {playerState.status.toUpperCase()}
          </div>
        </div>
      )}

      {/* Tension Level */}
      <div className="mt-4 border-t border-neon-green pt-4">
        <div className="flex justify-between mb-1">
          <span className="text-neon-green font-mono text-sm">紧张度</span>
          <span className="text-neon-green font-mono text-sm">
            {godWatchLevel === 0 ? '平静' : godWatchLevel === 1 ? '警告' : godWatchLevel === 2 ? '警戒' : '危险'}
          </span>
        </div>
        <div className="w-full bg-gray-800 rounded h-2 overflow-hidden">
          <div
            className="h-full transition-all duration-500"
            style={{
              width: `${(godWatchLevel / 3) * 100}%`,
              background: 'linear-gradient(to right, #00ff00, #ff0000)',
            }}
          />
        </div>
      </div>

      {/* Atmosphere */}
      <div className="mt-4 border-t border-neon-green pt-4">
        <div className="text-neon-green font-mono text-sm mb-2">氛围</div>
        <div className="text-neon-cyan font-mono text-xs italic">
          忧郁、古老、赛博神秘、衰败的壮丽
        </div>
      </div>
    </div>
  );
}
