"""Asset management API routes."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.scene_graph import SceneGraph
from app.state.asset_store import AssetStore, InvalidTransitionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])
scenes_router = APIRouter(prefix="/api/scenes", tags=["scenes"])

_store = AssetStore()
_generation_tasks: dict[str, asyncio.Task[Any]] = {}


# -- Request bodies -------------------------------------------------------------


class RejectBody(BaseModel):
    reviewer_note: str = ""


class PromptBody(BaseModel):
    prompt: str
    negative_prompt: str = ""


# -- Async generation helper ----------------------------------------------------


async def _run_generation(asset_id: str) -> None:
    """Background task: generate image for *asset_id* via ImageGenerator."""
    try:
        from app.ai.image_generator import ImageGenerationError, ImageGenerator
    except ImportError:
        _store.update_asset(
            asset_id,
            status=AssetStatus.FAILED,
            error_message="image generator unavailable",
        )
        _generation_tasks.pop(asset_id, None)
        return

    asset = _store.get_asset(asset_id)
    if asset is None:
        _generation_tasks.pop(asset_id, None)
        return

    # Get reference asset IDs via GenerationPlanner
    approved_refs: list[str] = []

    from app.config.features import SCENE_CONSISTENCY

    if SCENE_CONSISTENCY:
        try:
            from app.domains.creation.asset.generation_planner import GenerationPlanner

            planner = GenerationPlanner()
            plan = planner.create_plan(asset.parent_scene)

            if asset_id in plan.specs:
                ref_ids = plan.specs[asset_id].reference_asset_ids
                for ref_id in ref_ids:
                    ref_asset = _store.get_asset(ref_id)
                    if ref_asset and ref_asset.status in (
                        AssetStatus.APPROVED,
                        AssetStatus.COMPLETED,
                    ):
                        approved_refs.append(ref_id)
        except Exception as e:
            logger.warning(f"Failed to get plan references for {asset_id}: {e}")

    try:
        gen = ImageGenerator()
        results = await gen.generate(
            prompt=asset.prompt,
            negative_prompt=asset.negative_prompt,
            asset_id=asset_id,
            reference_asset_ids=approved_refs,
        )
        await gen.close()

        if not results:
            _store.update_asset(
                asset_id,
                status=AssetStatus.FAILED,
                error_message="no images generated",
            )
            return

        first = results[0]
        update_fields: dict[str, Any] = {
            "status": AssetStatus.COMPLETED,
            "seed": first.seed,
        }
        if first.file_path:
            update_fields["file_path"] = first.file_path
        elif first.url:
            update_fields["file_path"] = first.url

        _store.update_asset(asset_id, **update_fields)

        # If background asset completed, extract style and fill pending co-scene assets
        if asset.type == AssetType.BACKGROUND and update_fields.get("status") in (
            AssetStatus.COMPLETED,
            AssetStatus.CANDIDATES_READY,
        ):
            try:
                from app.ai.style_extractor import extract_style_profile_from_prompt

                profile = extract_style_profile_from_prompt(asset.prompt)

                for other_asset in _store.list_assets():
                    if (
                        other_asset.parent_scene == asset.parent_scene
                        and other_asset.type == AssetType.OBJECT
                        and other_asset.status == AssetStatus.PENDING
                    ):
                        _store.update_asset(
                            other_asset.id, style_profile=profile.model_dump(mode="json")
                        )
                        logger.info(
                            f"Filled style_profile for {other_asset.id} from background {asset.id}"
                        )
            except Exception as e:
                logger.warning(f"Failed to extract/fill style profiles: {e}")
    except ImageGenerationError as exc:
        _store.update_asset(
            asset_id,
            status=AssetStatus.FAILED,
            error_message=str(exc),
        )
    except Exception as exc:
        _store.update_asset(
            asset_id,
            status=AssetStatus.FAILED,
            error_message=f"unexpected error: {exc}",
        )
    finally:
        _generation_tasks.pop(asset_id, None)


# -- Endpoints ------------------------------------------------------------------


@router.get("")
async def list_assets() -> dict[str, list[Asset]]:
    """List all assets."""
    return {"assets": _store.list_assets()}


@router.get("/{asset_id}")
async def get_asset(asset_id: str) -> Asset:
    """Get a single asset by ID."""
    asset = _store.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/{asset_id}/generate")
async def generate_asset(asset_id: str) -> dict[str, str]:
    """Trigger async image generation for an asset."""
    asset = _store.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    try:
        _store.update_asset(asset_id, status=AssetStatus.GENERATING)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    task = asyncio.create_task(_run_generation(asset_id))
    _generation_tasks[asset_id] = task
    return {"task_id": asset_id, "status": "generating"}


@router.get("/{asset_id}/status")
async def get_status(asset_id: str) -> dict[str, str]:
    """Get generation status of an asset."""
    asset = _store.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"status": asset.status.value, "generation_status": asset.generation_status}


@router.post("/{asset_id}/approve")
async def approve_asset(asset_id: str) -> Asset:
    """Approve a completed asset."""
    try:
        return _store.update_asset(asset_id, status=AssetStatus.APPROVED)
    except KeyError:
        raise HTTPException(status_code=404, detail="Asset not found") from None
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{asset_id}/reject")
async def reject_asset(asset_id: str, body: RejectBody) -> Asset:
    """Reject a completed asset with an optional reviewer note."""
    try:
        return _store.update_asset(
            asset_id,
            status=AssetStatus.REJECTED,
            reviewer_note=body.reviewer_note,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Asset not found") from None
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/{asset_id}/prompt")
async def update_prompt(asset_id: str, body: PromptBody) -> Asset:
    """Update prompt and negative_prompt. Resets rejected/failed to pending."""
    asset = _store.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    fields: dict[str, Any] = {"prompt": body.prompt, "negative_prompt": body.negative_prompt}

    if asset.status in (AssetStatus.REJECTED, AssetStatus.FAILED):
        fields["status"] = AssetStatus.PENDING

    try:
        return _store.update_asset(asset_id, **fields)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/generate-all")
async def generate_all() -> dict[str, Any]:
    """Trigger generation for all pending assets using GenerationPlanner ordering."""
    from app.domains.creation.asset.generation_planner import GenerationPlanner

    planner = GenerationPlanner()

    # Group pending assets by scene and use planner order per scene
    pending = [a for a in _store.list_assets() if a.status == AssetStatus.PENDING]
    scene_ids = {a.parent_scene for a in pending if a.parent_scene}

    task_ids: list[str] = []
    for scene_id in scene_ids:
        try:
            plan = planner.create_plan(scene_id)
        except Exception as e:
            logger.warning(f"Failed to create plan for {scene_id}: {e}")
            continue

        for asset_id in plan.order:
            asset = _store.get_asset(asset_id)
            if asset and asset.status == AssetStatus.PENDING:
                try:
                    _store.update_asset(asset_id, status=AssetStatus.GENERATING)
                except InvalidTransitionError:
                    continue
                task = asyncio.create_task(_run_generation(asset_id))
                _generation_tasks[asset_id] = task
                task_ids.append(asset_id)

    return {"triggered": len(task_ids), "task_ids": task_ids}


@router.post("/bulk-approve")
async def bulk_approve() -> dict[str, int]:
    """Approve all completed assets."""
    completed = [a for a in _store.list_assets() if a.status == AssetStatus.COMPLETED]
    count = 0
    for asset in completed:
        try:
            _store.update_asset(asset.id, status=AssetStatus.APPROVED)
            count += 1
        except InvalidTransitionError:
            continue
    return {"approved": count}


# -- Scene orchestration endpoints ------------------------------------------------


@scenes_router.post("/{scene_id}/orchestrate")
async def orchestrate_scene(scene_id: str) -> dict[str, Any]:
    """Orchestrate generation of all assets in a scene using GenerationPlanner order."""
    from app.domains.creation.asset.generation_planner import GenerationPlanner

    planner = GenerationPlanner()
    plan = planner.create_plan(scene_id)

    order = plan.order
    triggered_count = 0

    for asset_id in order:
        asset = _store.get_asset(asset_id)
        if asset and asset.status == AssetStatus.PENDING:
            try:
                _store.update_asset(asset_id, status=AssetStatus.GENERATING)
                task = asyncio.create_task(_run_generation(asset_id))
                _generation_tasks[asset_id] = task
                triggered_count += 1
            except InvalidTransitionError:
                continue

    return {"order": order, "triggered": triggered_count}


@scenes_router.get("/{scene_id}/graph")
async def get_scene_graph(scene_id: str) -> dict[str, Any]:
    """Get scene graph structure with generation order and style sources."""
    from app.models.scene_graph import SceneGraph

    graph = SceneGraph.from_yaml(scene_id)
    return {
        "nodes": {k: v.model_dump(mode="json") for k, v in graph.nodes.items()},
        "generation_order": graph.generation_order,
        "style_sources": graph.style_sources,
    }


@scenes_router.get("/{scene_id}/orchestrate/status")
async def get_orchestrate_status(scene_id: str) -> dict[str, str]:
    """Get generation status of all assets in a scene."""
    assets = _store.list_assets()
    scene_assets = {
        a.id: a.status.value for a in assets if a.parent_scene == scene_id
    }
    return scene_assets
