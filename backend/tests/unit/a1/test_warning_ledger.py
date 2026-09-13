"""J3 披露协议 / warning ledger 单元测试（2-A1-v0.5.1 §3 J3）.

所有丢弃点的统一出口：结构化 ledger（source/detail/count/level）。
分级防警告疲劳：丢失性=warn，转换性/开关性=info。
"""
from app.domains.creation.a1.warning_ledger import (
    LEVEL_INFO,
    LEVEL_WARN,
    classify_level,
    entry,
    from_dead_edges,
    from_strings,
)


class TestEntry:
    def test_basic_shape(self):
        e = entry("graphify", "[edges] 引用了不存在的节点，边已丢弃: 'a' → 'b'")
        assert e == {
            "source": "graphify",
            "detail": "[edges] 引用了不存在的节点，边已丢弃: 'a' → 'b'",
            "count": 1,
            "level": "warn",
        }

    def test_explicit_count_and_level(self):
        e = entry("dead_edges", "失效边入死区(endpoint_missing): 3 条",
                  count=3, level=LEVEL_WARN)
        assert e["count"] == 3
        assert e["level"] == LEVEL_WARN


class TestClassifyLevel:
    def test_loss_warnings_are_warn(self):
        for detail in [
            "[edges] 引用了不存在的节点，边已丢弃: 'a' → 'b'",
            "[entries] 非法锚点已丢弃: 'x.y'",
            "[constraint_fields] 约束字段不在白名单，已丢弃: 'LAW.x'",
            "重复条目去重: 't'",
            "重复子条目去重: 't'",
            "children 深度超限(>2层)拒收: x / 't'",
            "标题超32字已截断: 't'",
            "graphify failed: timeout",
            "原文超20000字已截断后解析",
            "[constraint_fields] 非法键跳过: 'bad'",
        ]:
            assert classify_level(detail) == LEVEL_WARN, detail

    def test_conversion_and_switch_warnings_are_info(self):
        for detail in [
            "[edges] 词表外关系已转为开放问题: '师徒'",
            "children 挂载已禁用(A1_DEPTH_CHILDREN=0): x / 't'",
            "锚点无已答条目节点，深度条目跳过: 'x.y'",
        ]:
            assert classify_level(detail) == LEVEL_INFO, detail


class TestFromStrings:
    def test_empty(self):
        assert from_strings("assemble", []) == []

    def test_maps_source_and_classifies(self):
        out = from_strings("assemble", ["重复条目去重: 't'"])
        assert out[0]["source"] == "assemble"
        assert out[0]["level"] == LEVEL_WARN


class TestFromDeadEdges:
    def test_empty(self):
        assert from_dead_edges([]) == []

    def test_aggregates_by_reason_with_count(self):
        dead = [
            {"key": "k1", "from": "a", "to": "b", "relation": "r",
             "reason": "endpoint_missing"},
            {"key": "k2", "from": "c", "to": "d", "relation": "r",
             "reason": "endpoint_missing"},
            {"key": "k3", "from": "e", "to": "f", "relation": "r",
             "reason": "rejected"},
        ]
        out = from_dead_edges(dead)
        assert len(out) == 2
        by_reason = {e["detail"]: e for e in out}
        assert all(e["source"] == "dead_edges" for e in out)
        missing = next(e for e in out if "endpoint_missing" in e["detail"])
        assert missing["count"] == 2
        assert missing["level"] == LEVEL_WARN
        rejected = next(e for e in out if "rejected" in e["detail"])
        assert rejected["count"] == 1

    def test_unknown_reason_bucketed(self):
        out = from_dead_edges([{"key": "k", "reason": ""}])
        assert "unknown" in out[0]["detail"]
