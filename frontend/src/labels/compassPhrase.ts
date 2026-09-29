// 冲动罗盘一句话坐标文案（display-only）
// T8 (D21-12)：axis → 百分比倾向文案。阈值语义锚定 impulse spec §10.1：
// 叙事-建构倾向轴连续 [0,100]，100=纯叙事（讲故事的），0=纯建构（建设定的），
// 「说不清」初值≈70（落故事侧）——与后端 impulse_coords.py _AXIS_MIN/_AXIS_MAX = 0.0/100.0 一致。
// 显示规则：主导侧 = 轴值落在哪半边；百分比 = 距主导端的距离占比（建构侧镜像 100-axis）。

/** 主导侧人话名（轴两端映射，spec §10.1）。 */
export type CompassSide = '讲故事的' | '建设定的';

/** 一句话坐标文案（冒号后的倾向短语），如「讲故事的 70%」。 */
export function compassPhrase(axis: number): string {
  const clamped = Math.max(0, Math.min(100, axis));
  const narrative = clamped >= 50;
  const side: CompassSide = narrative ? '讲故事的' : '建设定的';
  const pct = Math.round(narrative ? clamped : 100 - clamped);
  return `${side} ${pct}%`;
}
