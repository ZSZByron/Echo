/**
 * RackPanel 灵感架安家 UI 测试（波次三 T5 守门）
 *
 * 覆盖（施工单 QA：灵感架渲染/安家交互）：
 * 1. 空池 → 不渲染（null）
 * 2. 有存量 → 条目 + 计数 + home 归属展示
 * 3. onStow 提供 → 条目可点击安家（回调收 item+index）；未提供 → 纯展示无按钮
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RackPanel, type RackItem } from '../RackPanel';

const POOL: RackItem[] = [
  { text: '主角的怀表能倒转七秒', home: '命运' },
  { text: '反派其实是未来的主角' },
];

describe('RackPanel 灵感架（波次三 T5）', () => {
  it('空池 → 组件不渲染', () => {
    render(<RackPanel pool={[]} />);
    expect(screen.queryByTestId('rack-panel')).toBeNull();
  });

  it('存量 2 条 → 计数与条目渲染，home 归属可见（纯展示模式）', () => {
    render(<RackPanel pool={POOL} />);

    expect(screen.getByTestId('rack-panel').textContent).toContain('还放着 2 个想法');
    expect(screen.getByText(/主角的怀表能倒转七秒/)).toBeTruthy();
    expect(screen.getByText(/→ 命运/)).toBeTruthy();
    expect(screen.getByText(/反派其实是未来的主角/)).toBeTruthy();
    // 纯展示模式：无安家按钮，提示为定稿存档话术
    expect(screen.queryByTestId('rack-item-stow')).toBeNull();
    expect(screen.getByText(/定稿时可以安家/)).toBeTruthy();
  });

  it('onStow 提供 → 点击条目触发安家回调（item + index）', () => {
    const onStow = vi.fn();
    render(<RackPanel pool={POOL} onStow={onStow} />);

    const buttons = screen.getAllByTestId('rack-item-stow');
    expect(buttons).toHaveLength(2);
    expect(buttons[0].textContent).toContain('[安家]');

    fireEvent.click(buttons[1]);
    expect(onStow).toHaveBeenCalledTimes(1);
    expect(onStow).toHaveBeenCalledWith(POOL[1], 1);

    expect(screen.getByText(/点击条目可送回访谈/)).toBeTruthy();
  });
});
