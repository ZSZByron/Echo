#!/usr/bin/env node
/**
 * verify-telemetry-metrics.mjs — R1 指标离线验证脚本（E0 埋点回收口径）
 *
 * 用法：
 *   node frontend/scripts/verify-telemetry-metrics.mjs <a1-telemetry-export.json 路径>
 *
 * 输入：`导出使用数据`按钮导出的 JSON（ImpulseTelemetryEvent[]，schema_version=1）
 * 输出（R1 三指标，口径对齐 docs/plans/2026-09-20-动机占比预测基线.md §1 与备忘 §6 层2）：
 *   1. 跳过率     = impulse_card_skipped / impulse_card_shown
 *   2. 9 型选卡分布 = impulse_card_selected 按 primary 计数（单一口径：只按主冲动计，占比 = 计数/选卡总数）
 *   3. 首答完成率   = 有 first_question_answered 的用户 / 该组用户（按 user_id 分组；
 *                     选卡组 = 有 selected 事件者优先归类，其余有 skipped 事件者归跳过组）
 *
 * 纪律：E0 数据为方向性（<500 样本），本脚本只做描述统计，不做推断。
 * 任何除法分母为 0 时输出 n/a（绝不输出 NaN）。
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const VALID_EVENTS = new Set([
  'impulse_card_shown',
  'impulse_card_selected',
  'impulse_card_skipped',
  'first_question_answered',
  'module_completed',
]);

const pct = (num, den) => (den > 0 ? `${((num / den) * 100).toFixed(1)}%` : 'n/a');

function fail(msg) {
  console.error(`ERROR: ${msg}`);
  process.exit(1);
}

const filePath = process.argv[2];
if (!filePath) fail('用法: node verify-telemetry-metrics.mjs <导出JSON路径>');

let events;
try {
  events = JSON.parse(readFileSync(filePath, 'utf-8'));
} catch (e) {
  fail(`无法读取/解析 JSON: ${e.message}`);
}
if (!Array.isArray(events)) fail('导出内容不是事件数组');
if (events.length === 0) fail('导出为空（0 条事件）——无法计算指标');

const bad = events.filter((e) => !e || typeof e !== 'object' || !VALID_EVENTS.has(e.event));
if (bad.length > 0) fail(`发现 ${bad.length} 条未知/畸形事件`);

// ---- 指标 1: 跳过率 ----
const shown = events.filter((e) => e.event === 'impulse_card_shown').length;
const skipped = events.filter((e) => e.event === 'impulse_card_skipped').length;

// ---- 指标 2: 选卡分布（第一冲动单一口径：仅按 primary）----
const distribution = {};
let selectedTotal = 0;
for (const e of events) {
  if (e.event !== 'impulse_card_selected') continue;
  const primary = e.data?.primary;
  if (typeof primary !== 'string') continue;
  distribution[primary] = (distribution[primary] ?? 0) + 1;
  selectedTotal += 1;
}

// ---- 指标 3: 首答完成率（选卡组 vs 跳过组，按 user_id 分组）----
const users = new Map(); // user_id -> { group, answered }
for (const e of events) {
  const uid = e.user_id ?? '';
  if (!users.has(uid)) users.set(uid, { group: 'other', answered: false });
  const u = users.get(uid);
  if (e.event === 'impulse_card_selected') u.group = 'selected'; // 选卡优先归类
  else if (e.event === 'impulse_card_skipped' && u.group !== 'selected') u.group = 'skipped';
  if (e.event === 'first_question_answered') u.answered = true;
}

const groups = { selected: { total: 0, answered: 0 }, skipped: { total: 0, answered: 0 }, other: { total: 0, answered: 0 } };
for (const u of users.values()) {
  groups[u.group].total += 1;
  if (u.answered) groups[u.group].answered += 1;
}

// ---- 输出 ----
console.log('=== R1 埋点指标（E0 方向性数据） ===');
console.log(`事件总数: ${events.length}（来自 ${users.size} 个本地标识）`);
console.log('');
console.log('1) 跳过率');
console.log(`   shown=${shown}  skipped=${skipped}  跳过率=${pct(skipped, shown)}`);
console.log('');
console.log('2) 9 型选卡分布（第一冲动单一口径，按 primary 计）');
console.log(`   选卡总次数=${selectedTotal}`);
const TYPES = [
  'setting_heavy', 'character_driven', 'plot', 'philosophy', 'exploration',
  'romance', 'nostalgia', 'healing', 'unsure',
];
for (const t of TYPES) {
  const c = distribution[t] ?? 0;
  console.log(`   ${t.padEnd(17)} ${String(c).padStart(3)}  ${pct(c, selectedTotal)}`);
}
const unknownTypes = Object.keys(distribution).filter((t) => !TYPES.includes(t));
for (const t of unknownTypes) console.log(`   (未知型) ${t}: ${distribution[t]}`);
console.log('');
console.log('3) 首答完成率（选卡组 vs 跳过组）');
console.log(`   选卡组: ${groups.selected.answered}/${groups.selected.total} = ${pct(groups.selected.answered, groups.selected.total)}`);
console.log(`   跳过组: ${groups.skipped.answered}/${groups.skipped.total} = ${pct(groups.skipped.answered, groups.skipped.total)}`);
console.log(`   其他(未过卡片屏): ${groups.other.answered}/${groups.other.total} = ${pct(groups.other.answered, groups.other.total)}`);
console.log('');
console.log('指标计算完成，无 NaN。注意：单用户导出时分组完成率仅反映该用户，属预期。');
