"""Graph registry API route."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.config.paths import ASSETS_DIR
from app.domains.creation.shared.stale_marker import (
    ensure_registry,
    list_user_graphs,
)

router = APIRouter(tags=["graph-registry"])

_REGISTRY_DB = str(ASSETS_DIR / "ugc.db")


@router.get("/api/graphs")
async def get_graphs(
    user_id: str = Query(..., description="User ID to list graphs for"),
) -> dict:
    """List all graph artifacts for a user, grouped by IP code."""
    ensure_registry(_REGISTRY_DB)
    try:
        return list_user_graphs(_REGISTRY_DB, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
