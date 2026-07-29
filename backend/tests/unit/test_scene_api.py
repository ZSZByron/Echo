"""Unit tests for GET /api/scene endpoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_manifest(tmp_path: Path) -> Path:
    """Return path to a temp manifest file."""
    return tmp_path / "manifest.json"


@pytest.fixture
def store(tmp_manifest: Path) -> Any:
    """Create an AssetStore pointed at a temp manifest, initialized from scenes."""
    from app.state.asset_store import AssetStore

    s = AssetStore(path=tmp_manifest)
    s.init_manifest()
    return s


@pytest.fixture
def client(store: Any) -> TestClient:
    """TestClient with AssetStore in routes patched to use our temp store."""
    from unittest.mock import patch

    def _fake_store():
        return store

    with patch("app.api.routes.AssetStore", _fake_store):
        from app.main import app

        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetScene:
    """Tests for GET /api/scene."""

    def test_returns_200_with_structure(self, client: TestClient) -> None:
        """GET /api/scene returns 200 with correct top-level structure."""
        resp = client.get("/api/scene")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scene_id"] == "temple_ruins"
        assert "name" in data
        assert "description" in data
        assert "atmosphere" in data
        assert "background_asset" in data
        assert isinstance(data["objects"], list)
        assert len(data["objects"]) == 7

    def test_background_asset_null_when_not_approved(
        self, client: TestClient
    ) -> None:
        """background_asset is null when bg asset is not approved."""
        resp = client.get("/api/scene")
        data = resp.json()
        assert data["background_asset"] is None

    def test_objects_have_position(self, client: TestClient) -> None:
        """Each object has a position with x and y."""
        resp = client.get("/api/scene")
        data = resp.json()
        for obj in data["objects"]:
            assert "position" in obj
            assert "x" in obj["position"]
            assert "y" in obj["position"]
            assert isinstance(obj["position"]["x"], (int, float))
            assert isinstance(obj["position"]["y"], (int, float))

    def test_objects_have_is_primary_boolean(self, client: TestClient) -> None:
        """objects[0] has is_primary as boolean."""
        resp = client.get("/api/scene")
        data = resp.json()
        for obj in data["objects"]:
            assert isinstance(obj["is_primary"], bool)

    def test_object_asset_null_when_not_approved(self, client: TestClient) -> None:
        """object.asset is null when not approved."""
        resp = client.get("/api/scene")
        data = resp.json()
        for obj in data["objects"]:
            assert obj["asset"] is None

    def test_background_asset_non_null_after_approval(
        self, client: TestClient, store: Any
    ) -> None:
        """After approving bg asset, background_asset is non-null."""
        from app.models.asset import AssetStatus

        # Transition to completed then approved
        store.update_asset("temple_ruins_bg", status=AssetStatus.GENERATING)
        store.update_asset("temple_ruins_bg", status=AssetStatus.COMPLETED)
        store.update_asset(
            "temple_ruins_bg",
            status=AssetStatus.APPROVED,
            file_path="/data/assets/temple_ruins_bg.png",
        )

        resp = client.get("/api/scene")
        data = resp.json()
        assert data["background_asset"] is not None
        assert "temple_ruins_bg" in data["background_asset"]

    def test_object_asset_non_null_after_approval(
        self, client: TestClient, store: Any
    ) -> None:
        """After approving an object asset, that object's asset field is non-null."""
        from app.models.asset import AssetStatus

        asset_id = "temple_ruins_ancient_locked_door"
        store.update_asset(asset_id, status=AssetStatus.GENERATING)
        store.update_asset(asset_id, status=AssetStatus.COMPLETED)
        store.update_asset(
            asset_id,
            status=AssetStatus.APPROVED,
            file_path="/data/assets/temple_ruins_ancient_locked_door.png",
        )

        resp = client.get("/api/scene")
        data = resp.json()
        door_obj = next(
            o for o in data["objects"] if o["id"] == "ancient_locked_door"
        )
        assert door_obj["asset"] is not None
        assert "ancient_locked_door" in door_obj["asset"]

    def test_is_primary_for_future_anchor(self, client: TestClient) -> None:
        """Objects with is_future_anchor=true should have is_primary=true."""
        resp = client.get("/api/scene")
        data = resp.json()
        # ancient_locked_door has is_future_anchor: true
        door = next(o for o in data["objects"] if o["id"] == "ancient_locked_door")
        assert door["is_primary"] is True
        # holographic_altar also is_future_anchor: true
        altar = next(o for o in data["objects"] if o["id"] == "holographic_altar")
        assert altar["is_primary"] is True

    def test_is_dangerous_from_interaction_targets(
        self, client: TestClient
    ) -> None:
        """is_dangerous reflects interaction_targets from YAML."""
        resp = client.get("/api/scene")
        data = resp.json()
        # ancient_locked_door is dangerous
        door = next(o for o in data["objects"] if o["id"] == "ancient_locked_door")
        assert door["is_dangerous"] is True
        # priest_corpse_01 is not dangerous
        corpse = next(o for o in data["objects"] if o["id"] == "priest_corpse_01")
        assert corpse["is_dangerous"] is False
