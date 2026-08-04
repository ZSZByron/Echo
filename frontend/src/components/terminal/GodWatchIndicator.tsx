import { useGameState } from '../../hooks/useGameState';
import { useEffect, useState } from 'react';

export function GodWatchIndicator() {
  const { godWatchLevel } = useGameState();
  const [visible, setVisible] = useState(false);
  const [glitchActive, setGlitchActive] = useState(false);

  useEffect(() => {
    if (godWatchLevel > 0) {
      setVisible(true);
      setGlitchActive(true);

      // Fade out after 5 seconds
      const fadeTimer = setTimeout(() => setVisible(false), 5000);

      // Stop glitch effect after 2 seconds
      const glitchTimer = setTimeout(() => setGlitchActive(false), 2000);

      return () => {
        clearTimeout(fadeTimer);
        clearTimeout(glitchTimer);
      };
    }
  }, [godWatchLevel]);

  if (!visible || godWatchLevel === 0) return null;

  const getIntensity = () => {
    if (godWatchLevel >= 3) return 'maximum';
    if (godWatchLevel >= 2) return 'high';
    return 'low';
  };

  const intensity = getIntensity();

  return (
    <>
      {/* Red glow overlay for terminal edges - stronger for maximum intensity */}
      <div
        className={`fixed inset-0 pointer-events-none z-50 transition-all duration-1000 ${
          intensity === 'maximum' ? 'bg-red-900/40' : intensity === 'high' ? 'bg-red-900/20' : 'bg-red-900/8'
        }`}
        style={{
          boxShadow: intensity === 'maximum' ? 'inset 0 0 150px rgba(255, 0, 64, 0.6)' :
                      intensity === 'high' ? 'inset 0 0 100px rgba(255, 0, 64, 0.4)' :
                      'inset 0 0 50px rgba(255, 0, 64, 0.2)',
        }}
      />

      {/* Noise effect overlay - more intense for maximum */}
      <div
        className={`fixed inset-0 pointer-events-none z-40 ${
          intensity === 'maximum' ? 'animate-pulse' : ''
        }`}
        style={{
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,0,64,0.03) 2px, rgba(255,0,64,0.03) 4px)',
          backgroundSize: '100% 4px',
          opacity: intensity === 'maximum' ? 0.3 : intensity === 'high' ? 0.15 : 0.05,
        }}
      />

      {/* Glitch effect for maximum intensity */}
      {glitchActive && intensity === 'maximum' && (
        <>
          <div
            className="fixed inset-0 pointer-events-none z-40"
            style={{
              background: 'repeating-linear-gradient(90deg, transparent, transparent 50px, rgba(255,0,64,0.1) 50px, rgba(255,0,64,0.1) 51px)',
              animation: 'glitch-slide 0.3s infinite',
            }}
          />
          <div
            className="fixed inset-0 pointer-events-none z-40"
            style={{
              background: 'repeating-linear-gradient(0deg, transparent, transparent 50px, rgba(255,0,64,0.1) 50px, rgba(255,0,64,0.1) 51px)',
              animation: 'glitch-slide 0.2s infinite reverse',
            }}
          />
        </>
      )}

      {/* Warning message with glitch animation */}
      <div className="fixed top-4 right-4 z-50">
        <div
          className={`text-neon-red text-glow-red font-mono text-lg ${
            intensity === 'maximum' && glitchActive ? 'animate-glitch' : 'animate-flicker'
          }`}
        >
          ⚠ 神王监控激活 - 等级 {godWatchLevel} ⚠
        </div>
      </div>

      {/* Red border pulse */}
      <div
        className={`fixed inset-0 pointer-events-none z-50 border-4 transition-all duration-300 ${
          intensity === 'maximum' ? 'border-red-600' : 'border-neon-red'
        }`}
        style={{
          opacity: intensity === 'maximum' ? 0.8 : intensity === 'high' ? 0.5 : 0.3,
          animation: intensity === 'maximum' ? 'border-pulse 1s infinite' : 'none',
        }}
      />
    </>
  );
}
