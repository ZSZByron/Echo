// T11 (D21-13): α 草稿版本徽标纯函数（display-only）。
//
// 显示诚实规则：version 串仅在 draft-version 端点 available=true 时原样直显
// （后端 draft_label() 产出 α0.{round} / α0.{round}{step-1}，如 α0.1 / α0.11）。
// 端点无数据 / 会话重启 / 网络失败 → 永不编造版本号，只显示「草稿」二字。
//
// 先例：plainQuestion / plainProgress / compassPhrase（labels/ 纯函数目录）。
import type { DraftVersion } from "../types/a1";

export type DraftBadgeState = "draft" | "finalized";

/** 徽标文案：draft + 版本 → 「α 草稿 v{version}」；draft 无版本 → 「草稿」；finalized → 「已定稿」。 */
export function draftBadge(state: DraftBadgeState, version?: string | null): string {
  if (state === "finalized") return "已定稿";
  return version ? `α 草稿 v${version}` : "草稿";
}

/** 图谱 stale 黄条文案（草稿/重定稿途中 → 追加 α 草稿期标记，视觉最小改动）。 */
export function draftStaleBarLabel(version: number): string {
  return `设定已更新——点此重新定稿查看新图（当前 v${version} · α 草稿期）`;
}

/**
 * IPPoster 徽标三态判定（优先级：α 草稿 > 已定稿 > 降级草稿）。
 * - draftVersion.available=true → α 草稿 v{version}（最具体态，压过海报已加载）
 * - 海报加载成功（poster 端点仅 finalized 可达）→ 已定稿
 * - 其余（available=false 且海报未加载 / 端点网络错误传 null）→ 草稿，绝无假版本号
 */
export function posterBadge(
  draftVersion: DraftVersion | null,
  posterLoaded: boolean
): string {
  if (draftVersion !== null && draftVersion.available) {
    return draftBadge("draft", draftVersion.version);
  }
  if (posterLoaded) return draftBadge("finalized");
  return draftBadge("draft");
}
