/**
 * Impulse type → seed grouping (name-matched, graceful fallback).
 *
 * Maps each of the 9 impulse types to recommended preset seed names
 * (verbatim from backend/app/domains/creation/seed/preset_loader.py
 * authoritative 8-seed list). Matching is by seed NAME at runtime —
 * never by id — to guard against backend id changes.
 *
 * Source of mapping rows: docs/plans/2026-09-18-impulse-entry-system-spec.md §5.2
 * Unsure semantics (D13): matched = story-side seeds shown first — ordering is
 * already expressed by the mapping table; no special handling in this function.
 */

/**
 * Structural counterpart of the `Seed` interface consumed by A1Workspace
 * (frontend/src/pages/a1/A1Workspace.tsx:23-29). A1Workspace declares it
 * locally without exporting; to avoid touching existing files we redefine
 * the same shape here. Fields must stay in sync with that declaration.
 */
export interface Seed {
  id: string;
  name: string;
  genre: string;
  description: string;
  dimension_defaults: Record<string, unknown>;
}

/** The 9 impulse type ids (verbatim; converges with T2's ImpulseTypeId at wiring time, T5). */
export type ImpulseTypeId =
  | 'setting_heavy'
  | 'character_driven'
  | 'plot'
  | 'philosophy'
  | 'exploration'
  | 'romance'
  | 'nostalgia'
  | 'healing'
  | 'unsure';

/**
 * Impulse type → recommended seed names (spec §5.2, verbatim — do not edit).
 * nostalgia is intentionally empty: nostalgia goes straight to upload, no seeds.
 */
export const TYPE_SEED_NAMES: Record<ImpulseTypeId, string[]> = {
  setting_heavy: ['群星彼岸', '碎天录'],
  character_driven: ['破晓之剑', '鸩酒与玫瑰'],
  plot: ['霓虹窃案', '鸩酒与玫瑰'],
  philosophy: ['深渊低语', '灰烬之路'],
  exploration: ['腐化深渊', '灰烬之路'],
  romance: ['鸩酒与玫瑰', '群星彼岸'],
  nostalgia: [],
  healing: ['破晓之剑'],
  unsure: ['霓虹窃案', '鸩酒与玫瑰'],
};

export interface SeedGrouping {
  matched: Seed[];
  rest: Seed[];
  degraded: boolean;
}

/**
 * Group seeds for an impulse type by exact name match.
 *
 * - `matched`: recommended seeds found in `seeds`, ordered by the mapping
 *   table order (not the input order).
 * - `rest`: all non-matched seeds, original order preserved.
 * - `degraded`: true when any recommended name is missing from `seeds`
 *   (partial or total mismatch). Logs a console.warn listing the missing
 *   names; never throws, never blocks. Empty mapping (nostalgia) yields
 *   matched=[] / degraded=false — legitimate (upload-first path).
 */
export function groupSeedsByType(seeds: Seed[], type: ImpulseTypeId): SeedGrouping {
  const recommended = TYPE_SEED_NAMES[type];

  const byName = new Map<string, Seed>();
  for (const seed of seeds) {
    byName.set(seed.name, seed);
  }

  const matched: Seed[] = [];
  const matchedNames = new Set<string>();
  for (const name of recommended) {
    const seed = byName.get(name);
    if (seed) {
      matched.push(seed);
      matchedNames.add(name);
    }
  }

  const missing = recommended.filter((name) => !matchedNames.has(name));
  const degraded = missing.length > 0;
  if (degraded) {
    console.warn(
      `[seedGrouping] impulse type "${type}": recommended seed(s) not found: ${missing.join(', ')} — degrading to flat list`
    );
  }

  const rest = seeds.filter((seed) => !matchedNames.has(seed.name));

  return { matched, rest, degraded };
}
