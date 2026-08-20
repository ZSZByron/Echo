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
    """Tag and enum dictionary model with layered traceability support.

    Supports both legacy flat structure and new layered structure:
    - Legacy: tag -> [values]
    - Layered: tag -> {attested: [...], proposed: [...]}
    """

    dimensions: dict[str, dict[str, Any]] = Field(
        description="Dimension -> tag -> enum values (or layered structure)"
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

    def _normalize_tag_data(self, tag_data: Any) -> dict[str, list[str]]:
        """Normalize tag data to layered structure.

        Args:
            tag_data: Either a list (legacy) or dict with attested/proposed keys

        Returns:
            Dict with attested and proposed keys
        """
        if isinstance(tag_data, list):
            # Legacy flat structure - treat all as proposed
            return {"attested": [], "proposed": tag_data}
        elif isinstance(tag_data, dict):
            # New layered structure
            if "attested" not in tag_data or "proposed" not in tag_data:
                raise ValueError(f"Tag data must have both 'attested' and 'proposed' keys")
            if not isinstance(tag_data["attested"], list):
                raise ValueError(f"'attested' must be a list")
            if not isinstance(tag_data["proposed"], list):
                raise ValueError(f"'proposed' must be a list")
            return tag_data
        else:
            raise ValueError(f"Tag data must be list or dict, got {type(tag_data)}")

    @model_validator(mode="after")
    def validate_enum_values(self) -> "TagDictionary":
        """Validate that all enum lists are well-formed."""
        for dim_name, tags in self.dimensions.items():
            for tag_name, tag_data in tags.items():
                try:
                    normalized = self._normalize_tag_data(tag_data)
                    # Check that combined list is non-empty
                    combined = normalized["attested"] + normalized["proposed"]
                    if len(combined) == 0:
                        raise ValueError(f"{dim_name}.{tag_name} has empty enum list")
                    # Validate all values are strings
                    for value in combined:
                        if not isinstance(value, str):
                            raise ValueError(f"{dim_name}.{tag_name} has non-string enum value: {value}")
                except ValueError as e:
                    raise ValueError(f"{dim_name}.{tag_name}: {e}")
        return self

    def get_enum_values(self, dim: str, tag: str) -> list[str]:
        """Get all enum values for a dimension and tag (attested + proposed).

        This maintains backward compatibility - returns the complete set.

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
        normalized = self._normalize_tag_data(tag_data)

        # Return merged attested + proposed
        return normalized["attested"] + normalized["proposed"]

    def get_attested_values(self, dim: str, tag: str) -> list[str]:
        """Get only attested enum values (from hierarchy L105-130).

        These are the values explicitly mentioned in the authoritative source.

        Args:
            dim: Dimension name (e.g., "LAW", "ACT")
            tag: Tag name (e.g., "world_structure", "dice_mode")

        Returns:
            List of attested enum value strings

        Raises:
            ValueError: If dimension or tag doesn't exist
        """
        if dim not in self.dimensions:
            raise ValueError(f"Invalid dimension: {dim}")
        if tag not in self.dimensions[dim]:
            raise ValueError(f"Invalid tag: {tag} for dimension: {dim}")

        tag_data = self.dimensions[dim][tag]
        normalized = self._normalize_tag_data(tag_data)
        return normalized["attested"].copy()

    def get_proposed_values(self, dim: str, tag: str) -> list[str]:
        """Get only proposed enum values (extension proposals).

        These are values added by the previous agent, pending user confirmation.

        Args:
            dim: Dimension name (e.g., "LAW", "ACT")
            tag: Tag name (e.g., "world_structure", "dice_mode")

        Returns:
            List of proposed enum value strings

        Raises:
            ValueError: If dimension or tag doesn't exist
        """
        if dim not in self.dimensions:
            raise ValueError(f"Invalid dimension: {dim}")
        if tag not in self.dimensions[dim]:
            raise ValueError(f"Invalid tag: {tag} for dimension: {dim}")

        tag_data = self.dimensions[dim][tag]
        normalized = self._normalize_tag_data(tag_data)
        return normalized["proposed"].copy()

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
