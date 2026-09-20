import { afterEach, describe, expect, it, vi } from 'vitest';
import { groupSeedsByType, TYPE_SEED_NAMES, type Seed } from '../seedGrouping';

// 8 authoritative preset seeds (backend/app/domains/creation/seed/preset_loader.py, ids 1-8)
const ALL_SEED_NAMES = [
  '深渊低语',
  '霓虹窃案',
  '腐化深渊',
  '灰烬之路',
  '碎天录',
  '群星彼岸',
  '破晓之剑',
  '鸩酒与玫瑰',
] as const;

function makeSeed(name: string): Seed {
  return {
    id: String(ALL_SEED_NAMES.indexOf(name as (typeof ALL_SEED_NAMES)[number]) + 1),
    name,
    genre: 'test-genre',
    description: `desc-${name}`,
    dimension_defaults: {},
  };
}

const fullSeeds: Seed[] = ALL_SEED_NAMES.map(makeSeed);

afterEach(() => {
  vi.restoreAllMocks();
});

describe('TYPE_SEED_NAMES', () => {
  it('has exactly 9 keys, verbatim', () => {
    expect(Object.keys(TYPE_SEED_NAMES).sort()).toEqual(
      [
        'setting_heavy',
        'character_driven',
        'plot',
        'philosophy',
        'exploration',
        'romance',
        'nostalgia',
        'healing',
        'unsure',
      ].sort()
    );
    expect(Object.keys(TYPE_SEED_NAMES)).toHaveLength(9);
  });

  it('matches spec §5.2 seed recommendation rows verbatim', () => {
    expect(TYPE_SEED_NAMES.setting_heavy).toEqual(['群星彼岸', '碎天录']);
    expect(TYPE_SEED_NAMES.character_driven).toEqual(['破晓之剑', '鸩酒与玫瑰']);
    expect(TYPE_SEED_NAMES.plot).toEqual(['霓虹窃案', '鸩酒与玫瑰']);
    expect(TYPE_SEED_NAMES.philosophy).toEqual(['深渊低语', '灰烬之路']);
    expect(TYPE_SEED_NAMES.exploration).toEqual(['腐化深渊', '灰烬之路']);
    expect(TYPE_SEED_NAMES.romance).toEqual(['鸩酒与玫瑰', '群星彼岸']);
    expect(TYPE_SEED_NAMES.nostalgia).toEqual([]);
    expect(TYPE_SEED_NAMES.healing).toEqual(['破晓之剑']);
    expect(TYPE_SEED_NAMES.unsure).toEqual(['霓虹窃案', '鸩酒与玫瑰']);
  });
});

describe('groupSeedsByType', () => {
  it('groups plot seeds in mapping-table order, rest preserves input order', () => {
    const { matched, rest, degraded } = groupSeedsByType(fullSeeds, 'plot');
    expect(degraded).toBe(false);
    expect(matched.map((s) => s.name)).toEqual(['霓虹窃案', '鸩酒与玫瑰']);
    expect(rest).toHaveLength(6);
    // rest preserves original (fullSeeds) order
    expect(rest.map((s) => s.name)).toEqual([
      '深渊低语',
      '腐化深渊',
      '灰烬之路',
      '碎天录',
      '群星彼岸',
      '破晓之剑',
    ]);
  });

  it('healing matches a single seed', () => {
    const { matched, rest, degraded } = groupSeedsByType(fullSeeds, 'healing');
    expect(degraded).toBe(false);
    expect(matched.map((s) => s.name)).toEqual(['破晓之剑']);
    expect(rest).toHaveLength(7);
  });

  it('matched order follows mapping table, not input order (romance)', () => {
    // reverse input order so input order != mapping order
    const reversed = [...fullSeeds].reverse();
    const { matched, degraded } = groupSeedsByType(reversed, 'romance');
    expect(degraded).toBe(false);
    // mapping order: 鸩酒与玫瑰 first, 群星彼岸 second — despite reversed input
    expect(matched.map((s) => s.name)).toEqual(['鸩酒与玫瑰', '群星彼岸']);
  });

  it('unsure puts story-side seed first (D13, via mapping order)', () => {
    const { matched, degraded } = groupSeedsByType(fullSeeds, 'unsure');
    expect(degraded).toBe(false);
    expect(matched[0]?.name).toBe('霓虹窃案');
  });

  it('nostalgia yields empty matched without degradation (upload path)', () => {
    const { matched, rest, degraded } = groupSeedsByType(fullSeeds, 'nostalgia');
    expect(matched).toEqual([]);
    expect(degraded).toBe(false);
    expect(rest).toHaveLength(8);
  });

  it('partial mismatch degrades with warn, keeps found matches in order', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const withoutRose = fullSeeds.filter((s) => s.name !== '鸩酒与玫瑰');
    const { matched, rest, degraded } = groupSeedsByType(withoutRose, 'plot');
    expect(degraded).toBe(true);
    expect(matched.map((s) => s.name)).toEqual(['霓虹窃案']);
    expect(rest).toHaveLength(6);
    expect(warn).toHaveBeenCalledTimes(1);
    expect(String(warn.mock.calls[0]?.[0])).toContain('鸩酒与玫瑰');
  });

  it('total mismatch (empty seed list) degrades without throwing', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const { matched, rest, degraded } = groupSeedsByType([], 'philosophy');
    expect(matched).toEqual([]);
    expect(rest).toEqual([]);
    expect(degraded).toBe(true);
    expect(warn).toHaveBeenCalledTimes(1);
    expect(String(warn.mock.calls[0]?.[0])).toContain('深渊低语');
    expect(String(warn.mock.calls[0]?.[0])).toContain('灰烬之路');
  });

  it('warns for every missing recommended name', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const onlySome = fullSeeds.filter((s) => s.name === '破晓之剑');
    const { degraded } = groupSeedsByType(onlySome, 'setting_heavy');
    expect(degraded).toBe(true);
    const msg = String(warn.mock.calls[0]?.[0]);
    expect(msg).toContain('群星彼岸');
    expect(msg).toContain('碎天录');
  });
});
