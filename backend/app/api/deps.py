"""Dependency injection for FastAPI routes.

Provides singleton instances of all core dependencies via Protocol-typed
getters for testability with dependency overrides.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol, runtime_checkable

from app.ai.config import load_provider_config
from app.ai.provider import LLMProvider, create_provider
from app.engine.rules_engine import RulesEngine
from app.engine.world_loader import WorldLoader
from app.models.action import JudgmentResult, ParsedIntent
from app.models.player import PlayerState

# Forward declaration for type hint in get_dimension_generator
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.domains.creation.constraint.dimension_generator import DimensionGenerator


# ---------------------------------------------------------------------------
# Protocol definitions for modules under parallel development (T5 / T6)
# ---------------------------------------------------------------------------


@runtime_checkable
class StateRepository(Protocol):
    async def init_db(self) -> None: ...

    async def get_state(self, player_id: str = "player_001") -> PlayerState | None: ...

    async def update_state(self, player_id: str, state: PlayerState) -> None: ...

    async def reset_state(self, player_id: str = "player_001") -> PlayerState: ...

    async def close(self) -> None: ...


@runtime_checkable
class IntentParser(Protocol):
    async def parse(self, player_input: str) -> ParsedIntent: ...


@runtime_checkable
class NarrativeRenderer(Protocol):
    async def render(
        self, judgment: JudgmentResult, intent: ParsedIntent, context: dict[str, object]
    ) -> str: ...


# ---------------------------------------------------------------------------
# Concrete singletons for modules that already exist
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_world_loader() -> WorldLoader:
    return WorldLoader()


@lru_cache(maxsize=1)
def get_rules_engine() -> RulesEngine:
    return RulesEngine(get_world_loader())


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    config = load_provider_config()
    return create_provider(config)


# ---------------------------------------------------------------------------
# Lazy singletons for T5/T6 modules
# ---------------------------------------------------------------------------


def get_state_repository() -> StateRepository:
    from app.state.database import StateRepository as _SR

    return _SR()


def get_intent_parser() -> IntentParser:
    from app.ai.parser import IntentParser as _IP

    return _IP(get_llm_provider())


def get_narrative_renderer() -> NarrativeRenderer:
    from app.ai.renderer import NarrativeRenderer as _NR

    return _NR(get_llm_provider())


@lru_cache(maxsize=1)
def get_dimension_generator() -> DimensionGenerator:
    """Singleton DimensionGenerator for constraint generation."""
    from app.domains.creation.constraint.dimension_generator import DimensionGenerator
    
    return DimensionGenerator(provider=get_llm_provider())
