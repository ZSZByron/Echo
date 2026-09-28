// 进度计数人话文案（display-only）
// T5 (D21-11)：进度主行「聊聊你的世界 {done}/{total}」（ux-flow §5.1）。
// 铁律：输出永不携带模块名 label；total 由调用方传入（sections.length），禁止硬编码 /10。

/** 纯计数文案：「聊聊你的世界 {done}/{total}」。 */
export function plainProgressLabel(done: number, total: number): string {
  return `聊聊你的世界 ${done}/${total}`;
}
