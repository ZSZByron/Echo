/**
 * A1 冲动入口埋点 —— localStorage 事件日志工具（E0 数据层）
 *
 * 零网络约定：本模块不发起任何网络请求（无 HTTP 上报 / 后台信标 / XHR）。数据仅落 localStorage，
 * 由用户手动导出 JSON（对应 spec §12.1.7 R1 对照组指标采集）。
 *
 * PII 警示：data 通道仅供调用方传非敏感元数据（如 primary/secondary、elapsed_ms、
 * module_id）。答案内容、上传文本等用户内容绝不得写入 data。
 *
 * module_completed 触发语义（由调用方 T7 负责，本模块不实现去重）：
 * 模块 done ratio 首次达到 ≥0.5 时每模块发一次（同一 session 同一模块只记一次）。
 */

export type ImpulseTelemetryEventName =
  | 'impulse_card_shown' // 卡片列表曝光（R1 对照组核心指标）
  | 'impulse_card_selected' // 选中冲动 { primary, secondary: string | null }
  | 'impulse_card_skipped' // 跳过冲动（R1 对照组 + 冲动"流失率"指标）
  | 'first_question_answered' // 首问回答 { elapsed_ms }（R1：卡片冲动 vs 自然发问）
  | 'module_completed'; // 模块完成 { module_id }（能力地图关键节点模块）

export interface ImpulseTelemetryEvent {
  schema_version: 1;
  event: ImpulseTelemetryEventName;
  ts: number; // Date.now()
  user_id: string; // localStorage 'user_id' 现有键（弱标识，非内容，D8）
  session_id?: string; // a1 会话 id（可选）
  data?: Record<string, unknown>;
}

const STORAGE_KEY = 'a1_telemetry_v1';
const MAX_EVENTS = 500;

/**
 * 读取并解析事件日志。损坏 / 缺失时重置为空数组。
 */
export function getImpulseTelemetry(): ImpulseTelemetryEvent[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      localStorage.removeItem(STORAGE_KEY);
      return [];
    }
    return parsed as ImpulseTelemetryEvent[];
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return [];
  }
}

/**
 * 追加一条事件（FIFO 上限 500 条，超出丢最旧）。
 * 内部补 ts / user_id / schema_version，调用方只关心 event 名与 data。
 */
export function logImpulseEvent(
  event: ImpulseTelemetryEventName,
  data?: Record<string, unknown>,
): void {
  const events = getImpulseTelemetry();
  const entry: ImpulseTelemetryEvent = {
    schema_version: 1,
    event,
    ts: Date.now(),
    user_id: localStorage.getItem('user_id') ?? '',
    ...(data !== undefined ? { data } : {}),
  };
  events.push(entry);
  const trimmed = events.slice(Math.max(0, events.length - MAX_EVENTS));
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
}

/**
 * 将存储全量导出为 JSON 文件下载。导出后不清空存储。
 * 无事件时静默返回（不下载）。
 */
export function exportImpulseTelemetry(): void {
  const events = getImpulseTelemetry();
  if (events.length === 0) return;

  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`;
  const blob = new Blob([JSON.stringify(events, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `a1-telemetry-${stamp}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
