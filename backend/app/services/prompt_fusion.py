"""Prompt fusion service for graph-driven asset pipeline.

Assembles 3-section image generation prompts by fusing a target node's
description with completed dependency edges and the background node's
visual context.

Sections:
  1. Subject — the target node's own description.
  2. Relation — visual_description from edges whose source node is
     completed (status == "completed"). Failed / pending nodes are skipped.
  3. Background — the background node's description for color-tone
     and lighting context.
"""
from __future__ import annotations

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.knowledge_graph import GraphNode, KnowledgeGraph


class PromptFusion:
    """Build fused prompts from knowledge graph state."""

    def build_prompt(
        self,
        node: GraphNode,
        graph: KnowledgeGraph,
        completed_nodes: dict[str, GraphNode],
    ) -> str:
        """Assemble a 3-section prompt for *node*.

        Parameters
        ----------
        node:
            The target node to generate a prompt for.
        graph:
            The owning knowledge graph (provides edges and background).
        completed_nodes:
            Mapping of node_id -> GraphNode for every node whose status
            is ``completed``. Used to filter which edges contribute to
            the relation section.

        Returns
        -------
        str
            Fused prompt with Chinese structural markers and English
            (or user-language) content.
        """
        # ── Section 1: Subject ──────────────────────────────────
        subject = self._build_subject(node)

        # ── Section 2: Relation ────────────────────────────────
        relation = self._build_relation(node, graph, completed_nodes)

        # ── Section 3: Background ────────────────────────────────
        background = self._build_background(graph, completed_nodes)

        return self._assemble(subject, relation, background)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_subject(node: GraphNode) -> str:
        return node.description

    @staticmethod
    def _build_relation(
        node: GraphNode,
        graph: KnowledgeGraph,
        completed_nodes: dict[str, GraphNode],
    ) -> list[str]:
        """Collect visual_description lines from completed dependency edges."""
        lines: list[str] = []
        for edge in graph.edges:
            # Only consider edges pointing TO the target node
            if edge.to_node_id != node.id:
                continue
            # Only include edges whose source is completed
            if edge.from_node_id not in completed_nodes:
                continue
            desc = edge.visual_description.strip()
            if desc:
                source_desc = completed_nodes[edge.from_node_id].description
                label = source_desc[:40] if source_desc else edge.from_node_id
                lines.append(f"  - 与已完成资产({label})的衔接: {desc}")
        return lines

    @staticmethod
    def _build_background(
        graph: KnowledgeGraph,
        completed_nodes: dict[str, GraphNode],
    ) -> str:
        """Extract background node description for lighting/tone context."""
        bg_id = graph.background_node_id
        if bg_id is None:
            return ""
        if bg_id not in completed_nodes:
            return ""
        return completed_nodes[bg_id].description

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _assemble(
        subject: str,
        relation: list[str],
        background: str,
    ) -> str:
        parts: list[str] = []

        # Section 1: Subject
        parts.append(f"【生成主体】{subject}")

        # Section 2: Relation (omit entirely when empty)
        if relation:
            parts.append("【关联衔接描述】")
            parts.extend(relation)

        # Section 3: Background (omit entirely when empty)
        if background:
            parts.append("【背景光影】")
            parts.append(background)

        return "\n".join(parts)
