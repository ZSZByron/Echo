"""Serial wave-based generation scheduler for graph-driven asset pipeline.

Schedules image generation across a knowledge graph by processing dependency
waves serially while parallelizing independent nodes within each wave.

Flow:
  1. Validate graph has no cycles (via cycle_detector).
  2. Get wave-based ordering (via topo_sort).
  3. For each wave, run nodes in parallel with asyncio.gather.
  4. Build prompts via PromptFusion, generate via ImageGenerator.
  5. Track completed node IDs as references for downstream waves.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from app.ai.image_generator import ImageGenerator
from app.services.prompt_fusion import PromptFusion

if TYPE_CHECKING:
    from app.models.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)

# Path to graph_algorithm test modules (topo_sort, cycle_detector, serial_parser)
_GRAPH_ALGO_DIR = str(Path(__file__).resolve().parents[2] / "tests" / "graph_algorithm")


def _import_topo_sort():
    """Lazy-import topo_sort.get_generation_waves."""
    if _GRAPH_ALGO_DIR not in sys.path:
        sys.path.insert(0, _GRAPH_ALGO_DIR)
    import topo_sort

    return topo_sort


def _import_cycle_detector():
    """Lazy-import cycle_detector.validate_graph."""
    if _GRAPH_ALGO_DIR not in sys.path:
        sys.path.insert(0, _GRAPH_ALGO_DIR)
    import cycle_detector

    return cycle_detector


class GenerationScheduler:
    """Wave-based serial scheduler for knowledge graph image generation.

    Processes waves sequentially; within each wave, nodes are generated in
    parallel (bounded by a semaphore).
    """

    def __init__(self, max_concurrency: int = 3) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run_generation(self, graph: KnowledgeGraph) -> dict:
        """Execute generation for all nodes in the graph.

        Args:
            graph: Knowledge graph with nodes, edges, background_node_id.

        Returns:
            Dict with keys: total, succeeded, failed, order.
            On cycle detection: succeeded=0, error key present.
        """
        from app.models.knowledge_graph import NodeStatus

        total = len(graph.nodes)

        # ── Step 1: Cycle detection ────────────────────────────────
        cycle_detector_mod = _import_cycle_detector()
        is_valid, cycles = cycle_detector_mod.validate_graph(graph)
        if not is_valid:
            logger.error("Graph validation failed: %d cycle(s) found", len(cycles))
            return {
                "total": total,
                "succeeded": 0,
                "failed": total,
                "order": [],
                "error": f"Graph contains {len(cycles)} cycle(s)",
            }

        # ── Step 2: Get wave ordering ──────────────────────────────
        topo_sort_mod = _import_topo_sort()
        try:
            waves = topo_sort_mod.get_generation_waves(graph)
        except ValueError as exc:
            return {
                "total": total,
                "succeeded": 0,
                "failed": total,
                "order": [],
                "error": str(exc),
            }

        # ── Step 3–4: Execute waves serially ──────────────────────
        prompt_fusion = PromptFusion()
        generator = ImageGenerator()

        completed_node_ids: list[str] = []
        succeeded = 0
        failed = 0
        order: list[str] = []

        try:
            for wave_idx, wave in enumerate(waves):
                logger.info("Wave %d: %s", wave_idx, wave)
                results = await asyncio.gather(
                    *(
                        self._generate_node(
                            node_id=node_id,
                            graph=graph,
                            prompt_fusion=prompt_fusion,
                            generator=generator,
                            completed_node_ids=completed_node_ids,
                        )
                        for node_id in wave
                    ),
                    return_exceptions=True,
                )

                for node_id, result in zip(wave, results):
                    order.append(node_id)
                    if isinstance(result, Exception):
                        logger.warning("Node %s failed: %s", node_id, result)
                        graph.nodes[node_id].status = NodeStatus.FAILED
                        failed += 1
                    else:
                        completed_node_ids.append(node_id)
                        graph.nodes[node_id].status = NodeStatus.COMPLETED
                        succeeded += 1
        finally:
            await generator.close()

        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "order": order,
        }

    async def _generate_node(
        self,
        node_id: str,
        graph: KnowledgeGraph,
        prompt_fusion: PromptFusion,
        generator: ImageGenerator,
        completed_node_ids: list[str],
    ) -> str:
        """Generate images for a single node.

        Builds prompt via PromptFusion using completed nodes as context,
        calls ImageGenerator with reference_asset_ids from all prior
        completed nodes.

        Returns node_id on success. Raises on failure.
        """
        from app.models.knowledge_graph import NodeStatus

        async with self._semaphore:
            node = graph.nodes[node_id]
            node.status = NodeStatus.GENERATING

            # Build completed_nodes dict for prompt fusion
            completed_nodes = {
                nid: graph.nodes[nid]
                for nid in completed_node_ids
                if nid in graph.nodes
            }

            prompt = prompt_fusion.build_prompt(node, graph, completed_nodes)

            await generator.generate(
                prompt=prompt,
                asset_id=node_id,
                reference_asset_ids=list(completed_node_ids),
            )

            return node_id
