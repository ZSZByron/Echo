"""Unit tests for FastAPI API endpoints."""
from __future__ import annotations
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.models.action import (
    ParsedIntent, JudgmentResult, JudgmentOutcome,
    StateChange, NarrativeContext, ActionType,
)
from app.models.player import PlayerState, PlayerStatus
from app.models.api import ActionRequest, ActionResponse


# ---------------------------------------------------------------------------
# Mock helper functions
# ---------------------------------------------------------------------------

def _make_mock_intent() -> ParsedIntent:
    return ParsedIntent(
        action_type=ActionType.BRUTE_FORCE,
        target="priest_corpse_01",
        intensity="medium",
        risk_acceptance=False,
        raw_input="test input",
        confidence=0.9,
    )


def _make_mock_judgment(
    outcome: JudgmentOutcome = JudgmentOutcome.SUCCESS,
    reason: str = "Test reason",
    damage: int = 0,
    state_changes: list[StateChange] | None = None,
    echo_triggered: bool = False,
    god_intervention: str | None = None,
) -> JudgmentResult:
    return JudgmentResult(
        result=outcome,
        reason=reason,
        damage=damage,
        state_changes=state_changes or [],
        god_intervention=god_intervention,
        narrative_context=NarrativeContext(
            scene_id="temple_ruins",
            atmosphere="test",
            tension_level=50,
        ),
        echo_triggered=echo_triggered,
    )


def _make_mock_player() -> PlayerState:
    return PlayerState(
        id="player_001",
        energy=80, health=90, strength=60, intelligence=70,
        echo_mode_enabled=False, mental_stability=85,
        location="temple_ruins", inventory=[],
        status=PlayerStatus.NORMAL, max_energy=100, max_health=100,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_deps():
    """Mock all dependencies for API testing."""
    mock_repo = AsyncMock()
    mock_repo.get_state.return_value = _make_mock_player()
    mock_repo.reset_state.return_value = _make_mock_player()
    mock_repo.update_state.return_value = None
    mock_repo.init_db.return_value = None
    mock_repo.close.return_value = None

    mock_parser = AsyncMock()
    mock_parser.parse.return_value = _make_mock_intent()

    mock_engine = AsyncMock()
    mock_engine.judge.return_value = _make_mock_judgment()

    mock_renderer = AsyncMock()
    mock_renderer.render.return_value = "[SYSTEM] Test narrative"

    return mock_repo, mock_parser, mock_engine, mock_renderer


# ---------------------------------------------------------------------------
# Test: Health endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /api/health returns 200 with healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "echo-ugc"


# ---------------------------------------------------------------------------
# Test: Action endpoint success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_action_endpoint_success(mock_deps):
    """POST /api/action with valid input returns 200 with complete response."""
    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    
    with patch("app.api.routes.get_state_repository", return_value=mock_repo), \
         patch("app.api.routes.get_intent_parser", return_value=mock_parser), \
         patch("app.api.routes.get_rules_engine", return_value=mock_engine), \
         patch("app.api.routes.get_narrative_renderer", return_value=mock_renderer):
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/action",
                json={"player_input": "test input", "player_id": "player_001", "current_scene": "temple_ruins"},
            )
    
    assert resp.status_code == 200
    data = resp.json()
    assert "judgment" in data
    assert "narrative" in data
    assert "updated_state" in data
    assert data["judgment"]["reason"] == "Test reason"
    assert data["narrative"] == "[SYSTEM] Test narrative"
    assert data["updated_state"]["id"] == "player_001"


# ---------------------------------------------------------------------------
# Test: Get state endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_state_endpoint(mock_deps):
    """GET /api/state returns 200 with PlayerState JSON."""
    mock_repo, *_ = mock_deps
    
    with patch("app.api.routes.get_state_repository", return_value=mock_repo):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/state?player_id=player_001")
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "player_001"
    assert data["health"] == 90
    assert data["energy"] == 80


# ---------------------------------------------------------------------------
# Test: Reset state endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_state_endpoint(mock_deps):
    """POST /api/reset returns 200 with reset PlayerState."""
    mock_repo, *_ = mock_deps
    
    with patch("app.api.routes.get_state_repository", return_value=mock_repo):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reset", json={"player_id": "player_001"})
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "player_001"


# ---------------------------------------------------------------------------
# Test: LLM failure graceful handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_failure_graceful(mock_deps):
    """Renderer exception triggers fallback narrative - still returns 200."""
    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    mock_renderer.render.side_effect = RuntimeError("LLM service down")
    
    with patch("app.api.routes.get_state_repository", return_value=mock_repo), \
         patch("app.api.routes.get_intent_parser", return_value=mock_parser), \
         patch("app.api.routes.get_rules_engine", return_value=mock_engine), \
         patch("app.api.routes.get_narrative_renderer", return_value=mock_renderer):
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/action",
                json={"player_input": "test", "player_id": "player_001", "current_scene": "temple_ruins"},
            )
    
    assert resp.status_code == 200
    data = resp.json()
    assert "[SYSTEM]" in data["narrative"]
    mock_renderer.render.side_effect = None


# ---------------------------------------------------------------------------
# Test: Orchestrator state change application
# ---------------------------------------------------------------------------

def test_orchestrator_apply_state_changes(mock_deps):
    """Orchestrator correctly applies health damage from judgment."""
    from app.orchestrator import Orchestrator

    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    
    # Setup: player with 90 health, judgment deals 15 damage
    player = _make_mock_player()
    player.health = 90
    
    judgment = _make_mock_judgment(
        outcome=JudgmentOutcome.FAIL,
        reason="Test failure",
        damage=15,
    )
    
    # Create orchestrator
    orch = Orchestrator(
        parser=mock_parser,
        engine=mock_engine,
        renderer=mock_renderer,
        state_repo=mock_repo,
    )
    
    # Apply state changes
    updated_player = orch._apply_state_changes(player, judgment)
    
    # Verify: health reduced by damage amount
    assert updated_player.health == 75
    assert updated_player.id == player.id


def test_orchestrator_apply_state_changes_with_health_change(mock_deps):
    """Orchestrator correctly applies state change for health property."""
    from app.orchestrator import Orchestrator

    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    
    player = _make_mock_player()
    player.health = 50
    
    # State change to set health to 75
    health_change = StateChange(
        target_type="player",
        target_id="player_001",
        property_name="health",
        old_value=50,
        new_value=75,
    )
    
    judgment = _make_mock_judgment(
        outcome=JudgmentOutcome.PARTIAL,
        reason="Partial success",
        state_changes=[health_change],
    )
    
    orch = Orchestrator(
        parser=mock_parser,
        engine=mock_engine,
        renderer=mock_renderer,
        state_repo=mock_repo,
    )
    
    updated_player = orch._apply_state_changes(player, judgment)
    
    # State change should apply
    assert updated_player.health == 75


def test_orchestrator_apply_state_changes_energy_clamped(mock_deps):
    """Orchestrator clamps energy values within valid range (0 to max_energy)."""
    from app.orchestrator import Orchestrator

    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    
    player = _make_mock_player()
    player.energy = 50
    player.max_energy = 100
    
    # Try to set energy above max
    overcharge_change = StateChange(
        target_type="player",
        target_id="player_001",
        property_name="energy",
        old_value=50,
        new_value=150,
    )
    
    judgment = _make_mock_judgment(
        outcome=JudgmentOutcome.SUCCESS,
        reason="Overcharge",
        state_changes=[overcharge_change],
    )
    
    orch = Orchestrator(
        parser=mock_parser,
        engine=mock_engine,
        renderer=mock_renderer,
        state_repo=mock_repo,
    )
    
    updated_player = orch._apply_state_changes(player, judgment)
    
    # Energy should be clamped to max_energy
    assert updated_player.energy == 100


def test_orchestrator_apply_state_changes_negative_clamped(mock_deps):
    """Orchestrator clamps negative values to minimum of 0."""
    from app.orchestrator import Orchestrator

    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    
    player = _make_mock_player()
    player.health = 30
    
    # Massive damage that would make health negative
    judgment = _make_mock_judgment(
        outcome=JudgmentOutcome.FORCED_FAIL,
        reason="Massive damage",
        damage=50,
    )
    
    orch = Orchestrator(
        parser=mock_parser,
        engine=mock_engine,
        renderer=mock_renderer,
        state_repo=mock_repo,
    )
    
    updated_player = orch._apply_state_changes(player, judgment)
    
    # Health should be clamped to 0
    assert updated_player.health == 0


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_action_endpoint_new_player(mock_deps):
    """When player state is None, orchestrator resets state before processing."""
    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    mock_repo.get_state.return_value = None  # Simulate new player
    mock_repo.reset_state.return_value = _make_mock_player()

    with patch("app.api.routes.get_state_repository", return_value=mock_repo), \
         patch("app.api.routes.get_intent_parser", return_value=mock_parser), \
         patch("app.api.routes.get_rules_engine", return_value=mock_engine), \
         patch("app.api.routes.get_narrative_renderer", return_value=mock_renderer):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/action",
                json={"player_input": "test", "player_id": "new_player", "current_scene": "temple_ruins"},
            )

    assert resp.status_code == 200
    mock_repo.reset_state.assert_called_once()


@pytest.mark.asyncio
async def test_get_state_new_player(mock_deps):
    """When no state exists, reset is called."""
    mock_repo, *_ = mock_deps
    mock_repo.get_state.return_value = None

    with patch("app.api.routes.get_state_repository", return_value=mock_repo):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/state?player_id=brand_new")

    assert resp.status_code == 200
    mock_repo.reset_state.assert_called_once()


def test_orchestrator_template_render_with_god():
    """Template render shows god intervention message."""
    judgment = _make_mock_judgment(
        outcome=JudgmentOutcome.GOD_INTERVENTION,
        reason="God intervenes!",
        god_intervention="Chronos",
    )
    from app.orchestrator import _template_render
    result = _template_render(judgment)
    assert "Chronos" in result
    assert "INTERVENTION" in result


def test_orchestrator_apply_non_player_changes_ignored(mock_deps):
    """State changes targeting non-player entities are skipped."""
    from app.orchestrator import Orchestrator
    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    player = _make_mock_player()

    # Non-player state change should be ignored
    scene_change = StateChange(
        target_type="scene",
        target_id="temple_ruins",
        property_name="atmosphere",
        old_value="calm",
        new_value="hostile",
    )
    judgment = _make_mock_judgment(state_changes=[scene_change])

    orch = Orchestrator(parser=mock_parser, engine=mock_engine, renderer=mock_renderer, state_repo=mock_repo)
    updated = orch._apply_state_changes(player, judgment)
    assert updated.location == player.location  # Unchanged


def test_orchestrator_apply_status_change(mock_deps):
    """State change for status field is applied."""
    from app.orchestrator import Orchestrator
    mock_repo, mock_parser, mock_engine, mock_renderer = mock_deps
    player = _make_mock_player()

    status_change = StateChange(
        target_type="player",
        target_id="player_001",
        property_name="status",
        old_value="normal",
        new_value="injured",
    )
    judgment = _make_mock_judgment(state_changes=[status_change])

    orch = Orchestrator(parser=mock_parser, engine=mock_engine, renderer=mock_renderer, state_repo=mock_repo)
    updated = orch._apply_state_changes(player, judgment)
    assert updated.status == PlayerStatus.INJURED
