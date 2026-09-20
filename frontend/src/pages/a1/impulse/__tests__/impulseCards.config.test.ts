import { describe, expect, it } from 'vitest';

import {
  IMPULSE_CARDS,
  IMPULSE_SCREEN_INTRO,
  type ImpulseTypeId,
} from '../impulseCards.config';

describe('impulseCards.config', () => {
  it('9 张卡的 id 逐字等于锁定枚举，顺序一致，unsure 殿后', () => {
    const expected: ImpulseTypeId[] = [
      'setting_heavy',
      'character_driven',
      'plot',
      'philosophy',
      'exploration',
      'romance',
      'nostalgia',
      'healing',
      'unsure',
    ];
    expect(IMPULSE_CARDS.map((c) => c.id)).toEqual(expected);
    expect(IMPULSE_CARDS[IMPULSE_CARDS.length - 1]?.id).toBe('unsure');
  });

  it('每张卡 label ≤ 6 字', () => {
    for (const card of IMPULSE_CARDS) {
      expect(card.label.length, `label of ${card.id}`).toBeLessThanOrEqual(6);
      expect(card.label.length, `label of ${card.id}`).toBeGreaterThan(0);
    }
  });

  it('每张卡 tagline 15-30 字', () => {
    for (const card of IMPULSE_CARDS) {
      expect(
        card.tagline.length,
        `tagline of ${card.id}: ${card.tagline}`,
      ).toBeGreaterThanOrEqual(15);
      expect(
        card.tagline.length,
        `tagline of ${card.id}: ${card.tagline}`,
      ).toBeLessThanOrEqual(30);
    }
  });

  it('屏幕引导语为非空字符串且含诚实框架措辞', () => {
    expect(typeof IMPULSE_SCREEN_INTRO).toBe('string');
    expect(IMPULSE_SCREEN_INTRO.length).toBeGreaterThan(0);
    expect(IMPULSE_SCREEN_INTRO).toContain('帮我们');
  });
});
