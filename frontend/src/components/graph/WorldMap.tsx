/**
 * WorldMap — 活地图七大陆视图（波次三 T2，拍3-3）
 *
 * 一目了然「世界长到哪了」：L1×7 大陆卡片网格，每大陆下列 L2 模块，
 * 已答模块亮起、未答灰。数据源 = KnowledgeGraph.nodes（tier/level/description）。
 *
 * 不改后端；纯只读消费既有 /file/{id}/graph 端点数据。
 */
import React from 'react';
import type { KnowledgeGraph, GraphNode } from '../../types/graph';

/** L1 大陆元数据（id → 中文标签 + 图标 emoji）。与 THREE_TIER_TREE L1 对齐。 */
const CONTINENTS: { id: string; label: string; icon: string }[] = [
  { id: 'ip', label: 'IP 定位', icon: '◉' },
  { id: 'worldview', label: '世界观', icon: '🌍' },
  { id: 'story_line', label: '剧情', icon: '📖' },
  { id: 'character', label: '角色', icon: '👤' },
  { id: 'gameplay', label: '玩法', icon: '🎲' },
  { id: 'visual', label: '视觉', icon: '🎨' },
  { id: 'setting_boundary', label: '设定边界', icon: '⚖️' },
];

/** 从 graph nodes 提取每大陆已答 L2 模块集合。 */
function buildContinentMap(nodes: GraphNode[]): Map<string, Set<string>> {
  const map = new Map<string, Set<string>>();
  for (const c of CONTINENTS) map.set(c.id, new Set());
  for (const n of nodes) {
    // L2 判定只认 level===2（废弃 tier===2 误用与 serial 首段虚构映射）
    if (n.level !== 2) continue;
    // 归属只认 n.continent（后端 THREE_TIER_TREE L1 id）；
    // 空/未知大陆 → 跳过不点亮（诚实降级，不猜）
    const continent = n.continent ?? '';
    if (!map.has(continent)) continue;
    map.get(continent)!.add(n.description?.split(':')[0] || n.id);
  }
  return map;
}

export interface WorldMapProps {
  graph: KnowledgeGraph | null;
}

export function WorldMap({ graph }: WorldMapProps) {
  const nodes = Object.values(graph?.nodes ?? {});
  const continentMap = React.useMemo(() => buildContinentMap(nodes), [nodes]);
  // 总点亮 = 各大陆已答集合 size 之和（与卡片口径一致）
  const totalAnswered = Array.from(continentMap.values()).reduce(
    (sum, s) => sum + s.size,
    0,
  );

  return (
    <div className="world-map" style={{ padding: '16px' }}>
      <div style={{ marginBottom: '12px', fontSize: '14px', color: '#888' }}>
        世界全貌 · 已点亮 {totalAnswered} 处
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: '12px',
        }}
      >
        {CONTINENTS.map(c => {
          const answered = continentMap.get(c.id) ?? new Set<string>();
          const isLit = answered.size > 0;
          return (
            <div
              key={c.id}
              data-testid={`continent-${c.id}`}
              style={{
                border: `1px solid ${isLit ? '#a78bfa' : '#333'}`,
                borderRadius: '8px',
                padding: '12px',
                background: isLit ? 'rgba(167,139,250,0.08)' : 'rgba(40,40,40,0.4)',
                opacity: isLit ? 1 : 0.5,
                transition: 'all 0.3s',
              }}
            >
              <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '6px' }}>
                {c.icon} {c.label}
                {isLit && (
                  <span style={{ marginLeft: '6px', fontSize: '11px', color: '#a78bfa' }}>
                    {answered.size} 处
                  </span>
                )}
              </div>
              {answered.size > 0 ? (
                <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12px', color: '#ccc' }}>
                  {Array.from(answered).slice(0, 6).map(m => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              ) : (
                <span style={{ fontSize: '11px', color: '#555' }}>尚未触及</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
