import { describe, expect, it } from 'vitest';
import { RELATION_LABELS, relationLabel, translateRelationInProse } from '../relationLabel';

// 与后端 app/domains/creation/a1/concept_edge_vocab.py RELATION_LABELS 逐字对齐（18 条）
const BACKEND_LABELS: Record<string, string> = {
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
  CONSTRAINT_LIMITS: '边界锚定',
  RULE_CULTURE_ORDER: '文化秩序',
  RULE_ERA_MARK: '纪元标记',
  RULE_CONTENT_GATE: '内容红线',
  RULE_CLIMATE_ZONE: '气候分区',
  RULE_ACTION_SCOPE: '行为边界',
  RULE_POWER_SATURATION: '力量饱和',
  RULE_ENV_STATE: '环境状态',
};

describe('relationLabel', () => {
  it('与后端 RELATION_LABELS 逐字对齐', () => {
    expect(Object.keys(RELATION_LABELS).length).toBe(Object.keys(BACKEND_LABELS).length);
    for (const [code, label] of Object.entries(BACKEND_LABELS)) {
      expect(RELATION_LABELS[code]).toBe(label);
    }
  });

  it('未知码原样返回（诚实降级）', () => {
    expect(relationLabel('SOME_FUTURE_CODE')).toBe('SOME_FUTURE_CODE');
    expect(relationLabel('')).toBe('');
    expect(relationLabel(undefined)).toBe('');
    expect(relationLabel(null)).toBe('');
  });

  it('中文关系名原样返回', () => {
    expect(relationLabel('力量源自')).toBe('力量源自');
  });

  it('用户实测码全部翻译', () => {
    expect(relationLabel('GEO_CONTAINS')).toBe('地理包含');
    expect(relationLabel('CONSTRAINT_LIMITS')).toBe('边界锚定');
    expect(relationLabel('EVENT_CAUSED_BY')).toBe('事件因果');
  });
});

describe('translateRelationInProse（存量句子兜底）', () => {
  it('历史开放问题句中的码被翻译，其余不动', () => {
    expect(
      translateRelationInProse('「世界本体」与「地理空间」之间是否存在「GEO_CONTAINS」这样的关系？请用世界观设定描述。')
    ).toBe('「世界本体」与「地理空间」之间是否存在「地理包含」这样的关系？请用世界观设定描述。');
  });

  it('中文关系与未知码不受影响', () => {
    expect(translateRelationInProse('「力量源自」已确认')).toBe('「力量源自」已确认');
    expect(translateRelationInProse('「UNKNOWN_CODE」待审')).toBe('「UNKNOWN_CODE」待审');
  });

  it('普通文本不含码时不改写', () => {
    const text = '请补充「历史时间线」的细节描述。';
    expect(translateRelationInProse(text)).toBe(text);
  });
});
