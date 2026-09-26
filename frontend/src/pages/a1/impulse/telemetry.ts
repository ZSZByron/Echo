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
  | 'module_completed' // 模块完成 { module_id }（能力地图关键节点模块）
  | 'restart_to_entry'; // 重新开始：用户确认后清除本地工作区状态回到冲动入口

export interface ImpulseTelemetryEvent {
  schema_version: 1 | 2; // v2 = M4c（三项指标升级）；读取端版本容忍（v1 存量照常解析）
  event: ImpulseTelemetryEventName;
  ts: number; // Date.now()
  user_id: string; // localStorage 'user_id' 现有键（弱标识，非内容，D8）
  session_id?: string; // a1 会话 id（可选）
  data?: Record<string, unknown>;
}

// 存储键保持 a1_telemetry_v1（物理键名不变，schema 版本演进在事件字段内——
// 升级/降级都不得破坏既有本地数据）。
const STORAGE_KEY = 'a1_telemetry_v1';
const MAX_EVENTS = 500;
const SCHEMA_VERSION = 2 as const;

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
    schema_version: SCHEMA_VERSION,
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
 * 回填会话 id：遍历存储全量事件，session_id 为空的就地补 sessionId（含重写 localStorage）。
 * 已有值不覆盖；幂等可重复调用。零网络：仅本地存储操作。
 */
export function attachSessionId(sessionId: string): void {
  const events = getImpulseTelemetry();
  let changed = false;
  for (const e of events) {
    if (e.session_id === undefined) {
      e.session_id = sessionId;
      changed = true;
    }
  }
  if (changed) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
  }
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

// ---------------------------------------------------------------------------
// M4c 埋点三项升级（v2）：跳过率 / 完成度 / 自报-行为错位地图
// 全部为事件日志上的确定性派生函数（零 LLM、零网络），对 v1/v2 事件版本容忍。
// ---------------------------------------------------------------------------

/** 跳过率：impulse_card_skipped / (selected + skipped)；无决策 → 0。 */
export function computeSkipRate(events: ImpulseTelemetryEvent[]): number {
  let skipped = 0;
  let selected = 0;
  for (const e of events) {
    if (e.event === 'impulse_card_skipped') skipped++;
    else if (e.event === 'impulse_card_selected') selected++;
  }
  const decisions = skipped + selected;
  return decisions === 0 ? 0 : skipped / decisions;
}

/** 完成度：去重后已完成模块数 + 首问是否已回答。 */
export function computeModuleCompletion(events: ImpulseTelemetryEvent[]): {
  completed_modules: number;
  first_question_answered: boolean;
} {
  const modules = new Set<string>();
  let firstQuestion = false;
  for (const e of events) {
    if (e.event === 'module_completed') {
      const mid = e.data?.['module_id'];
      if (typeof mid === 'string') modules.add(mid);
    } else if (e.event === 'first_question_answered') {
      firstQuestion = true;
    }
  }
  return {
    completed_modules: modules.size,
    first_question_answered: firstQuestion,
  };
}

export interface MismatchMapEntry {
  selected: number;
  skipped: number;
  completed_modules: number;
  /** 自报（选了该冲动）但零模块完成 = 错位。 */
  mismatched: boolean;
}

/**
 * 自报-行为错位地图：按自报冲动（impulse_card_selected data.primary）分组，
 * 对照行为面（该冲动下的选/跳 + 全局模块完成去重数）。确定性派生，无版本
 * 门槛（v1 事件同样参与统计）。
 */
export function computeStatedBehaviorMismatchMap(
  events: ImpulseTelemetryEvent[],
): Record<string, MismatchMapEntry> {
  const map: Record<string, MismatchMapEntry> = {};
  const { completed_modules } = computeModuleCompletion(events);
  for (const e of events) {
    if (e.event !== 'impulse_card_selected') continue;
    const primary = e.data?.['primary'];
    if (typeof primary !== 'string' || primary === '') continue;
    const entry = (map[primary] ??= {
      selected: 0,
      skipped: 0,
      completed_modules,
      mismatched: false,
    });
    entry.selected++;
    entry.completed_modules = completed_modules;
  }
  for (const e of events) {
    if (e.event !== 'impulse_card_skipped') continue;
    const primary = e.data?.['primary'];
    if (typeof primary !== 'string' || primary === '') continue;
    const entry = (map[primary] ??= {
      selected: 0,
      skipped: 0,
      completed_modules,
      mismatched: false,
    });
    entry.skipped++;
    entry.completed_modules = completed_modules;
  }
  for (const entry of Object.values(map)) {
    entry.mismatched = entry.selected > 0 && entry.completed_modules === 0;
  }
  return map;
}
