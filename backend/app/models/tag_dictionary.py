"""Tag and enum dictionary for 断点A data layer.

Provides YAML-based tag and enum value dictionary for 6 constraint dimensions
plus A2 additions (LOC and STY) with layered traceability support.

Core interface:
- load_tag_dictionary(): Load and validate dictionary
- get_enum_values(dim, tag): Query enum values (attested + proposed merged)
- get_attested_values(dim, tag): Query only attested values (from hierarchy L105-130)
- get_proposed_values(dim, tag): Query only proposed values (extension proposals)
- validate(dim, tag, value): Check if value is in closed enum set
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class TagDictionary(BaseModel):
    """Tag and enum dictionary model with merged flat structure (post-ruling A).

    After 2026-08-21 user ruling A, all proposed values have been promoted to attested.
    Structure: tag -> {values: [...]}
    """

    dimensions: dict[str, dict[str, Any]] = Field(
        description="Dimension -> tag -> enum values (flat list with 'values' key)"
    )

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, v: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Validate that all required dimensions exist."""
        required_dims = ["LAW", "ACT", "NAR", "WST", "SOC", "RED", "LOC", "STY"]
        for dim in required_dims:
            if dim not in v:
                raise ValueError(f"Missing required dimension: {dim}")
        return v

    def _get_values_list(self, tag_data: Any) -> list[str]:
        """Extract values list from tag data.

        Args:
            tag_data: Dict with 'values' key (new flat structure)

        Returns:
            List of enum values
        """
        if isinstance(tag_data, dict) and "values" in tag_data:
            values = tag_data["values"]
            if not isinstance(values, list):
                raise ValueError(f"'values' must be a list")
            return values
        else:
            raise ValueError(f"Tag data must be a dict with 'values' key, got {type(tag_data)}")

    @model_validator(mode="after")
    def validate_enum_values(self) -> "TagDictionary":
        """Validate that all enum lists are well-formed."""
        for dim_name, tags in self.dimensions.items():
            for tag_name, tag_data in tags.items():
                try:
                    values = self._get_values_list(tag_data)
                    # Check that list is non-empty
                    if len(values) == 0:
                        raise ValueError(f"{dim_name}.{tag_name} has empty enum list")
                    # Validate all values are strings
                    for value in values:
                        if not isinstance(value, str):
                            raise ValueError(f"{dim_name}.{tag_name} has non-string enum value: {value}")
                except ValueError as e:
                    raise ValueError(f"{dim_name}.{tag_name}: {e}")
        return self

    def get_enum_values(self, dim: str, tag: str) -> list[str]:
        """Get all enum values for a dimension and tag.

        Args:
            dim: Dimension name (e.g., "LAW", "ACT")
            tag: Tag name (e.g., "world_structure", "dice_mode")

        Returns:
            List of enum value strings (closed set)

        Raises:
            ValueError: If dimension or tag doesn't exist
        """
        if dim not in self.dimensions:
            raise ValueError(f"Invalid dimension: {dim}")
        if tag not in self.dimensions[dim]:
            raise ValueError(f"Invalid tag: {tag} for dimension: {dim}")

        tag_data = self.dimensions[dim][tag]
        return self._get_values_list(tag_data).copy()

    def get_attested_values(self, dim: str, tag: str) -> list[str]:
        """Get attested enum values (after ruling A, same as get_enum_values).

        Deprecated: After 2026-08-21 ruling A, attested = all values.

        Args:
            dim: Dimension name (e.g., "LAW", "ACT")
            tag: Tag name (e.g., "world_structure", "dice_mode")

        Returns:
            List of enum value strings (same as get_enum_values)

        Raises:
            ValueError: If dimension or tag doesn't exist
        """
        return self.get_enum_values(dim, tag)

    def get_proposed_values(self, dim: str, tag: str) -> list[str]:
        """Get proposed enum values (after ruling A, always empty list).

        Deprecated: After 2026-08-21 ruling A, all proposed values were promoted to attested.

        Args:
            dim: Dimension name (e.g., "LAW", "ACT")
            tag: Tag name (e.g., "world_structure", "dice_mode")

        Returns:
            Empty list (no proposed values after ruling A)

        Raises:
            ValueError: If dimension or tag doesn't exist
        """
        if dim not in self.dimensions:
            raise ValueError(f"Invalid dimension: {dim}")
        if tag not in self.dimensions[dim]:
            raise ValueError(f"Invalid tag: {tag} for dimension: {dim}")
        return []

    def validate_enum_value(self, dim: str, tag: str, value: str) -> bool:
        """Validate if a value is in the closed enum set.

        Args:
            dim: Dimension name (e.g., "LAW", "ACT")
            tag: Tag name (e.g., "world_structure", "dice_mode")
            value: Value to validate

        Returns:
            True if value is valid, False otherwise
        """
        try:
            enum_values = self.get_enum_values(dim, tag)
            return value in enum_values
        except ValueError:
            return False


def load_tag_dictionary() -> TagDictionary:
    """Load tag dictionary from YAML.

    Returns:
        TagDictionary instance with loaded and validated data

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        ValueError: If YAML structure is invalid
    """
    yaml_path = Path(__file__).parent.parent / "config" / "tag_dictionary.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Tag dictionary YAML not found: {yaml_path}")

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")

    return TagDictionary(dimensions=data)


# Global cache for loaded dictionary
_dictionary_cache: TagDictionary | None = None


def _get_dictionary() -> TagDictionary:
    """Get cached dictionary instance, loading if necessary."""
    global _dictionary_cache
    if _dictionary_cache is None:
        _dictionary_cache = load_tag_dictionary()
    return _dictionary_cache


def get_enum_values(dim: str, tag: str) -> list[str]:
    """Convenience function to get enum values for a dimension and tag.

    This is a module-level convenience wrapper around TagDictionary.get_enum_values().
    Used by dimension.py and other modules that need direct access without maintaining
    a dictionary instance.

    Args:
        dim: Dimension name (e.g., "LAW", "ACT")
        tag: Tag name (e.g., "world_structure", "dice_mode")

    Returns:
        List of enum value strings (closed set)

    Raises:
        ValueError: If dimension or tag doesn't exist
    """
    dictionary = _get_dictionary()
    return dictionary.get_enum_values(dim, tag)
