"""TDD tests for visual_design_bg_pipeline.parse_worldview_text.

Tests the ✦ section + field:value + ；separator parsing logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend/ to sys.path so `from experiments.xxx import` works
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from experiments.visual_design_bg_pipeline import parse_worldview_text  # noqa: E402

SAMPLE_TEXT = """✦IP定位
name:明华世界；concept:正本清源；world_type:东方仙侠

✦视觉设计
keywords:东方国风、少数民族风情；architecture:中式建筑，传统古典；material:木质，石质

✦玩法设计DNA
player_role:刚筑基入门的弟子"""


def test_parse_single_section_with_multiple_fields():
    """视觉设计节有3个字段，全部正确解析"""
    result = parse_worldview_text(SAMPLE_TEXT)
    visual = result["视觉设计"]
    assert visual["keywords"] == "东方国风、少数民族风情"
    assert visual["architecture"] == "中式建筑，传统古典"
    assert visual["material"] == "木质，石质"


def test_parse_multiple_sections():
    """3个节标记全部识别"""
    result = parse_worldview_text(SAMPLE_TEXT)
    assert "IP定位" in result
    assert "视觉设计" in result
    assert "玩法设计DNA" in result


def test_parse_field_with_chinese_comma_in_value():
    """值内的中文逗号，不应分割字段"""
    result = parse_worldview_text(SAMPLE_TEXT)
    assert result["视觉设计"]["architecture"] == "中式建筑，传统古典"


def test_parse_section_with_name_field():
    """IP定位节的name字段正确解析"""
    result = parse_worldview_text(SAMPLE_TEXT)
    assert result["IP定位"]["name"] == "明华世界"
    assert result["IP定位"]["concept"] == "正本清源"


def test_parse_empty_text_returns_empty_dict():
    """空文本返回空dict"""
    assert parse_worldview_text("") == {}


def test_parse_no_section_marker_returns_empty():
    """无节标记的文本返回空dict"""
    assert parse_worldview_text("just some text without markers") == {}


def test_parse_section_with_no_fields_returns_empty_dict():
    """节标记存在但无字段，返回空dict值"""
    text = "✦空节\n"
    result = parse_worldview_text(text)
    assert result["空节"] == {}


def test_parse_real_minghua_file_structure():
    """用真实明华修仙.txt的视觉设计节结构测试"""
    real_text = """✦视觉设计
keywords:东方国风、少数民族风情、异域风情、奇幻种族美感；architecture:中式建筑，传统古典，未来主义；material:木质，石质，少数用金属"""
    result = parse_worldview_text(real_text)
    assert result["视觉设计"]["keywords"] == "东方国风、少数民族风情、异域风情、奇幻种族美感"
    assert result["视觉设计"]["architecture"] == "中式建筑，传统古典，未来主义"
    assert result["视觉设计"]["material"] == "木质，石质，少数用金属"
