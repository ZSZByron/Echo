/**
 * ImpulseCards 组件级单测（计划 e0-impulse-entry T5）
 *
 * QA 三场景：主+次状态机（含同卡取消）、skip 常驻可达 + skipped 事件、unsure 殿后兜底行。
 * T1 教训：不用 fake timers / waitFor——交互后同步断言。
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ImpulseCards } from '../ImpulseCards';
import { getImpulseTelemetry } from '../telemetry';
import type { ImpulseTypeId } from '../impulseCards.config';
import type { Seed } from '../seedGrouping';

const SEEDS: Seed[] = [
  {
    id: '1',
    name: '深渊低语',
    genre: '哲理',
    description: 'desc',
    dimension_defaults: {},
  },
];

const PRIMARY_CARDS: ImpulseTypeId[] = [
  'setting_heavy',
  'character_driven',
  'plot',
  'philosophy',
  'exploration',
  'romance',
  'nostalgia',
  'healing',
];

const card = (id: ImpulseTypeId) => screen.getByTestId(`impulse-card-${id}`);

function renderCards(overrides: Partial<Parameters<typeof ImpulseCards>[0]> = {}) {
  const onCardCommit = vi.fn();
  const onSkip = vi.fn();
  const props = { seeds: SEEDS, onCardCommit, onSkip, ...overrides };
  render(<ImpulseCards {...props} />);
  return props;
}

describe('ImpulseCards', () => {
  beforeEach(() => {
    cleanup();
    localStorage.removeItem('a1_telemetry_v1');
  });

  it('renders 9 cards + intro + footer export button', () => {
    renderCards();
    for (const id of [...PRIMARY_CARDS, 'unsure']) {
      expect(card(id)).toBeInTheDocument();
    }
    expect(screen.getByTestId('impulse-confirm')).toBeInTheDocument();
    expect(screen.getByTestId('impulse-skip')).toBeInTheDocument();
    expect(screen.getByTestId('impulse-export')).toBeInTheDocument();
  });

  it('logs impulse_card_shown exactly once on mount (StrictMode-safe ref guard)', () => {
    renderCards();
    const shown = getImpulseTelemetry().filter((e) => e.event === 'impulse_card_shown');
    expect(shown).toHaveLength(1);
  });

  it('confirm button is disabled until primary selected', () => {
    renderCards();
    const confirm = screen.getByTestId('impulse-confirm') as HTMLButtonElement;
    expect(confirm.disabled).toBe(true);
    fireEvent.click(card('plot'));
    expect(confirm.disabled).toBe(false);
  });

  it('QA scenario 1: primary + secondary state machine incl. same-card cancel', () => {
    const { onCardCommit } = renderCards();

    // 点剧情 = primary
    fireEvent.click(card('plot'));
    expect(card('plot')).toHaveAttribute('data-selected', 'primary');

    // 点爱情 = secondary，剧情保持 primary
    fireEvent.click(card('romance'));
    expect(card('plot')).toHaveAttribute('data-selected', 'primary');
    expect(card('romance')).toHaveAttribute('data-selected', 'secondary');

    // 再点爱情 = 取消次选，primary 不变
    fireEvent.click(card('romance'));
    expect(card('plot')).toHaveAttribute('data-selected', 'primary');
    expect(card('romance')).not.toHaveAttribute('data-selected');

    // 主卡二重点击 = 全部取消（不升级为次选）
    fireEvent.click(card('plot'));
    expect(card('plot')).not.toHaveAttribute('data-selected');
    expect(card('romance')).not.toHaveAttribute('data-selected');

    // 仅选主卡时确认 → onCardCommit({ primary, secondary: null })
    fireEvent.click(card('plot'));
    fireEvent.click(screen.getByTestId('impulse-confirm'));
    expect(onCardCommit).toHaveBeenCalledWith({ primary: 'plot', secondary: null });
  });

  it('QA scenario 2: skip always present/enabled, fires skipped event + onSkip', () => {
    const { onSkip } = renderCards();

    // 不选任何卡，skip 已存在且 enabled
    const skip = screen.getByTestId('impulse-skip') as HTMLButtonElement;
    expect(skip).toBeInTheDocument();
    expect(skip.disabled).toBe(false);

    fireEvent.click(skip);
    expect(onSkip).toHaveBeenCalledTimes(1);
    const events = getImpulseTelemetry();
    expect(events.some((e) => e.event === 'impulse_card_skipped')).toBe(true);
    // 未写 selected 事件
    expect(events.some((e) => e.event === 'impulse_card_selected')).toBe(false);
  });

  it('QA scenario 3: unsure is the 9th card in its own fallback row', () => {
    renderCards();
    const fallbackRow = document.querySelector('[data-slot="fallback"]');
    expect(fallbackRow).not.toBeNull();
    expect(fallbackRow).toContainElement(card('unsure'));
    // 兜底行内只有 unsure 一张卡
    expect(fallbackRow!.querySelectorAll('[data-testid^="impulse-card-"]')).toHaveLength(1);
  });

  it('confirm writes impulse_card_selected with primary + secondary', () => {
    const { onCardCommit } = renderCards();
    fireEvent.click(card('healing'));
    fireEvent.click(card('philosophy'));
    fireEvent.click(screen.getByTestId('impulse-confirm'));
    expect(onCardCommit).toHaveBeenCalledWith({
      primary: 'healing',
      secondary: 'philosophy',
    });
    const selected = getImpulseTelemetry().find((e) => e.event === 'impulse_card_selected');
    expect(selected?.data).toEqual({ primary: 'healing', secondary: 'philosophy' });
  });
});
