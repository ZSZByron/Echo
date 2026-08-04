"""LLM-based graph extraction from free-text scene descriptions.

Uses the existing LLMProvider abstraction (app.ai.provider) to call an LLM,
extract structured node/edge JSON, and convert to a KnowledgeGraph object.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai.config import load_provider_config
from app.ai.provider import LLMProvider, create_provider
from app.models.knowledge_graph import EdgeType, KnowledgeGraph

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是一个场景结构提取器。给定一段自然语言场景描述，你必须将其分解为一个 \
资产层级图谱。

输出严格的JSON对象，格式如下（不要包含任何其他文字）：

```json
{
  "background": {"description": "场景背景的视觉描述"},
  "nodes": [
    {"serial": "1", "description": "资产的视觉描述", "parent_serial": null},
    {"serial": "1-1", "description": "子资产的视觉描述", "parent_serial": "1"}
  ],
  "edges": [
    {"from": "1-1", "to": "2-1", "edge_type": "cross", "visual_description": ""}
  ]
}
```

规则：
1. "serial" 是层级序号（如 "1", "1-1", "1-1-1"）。
2. "parent_serial" 表示父节点序号，顶层节点为 null。
3. "edge_type" 只有 "tree"（父子关系）或 "cross"（跨树引用）。
4. "visual_description" 在所有 edge 中必须为空字符串 ""——由用户手动填写。
5. 只输出JSON，不要输出其他内容。
"""

_USER_PROMPT_TEMPLATE = """\
请从以下场景描述中提取资产层级图谱：

{scene_description}
"""

# ---------------------------------------------------------------------------
# JSON repair helpers
# ---------------------------------------------------------------------------

# LLM sometimes wraps JSON in markdown code fences
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _try_parse_json(raw: str) -> dict[str, Any]:
    """Attempt to parse *raw* string as JSON with basic repair strategies.

    Strategies tried in order:
    1. Direct ``json.loads``.
    2. Strip markdown code fences first.
    3. Find first ``{`` and last ``}`` and extract that substring.

    Raises:
        ValueError: If all strategies fail.
    """
    # 1. Direct parse
    try:
        return json.loads(raw)  # type: ignore[return-value]
    except json.JSONDecodeError:
        pass

    # 2. Strip code fences
    fenced = _CODE_FENCE_RE.findall(raw)
    for candidate in fenced:
        try:
            return json.loads(candidate.strip())  # type: ignore[return-value]
        except json.JSONDecodeError:
            continue

    # 3. Brace extraction
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(raw[first_brace : last_brace + 1])  # type: ignore[return-value]
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Failed to parse LLM response as JSON after all repair attempts. "
        f"Raw response (first 500 chars): {raw[:500]}"
    )


# ---------------------------------------------------------------------------
# GraphExtractor
# ---------------------------------------------------------------------------


class GraphExtractor:
    """Extract a KnowledgeGraph from a free-text scene description via LLM.

    Usage::

        extractor = GraphExtractor()
        result = await extractor.extract_from_text("玩家进入神庙大厅...")
    """

    def __init__(self) -> None:
        self._provider: LLMProvider | None = None

    # -- lazy-init so import-time doesn't require env vars ---------------

    def _ensure_provider(self) -> LLMProvider:
        if self._provider is not None:
            return self._provider
        config = load_provider_config()
        self._provider = create_provider(config)
        return self._provider

    # -- low-level LLM call ----------------------------------------------

    async def _call_llm(self, scene_description: str) -> str:
        """Call the configured LLM and return raw text response."""
        provider = self._ensure_provider()
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _USER_PROMPT_TEMPLATE.format(
                    scene_description=scene_description
                ),
            },
        ]
        # Use chat_json for providers that support structured JSON output,
        # falling back gracefully.
        try:
            result = await provider.chat_json(messages)
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            # Fallback to plain chat
            return await provider.chat(messages)

    # -- public API -------------------------------------------------------

    async def extract_from_text(self, scene_description: str) -> dict[str, Any]:
        """Extract a graph structure from *scene_description*.

        Returns a dict with keys: ``background``, ``nodes``, ``edges``.

        Raises:
            ValueError: If the LLM response cannot be parsed into valid JSON.
        """
        raw = await self._call_llm(scene_description)
        data = _try_parse_json(raw)
        return self._normalize(data)

    # -- conversion -------------------------------------------------------

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize LLM output.

        Ensures required keys exist, edge ``visual_description`` is empty string.
        """
        if "background" not in data or "nodes" not in data:
            raise ValueError(
                "LLM output missing required keys 'background' or 'nodes'."
            )

        # Ensure edges list exists
        data.setdefault("edges", [])

        # Force all edge visual_description to empty string (user must hand-write)
        for edge in data["edges"]:
            edge.setdefault("visual_description", "")
            edge["visual_description"] = ""

        return data

    @staticmethod
    def to_knowledge_graph(
        data: dict[str, Any], scene_id: str = "extracted"
    ) -> KnowledgeGraph:
        """Convert normalized LLM output to a KnowledgeGraph model.

        Args:
            data: Normalized dict from :meth:`extract_from_text`.
            scene_id: Scene identifier for the graph.

        Returns:
            A populated KnowledgeGraph instance.
        """
        graph = KnowledgeGraph(scene_id=scene_id)

        # Add nodes
        for node_data in data.get("nodes", []):
            serial = node_data.get("serial", "")
            description = node_data.get("description", "")
            graph.add_node(serial=serial, description=description)

        # Add tree edges from parent_serial relationships
        for node_data in data.get("nodes", []):
            serial = node_data.get("serial", "")
            parent_serial = node_data.get("parent_serial")
            if parent_serial and parent_serial in graph.nodes:
                graph.add_edge(
                    from_id=parent_serial,
                    to_id=serial,
                    edge_type=EdgeType.TREE,
                )

        # Add cross edges from explicit edges list
        for edge_data in data.get("edges", []):
            from_id = edge_data.get("from", "")
            to_id = edge_data.get("to", "")
            edge_type_str = edge_data.get("edge_type", "cross")
            visual_desc = edge_data.get("visual_description", "")

            # Skip tree edges already created from parent_serial
            if edge_type_str == "tree":
                continue

            edge_type = EdgeType(edge_type_str)
            if from_id in graph.nodes and to_id in graph.nodes:
                graph.add_edge(
                    from_id=from_id,
                    to_id=to_id,
                    edge_type=edge_type,
                    visual_desc=visual_desc,
                )

        return graph
