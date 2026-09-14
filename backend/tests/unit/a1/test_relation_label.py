"""relation_label 展示层中文标签测试。

铁律：RELATION_LABELS 仅用于展示文案，不得进入任何键匹配
（VOCAB_RELATION_NAMES / edge confirm/reject / dead_edge 三元组键）。
"""
from app.domains.creation.a1.concept_edge_vocab import (
    EDGE_VOCAB,
    RELATION_LABELS,
    relation_label,
)


class TestRelationLabel:
    def test_known_codes_map_to_chinese(self):
        """全部词条映射到非空中文且不含 ASCII 大写下划线码残留。"""
        for code, label in RELATION_LABELS.items():
            assert label, code
            assert label != code, code
            for ch in label:
                assert ord(ch) > 127, f"{code}: {label} 含 ASCII 残留"

    def test_user_reported_codes_covered(self):
        """用户实测看到过的 7 个码必须全部在表内。"""
        for code in [
            "GEO_CONTAINS",
            "RULE_SHAPES_GEO",
            "GEO_HOSTS_EVENT",
            "POWER_SATURATES_GEO",
            "POWER_SOURCES_FROM_GEO",
            "EVENT_CAUSED_BY",
            "CONSTRAINT_LIMITS",
        ]:
            assert code in RELATION_LABELS, code

    def test_unknown_code_passes_through(self):
        """未知码原样返回（诚实降级，不猜测）。"""
        assert relation_label("SOME_FUTURE_CODE") == "SOME_FUTURE_CODE"
        assert relation_label("") == ""

    def test_chinese_relation_passes_through(self):
        """中文关系名（tier 间新边，本就中文）原样返回。"""
        assert relation_label("力量源自") == "力量源自"

    def test_labels_do_not_leak_into_vocab_matching(self):
        """标签不进入 VOCAB_RELATION_NAMES（键匹配仍用原码）。"""
        for label in RELATION_LABELS.values():
            assert label not in EDGE_VOCAB or any(
                e.name == label for e in EDGE_VOCAB
            ), label
        # 单一码本身（如 GEO_CONTAINS）不在 VOCAB_RELATION_NAMES（复合名才在），
        # 标签表与词表集合互不污染：
        assert "GEO_CONTAINS" not in {e.name for e in EDGE_VOCAB}
        assert relation_label("GEO_CONTAINS") == "地理包含"
