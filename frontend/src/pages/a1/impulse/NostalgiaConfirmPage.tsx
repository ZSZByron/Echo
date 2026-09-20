/**
 * NostalgiaConfirmPage — 怀旧型上传预填确认页（E0 冲动承接入口）
 *
 * 纯展示组件：不发埋点、不调 API、无内部状态。
 * 诚实纪律（三铁律之诚实 + R1 精神）：
 * - prefillCount > 0 → 标题"它认出了你的世界"（spec §8.2 逐字）+ 计数副文案
 * - prefillCount === 0 → 降级标题"我们读完了你的文档"，绝不渲染"认出"类文案
 */
interface NostalgiaConfirmPageProps {
  prefillCount: number; // 有效预填字段数（非空非占位）
  seedName: string; // 上传文件名（与 handleUploadSuccess 伪 seedInfo.name 同源）
  onContinue: () => void; // 继续进入访谈
}

export function NostalgiaConfirmPage({ prefillCount, seedName, onContinue }: NostalgiaConfirmPageProps) {
  const hasPrefill = prefillCount > 0;

  return (
    <div data-testid="nostalgia-confirm" className="min-h-screen starry-gradient p-8">
      <div className="max-w-2xl mx-auto">
        <div className="glass-card p-10 text-center">
          {/* 星尘点缀，与卡片屏家族视觉一致 */}
          <div className="text-stardust-400 text-2xl mb-4">✦</div>

          {hasPrefill ? (
            <>
              <h1 className="text-3xl font-bold text-stardust-300 mb-3 glow-starlight">
                它认出了你的世界
              </h1>
              <p className="text-nebula-400 text-sm mb-2">来自《{seedName}》</p>
              <p className="text-void-400 mb-8 leading-relaxed">
                从你的文档里认出了 {prefillCount} 处设定，已为你预填——先确认，再继续。
              </p>
            </>
          ) : (
            <>
              <h1 className="text-3xl font-bold text-stardust-300 mb-3 glow-starlight">
                我们读完了你的文档
              </h1>
              <p className="text-nebula-400 text-sm mb-2">来自《{seedName}》</p>
              <p className="text-void-400 mb-8 leading-relaxed">
                文档里还没能直接落成设定的部分，让我们在访谈里一起聊出这个世界。
              </p>
            </>
          )}

          <button
            type="button"
            data-testid="nostalgia-continue"
            onClick={onContinue}
            className="bg-stardust-400 text-space-950 px-8 py-3 rounded-lg font-medium hover:bg-stardust-300 transition-colors"
          >
            继续
          </button>
        </div>
      </div>
    </div>
  );
}

export default NostalgiaConfirmPage;
