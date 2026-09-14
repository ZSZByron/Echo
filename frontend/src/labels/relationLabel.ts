// 边关系类型码 → 中文展示标签（display-only）
// 与后端 app/domains/creation/a1/concept_edge_vocab.py 的 RELATION_LABELS 逐字对齐。
// 铁律：仅用于展示文案；键匹配（confirm/reject/discard、dead-edge 三元组）
// 一律使用原始 code，不得引用本表。

export const RELATION_LABELS: Record<string, string> = {
  // ◇ 结构边（词汇表复合名的单一码拆解）
  GEO_CONTAINS: '地理包含',
  GEO_ABOVE: '垂直上位',
  GEO_BELOW: '垂直下位',
  POWER_SATURATES_GEO: '力量浸润地理',
  POWER_SOURCES_FROM_GEO: '力量源自地理',
  RULE_SHAPES_GEO: '法则塑形地理',
  EVENT_CAUSED_BY: '事件因果',
  GEO_HOSTS_EVENT: '地理承载事件',
  FACTION_OPPOSES: '阵营对立',
  ALLIED: '阵营结盟',
  // ★ 规则边
  CONSTRAINT_LIMITS: '边界锚定',
  // application_tree target_edge_type（cst 边 visual_description 域）
  RULE_CULTURE_ORDER: '文化秩序',
  RULE_ERA_MARK: '纪元标记',
  RULE_CONTENT_GATE: '内容红线',
  RULE_CLIMATE_ZONE: '气候分区',
  RULE_ACTION_SCOPE: '行为边界',
  RULE_POWER_SATURATION: '力量饱和',
  RULE_ENV_STATE: '环境状态',
};

/** 展示层标签；未知码原样返回（诚实降级）。 */
export function relationLabel(code: string | undefined | null): string {
  if (!code) return '';
  return RELATION_LABELS[code] ?? code;
}

/**
 * 整句兜底翻译：把句中「UPPER_SNAKE」形式的码替换为中文标签。
 * 用于后端拼装的历史存量句子（开放问题/聊天消息），中文或未知内容不动。
 */
export function translateRelationInProse(text: string): string {
  return text.replace(/「([A-Z][A-Z0-9_]+)」/g, (match, code: string) => {
    const label = RELATION_LABELS[code];
    return label ? `「${label}」` : match;
  });
}
