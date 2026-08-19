"""Tag and enum dictionary for 断点A data layer.

Provides YAML-based tag and enum value dictionary for 6 constraint dimensions
plus A2 additions (LOC and STY).

Core interface:
- load_tag_dictionary(): Load and validate dictionary
- get_enum_values(dim, tag): Query enum values for a dimension.tag
- validate(dim, tag, value): Check if value is in closed enum set
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class TagDictionary(BaseModel):
    """Tag and enum dictionary model."""

    dimensions: dict[str, dict[str, list[str]]] = Field(
        description="Dimension -> tag -> enum values mapping"
    )

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, v: dict[str, dict[str, list[str]]]) -> dict[str, dict[str, list[str]]]:
        """Validate that all required dimensions exist."""
        required_dims = ["LAW", "ACT", "NAR", "WST", "SOC", "RED", "LOC", "STY"]
        for dim in required_dims:
            if dim not in v:
                raise ValueError(f"Missing required dimension: {dim}")
        return v

    @model_validator(mode="after")
    def validate_enum_values(self) -> "TagDictionary":
        """Validate that all enum lists are non-empty."""
        for dim_name, tags in self.dimensions.items():
            for tag_name, enum_values in tags.items():
                if not isinstance(enum_values, list):
                    raise ValueError(f"{dim_name}.{tag_name} enum values must be a list")
                if len(enum_values) == 0:
                    raise ValueError(f"{dim_name}.{tag_name} has empty enum list")
                for value in enum_values:
                    if not isinstance(value, str):
                        raise ValueError(f"{dim_name}.{tag_name} has non-string enum value: {value}")
        return self

    def get_enum_values(self, dim: str, tag: str) -> list[str]:
        """Get enum values for a dimension and tag.

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

        return self.dimensions[dim][tag]

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
