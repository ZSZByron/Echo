"""FastAPI Main Application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.a1_routes import router as a1_router
from app.api.assets_routes import router as assets_router, scenes_router as scenes_router
from app.api.constraints_routes import constraints_router
from app.api.deps import get_state_repository
from app.api.graph_routes import graph_router
from app.api.graph_registry_routes import router as graph_registry_router
from app.api.identity_routes import router as identity_router
from app.api.routes import router
from app.api.seed_routes import router as seed_router

# Load .env file from backend root directory (backend/.env)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize database on startup, cleanup on shutdown."""
    repo = get_state_repository()
    await repo.init_db()
    yield
    await repo.close()


app = FastAPI(
    title="Echo UGC API",
    description="AI-Interactive Rule Terminal",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(assets_router)
app.include_router(scenes_router)
app.include_router(graph_router)
app.include_router(seed_router)
app.include_router(constraints_router)
app.include_router(graph_registry_router)
app.include_router(identity_router)
app.include_router(a1_router)

# Mount data/assets directory for serving generated images
_assets_dir = Path(__file__).resolve().parent.parent.parent / "data" / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")
