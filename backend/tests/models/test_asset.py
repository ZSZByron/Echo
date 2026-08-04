"""Tests for Asset model extensions — classification, related nodes, backward compat."""
from __future__ import annotations

import pytest

from app.models.asset import Asset, AssetClassification, AssetType


class TestAssetClassification:
    """Test AssetClassification enum values."""

    def test_enum_values_exist(self) -> None:
        assert AssetClassification.STORY.value == "story"
        assert AssetClassification.EVENT.value == "event"
        assert AssetClassification.ENVIRONMENT.value == "environment"

    def test_enum_construction_from_string(self) -> None:
        assert AssetClassification("story") is AssetClassification.STORY
        assert AssetClassification("event") is AssetClassification.EVENT
        assert AssetClassification("environment") is AssetClassification.ENVIRONMENT

    def test_enum_is_str_enum(self) -> None:
        assert isinstance(AssetClassification.STORY, str)
        assert AssetClassification.STORY == "story"


class TestAssetBackwardCompatibility:
    """Ensure existing Asset instantiation without new fields still works."""

    def test_minimal_fields_default_classification(self) -> None:
        a = Asset(
            id="test_bg",
            type=AssetType.BACKGROUND,
            name="Test",
            parent_scene="scene1",
        )
        assert a.classification is AssetClassification.ENVIRONMENT
        assert a.related_story_node is None
        assert a.related_event_node is None

    def test_existing_field_defaults_unchanged(self) -> None:
        a = Asset(
            id="check_defaults",
            type=AssetType.OBJECT,
            name="DefaultsCheck",
            parent_scene="scene1",
        )
        from app.models.asset import AssetStatus
        assert a.status is AssetStatus.PENDING
        assert a.generation_status == "pending"
        assert a.candidates == []
        assert a.reference_asset_ids == []
        assert a.prompt == ""
        assert a.negative_prompt == ""


class TestAssetNewFields:
    """Test Asset with new fields explicitly set."""

    def test_set_classification_story(self) -> None:
        a = Asset(
            id="test_prop",
            type=AssetType.OBJECT,
            name="Sword",
            parent_scene="scene1",
            classification=AssetClassification.STORY,
            related_story_node="node_123",
        )
        assert a.classification is AssetClassification.STORY
        assert a.related_story_node == "node_123"
        assert a.related_event_node is None

    def test_set_classification_event(self) -> None:
        a = Asset(
            id="test_event",
            type=AssetType.BACKGROUND,
            name="Event BG",
            parent_scene="scene2",
            classification=AssetClassification.EVENT,
            related_event_node="event_456",
        )
        assert a.classification is AssetClassification.EVENT
        assert a.related_story_node is None
        assert a.related_event_node == "event_456"

    def test_all_new_fields_set(self) -> None:
        a = Asset(
            id="full",
            type=AssetType.OBJECT,
            name="Full",
            parent_scene="s",
            classification=AssetClassification.STORY,
            related_story_node="sn1",
            related_event_node="en1",
        )
        assert a.classification is AssetClassification.STORY
        assert a.related_story_node == "sn1"
        assert a.related_event_node == "en1"

    def test_classification_serialization_roundtrip(self) -> None:
        a = Asset(
            id="ser",
            type=AssetType.BACKGROUND,
            name="Ser",
            parent_scene="s",
            classification=AssetClassification.EVENT,
            related_story_node="sn",
            related_event_node="en",
        )
        data = a.model_dump()
        assert data["classification"] == AssetClassification.EVENT
        assert data["related_story_node"] == "sn"
        assert data["related_event_node"] == "en"

        # model_dump(mode='json') for JSON-compatible output
        json_data = a.model_dump(mode="json")
        assert json_data["classification"] == "event"

        # Reconstruct from dict
        b = Asset.model_validate(data)
        assert b.classification is AssetClassification.EVENT
        assert b.related_story_node == "sn"
