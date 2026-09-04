/**
 * A1 Knowledge Graph Component
 *
 * Read-only knowledge graph visualization using React Flow.
 * Displays A1 worldview nodes with hierarchical topology and constraint relationships.
 * 
 * Extended with concept network view showing semantic edges with review workflow.
 */

import React, { useMemo, useCallback, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
} from 'reactflow';
import type { Node, Edge } from 'reactflow';
import type { KnowledgeGraph, GraphNode, GraphEdge } from '../../types/graph';
import type { ConceptTerm } from '../../types/a1';
import { confirmEdge, rejectEdge } from '../../api/a1';
import 'reactflow/dist/style.css';

export interface A1KnowledgeGraphProps {
  graph: KnowledgeGraph | null;
  isLoading: boolean;
  error: string | null;
  onRetry?: () => void;
  fileId?: string;
  edgeStats?: {
    semantic_total: number;
    semantic_confirmed: number;
    rule_total: number;
    structure_total: number;
    pending_review: number;
  };
  openQuestions?: import('../../pages/a1/A1Workspace').OpenQuestionRecord[];
  onRefresh?: () => void;
  /** Controlled view mode (toolbar rendered by parent fullscreen layout) */
  viewMode?: 'tree' | 'concept';
  onViewModeChange?: (mode: 'tree' | 'concept') => void;
  /** Canvas edge clicked -> parent panel scrolls/highlights matching entry */
  onEdgeFocus?: (edgeKey: string) => void;
  /** Edge key to highlight (set when panel entry focused) */
  focusEdgeKey?: string | null;
  /** Edge key hovered in the review panel (canvas dimming sync) */
  hoverEdgeKey?: string | null;
  /** Concept terms (T-D): unconfirmed term nodes render semi-transparent with dashed border */
  conceptTerms?: ConceptTerm[];
}

/** Canonical concept edge key: `from/to/relation` (slash-separated). */
export const conceptEdgeKey = (edge: Pick<GraphEdge, 'from_node_id' | 'to_node_id' | 'relation' | 'visual_description'>): string =>
  `${edge.from_node_id}/${edge.to_node_id}/${edge.relation || edge.visual_description}`;

/** Detect concept-term node (v0.4 legacy two-phase artifact): strict `term:` id prefix only. */
export const isConceptTermNode = (node: { id: string }): boolean =>
  node.id.startsWith('term:');

/** Detect v0.5 depth-tree node: id prefix `d:` (form `d:{anchor}:{title}`, level=4). */
export const isDepthNode = (id: string): boolean => id.startsWith('d:');

/** Cluster palette for concept-term nodes (reuses existing module cluster colors). */
const TERM_CLUSTER_COLORS = [
  '#a78bfa', // nebula purple
  '#fbbf24', // stardust amber
  '#10b981', // emerald
  '#60a5fa', // blue
  '#f472b6', // pink
];

/** Deterministic cluster color from node id hash. */
const termClusterColor = (id: string): string => {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) | 0;
  }
  return TERM_CLUSTER_COLORS[Math.abs(hash) % TERM_CLUSTER_COLORS.length];
};

/**
 * Tier presentation bands (v0.5 governance doc §3): concept-mode module grouping.
 * TIER_MAP semantics: 0 存在基座 / 1 动力学 / 2 显现 / 3 时间 / 4 表达 / 5 命题 / 6 治理.
 * Nodes without a tier (tier undefined) fall into the "无分组" band.
 */
export const TIER_LEGEND: { tier: number; name: string; color: string }[] = [
  { tier: 0, name: '存在基座', color: '#38bdf8' },
  { tier: 1, name: '动力学', color: '#f472b6' },
  { tier: 2, name: '显现', color: '#10b981' },
  { tier: 3, name: '时间', color: '#fbbf24' },
  { tier: 4, name: '表达', color: '#a78bfa' },
  { tier: 5, name: '命题', color: '#60a5fa' },
  { tier: 6, name: '治理', color: '#f87171' },
];

/** Sentinel band for module nodes whose tier is undefined. */
export const TIER_UNGROUPED = -1;

export const tierLegendColor = (tier: number | undefined): string => {
  if (tier === undefined) return '#6b7280';
  return TIER_LEGEND.find(t => t.tier === tier)?.color ?? '#6b7280';
};

/** Column / row spacing for concept-mode tier bands. */
export const CONCEPT_TIER_COLUMN_SPACING = 340;
export const CONCEPT_TIER_ROW_SPACING = 220;
export const CONCEPT_MODULE_Y = 240;
/**
 * Vertical band Y for each node tier (occlusion fix R1).
 * Adjacent bands keep >=100px clear height given conservative node heights
 * (L2 ~84, L3 ~64, term ~46, L4/L5 ~76 — see NODE_SIZE_ESTIMATES).
 */
export const BAND_Y = {
  L0: -260, // constraints (top)
  L1: 0,    // background root
  L2: 240,  // modules
  L3: 520,  // entries
  TERM: 800, // concept-term row
  L4: 1000, // depth-tree entries
  L5: 1200, // depth-tree grandchildren
} as const;

/** Horizontal spacing constants (occlusion fix R1/R2). */
export const MODULE_SPACING = 280;
export const MODULE_GAP = 30; // tuned 40->30 (F1 width budget; wrapped rows tightened)
export const ENTRY_SPACING = 190; // > L3 maxWidth (180) so entry bboxes never touch (F1 width budget)
export const ENTRY_HALF_WIDTH = 95; // conservative half width of an entry node (> real 90, F1 width budget)
/** Entries wrap into a grid: max ENTRIES_PER_ROW per row (black-screen width fix F1). */
export const ENTRIES_PER_ROW = 3;
/** Vertical distance between entry wrap rows (> L3 estimated height 64). */
export const ENTRY_ROW_HEIGHT = 110;
/** Depth slots (L4) wrap too: max DEPTH_SLOTS_PER_ROW slots per row. */
export const DEPTH_SLOTS_PER_ROW = 2;
/** FitView floor (black-screen fix F3): keeps nodes >= ~60px rendered width. */
export const GRAPH_MIN_ZOOM = 0.3;
export const DEPTH_SPACING = 220;
export const DEPTH_SLOT = 200;
export const TERM_SPACING = 190; // > term node width estimate (170)

/** Conservative bounding boxes per node kind (occlusion fix R6, pure layout tests).
 *  NOTE: these heights assume the 2-line CSS clamp (WebkitLineClamp: 2) applied to
 *  L1/L2/L3/term/L4 labels in toReactFlowNode — unclamped long text breaks the
 *  ENTRY_ROW_HEIGHT wrap-grid guarantee (overlap regression fix). */
export const NODE_SIZE_ESTIMATES = {
  L0: { width: 180, height: 56 },
  L1: { width: 220, height: 64 },
  L2: { width: 200, height: 84 },
  L3: { width: 180, height: 64 },
  term: { width: 170, height: 46 },
  L4: { width: 200, height: 76 },
  L5: { width: 200, height: 76 },
} as const;

/** Deterministic stacking order (occlusion fix R5): later levels above earlier ones. */
export const NODE_Z_INDEX = {
  L1: 0,
  L2: 1,
  L3: 2,
  term: 3,
  L4: 4,
  L5: 5,
  L0: 6, // constraints render on top (fixes DOM-order overlap despite top canvas position)
} as const;

/** Layout kind of a graph node (drives band / size / zIndex selection). */
export type NodeLayoutKind = keyof typeof NODE_SIZE_ESTIMATES;

export const nodeLayoutKind = (node: Pick<GraphNode, 'id' | 'level'>): NodeLayoutKind => {
  if (isConceptTermNode(node)) return 'term';
  if (isDepthNode(node.id)) return node.level === 5 ? 'L5' : 'L4';
  if (node.level <= 0) return 'L0';
  if (node.level === 1) return 'L1';
  if (node.level === 2) return 'L2';
  return 'L3';
};

/**
 * Pure tier-band layout for concept-mode module nodes (T14).
 * Each tier occupies its own vertical column (ordered tier 0→6, ungrouped last);
 * modules within a tier stack vertically. Returns id -> {x, y, tierBand}.
 */
export const layoutConceptModules = (
  modules: { id: string; tier?: number }[]
): Map<string, { x: number; y: number; tierBand: number }> => {
  const byTier = new Map<number, { id: string; tier?: number }[]>();
  modules.forEach(m => {
    const band = typeof m.tier === 'number' ? m.tier : TIER_UNGROUPED;
    if (!byTier.has(band)) byTier.set(band, []);
    byTier.get(band)!.push(m);
  });

  const bandOrder = [...byTier.keys()].sort((a, b) => {
    if (a === TIER_UNGROUPED) return 1;
    if (b === TIER_UNGROUPED) return -1;
    return a - b;
  });
  const totalWidth = (bandOrder.length - 1) * CONCEPT_TIER_COLUMN_SPACING;

  const positions = new Map<string, { x: number; y: number; tierBand: number }>();
  bandOrder.forEach((band, colIndex) => {
    const columnX = colIndex * CONCEPT_TIER_COLUMN_SPACING - totalWidth / 2;
    byTier.get(band)!.forEach((m, rowIndex) => {
      positions.set(m.id, {
        x: columnX,
        y: CONCEPT_MODULE_Y + rowIndex * CONCEPT_TIER_ROW_SPACING,
        tierBand: band,
      });
    });
  });
  return positions;
};

/**
 * Parse constraint description into display format
 * Format: "[A1] Constraint(LAW.world_structure=value)" -> "LAW.world_structure: value"
 */
const parseConstraintDescription = (description: string): { dimension: string; key: string; value: string } => {
  const match = description.match(/Constraint\((\w+)\.(\w+)=([^)]+)\)/);
  if (match) {
    return { dimension: match[1], key: match[2], value: match[3] };
  }
  // Fallback for malformed constraint strings
  const parts = description.split('=');
  if (parts.length === 2) {
    const leftParts = parts[0].split('.');
    return {
      dimension: leftParts[leftParts.length - 2] || 'UNKNOWN',
      key: leftParts[leftParts.length - 1] || 'UNKNOWN',
      value: parts[1].replace(')', '')
    };
  }
  return { dimension: 'UNKNOWN', key: 'UNKNOWN', value: description };
};

/**
 * Calculate node position based on level-based layout algorithm.
 * Y bands come from BAND_Y (R1); legacy fallback for simple/degenerate graphs
 * and direct test consumption — full overlap-free layout lives in computeNodeLayout.
 */
export const calculateNodePosition = (
  level: number,
  indexInLevel: number,
  totalInLevel: number,
  parentX?: number
): { x: number; y: number } => {
  const LEVEL_TO_BAND_Y: Record<number, number> = {
    0: BAND_Y.L0,
    1: BAND_Y.L1,
    2: BAND_Y.L2,
    3: BAND_Y.L3,
    4: BAND_Y.L4,
    5: BAND_Y.L5
  };

  const y = LEVEL_TO_BAND_Y[level] ?? 0;

  let x = 0;

  if (level === 1) {
    // Background root: center
    x = 0;
  } else if (level === 2) {
    // Modules: evenly spaced, centered
    const totalWidth = (totalInLevel - 1) * MODULE_SPACING;
    x = (indexInLevel * MODULE_SPACING) - (totalWidth / 2);
  } else if (level === 3 && parentX !== undefined) {
    // Entries: under their parent module
    const totalWidth = (totalInLevel - 1) * ENTRY_SPACING;
    x = parentX + (indexInLevel * ENTRY_SPACING) - (totalWidth / 2);
  } else if ((level === 4 || level === 5) && parentX !== undefined) {
    // Depth-tree nodes: under their parent entry (L4) / parent depth node (L5)
    const totalWidth = (totalInLevel - 1) * DEPTH_SPACING;
    x = parentX + (indexInLevel * DEPTH_SPACING) - (totalWidth / 2);
  } else if (level === 0) {
    // Constraints: evenly spaced at top
    const totalWidth = (totalInLevel - 1) * MODULE_SPACING;
    x = (indexInLevel * MODULE_SPACING) - (totalWidth / 2);
  }

  return { x, y };
};

/**
 * Pure overlap-free layout (occlusion fix R6).
 * Computes deterministic positions for every node kind; React Flow node
 * assembly (styles/labels) stays in layoutNodes — this function is the
 * testable coordinate core.
 *
 * Guarantees:
 * - R2: tree-mode module spacing adapts to each module's entry-band + depth width
 * - R3: depth groups are assigned horizontal slots per module (no cross-entry overlap)
 * - R4: concept-mode detail bands shift below the deepest tier column
 * - R5: deterministic zIndex per kind
 */
export interface NodeLayoutBox {
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
  /** Concept-mode tier band (modules only, mode='concept'). */
  tierBand?: number;
}

/** Sequential x layout, centred on 0, for items with individual half-widths.
 *  gapOf defaults to halfsum + MODULE_GAP; wrap rows pass a tighter gap
 *  (halfsum only, no module gap) to keep row width low (F1). */
const sequentialCentredXs = (
  halfWidths: number[],
  minGap: number,
  gapOf: (a: number, b: number) => number = (a, b) => Math.max(minGap, a + b + MODULE_GAP)
): number[] => {
  if (halfWidths.length === 0) return [];
  const xs: number[] = [0];
  for (let i = 1; i < halfWidths.length; i++) {
    xs.push(xs[i - 1] + gapOf(halfWidths[i - 1], halfWidths[i]));
  }
  const mean = xs.reduce((a, b) => a + b, 0) / xs.length;
  return xs.map(x => x - mean);
};

/** Balanced-centred variant: shifts so left/right extents (incl. half-widths)
 *  are symmetric — wrap rows with a wide leading item stay inside the module
 *  envelope (F1). */
const balancedCentredXs = (
  halfs: number[],
  minGap: number,
  gapOf: (a: number, b: number) => number
): number[] => {
  const xs = sequentialCentredXs(halfs, minGap, gapOf);
  if (xs.length === 0) return xs;
  const left = xs[0] - halfs[0];
  const right = xs[xs.length - 1] + halfs[halfs.length - 1];
  const shift = (left + right) / 2;
  return xs.map(x => x - shift);
};

export const computeNodeLayout = (
  nodes: GraphNode[],
  edges: GraphEdge[],
  mode: 'tree' | 'concept' = 'tree'
): Map<string, NodeLayoutBox> => {
  const boxes = new Map<string, NodeLayoutBox>();

  // Concept = module relation web (T15, aligns with governance doc T14 contract):
  // only module-level nodes participate — L2 modules + L1 root + L0 constraints.
  // L3 entries / term nodes / depth nodes produce NO box in concept mode (their
  // detail ocean drowned the tier grouping); semantic edges still render so the
  // concept view becomes a clean module relationship network. Tree mode keeps
  // rendering everything.
  if (mode === 'concept') {
    nodes = nodes.filter(n => n.level <= 2 && !isConceptTermNode(n));
  }

  const byLevel: Record<number, GraphNode[]> = {};
  nodes.forEach(n => {
    if (!byLevel[n.level]) byLevel[n.level] = [];
    byLevel[n.level].push(n);
  });

  // Parent map from tree edges (entries + depth nodes)
  const parentOf = new Map<string, string>();
  edges.forEach(e => {
    if (e.edge_type === 'tree') parentOf.set(e.to_node_id, e.from_node_id);
  });

  const modules = byLevel[2] ?? [];
  const entries = byLevel[3] ?? [];

  // --- R3: per-entry depth slot plans (L4 centers inside an entry slot) ---
  const l4ByEntry = new Map<string, GraphNode[]>();
  const l5ByL4 = new Map<string, GraphNode[]>();
  nodes.forEach(n => {
    const kind = nodeLayoutKind(n);
    if (kind !== 'L4' && kind !== 'L5') return;
    const p = parentOf.get(n.id);
    if (!p) return;
    if (kind === 'L4') {
      if (!l4ByEntry.has(p)) l4ByEntry.set(p, []);
      l4ByEntry.get(p)!.push(n);
    } else {
      if (!l5ByL4.has(p)) l5ByL4.set(p, []);
      l5ByL4.get(p)!.push(n);
    }
  });

  // Width each L4 node needs so its L5 row fits beneath it
  const l4RequiredWidth = (l4Id: string): number => {
    const l5Count = l5ByL4.get(l4Id)?.length ?? 0;
    return Math.max(DEPTH_SLOT, (l5Count - 1) * DEPTH_SPACING + DEPTH_SLOT + MODULE_GAP / 2);
  };

  const entryDepthPlan = new Map<string, { width: number; centers: number[]; rows: number[] }>();
  let maxDepthRows = 1;
  l4ByEntry.forEach((children, entryId) => {
    const reqs = children.map(c => l4RequiredWidth(c.id));
    // F1 (black-screen fix): wrap the L4 slot chain into rows of DEPTH_SLOTS_PER_ROW
    // so a wide depth fan cannot blow up the entry (and module) half width.
    const rowCount = Math.ceil(reqs.length / DEPTH_SLOTS_PER_ROW);
    const centers: number[] = [];
    const rows: number[] = [];
    let spanHalf = DEPTH_SLOT / 2;
    for (let r = 0; r < rowCount; r++) {
      const rowReqs = reqs.slice(r * DEPTH_SLOTS_PER_ROW, (r + 1) * DEPTH_SLOTS_PER_ROW);
      const xs = balancedCentredXs(
        rowReqs.map(w => w / 2),
        DEPTH_SLOT,
        (a, b) => Math.max(DEPTH_SLOT, a + b) // no module gap inside a slot row
      );
      rowReqs.forEach((_, i) => {
        centers.push(xs[i] ?? 0);
        rows.push(r);
      });
      if (xs.length > 0) {
        // True row extent half: farthest slot box edge from row centre.
        spanHalf = Math.max(
          spanHalf,
          ...xs.map((x, i) => Math.abs(x) + rowReqs[i] / 2)
        );
      }
    }
    maxDepthRows = Math.max(maxDepthRows, rowCount);
    entryDepthPlan.set(entryId, { width: spanHalf * 2, centers, rows });
  });

  const entryHalfWidth = (entryId: string): number => {
    const plan = entryDepthPlan.get(entryId);
    return Math.max(ENTRY_HALF_WIDTH, plan ? plan.width / 2 : 0);
  };

  // Entries grouped by module (orphans treated as one pseudo-module at x=0)
  const entriesByModule = new Map<string, GraphNode[]>();
  entries.forEach(e => {
    const p = parentOf.get(e.id) ?? '__orphans__';
    if (!entriesByModule.has(p)) entriesByModule.set(p, []);
    entriesByModule.get(p)!.push(e);
  });

  // Relative (module-centred) entry xs + each module's required half width.
  // F1 (black-screen fix): entries wrap into a grid of ENTRIES_PER_ROW per row
  // instead of a single long line, capping each module's half width at ~300px.
  const relEntryXs = new Map<string, { x: number; row: number }[]>(); // moduleId -> per-entry relative x + row
  const moduleHalfWidth = new Map<string, number>();
  let maxEntryRows = 1;
  entriesByModule.forEach((children, moduleId) => {
    // F1: wrap into rows of <= ENTRIES_PER_ROW; a depth-bearing entry always
    // gets an exclusive row (its L4 slot fan is wider than a shared row allows).
    const rows: GraphNode[][] = [];
    let current: GraphNode[] | null = null;
    for (const c of children) {
      const hasPlan = entryDepthPlan.has(c.id);
      if (
        !current ||
        current.length >= ENTRIES_PER_ROW ||
        hasPlan ||
        current.some(d => entryDepthPlan.has(d.id))
      ) {
        current = [c];
        rows.push(current);
      } else {
        current.push(c);
      }
    }
    maxEntryRows = Math.max(maxEntryRows, rows.length);
    const placed: { x: number; row: number }[] = [];
    let spanHalf = ENTRY_HALF_WIDTH;
    rows.forEach((row, rowIdx) => {
      const halfs = row.map(c => entryHalfWidth(c.id));
      const xs = balancedCentredXs(
        halfs,
        ENTRY_SPACING,
        (a, b) => Math.max(ENTRY_SPACING, a + b) // no module gap inside an entry row
      );
      row.forEach((c, i) => placed.push({ x: xs[i] ?? 0, row: rowIdx }));
      const rowHalf = xs.length > 0
        ? Math.max(...xs.map((x, i) => Math.abs(x) + halfs[i]))
        : ENTRY_HALF_WIDTH;
      spanHalf = Math.max(spanHalf, rowHalf);
    });
    relEntryXs.set(moduleId, placed);
    moduleHalfWidth.set(moduleId, spanHalf);
  });

  // --- R2/R4: module x placement ---
  const moduleX = new Map<string, number>();
  const moduleY = new Map<string, number>();
  let conceptPositions: Map<string, { x: number; y: number; tierBand: number }> | null = null;

  if (mode === 'concept') {
    conceptPositions = layoutConceptModules(modules);
  }

  if (mode === 'tree') {
    const xs = sequentialCentredXs(
      modules.map(m => moduleHalfWidth.get(m.id) ?? ENTRY_HALF_WIDTH),
      MODULE_SPACING,
      (a, b) => Math.max(MODULE_SPACING, a + b) // no extra gap term (F1 width budget)
    );
    modules.forEach((m, i) => {
      moduleX.set(m.id, xs[i] ?? 0);
      moduleY.set(m.id, BAND_Y.L2);
    });
  } else {
    // Concept mode: keep tier column ORDER (T14 contract) but space columns
    // dynamically so entry/depth bands of adjacent columns never overlap.
    const byBand = new Map<number, string[]>();
    modules.forEach(m => {
      const p = conceptPositions!.get(m.id);
      if (!p) return;
      if (!byBand.has(p.tierBand)) byBand.set(p.tierBand, []);
      byBand.get(p.tierBand)!.push(m.id);
    });
    // Band order follows layoutConceptModules column order (tier 0→6, ungrouped last)
    const bandIds = [...byBand.keys()].sort(
      (a, b) => conceptPositions!.get(byBand.get(a)![0])!.x - conceptPositions!.get(byBand.get(b)![0])!.x
    );
    // Fan modules within each band (centred on 0), record each band's half width
    const bandFanXs = new Map<number, number[]>();
    const bandHalfs = bandIds.map(band => {
      const ids = byBand.get(band)!;
      const halfs = ids.map(id => moduleHalfWidth.get(id) ?? ENTRY_HALF_WIDTH);
      const xs = sequentialCentredXs(
        halfs,
        MODULE_SPACING,
        (a, b) => Math.max(MODULE_SPACING, a + b) // no extra gap term (F1)
      );
      bandFanXs.set(band, xs);
      let half = ENTRY_HALF_WIDTH;
      ids.forEach((id, i) => {
        half = Math.max(half, Math.abs(xs[i] ?? 0) + halfs[i]);
      });
      return half;
    });
    // Dynamic column spacing (ordered columns, centred on 0)
    const colXs = sequentialCentredXs(
      bandHalfs,
      CONCEPT_TIER_COLUMN_SPACING,
      (a, b) => Math.max(CONCEPT_TIER_COLUMN_SPACING, a + b) // no extra gap term (F1)
    );
    bandIds.forEach((band, bi) => {
      const ids = byBand.get(band)!;
      const fanXs = bandFanXs.get(band)!;
      ids.forEach((id, i) => {
        moduleX.set(id, colXs[bi] + (fanXs[i] ?? 0));
        moduleY.set(id, conceptPositions!.get(id)!.y);
      });
    });
  }

  // --- Place modules / root / constraints ---
  const boxFor = (kind: NodeLayoutKind, x: number, y: number, tierBand?: number): NodeLayoutBox => ({
    x,
    y,
    width: NODE_SIZE_ESTIMATES[kind].width,
    height: NODE_SIZE_ESTIMATES[kind].height,
    zIndex: NODE_Z_INDEX[kind],
    ...(tierBand !== undefined ? { tierBand } : {}),
  });

  modules.forEach(m => {
    const p = conceptPositions?.get(m.id);
    boxes.set(m.id, boxFor('L2', moduleX.get(m.id) ?? 0, moduleY.get(m.id) ?? BAND_Y.L2, p?.tierBand));
  });

  (byLevel[1] ?? []).forEach((n, index) => {
    const pos = calculateNodePosition(1, index, (byLevel[1] ?? []).length);
    boxes.set(n.id, boxFor('L1', pos.x, pos.y));
  });
  const constraints = byLevel[0] ?? [];
  constraints.forEach((n, index) => {
    const pos = calculateNodePosition(0, index, constraints.length);
    boxes.set(n.id, boxFor('L0', pos.x, pos.y));
  });

  // --- R4: detail bands (shifted below the deepest tier column in concept mode) ---
  // F1: TERM/L4/L5 bands shift below the deepest entry wrap row AND the deepest
  // L4 depth wrap row (a second L4 row sits ENTRY_ROW_HEIGHT below bandY.L4).
  const entryRowDepth = (maxEntryRows - 1) * ENTRY_ROW_HEIGHT;
  const depthRowDepth = (maxDepthRows - 1) * ENTRY_ROW_HEIGHT;
  let bandTop = BAND_Y.L3 + entryRowDepth + depthRowDepth;
  if (mode === 'concept') {
    const colRowCount = new Map<number, number>();
    modules.forEach(m => {
      const p = conceptPositions!.get(m.id);
      if (!p) return;
      colRowCount.set(p.tierBand, (colRowCount.get(p.tierBand) ?? 0) + 1);
    });
    const maxRowCount = colRowCount.size > 0 ? Math.max(...colRowCount.values()) : 1;
    bandTop = Math.max(
      bandTop,
      CONCEPT_MODULE_Y + (maxRowCount - 1) * CONCEPT_TIER_ROW_SPACING + 180 + entryRowDepth + depthRowDepth
    );
  }
  const bandY = {
    L3: bandTop,
    // F1: TERM must clear the deepest entry wrap row; L4 must clear TERM;
    // L5 keeps >= one L4 wrap row + node height above its floor.
    TERM: bandTop + Math.max(
      BAND_Y.TERM - BAND_Y.L3,
      entryRowDepth + NODE_SIZE_ESTIMATES.L3.height + 16
    ),
    L4: bandTop + Math.max(
      BAND_Y.L4 - BAND_Y.L3,
      entryRowDepth + NODE_SIZE_ESTIMATES.L3.height + 16 + NODE_SIZE_ESTIMATES.term.height + 40
    ),
    L5: bandTop + Math.max(
      BAND_Y.L5 - BAND_Y.L3,
      entryRowDepth + NODE_SIZE_ESTIMATES.L3.height + 16 + NODE_SIZE_ESTIMATES.term.height + 40
        + ENTRY_ROW_HEIGHT + NODE_SIZE_ESTIMATES.L4.height
    ),
  };

  // --- Entries under their module, wrapped into rows (F1) ---
  // Track each entry's wrap row so its L4 children can follow it vertically
  // (exclusive-row layout: same-module depth-bearing entries share x).
  const entryRowOf = new Map<string, number>();
  entriesByModule.forEach((children, moduleId) => {
    const baseX = moduleId === '__orphans__' ? 0 : (moduleX.get(moduleId) ?? 0);
    const placed = relEntryXs.get(moduleId) ?? [];
    children.forEach((c, i) => {
      const p = placed[i] ?? { x: 0, row: 0 };
      entryRowOf.set(c.id, p.row);
      boxes.set(c.id, boxFor('L3', baseX + p.x, bandY.L3 + p.row * ENTRY_ROW_HEIGHT));
    });
  });

  // --- Term row ---
  const termNodes = nodes.filter(n => nodeLayoutKind(n) === 'term');
  if (termNodes.length > 0) {
    const totalWidth = (termNodes.length - 1) * TERM_SPACING;
    termNodes.forEach((n, index) => {
      boxes.set(n.id, boxFor('term', index * TERM_SPACING - totalWidth / 2, bandY.TERM));
    });
  }

  // --- R3: depth slots (L4 within their entry's slot, wrapped into rows F1) ---
  // centers[] are row-centred on the entry x (each wrap row is centred independently).
  const l4RowY = new Map<string, number>();
  entries.forEach(entry => {
    const plan = entryDepthPlan.get(entry.id);
    const entryBox = boxes.get(entry.id);
    if (!plan || !entryBox) return;
    const children = l4ByEntry.get(entry.id)!;
    const entryWrapRow = entryRowOf.get(entry.id) ?? 0;
    children.forEach((c, i) => {
      // y follows BOTH the parent entry's wrap row AND the slot's own wrap row
      const y = bandY.L4 + (entryWrapRow + (plan.rows[i] ?? 0)) * ENTRY_ROW_HEIGHT;
      l4RowY.set(c.id, y);
      boxes.set(c.id, boxFor('L4', entryBox.x + plan.centers[i], y));
    });
  });

  // --- L5 under their L4 parent (following its wrap row); y offset clears the
  // next L4 wrap row (ENTRY_ROW_HEIGHT + L4 height) so rows never collide ---
  const L5_ROW_OFFSET = ENTRY_ROW_HEIGHT + NODE_SIZE_ESTIMATES.L4.height;
  l5ByL4.forEach((children, l4Id) => {
    const parentBox = boxes.get(l4Id);
    if (!parentBox) return;
    const py = l4RowY.get(l4Id) ?? bandY.L4;
    const y = Math.max(bandY.L5, py + L5_ROW_OFFSET);
    const totalWidth = (children.length - 1) * DEPTH_SPACING;
    children.forEach((c, index) => {
      boxes.set(c.id, boxFor('L5', parentBox.x + index * DEPTH_SPACING - totalWidth / 2, y));
    });
  });

  return boxes;
};

export function A1KnowledgeGraph({ 
  graph, 
  isLoading, 
  error, 
  onRetry, 
  fileId, 
  edgeStats, 
  openQuestions = [],
  onRefresh,
  viewMode: viewModeProp,
  onViewModeChange,
  onEdgeFocus,
  focusEdgeKey = null,
  hoverEdgeKey = null,
  conceptTerms,
}: A1KnowledgeGraphProps) {
  // View mode state: 'tree' | 'concept' (controlled when viewModeProp provided)
  const [internalViewMode, setInternalViewMode] = useState<'tree' | 'concept'>('tree');
  const viewMode = viewModeProp ?? internalViewMode;
  const setViewMode = (mode: 'tree' | 'concept') => {
    if (onViewModeChange) {
      onViewModeChange(mode);
    } else {
      setInternalViewMode(mode);
    }
  };
  const isControlled = viewModeProp !== undefined;
  
  // Filter state
  const [filters, setFilters] = useState({
    confidence: [] as ('rule' | 'semantic' | 'structure')[],
    status: [] as ('confirmed' | 'pending' | 'rejected')[]
  });
  
  // Edge hover state for highlighting
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);
  
  // Review card state
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [showRejectConfirm, setShowRejectConfirm] = useState(false);
  
  // Stats from props or derived from graph
  const stats = useMemo(() => {
    if (edgeStats) {
      return edgeStats;
    }
    if (!graph) {
      return {
        semantic_total: 0,
        semantic_confirmed: 0,
        rule_total: 0,
        structure_total: 0,
        pending_review: 0
      };
    }
    // Derive from graph edges
    const semanticEdges = graph.edges.filter(e => e.confidence === 'semantic');
    const ruleEdges = graph.edges.filter(e => e.confidence === 'rule');
    const structureEdges = graph.edges.filter(e => e.confidence === 'structure');
    const pendingEdges = graph.edges.filter(e => e.confidence === 'semantic' && e.confirmed === false);
    
    return {
      semantic_total: semanticEdges.length,
      semantic_confirmed: semanticEdges.filter(e => e.confirmed).length,
      rule_total: ruleEdges.length,
      structure_total: structureEdges.length,
      pending_review: pendingEdges.length
    };
  }, [graph, edgeStats]);
  /**
   * Transform GraphNode to ReactFlow Node with styling based on level
   */
  const toReactFlowNode = useCallback((node: GraphNode): Node => {
    const isConstraint = node.id.startsWith('cst_') || node.level === 0;
    const isTerm = isConceptTermNode(node);
    const isDepth = isDepthNode(node.id);

    // T-D: unconfirmed concept term -> semi-transparent + dashed border
    const termMeta = conceptTerms?.find(t => node.id === `term:${t.term}`);
    const isUnconfirmedTerm = isTerm && termMeta !== undefined && !termMeta.confirmed;

    let nodeStyle: React.CSSProperties = {};
    let label = '';
    /** Full text shown via title tooltip (LLM summaries / depth entries). */
    let tooltip: string | undefined;
    /** Extra style applied to the label wrapper (e.g. 2-line clamp for L2 summaries). */
    let labelExtraStyle: React.CSSProperties = {};

    if (isTerm) {
      // Concept-term node: small circular dot + word label, clustered by module palette
      const clusterColor = termClusterColor(node.id);
      nodeStyle = {
        border: isUnconfirmedTerm
          ? `1.5px dashed ${clusterColor}`
          : `1.5px solid ${clusterColor}`,
        backgroundColor: 'rgba(19, 19, 42, 0.85)',
        borderRadius: '9999px',
        padding: '4px 12px',
        fontSize: '12px',
        opacity: isUnconfirmedTerm ? 0.5 : 1,
        boxShadow: `0 0 6px ${clusterColor}40`
      };
      label = `● ${node.description}`;
      // 2-line clamp keeps term nodes within NODE_SIZE_ESTIMATES.term.height.
      tooltip = node.description;
      labelExtraStyle = {
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden'
      };
    } else if (isDepth) {
      // v0.5 depth-tree node (level 4): thin cluster-colored border, content = LLM entry description
      const clusterColor = termClusterColor(node.id);
      nodeStyle = {
        border: `1px solid ${clusterColor}`,
        backgroundColor: 'rgba(19, 19, 42, 0.7)',
        borderRadius: '4px',
        padding: '6px 8px',
        minWidth: '140px',
        maxWidth: '200px',
        fontSize: '12px',
        boxShadow: `0 0 4px ${clusterColor}30`
      };
      label = `▸ ${node.description}`;
      tooltip = node.description;
      // 2-line clamp keeps the rendered height <= NODE_SIZE_ESTIMATES.L4.height
      // (long LLM entry descriptions would otherwise stretch the node and break
      // the ENTRY_ROW_HEIGHT wrap-grid guarantee).
      labelExtraStyle = {
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden'
      };
    } else if (node.level === 1) {
      // Background root node: golden border
      nodeStyle = {
        border: '2px solid var(--color-stardust-400)',
        backgroundColor: 'rgba(19, 19, 42, 0.95)',
        borderRadius: '8px',
        padding: '12px',
        minWidth: '200px',
        boxShadow: '0 0 10px rgba(251, 191, 36, 0.3)'
      };
      label = `✦ ${node.description}`;
      // Defensive clamp: L1 descriptions (LLM summaries) can be long; keep the
      // node within its NODE_SIZE_ESTIMATES.L1 box (maxWidth 260 + 2-line clamp).
      tooltip = node.description;
      nodeStyle.maxWidth = '260px';
      labelExtraStyle = {
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden'
      };
    } else if (node.level === 2) {
      // Module node: purple border
      nodeStyle = {
        border: '2px solid rgba(167, 139, 250, 0.6)',
        backgroundColor: 'rgba(28, 28, 61, 0.8)',
        borderRadius: '6px',
        padding: '10px',
        minWidth: '160px',
        boxShadow: '0 0 8px rgba(139, 92, 246, 0.2)'
      };
      label = `▤ ${node.description}`;
      tooltip = node.description;
      // LLM summary: clamp to 2 lines, full text in tooltip
      labelExtraStyle = {
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden'
      };
    } else if (node.level === 3) {
      // Entry node: thin white border, parse description
      const parts = node.description.split(':');
      if (parts.length >= 2) {
        const entryLabel = parts[0].trim();
        const entryValue = parts.slice(1).join(':').trim();
        nodeStyle = {
          border: '1px solid rgba(255, 255, 255, 0.15)',
          backgroundColor: 'rgba(19, 19, 42, 0.7)',
          borderRadius: '4px',
          padding: '8px',
          minWidth: '140px',
          maxWidth: '180px',
          fontSize: '13px'
        };
        label = `· ${entryLabel}: ${entryValue}`;
        // 2-line clamp + tooltip: real-data entry values are 50-100 char sentences;
        // without clamping the node grows to 200px+ and breaks the wrap grid.
        tooltip = node.description;
        labelExtraStyle = {
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        };
      } else {
        nodeStyle = {
          border: '1px solid rgba(255, 255, 255, 0.15)',
          backgroundColor: 'rgba(19, 19, 42, 0.7)',
          borderRadius: '4px',
          padding: '8px',
          minWidth: '140px',
          maxWidth: '180px'
        };
        label = `· ${node.description}`;
        tooltip = node.description;
        labelExtraStyle = {
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        };
      }
    } else if (isConstraint) {
      // Constraint node: amber border
      const parsed = parseConstraintDescription(node.description);
      nodeStyle = {
        border: '2px solid rgba(245, 158, 11, 0.6)',
        backgroundColor: 'rgba(28, 28, 61, 0.8)',
        borderRadius: '6px',
        padding: '8px',
        minWidth: '160px',
        fontSize: '12px',
        boxShadow: '0 0 8px rgba(245, 158, 11, 0.2)'
      };
      label = `⚙ [${parsed.dimension}] ${parsed.key}: ${parsed.value}`;
    }

    return {
      id: node.id,
      type: 'default',
      position: { x: 0, y: 0 }, // Will be set by layout
      className: isTerm ? 'concept-term-node' : undefined,
      data: {
        label: (
          <div
            title={tooltip}
            style={{
              color: 'white',
              fontFamily: 'ui-sans-serif, system-ui, sans-serif',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              ...labelExtraStyle
            }}
          >
            {label}
          </div>
        )
      },
      style: nodeStyle
    };
  }, [conceptTerms]);

  /**
   * Transform GraphEdge to ReactFlow Edge with concept network styling
   */
  const toReactFlowEdge = useCallback((edge: GraphEdge): Edge => {
    const isTree = edge.edge_type === 'tree';
    const isSemantic = edge.confidence === 'semantic';
    const isRule = edge.confidence === 'rule';
    const isStructure = edge.confidence === 'structure';
    const isConfirmed = edge.confirmed === true;
    const isPending = edge.confidence === 'semantic' && edge.confirmed === false;

    let edgeStyle: React.CSSProperties = {};
    let animated = false;
    let label: string | undefined = undefined;
    let labelStyle: React.CSSProperties = {};
    let className = '';

    if (isTree) {
      // TREE: purple solid line (unchanged)
      edgeStyle = {
        stroke: '#a78bfa',
        strokeWidth: 2,
        strokeDasharray: undefined
      };
      className = 'edge-tree';
    } else if (isPending) {
      // ◆ semantic pending: amber dashed + breathing animation + ? badge
      edgeStyle = {
        stroke: '#f59e0b',
        strokeWidth: 1.5,
        strokeDasharray: '6,4',
        animation: 'breathing 2s ease-in-out infinite'
      };
      animated = true;
      label = `? ${edge.relation || edge.visual_description}`;
      labelStyle = {
        fontSize: '11px',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        fill: '#f59e0b',
        fontWeight: 'bold'
      };
      className = 'edge-semantic-pending';
    } else if (isSemantic && isConfirmed) {
      // ◆ semantic confirmed: amber solid
      edgeStyle = {
        stroke: '#f59e0b',
        strokeWidth: 2,
        strokeDasharray: undefined
      };
      label = edge.relation || edge.visual_description;
      labelStyle = {
        fontSize: '11px',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        fill: '#f59e0b'
      };
      className = 'edge-semantic-confirmed';
    } else if (isRule) {
      // ★ rule: green dotted + relation label
      edgeStyle = {
        stroke: '#10b981',
        strokeWidth: 1.5,
        strokeDasharray: '2,2'
      };
      label = `★ ${edge.relation || edge.visual_description}`;
      labelStyle = {
        fontSize: '11px',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        fill: '#10b981',
        fontWeight: 'bold'
      };
      className = 'edge-rule';
    } else if (isStructure) {
      // ◇ structure: blue-gray line
      edgeStyle = {
        stroke: '#6b7280',
        strokeWidth: 1.5,
        strokeDasharray: undefined
      };
      label = `◇ ${edge.relation || edge.visual_description}`;
      labelStyle = {
        fontSize: '10px',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        fill: '#6b7280'
      };
      className = 'edge-structure';
    } else {
      // CROSS (legacy): amber dashed
      edgeStyle = {
        stroke: '#f59e0b',
        strokeWidth: 1.5,
        strokeDasharray: '6,4'
      };
      label = edge.visual_description;
      labelStyle = {
        fontSize: '10px',
        fontFamily: 'ui-monospace, Consolas, monospace',
        fill: '#888'
      };
      className = 'edge-cross';
    }

    // Apply hover dimming effect (canvas hover + panel entry hover merged)
    const activeHover = hoverEdgeKey ?? hoveredEdge;
    const isFocused = focusEdgeKey && conceptEdgeKey(edge) === focusEdgeKey;
    const edgeKeyId = conceptEdgeKey(edge);
    const isDimmed = activeHover && activeHover !== edgeKeyId && activeHover !== `${edge.from_node_id}-${edge.to_node_id}`;
    if (isFocused) {
      edgeStyle.stroke = '#34d399';
      edgeStyle.strokeWidth = 3;
    } else if (isDimmed && activeHover) {
      edgeStyle.opacity = '0.2';
      edgeStyle.stroke = '#444';
    }

    return {
      id: `${edge.from_node_id}-${edge.to_node_id}`,
      source: edge.from_node_id,
      target: edge.to_node_id,
      type: 'smoothstep',
      animated,
      style: edgeStyle,
      label,
      labelStyle,
      className,
      data: {
        ...edge,
        edgeKey: edgeKeyId,
        onEdgeClick: () => handleEdgeClick(edge)
      }
    };
  }, [hoveredEdge, hoverEdgeKey, focusEdgeKey]);

  /**
   * Calculate layout positions for all nodes.
   * Coordinates/zIndex come from the pure computeNodeLayout (occlusion fix R1-R5);
   * this wrapper only assembles React Flow nodes.
   */
  const layoutNodes = useCallback((
    nodes: GraphNode[],
    edges: GraphEdge[],
    mode: 'tree' | 'concept' = 'tree'
  ): Node[] => {
    const layout = computeNodeLayout(nodes, edges, mode);

    const positionedNodes: Node[] = [];
    nodes.forEach(node => {
      const box = layout.get(node.id);
      if (!box) return;
      const rfNode = toReactFlowNode(node);
      rfNode.position = { x: box.x, y: box.y };
      rfNode.zIndex = box.zIndex; // R5: deterministic stacking (L1→L0 top)
      if (box.tierBand !== undefined) {
        // T14: preserve tier-group test hooks
        rfNode.data = { ...rfNode.data, testId: `tier-group-${box.tierBand}` };
      }
      positionedNodes.push(rfNode);
    });

    return positionedNodes;
  }, [toReactFlowNode]);

  /**
   * Handle edge click - panel focus mode (T-C) or legacy review card
   */
  const handleEdgeClick = useCallback((edge: GraphEdge) => {
    if (onEdgeFocus) {
      onEdgeFocus(conceptEdgeKey(edge));
      return;
    }
    setSelectedEdge(edge);
  }, [onEdgeFocus]);

  /**
   * Handle edge confirm
   */
  const handleConfirmEdge = useCallback(async () => {
    if (!selectedEdge || !fileId) return;
    
    const edgeKey = conceptEdgeKey(selectedEdge);
    try {
      await confirmEdge(fileId, edgeKey);
      setSelectedEdge(null);
      onRefresh?.();
    } catch (error) {
      console.error('Failed to confirm edge:', error);
    }
  }, [selectedEdge, fileId, onRefresh]);

  /**
   * Handle edge reject (with confirmation)
   */
  const handleRejectEdge = useCallback(async () => {
    if (!selectedEdge || !fileId) return;
    
    if (!showRejectConfirm) {
      setShowRejectConfirm(true);
      return;
    }
    
    const edgeKey = conceptEdgeKey(selectedEdge);
    try {
      await rejectEdge(fileId, edgeKey);
      setSelectedEdge(null);
      setShowRejectConfirm(false);
      onRefresh?.();
    } catch (error) {
      console.error('Failed to reject edge:', error);
    }
  }, [selectedEdge, fileId, showRejectConfirm, onRefresh]);

  /**
   * Apply filters to edges
   */
  const filteredEdges = useMemo(() => {
    if (!graph) return [];
    
    return graph.edges.filter(edge => {
      // Default filter: show confirmed + pending, hide rejected
      const showByDefault = edge.confirmed !== false || edge.confidence === 'semantic';
      
      // Confidence filter
      if (filters.confidence.length > 0 && !filters.confidence.includes(edge.confidence as any)) {
        return false;
      }
      
      // Status filter
      if (filters.status.length > 0) {
        const isConfirmed = edge.confirmed === true;
        const isPending = edge.confidence === 'semantic' && edge.confirmed === false;
        const isRejected = false; // We'll need to track rejected edges separately
        
        if (filters.status.includes('confirmed') && !isConfirmed) return false;
        if (filters.status.includes('pending') && !isPending) return false;
        if (filters.status.includes('rejected') && !isRejected) return false;
      }
      
      return showByDefault;
    });
  }, [graph, filters]);

  /**
   * Memoize flow nodes and edges from graph data
   */
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!graph) {
      return { flowNodes: [], flowEdges: [] };
    }

    const graphNodes = Object.values(graph.nodes);
    const edgesToUse = viewMode === 'concept' ? filteredEdges : graph.edges;
    const flowEdges = edgesToUse.map(toReactFlowEdge);
    const flowNodes = layoutNodes(graphNodes, edgesToUse, viewMode);

    return { flowNodes, flowEdges };
  }, [graph, toReactFlowEdge, layoutNodes, viewMode, filteredEdges]);

  /**
   * Loading state
   */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-stardust-400 text-sm">构建知识图谱中...</p>
        </div>
      </div>
    );
  }

  /**
   * Error state
   */
  if (error) {
    return (
      <div className="glass-panel p-6 m-4 flex flex-col items-center gap-4">
        <p className="text-cosmos-error text-center">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-nebula-500 hover:bg-nebula-400 text-white rounded-md transition-colors"
          >
            重试
          </button>
        )}
      </div>
    );
  }

  /**
   * Empty state
   */
  if (!graph) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <p className="text-void-400 text-sm">暂无图谱数据</p>
      </div>
    );
  }

  /**
   * Render React Flow graph
   */
  return (
    <div className="relative h-full w-full">
      {/* Top control bar */}
      <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between gap-4">
        {/* View toggle tabs (hidden in controlled fullscreen mode — tabs live in parent toolbar) */}
        {!isControlled && (
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('tree')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'tree'
                ? 'bg-nebula-500 text-white'
                : 'bg-void-800 text-void-400 hover:bg-void-700'
            }`}
          >
            行政树
          </button>
          <button
            onClick={() => setViewMode('concept')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'concept'
                ? 'bg-nebula-500 text-white'
                : 'bg-void-800 text-void-400 hover:bg-void-700'
            }`}
          >
            概念网
          </button>
        </div>
        )}

        {/* Statistics bar (hidden in controlled mode — shown in parent toolbar) */}
        {!isControlled && (
        <div className="flex items-center gap-4 text-sm">
          {stats.pending_review > 0 && (
            <div className="flex items-center gap-2 px-3 py-1 bg-amber-900/30 border border-amber-500/30 rounded-md">
              <span className="text-amber-400">待确认边</span>
              <span className="text-amber-300 font-bold">{stats.pending_review}</span>
            </div>
          )}
          {(() => {
            // P0: 只把 pending/asked 算作「待问」
            const pendingOpenQuestions = openQuestions.filter(
              (q) => q.status === 'pending' || q.status === 'asked'
            );
            return pendingOpenQuestions.length > 0 ? (
              <div className="flex items-center gap-2 px-3 py-1 bg-blue-900/30 border border-blue-500/30 rounded-md">
                <span className="text-blue-400">待问</span>
                <span className="text-blue-300 font-bold">{pendingOpenQuestions.length}</span>
              </div>
            ) : null;
          })()}
        </div>
        )}

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-green-400">★</span>
            <span className="text-void-400">铁律推断</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-amber-400">◆</span>
            <span className="text-void-400">联想</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">◇</span>
            <span className="text-void-400">结构拆解</span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-3 rounded-sm"
              style={{ backgroundColor: 'transparent', border: `1px solid ${TERM_CLUSTER_COLORS[0]}` }}
            />
            <span className="text-void-400">分条目</span>
          </div>
        </div>
      </div>

      {/* Tier band legend (concept mode, T14): 7 tier colors + 无分组 */}
      {viewMode === 'concept' && (
        <div
          className="absolute top-16 right-4 z-10 flex flex-col gap-1 p-3 bg-void-900/90 border border-void-700 rounded-md backdrop-blur-sm"
          data-testid="tier-legend"
        >
          <div className="text-xs text-void-400 font-medium mb-1">层级带</div>
          {TIER_LEGEND.map(({ tier, name, color }) => (
            <div key={tier} className="flex items-center gap-2 text-xs">
              <span
                className="inline-block w-3 h-3 rounded-sm"
                style={{ backgroundColor: 'transparent', border: `1.5px solid ${color}` }}
              />
              <span className="text-void-400">{`tier ${tier} · ${name}`}</span>
            </div>
          ))}
          <div className="flex items-center gap-2 text-xs">
            <span
              className="inline-block w-3 h-3 rounded-sm"
              style={{ backgroundColor: 'transparent', border: '1.5px dashed #6b7280' }}
            />
            <span className="text-void-400">无分组</span>
          </div>
          {filteredEdges.filter(e => e.confidence === 'semantic').length === 0 && (
            <div
              className="text-xs text-void-400/70 italic mt-1 border-t border-void-700 pt-2"
              data-testid="no-semantic-edges-hint"
            >
              本轮无语义边（定稿降级或暂无派生关系）
            </div>
          )}
        </div>
      )}

      {/* Filter controls (concept mode only) */}
      {viewMode === 'concept' && (
        <div className="absolute top-16 left-4 z-10 flex flex-col gap-2 p-3 bg-void-900/90 border border-void-700 rounded-md backdrop-blur-sm">
          <div className="text-xs text-void-400 font-medium mb-1">可信级</div>
          <button
            type="button"
            onClick={() => setFilters(prev => ({
              ...prev,
              confidence: prev.confidence.includes('rule')
                ? prev.confidence.filter(c => c !== 'rule')
                : [...prev.confidence, 'rule'],
            }))}
            className={`px-2 py-1 rounded text-xs border transition-colors ${
              filters.confidence.includes('rule')
                ? 'bg-emerald-900/60 border-emerald-500 text-emerald-300'
                : 'bg-void-800 border-void-600 text-void-300 hover:border-void-400'
            }`}
            aria-pressed={filters.confidence.includes('rule')}
          >
            ★ 规则
          </button>
          <button
            type="button"
            onClick={() => setFilters(prev => ({
              ...prev,
              confidence: prev.confidence.includes('semantic')
                ? prev.confidence.filter(c => c !== 'semantic')
                : [...prev.confidence, 'semantic'],
            }))}
            className={`px-2 py-1 rounded text-xs border transition-colors ${
              filters.confidence.includes('semantic')
                ? 'bg-amber-900/60 border-amber-500 text-amber-300'
                : 'bg-void-800 border-void-600 text-void-300 hover:border-void-400'
            }`}
            aria-pressed={filters.confidence.includes('semantic')}
          >
            ◆ 语义
          </button>
          <button
            type="button"
            onClick={() => setFilters(prev => ({
              ...prev,
              confidence: prev.confidence.includes('structure')
                ? prev.confidence.filter(c => c !== 'structure')
                : [...prev.confidence, 'structure'],
            }))}
            className={`px-2 py-1 rounded text-xs border transition-colors ${
              filters.confidence.includes('structure')
                ? 'bg-gray-700/60 border-gray-500 text-gray-300'
                : 'bg-void-800 border-void-600 text-void-300 hover:border-void-400'
            }`}
            aria-pressed={filters.confidence.includes('structure')}
          >
            ◇ 结构
          </button>
          
          <div className="text-xs text-void-400 font-medium mb-1 mt-2">状态</div>
          <button
            type="button"
            onClick={() => setFilters(prev => ({
              ...prev,
              status: prev.status.includes('confirmed')
                ? prev.status.filter(s => s !== 'confirmed')
                : [...prev.status, 'confirmed'],
            }))}
            className={`px-2 py-1 rounded text-xs border transition-colors ${
              filters.status.includes('confirmed')
                ? 'bg-blue-900/60 border-blue-500 text-blue-300'
                : 'bg-void-800 border-void-600 text-void-300 hover:border-void-400'
            }`}
            aria-pressed={filters.status.includes('confirmed')}
          >
            已确认
          </button>
          <button
            type="button"
            onClick={() => setFilters(prev => ({
              ...prev,
              status: prev.status.includes('pending')
                ? prev.status.filter(s => s !== 'pending')
                : [...prev.status, 'pending'],
            }))}
            className={`px-2 py-1 rounded text-xs border transition-colors ${
              filters.status.includes('pending')
                ? 'bg-amber-900/60 border-amber-500 text-amber-300'
                : 'bg-void-800 border-void-600 text-void-300 hover:border-void-400'
            }`}
            aria-pressed={filters.status.includes('pending')}
          >
            待确认
          </button>
        </div>
      )}

      {/* Edge review card */}
      {selectedEdge && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 w-96">
          <div className="glass-panel p-4 rounded-lg border border-amber-500/30 shadow-xl">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="text-sm font-medium text-amber-400 mb-1">
                  ◆ 语义边待确认
                </div>
                <div className="text-xs text-void-400 mb-2">
                  {selectedEdge.relation || selectedEdge.visual_description}
                </div>
                <div className="text-xs text-void-300 leading-relaxed">
                  推理依据：{selectedEdge.visual_description}
                </div>
              </div>
              <button
                onClick={() => setSelectedEdge(null)}
                className="text-void-400 hover:text-white transition-colors"
              >
                ✕
              </button>
            </div>
            
            {!showRejectConfirm ? (
              <div className="flex gap-2">
                <button
                  onClick={handleConfirmEdge}
                  className="flex-1 px-3 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-md transition-colors"
                >
                  ✓ 确认
                </button>
                <button
                  onClick={handleRejectEdge}
                  className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-500 text-white text-sm rounded-md transition-colors"
                >
                  ✗ 删除
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="text-xs text-red-400 font-medium">
                  ⚠ 二次确认：确定要删除这条边吗？
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleRejectEdge}
                    className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-500 text-white text-sm rounded-md transition-colors"
                  >
                    确认删除
                  </button>
                  <button
                    onClick={() => setShowRejectConfirm(false)}
                    className="flex-1 px-3 py-2 bg-void-700 hover:bg-void-600 text-white text-sm rounded-md transition-colors"
                  >
                    取消
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        fitViewOptions={{ minZoom: GRAPH_MIN_ZOOM, padding: 0.15 }}
        elevateNodesOnSelect
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        edgesFocusable={true}
        panOnScroll
        zoomOnScroll
        minZoom={GRAPH_MIN_ZOOM}
        maxZoom={1.5}
        onEdgeMouseEnter={(_, edge) => {
          setHoveredEdge(edge.id);
        }}
        onEdgeMouseLeave={() => {
          setHoveredEdge(null);
        }}
        onEdgeClick={(_edgeEvent, edge) => {
          const graphEdge = graph?.edges.find(ge => 
            `${ge.from_node_id}-${ge.to_node_id}` === edge.id
          );
          if (graphEdge) {
            handleEdgeClick(graphEdge);
          }
        }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="rgba(255,255,255,0.1)" />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const nodeData = graph?.nodes[node.id];
            if (!nodeData) return '#a78bfa';

            if (nodeData.level === 1) return 'var(--color-stardust-400)';
            if (nodeData.level === 2) return 'var(--color-nebula-400)';
            if (isConceptTermNode(nodeData)) return termClusterColor(nodeData.id);
            if (isDepthNode(nodeData.id)) return termClusterColor(nodeData.id);
            if (nodeData.level === 3 || nodeData.id.startsWith('cst_')) return '#ffffff';
            return '#a78bfa';
          }}
          maskColor="rgba(19, 19, 42, 0.8)"
        />
      </ReactFlow>

      {/* CSS animations */}
      <style>{`
        @keyframes breathing {
          0%, 100% {
            stroke-opacity: 1;
            stroke-width: 1.5;
          }
          50% {
            stroke-opacity: 0.6;
            stroke-width: 1.0;
          }
        }
        
        .edge-semantic-pending {
          animation: breathing 2s ease-in-out infinite;
        }

        @keyframes edge-review-flash {
          0%, 100% { background-color: transparent; }
          30% { background-color: rgba(52, 211, 153, 0.35); }
        }
        .edge-review-flash {
          animation: edge-review-flash 0.8s ease-in-out 2;
        }
      `}</style>
    </div>
  );
}
