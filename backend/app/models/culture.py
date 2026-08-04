"""CultureTree models for cultural metadata."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CultureNode(BaseModel):
    """文化树节点（递归结构）。"""
    id: str
    name: str
    description: str
    values: list[str] = Field(default_factory=list)
    aesthetic_principles: list[str] = Field(default_factory=list)
    child_nodes: list[CultureNode] = Field(default_factory=list)


class CultureTree(BaseModel):
    """文化树。"""
    id: str
    name: str
    root: CultureNode
    version: str = "1.0"
