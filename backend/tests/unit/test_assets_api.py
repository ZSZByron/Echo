"""Unit tests for the /api/assets endpoint group."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

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
    """Create an AssetStore pointed at a temp manifest and inject it into the routes module."""
    from app.state.asset_store import AssetStore

    s = AssetStore(path=tmp_manifest)
    s.init_manifest()
    return s


@pytest.fixture
def client(store: Any) -> TestClient:
    """TestClient with the routes module's _store replaced by our temp store."""
    import app.api.assets_routes as ar

    ar._store = store
    # Replace _run_generation with a no-op async mock
    ar._run_generation = AsyncMock()  # type: ignore[assignment]

    from app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListAssets:
    def test_list_returns_assets(self, client: TestClient) -> None:
        """GET /api/assets returns a list of assets."""
        resp = client.get("/api/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert "assets" in data
        assert isinstance(data["assets"], list)
        assert len(data["assets"]) > 0

    def test_list_returns_correct_ids(self, client: TestClient) -> None:
        """GET /api/assets returns the expected asset IDs."""
        resp = client.get("/api/assets")
        ids = [a["id"] for a in resp.json()["assets"]]
        assert "temple_ruins_bg" in ids


class TestGetAsset:
    def test_get_single_asset(self, client: TestClient) -> None:
        """GET /api/assets/{id} returns the asset."""
        resp = client.get("/api/assets/temple_ruins_bg")
        assert resp.status_code == 200
        asset = resp.json()
        assert asset["id"] == "temple_ruins_bg"

    def test_get_missing_asset_404(self, client: TestClient) -> None:
        """GET /api/assets/{id} returns 404 for non-existent asset."""
        resp = client.get("/api/assets/nonexistent_asset")
        assert resp.status_code == 404


class TestGenerateAsset:
    def test_generate_returns_task_id_and_status(
        self, client: TestClient
    ) -> None:
        """POST /api/assets/{id}/generate returns task_id and generating status."""
        resp = client.post("/api/assets/temple_ruins_bg/generate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "temple_ruins_bg"
        assert data["status"] == "generating"

    def test_generate_missing_asset_404(self, client: TestClient) -> None:
        """POST /api/assets/{id}/generate returns 404 for non-existent asset."""
        resp = client.post("/api/assets/nonexistent/generate")
        assert resp.status_code == 404


class TestGetStatus:
    def test_status_returns_current_status(self, client: TestClient) -> None:
        """GET /api/assets/{id}/status returns the current status."""
        resp = client.get("/api/assets/temple_ruins_bg/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["generation_status"] == "pending"

    def test_status_missing_asset_404(self, client: TestClient) -> None:
        """GET /api/assets/{id}/status returns 404 for non-existent asset."""
        resp = client.get("/api/assets/nonexistent/status")
        assert resp.status_code == 404


class TestApproveAsset:
    def test_approve_completed_asset(
        self, client: TestClient, store: Any
    ) -> None:
        """POST /api/assets/{id}/approve on a completed asset succeeds."""
        # Move asset to completed via valid transitions
        store.update_asset("temple_ruins_bg", status="generating")
        store.update_asset("temple_ruins_bg", status="completed")

        resp = client.post("/api/assets/temple_ruins_bg/approve")
        assert resp.status_code == 200
        asset = resp.json()
        assert asset["status"] == "approved"

    def test_approve_pending_returns_409(self, client: TestClient) -> None:
        """POST /api/assets/{id}/approve on a pending asset returns 409."""
        resp = client.post("/api/assets/temple_ruins_bg/approve")
        assert resp.status_code == 409

    def test_approve_missing_asset_404(self, client: TestClient) -> None:
        """POST /api/assets/{id}/approve on non-existent asset returns 404."""
        resp = client.post("/api/assets/nonexistent/approve")
        assert resp.status_code == 404


class TestRejectAsset:
    def test_reject_completed_asset(
        self, client: TestClient, store: Any
    ) -> None:
        """POST /api/assets/{id}/reject on a completed asset succeeds with note."""
        store.update_asset("temple_ruins_bg", status="generating")
        store.update_asset("temple_ruins_bg", status="completed")

        resp = client.post(
            "/api/assets/temple_ruins_bg/reject",
            json={"reviewer_note": "bad composition"},
        )
        assert resp.status_code == 200
        asset = resp.json()
        assert asset["status"] == "rejected"
        assert asset["reviewer_note"] == "bad composition"

    def test_reject_pending_returns_409(self, client: TestClient) -> None:
        """POST /api/assets/{id}/reject on a pending asset returns 409."""
        resp = client.post(
            "/api/assets/temple_ruins_bg/reject",
            json={"reviewer_note": ""},
        )
        assert resp.status_code == 409


class TestUpdatePrompt:
    def test_update_prompt_changes_prompt(self, client: TestClient) -> None:
        """PUT /api/assets/{id}/prompt updates prompt and negative_prompt."""
        resp = client.put(
            "/api/assets/temple_ruins_bg/prompt",
            json={"prompt": "new prompt text", "negative_prompt": "no blur"},
        )
        assert resp.status_code == 200
        asset = resp.json()
        assert asset["prompt"] == "new prompt text"
        assert asset["negative_prompt"] == "no blur"

    def test_update_prompt_resets_rejected_to_pending(
        self, client: TestClient, store: Any
    ) -> None:
        """PUT prompt on a rejected asset resets status to pending."""
        store.update_asset("temple_ruins_bg", status="generating")
        store.update_asset("temple_ruins_bg", status="completed")
        store.update_asset("temple_ruins_bg", status="rejected")

        resp = client.put(
            "/api/assets/temple_ruins_bg/prompt",
            json={"prompt": "revised prompt", "negative_prompt": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    def test_update_prompt_missing_asset_404(
        self, client: TestClient
    ) -> None:
        """PUT /api/assets/{id}/prompt on non-existent asset returns 404."""
        resp = client.put(
            "/api/assets/nonexistent/prompt",
            json={"prompt": "x", "negative_prompt": ""},
        )
        assert resp.status_code == 404


class TestGenerateAll:
    def test_generate_all_triggers_pending(
        self, client: TestClient
    ) -> None:
        """POST /api/assets/generate-all triggers generation for all pending."""
        resp = client.post("/api/assets/generate-all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["triggered"] > 0
        assert len(data["task_ids"]) == data["triggered"]

    def test_generate_all_no_pending(
        self, client: TestClient, store: Any
    ) -> None:
        """POST /api/assets/generate-all with no pending returns triggered=0."""
        # Move all assets to generating so none are pending
        for asset in store.list_assets():
            store.update_asset(asset.id, status="generating")

        resp = client.post("/api/assets/generate-all")
        assert resp.status_code == 200
        assert resp.json()["triggered"] == 0


class TestBulkApprove:
    def test_bulk_approve_completed_assets(
        self, client: TestClient, store: Any
    ) -> None:
        """POST /api/assets/bulk-approve approves all completed assets."""
        # Move two assets to completed
        assets = store.list_assets()
        for asset in assets[:2]:
            store.update_asset(asset.id, status="generating")
            store.update_asset(asset.id, status="completed")

        resp = client.post("/api/assets/bulk-approve")
        assert resp.status_code == 200
        assert resp.json()["approved"] == 2

    def test_bulk_approve_no_completed(
        self, client: TestClient
    ) -> None:
        """POST /api/assets/bulk-approve with no completed returns approved=0."""
        resp = client.post("/api/assets/bulk-approve")
        assert resp.status_code == 200
        assert resp.json()["approved"] == 0
