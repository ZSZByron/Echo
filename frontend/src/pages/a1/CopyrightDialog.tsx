/**
 * CopyrightDialog Component
 *
 * Modal overlay for displaying copyright matches and conversion options.
 * Shows when uploaded content triggers copyright detection.
 */

import '../../components/theme.css';

export interface CopyrightMatch {
  term: string;
  work: string;
  evidence: string;
}

export interface CopyrightReport {
  risk_level: string;
  matches: CopyrightMatch[];
}

interface CopyrightDialogProps {
  report: CopyrightReport;
  onConvert: () => void;
  onCancel: () => void;
  isProcessing: boolean;
}

export function CopyrightDialog({ report, onConvert, onCancel, isProcessing }: CopyrightDialogProps) {
  return (
    <div className="fixed inset-0 bg-space-950/90 backdrop-blur-sm z-50 flex items-center justify-center p-8">
      <div className="glass-panel max-w-3xl w-full p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="text-cosmos-error text-2xl">⚠</div>
          <h2 className="text-stardust-300 text-xl font-medium">版权风险检测</h2>
        </div>

        <div className="mb-6">
          <p className="text-gray-200 mb-4">
            检测到您上传的内容可能与以下已发布作品存在相似元素：
          </p>

          {report.matches.length > 0 ? (
            <div className="bg-space-800/40 border border-cosmos-error/20 rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-space-900/60">
                  <tr>
                    <th className="text-left text-stardust-300 px-4 py-3 text-sm font-medium border-b border-white/5">相似术语</th>
                    <th className="text-left text-stardust-300 px-4 py-3 text-sm font-medium border-b border-white/5">疑似作品</th>
                    <th className="text-left text-stardust-300 px-4 py-3 text-sm font-medium border-b border-white/5">证据说明</th>
                  </tr>
                </thead>
                <tbody>
                  {report.matches.map((match: CopyrightMatch, index: number) => (
                    <tr key={index} className="border-b border-white/5 last:border-0">
                      <td className="px-4 py-3 text-nebula-400 text-sm">{match.term}</td>
                      <td className="px-4 py-3 text-gray-200 text-sm">{match.work}</td>
                      <td className="px-4 py-3 text-void-400 text-sm">{match.evidence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-space-800/40 border border-cosmos-warning/20 rounded-lg p-4">
              <p className="text-cosmos-warning text-sm">
                风险等级: {report.risk_level}
              </p>
            </div>
          )}
        </div>

        <div className="flex gap-4">
          <button
            onClick={onConvert}
            disabled={isProcessing}
            className="flex-1 bg-cosmos-success text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-cosmos-success/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isProcessing ? '转换中...' : '转换使用（AI 改编规避）'}
          </button>
          <button
            onClick={onCancel}
            disabled={isProcessing}
            className="flex-1 bg-space-700 text-stardust-300 px-6 py-3 rounded-lg font-medium hover:bg-space-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors border border-white/10"
          >
            取消上传
          </button>
        </div>

        <div className="mt-4 p-3 bg-space-800/40 border border-white/5 rounded">
          <p className="text-void-400 text-xs">
            选择「转换使用」将对相似元素进行原创化改写，保留世界观结构的同时规避版权风险。
          </p>
        </div>
      </div>
    </div>
  );
}
