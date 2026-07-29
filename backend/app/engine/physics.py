"""Pure physics calculations for the rules engine."""
from __future__ import annotations

INTENSITY_MULTIPLIERS: dict[str, float] = {
    "low": 0.5,
    "medium": 1.0,
    "maximum": 1.5,
}


def check_strength_vs_hardness(
    player_strength: int, target_hardness: int
) -> bool:
    """Return True if player strength meets or exceeds target hardness."""
    return player_strength >= target_hardness


def calculate_damage(force: int, resistance: int) -> int:
    """Calculate damage based on force minus resistance. Minimum 0."""
    return max(0, force - resistance)


def calculate_energy_cost(base_cost: int, intensity: str) -> int:
    """Calculate energy cost based on action intensity multiplier."""
    multiplier = INTENSITY_MULTIPLIERS.get(intensity, 1.0)
    return max(0, int(base_cost * multiplier))
