"""Tests for constraints API endpoint."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_dimension_generator
from app.ai.provider import LLMProvider
from app.models.dimension import DimensionResultSet
from app.domains.creation.constraint.dimension_generator import DimensionGenerator


VALID_DIMENSIONS = {
    "RED": {"forbidden": ["暴力"], "note": "禁止"},
    "LAW": {"rules": ["法则"], "mechanism": "机制"},
    "ACT": {"actions": [{"trigger": "t", "check": "c", "success": "s", "failure": "f"}]},
    "NAR": {"style": "风格", "keywords": ["词"], "tone": "基调"},
    "WST": {"effects": [{"name": "效果", "type": "buff", "magnitude": "+1"}]},
    "SOC": {"relations": [{"target": "目标", "type": "盟友", "value": "友好"}]},
}


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""
    async def chat(self, messages, **kwargs): 
        return "mock response"
    
    async def chat_json(self, messages, **kwargs) -> dict[str, Any]: 
        return VALID_DIMENSIONS


@pytest.fixture
def client():
    """TestClient with mocked generator."""
    # Use real DimensionGenerator with mock provider to preserve _loader.get_weights()
    mock_gen = DimensionGenerator(provider=MockProvider())
    app.dependency_overrides[get_dimension_generator] = lambda: mock_gen
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# Test 1: Normal 200 response
def test_post_generate_returns_200(client: TestClient):
    """POST /api/constraints/generate with valid body → 200 + dimensions."""
    response = client.post("/api/constraints/generate", json={
        "seed_input": "古代水晶祭坛",
        "seed_description": "水晶祭坛",
        "layer": "asset",
        "intent": "测试",
    })
    assert response.status_code == 200
    data = response.json()
    assert "dimensions" in data
    assert data["layer"] == "asset"
    assert "weights" in data
    assert "elapsed_seconds" in data


# Test 2: Invalid layer → 422
def test_post_generate_invalid_layer_returns_422(client: TestClient):
    """layer='invalid' → 422 validation error."""
    response = client.post("/api/constraints/generate", json={
        "seed_input": "test",
        "layer": "invalid_layer",
    })
    assert response.status_code == 422


# Test 3: Missing seed_input → 422
def test_post_generate_missing_seed_returns_422(client: TestClient):
    """Missing seed_input → 422."""
    response = client.post("/api/constraints/generate", json={
        "layer": "world",
    })
    assert response.status_code == 422


# Test 4: Empty seed_input → 422 (min_length=1)
def test_post_generate_empty_seed_returns_422(client: TestClient):
    """seed_input='' → 422 (min_length=1)."""
    response = client.post("/api/constraints/generate", json={
        "seed_input": "",
        "layer": "world",
    })
    assert response.status_code == 422
