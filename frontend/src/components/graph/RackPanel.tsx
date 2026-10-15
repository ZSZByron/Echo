/**
 * RackPanel — 灵感架图谱页安家 UI（波次三 T5，拍2-13 回收时机三·图谱页）
 *
 * 展示 material_pool 存量（「你还有 N 个想法在灵感架上」），
 * 提示用户可在收尾时安家或随定稿存档。
 *
 * 数据源 = GET /file/{id} 端点返回的 material_pool（T5 透出补线）。
 * 不实现安家操作后端逻辑（批D 回收机制已落，此处仅展示+引导）。
 */
import React from 'react';

export interface RackItem {
  text?: string;
  home?: string;
  turn?: number;
}

export interface RackPanelProps {
  pool: RackItem[];
}

export function RackPanel({ pool }: RackPanelProps) {
  if (!pool || pool.length === 0) return null;

  return (
    <div
      className="rack-panel"
      data-testid="rack-panel"
      style={{
        border: '1px solid #f59e0b',
        borderRadius: '8px',
        padding: '12px',
        background: 'rgba(245,158,11,0.06)',
        marginTop: '12px',
      }}
    >
      <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#f59e0b', marginBottom: '8px' }}>
        💡 灵感架上还放着 {pool.length} 个想法
      </div>
      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12px', color: '#ccc' }}>
        {pool.map((item, i) => (
          <li key={i} style={{ marginBottom: '4px' }}>
            {item.text || '(未命名想法)'}
            {item.home && (
              <span style={{ color: '#666', marginLeft: '4px' }}>→ {item.home}</span>
            )}
          </li>
        ))}
      </ul>
      <div style={{ fontSize: '11px', color: '#888', marginTop: '8px' }}>
        定稿时可以安家到对应模块，或随定稿存档保留。
      </div>
    </div>
  );
}
