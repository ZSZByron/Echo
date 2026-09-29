/**
 * ImpulseCompass Component (D21-12, T8)
 *
 * 罗盘独立组件（ux-flow §5.3）：一句话坐标 + 三值纠偏按钮（按钮不是滑块）。
 * 静默原则（D21⑩）：applied=false 阻尼时坐标不动、无错误弹窗；端点不可达时渲染壳、不崩溃。
 * safety_flag=true：三按钮禁用 + 灰显提示「当前以你的感受为准」（不出现安全术语）。
 *
 * 坐标文案 compassPhrase 抽到 labels/compassPhrase.ts（labels/ 先例：plainQuestion/plainProgress），
 * 此处 re-export 保持单点导入。
 */

import { useEffect, useState } from 'react';
import { nudgeCoords } from '../../api/a1';
import type { NudgeSignal, ImpulseCoords } from '../../types/a1';
import { compassPhrase } from '../../labels/compassPhrase';

export { compassPhrase } from '../../labels/compassPhrase';

export interface ImpulseCompassProps {
  /** 会话文件 ID（nudge 请求路径参数）。 */
  fileId: string;
  /** 父级持有的坐标看板数据（挂载 GET + chat 后刷新）。null = 降级壳。 */
  coords: ImpulseCoords | null;
}

const NUDGE_BUTTONS: ReadonlyArray<{ label: string; signal: NudgeSignal }> = [
  { label: '更像讲故事', signal: 'user_nudge_story' },
  { label: '差不多', signal: 'user_nudge_confirm' },
  { label: '更像建设定', signal: 'user_nudge_builder' },
];

export function ImpulseCompass({ fileId, coords }: ImpulseCompassProps) {
  // 显示值优先跟随父级刷新（挂载 GET / chat 后刷新），nudge applied 时以响应覆盖。
  const [axis, setAxis] = useState<number | null>(coords?.axis ?? null);

  useEffect(() => {
    setAxis(coords?.axis ?? null);
  }, [coords]);

  const handleNudge = async (signal: NudgeSignal) => {
    try {
      const res = await nudgeCoords(fileId, signal);
      // 诚实透传：applied=false（护栏阻尼）→ 坐标不动，不提示不报错。
      if (res.applied) {
        setAxis(res.axis);
      }
    } catch {
      // 静默降级：端点不可达 → 保持原显示，按钮不锁定（护栏在后端）。
    }
  };

  const safety = coords?.safety_flag ?? false;

  return (
    <div className="glass-panel p-5" data-testid="impulse-compass">
      <h3 className="text-stardust-300 text-lg font-medium mb-3 flex items-center gap-2">
        <span>✧</span>
        冲动罗盘
      </h3>
      <p className="text-gray-300 text-sm mb-4">
        目前感觉你更像：
        <span data-testid="compass-reading" className="text-stardust-300 font-medium">
          {axis === null ? '——' : compassPhrase(axis)}
        </span>
      </p>
      <div className="flex flex-wrap gap-2">
        {NUDGE_BUTTONS.map(({ label, signal }) => (
          <button
            key={signal}
            onClick={() => handleNudge(signal)}
            disabled={safety}
            data-testid={`compass-nudge-${signal}`}
            className={`border rounded-lg px-3 py-1.5 text-sm transition-colors ${
              safety
                ? 'border-white/5 text-void-500 cursor-not-allowed'
                : 'border-nebula-400/30 text-void-400 hover:text-stardust-300 hover:border-nebula-400/60'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {safety && (
        <p className="text-void-500 text-xs mt-3">当前以你的感受为准</p>
      )}
    </div>
  );
}
