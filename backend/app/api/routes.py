"""FastAPI route handlers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import (
    StateRepository,
    get_intent_parser,
    get_narrative_renderer,
    get_rules_engine,
    get_state_repository,
    get_world_loader,
)
from app.models.api import ActionRequest, ActionResponse
from app.models.asset import AssetStatus
from app.models.player import PlayerState
from app.models.scene_response import Position, SceneObjectDTO, SceneResponse
from app.orchestrator import Orchestrator
from app.state.asset_store import AssetStore

router = APIRouter(prefix="/api")


@router.post("/action", response_model=ActionResponse)
async def process_action(request: ActionRequest) -> ActionResponse:
    """Main interaction endpoint."""
    orchestrator = Orchestrator(
        parser=get_intent_parser(),
        engine=get_rules_engine(),
        renderer=get_narrative_renderer(),
        state_repo=get_state_repository(),
    )
    return await orchestrator.process_action(request)


@router.get("/state", response_model=PlayerState)
async def get_state(player_id: str = "player_001") -> PlayerState:
    """Get current player state."""
    repo: StateRepository = get_state_repository()
    state = await repo.get_state(player_id=player_id)
    if state is None:
        state = await repo.reset_state(player_id=player_id)
    return state


@router.post("/reset", response_model=PlayerState)
async def reset_state(player_id: str = "player_001") -> PlayerState:
    """Reset player state to default."""
    repo: StateRepository = get_state_repository()
    return await repo.reset_state(player_id=player_id)


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "healthy", "service": "echo-ugc"}


@router.get("/scene", response_model=SceneResponse)
async def get_scene(scene_id: str = "temple_ruins") -> SceneResponse:
    """Return scene with only approved assets included."""
    loader = get_world_loader()
    scene = loader.load_scene(scene_id)
    store = AssetStore()

    # Build a lookup of interaction_targets for is_dangerous
    target_map: dict[str, bool] = {}
    for t in scene.interaction_targets:
        target_map[t.object_id] = t.is_dangerous

    # Background asset
    bg_asset_id = f"{scene_id}_bg"
    bg_asset = store.get_asset(bg_asset_id)
    bg_path: str | None = None
    if (
        bg_asset is not None
        and bg_asset.status == AssetStatus.APPROVED
        and bg_asset.file_path
    ):
        bg_path = f"/assets/{bg_asset_id}.png"

    # Build object DTOs
    dto_objects: list[SceneObjectDTO] = []
    for obj in scene.accessible_objects:
        # Resolve position
        raw_pos = obj.position or {"x": 0.0, "y": 0.0}
        position = Position(x=raw_pos["x"], y=raw_pos["y"])

        # Asset lookup
        obj_asset_id = f"{scene_id}_{obj.id}"
        obj_asset = store.get_asset(obj_asset_id)
        obj_asset_path: str | None = None
        if (
            obj_asset is not None
            and obj_asset.status == AssetStatus.APPROVED
            and obj_asset.file_path
        ):
            obj_asset_path = f"/assets/{obj_asset_id}.png"

        # Flags
        is_dangerous = target_map.get(obj.id, False)
        is_primary = obj.is_future_anchor or is_dangerous

        dto_objects.append(
            SceneObjectDTO(
                id=obj.id,
                name=obj.name,
                type=obj.type,
                description=obj.description,
                position=position,
                asset=obj_asset_path,
                is_primary=is_primary,
                is_dangerous=is_dangerous,
            )
        )

    return SceneResponse(
        scene_id=scene.scene_id,
        name=scene.name,
        description=scene.description,
        atmosphere=scene.atmosphere,
        background_asset=bg_path,
        objects=dto_objects,
    )
