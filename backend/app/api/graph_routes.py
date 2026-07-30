"""Knowledge graph API routes for extraction, validation, persistence, and generation."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.knowledge_graph import KnowledgeGraph
from app.state.graph_store import GraphStore

logger = logging.getLogger(__name__)

graph_router = APIRouter(prefix="/api/graph", tags=["graph"])

_store = GraphStore()

# Project root needed by cycle_detector/models.py (from backend.app.models...)
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
# Path to graph_algorithm test modules (topo_sort, cycle_detector)
_GRAPH_ALGO_DIR = str(Path(__file__).resolve().parents[3] / "tests" / "graph_algorithm")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ExtractRequest(BaseModel):
    """Input for graph extraction endpoint."""

    scene_description: str


class ValidateResponse(BaseModel):
    """Output for graph validation endpoint."""

    is_valid: bool
    cycles: list[Any] = []


class SaveResponse(BaseModel):
    """Output for graph save endpoint."""

    scene_id: str
    saved: bool = True


class DeleteResponse(BaseModel):
    """Output for graph delete endpoint."""

    deleted: bool = True


class GenerateResponse(BaseModel):
    """Output for graph generation endpoint."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    order: list[str] = []
    error: str | None = None


# ---------------------------------------------------------------------------
# Helper: lazy import cycle detector
# ---------------------------------------------------------------------------


def _import_cycle_detector():
    """Lazy-import cycle_detector.validate_graph."""
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    if _GRAPH_ALGO_DIR not in sys.path:
        sys.path.insert(0, _GRAPH_ALGO_DIR)
    import cycle_detector

    return cycle_detector


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@graph_router.post("/extract")
async def extract_graph(body: ExtractRequest) -> dict[str, Any]:
    """Extract a knowledge graph skeleton from free-text scene description via LLM."""
    try:
        from app.services.graph_extractor import GraphExtractor
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Graph extractor unavailable") from exc

    if not body.scene_description.strip():
        raise HTTPException(status_code=400, detail="scene_description must not be empty")

    try:
        extractor = GraphExtractor()
        raw_data = await extractor.extract_from_text(body.scene_description)
        graph = extractor.to_knowledge_graph(raw_data)
        return graph.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Graph extraction failed")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}") from exc


@graph_router.post("/validate")
async def validate_graph(body: dict[str, Any]) -> ValidateResponse:
    """Validate a knowledge graph for cycle detection.

    Accepts a KnowledgeGraph JSON (same format as to_dict output).
    """
    try:
        graph = KnowledgeGraph.from_dict(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid graph data: {exc}") from exc

    if not graph.nodes:
        return ValidateResponse(is_valid=True, cycles=[])

    try:
        cycle_detector_mod = _import_cycle_detector()
        is_valid, cycles = cycle_detector_mod.validate_graph(graph)
        return ValidateResponse(is_valid=is_valid, cycles=cycles)
    except Exception as exc:
        logger.exception("Graph validation failed")
        raise HTTPException(status_code=500, detail=f"Validation failed: {exc}") from exc


@graph_router.post("/save")
async def save_graph(body: dict[str, Any]) -> SaveResponse:
    """Save a knowledge graph to the database.

    Accepts a KnowledgeGraph JSON. Performs cycle validation before saving.
    """
    try:
        graph = KnowledgeGraph.from_dict(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid graph data: {exc}") from exc

    if not graph.nodes:
        raise HTTPException(status_code=400, detail="Graph must contain at least one node")

    # Validate before saving
    try:
        cycle_detector_mod = _import_cycle_detector()
        is_valid, cycles = cycle_detector_mod.validate_graph(graph)
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail=f"Graph contains {len(cycles)} cycle(s). Cannot save an invalid graph.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Validation failed: {exc}") from exc

    try:
        await _store.init_db()
        await _store.save_graph(graph)
        return SaveResponse(scene_id=graph.scene_id)
    except Exception as exc:
        logger.exception("Graph save failed")
        raise HTTPException(status_code=500, detail=f"Save failed: {exc}") from exc


@graph_router.get("/{scene_id}")
async def get_graph(scene_id: str) -> dict[str, Any]:
    """Load a knowledge graph from the database by scene_id."""
    try:
        await _store.init_db()
        graph = await _store.load_graph(scene_id)
    except Exception as exc:
        logger.exception("Graph load failed")
        raise HTTPException(status_code=500, detail=f"Load failed: {exc}") from exc

    if not graph.nodes:
        raise HTTPException(status_code=404, detail=f"Graph not found for scene_id '{scene_id}'")

    return graph.to_dict()


@graph_router.delete("/{scene_id}")
async def delete_graph(scene_id: str) -> DeleteResponse:
    """Delete a knowledge graph from the database by scene_id."""
    try:
        await _store.init_db()
        graph = await _store.load_graph(scene_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Load failed: {exc}") from exc

    if not graph.nodes:
        raise HTTPException(status_code=404, detail=f"Graph not found for scene_id '{scene_id}'")

    try:
        await _store.delete_graph(scene_id)
        return DeleteResponse()
    except Exception as exc:
        logger.exception("Graph delete failed")
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}") from exc


@graph_router.post("/generate")
async def generate_graph(body: dict[str, Any]) -> GenerateResponse:
    """Trigger serial wave-based generation for a knowledge graph.

    Accepts a KnowledgeGraph JSON. Returns generation results including
    total, succeeded, failed counts and the execution order.
    """
    try:
        graph = KnowledgeGraph.from_dict(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid graph data: {exc}") from exc

    if not graph.nodes:
        raise HTTPException(status_code=400, detail="Graph must contain at least one node")

    try:
        from app.services.generation_scheduler import GenerationScheduler
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Generation scheduler unavailable") from exc

    try:
        scheduler = GenerationScheduler()
        result = await scheduler.run_generation(graph)
        return GenerateResponse(
            total=result.get("total", 0),
            succeeded=result.get("succeeded", 0),
            failed=result.get("failed", 0),
            order=result.get("order", []),
            error=result.get("error"),
        )
    except Exception as exc:
        logger.exception("Graph generation failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc
