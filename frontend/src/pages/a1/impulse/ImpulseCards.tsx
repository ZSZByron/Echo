/**
 * 冲动卡卡片屏（计划 e0-impulse-entry T5）
 *
 * 纯展示 + 交互组件：9 卡渲染、主+次多选状态机、skip 常驻（D2-③）、
 * 页脚埋点导出入口。seeds 由父级 props 传入（本组件不 fetch）。
 * 不感知各型路由差异——确认后一律经 onCardCommit 交由 wiring 层（T7）决定落点。
 *
 * 埋点：挂载时 impulse_card_shown（ref 守卫防 StrictMode 双挂载）、
 * 确认时 impulse_card_selected、跳过时 impulse_card_skipped。
 */

import { useEffect, useRef, useState } from 'react';
import {
  IMPULSE_CARDS,
  IMPULSE_SCREEN_INTRO,
  type ImpulseTypeId,
} from './impulseCards.config';
import { logImpulseEvent, exportImpulseTelemetry } from './telemetry';
import type { Seed } from './seedGrouping';

interface ImpulseCardsProps {
  seeds: Seed[];
  onCardCommit: (selection: {
    primary: ImpulseTypeId;
    secondary: ImpulseTypeId | null;
  }) => void;
  onSkip: () => void;
}

const CONFIRM_LABEL = '就这样，开始';
const SKIP_LABEL = '跳过，直接开始';
const EXPORT_LABEL = '导出使用数据';

export function ImpulseCards({ onCardCommit, onSkip }: ImpulseCardsProps) {
  const [primary, setPrimary] = useState<ImpulseTypeId | null>(null);
  const [secondary, setSecondary] = useState<ImpulseTypeId | null>(null);
  const shownLoggedRef = useRef(false);

  // 挂载曝光埋点——ref 守卫，React 18 StrictMode 双挂载下严格只发一次
  useEffect(() => {
    if (shownLoggedRef.current) return;
    shownLoggedRef.current = true;
    logImpulseEvent('impulse_card_shown');
  }, []);

  const handleCardClick = (id: ImpulseTypeId) => {
    // 点击已选中卡 = 取消该选中（主卡二重点击即取消，不升级为次选）
    if (primary === id) {
      setPrimary(null);
      // 主取消时次卡顺位补为主？不——规格无此语义，次选保持独立，仅清除
      return;
    }
    if (secondary === id) {
      setSecondary(null);
      return;
    }
    if (primary === null) {
      setPrimary(id);
      return;
    }
    setSecondary(id);
  };

  const handleConfirm = () => {
    if (primary === null) return;
    logImpulseEvent('impulse_card_selected', { primary, secondary });
    onCardCommit({ primary, secondary });
  };

  const handleSkip = () => {
    logImpulseEvent('impulse_card_skipped');
    onSkip();
  };

  const gridCards = IMPULSE_CARDS.filter((c) => c.id !== 'unsure');
  const fallbackCard = IMPULSE_CARDS[IMPULSE_CARDS.length - 1];

  const selectionClass = (id: ImpulseTypeId): string => {
    if (primary === id) return 'border-stardust-400 ring-1 ring-stardust-400/60';
    if (secondary === id) return 'border-nebula-400/70 border-dashed';
    return 'border-transparent';
  };

  return (
    <div className="min-h-screen starry-gradient p-8" data-testid="impulse-cards">
      <div className="max-w-6xl mx-auto">
        {/* 顶部引导语（E1 诚实框架） */}
        <div className="glass-panel p-8 mb-8">
          <h1 className="text-3xl font-bold text-stardust-300 mb-2 glow-starlight">
            你为什么想创造一个世界？
          </h1>
          <p className="text-void-400">{IMPULSE_SCREEN_INTRO}</p>
        </div>

        {/* 8 卡网格 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {gridCards.map((card) => (
            <div
              key={card.id}
              role="button"
              tabIndex={0}
              data-testid={`impulse-card-${card.id}`}
              data-selected={primary === card.id ? 'primary' : secondary === card.id ? 'secondary' : undefined}
              onClick={() => handleCardClick(card.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') handleCardClick(card.id);
              }}
              className={`glass-card p-6 cursor-pointer border-2 transition-all hover:border-stardust-400/40 ${selectionClass(card.id)}`}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-stardust-300 text-lg font-medium">{card.label}</h3>
                {primary === card.id && (
                  <span className="text-xs text-space-950 bg-stardust-400 rounded-full px-2 py-0.5">主</span>
                )}
                {secondary === card.id && (
                  <span className="text-xs text-space-950 bg-nebula-400 rounded-full px-2 py-0.5">次</span>
                )}
              </div>
              <p className="text-gray-300 text-sm leading-relaxed">{card.tagline}</p>
            </div>
          ))}
        </div>

        {/* unsure 殿后兜底行（视觉弱化） */}
        <div data-slot="fallback" className="max-w-md mx-auto mb-8">
          <div
            role="button"
            tabIndex={0}
            data-testid={`impulse-card-${fallbackCard.id}`}
            data-selected={primary === fallbackCard.id ? 'primary' : secondary === fallbackCard.id ? 'secondary' : undefined}
            onClick={() => handleCardClick(fallbackCard.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') handleCardClick(fallbackCard.id);
            }}
            className={`glass-card p-4 cursor-pointer border-2 opacity-70 hover:opacity-100 transition-all ${selectionClass(fallbackCard.id)}`}
          >
            <p className="text-void-400 text-sm text-center">
              {fallbackCard.label} —— {fallbackCard.tagline}
            </p>
          </div>
        </div>

        {/* 确认 + skip（skip 常驻，D2-③） */}
        <div className="glass-panel p-6 flex items-center justify-center gap-6 mb-6">
          <button
            type="button"
            data-testid="impulse-confirm"
            onClick={handleConfirm}
            disabled={primary === null}
            className="bg-stardust-400 text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-stardust-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {CONFIRM_LABEL}
          </button>
          <button
            type="button"
            data-testid="impulse-skip"
            onClick={handleSkip}
            className="text-void-400 hover:text-stardust-300 underline underline-offset-4 transition-colors"
          >
            {SKIP_LABEL}
          </button>
        </div>

        {/* 页脚埋点导出入口（测试员工具，视觉弱化） */}
        <footer className="text-center pb-4">
          <button
            type="button"
            data-testid="impulse-export"
            onClick={exportImpulseTelemetry}
            className="text-void-500 hover:text-void-400 text-xs opacity-60 hover:opacity-100 transition-opacity"
          >
            {EXPORT_LABEL}
          </button>
        </footer>
      </div>
    </div>
  );
}

export default ImpulseCards;
