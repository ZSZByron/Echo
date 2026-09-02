# -*- coding: utf-8 -*-
"""Gate-aware sync_position tests (有缺失，在窗口询问)."""

from app.domains.creation.a1.guide_engine import A1Session, sync_position
from app.domains.creation.seed.a1_question_tree import MODULES


def make_session():
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


class TestGateAwareSync:
    """Modules below the 50% gate are asked about FIRST in the chat window."""

    def test_missing_module_preferred_over_minor_fields(self):
        s = make_session()
        # Fill IP定位 to 3/4 (over half); leave 世界本体 empty (gate-failing)
        for f in ["name", "concept", "world_type"]:
            s.answers[f"IP定位.{f}"] = "x"
        sync_position(s)
        assert s.current_module == "世界本体"
        assert s.current_subfield == "origin"

    def test_fallback_global_order_when_no_module_under_gate(self):
        s = make_session()
        # Every module over half except one trailing field in the FIRST module
        for m in MODULES:
            fields = m["fields"]
            for f in fields:
                s.answers[f"{m['id']}.{f['id']}"] = "x"
        # Clear one field in the last module (2 fields -> 1/2 not over half)
        last = MODULES[-1]
        s.answers.pop(f"{last['id']}.{last['fields'][-1]['id']}")
        sync_position(s)
        assert s.current_module == last["id"]

    def test_empty_session_first_module_first_field(self):
        s = make_session()
        sync_position(s)
        assert s.current_module == MODULES[0]["id"]
        assert s.current_subfield == MODULES[0]["fields"][0]["id"]

    def test_all_filled_completes(self):
        s = make_session()
        for m in MODULES:
            for f in m["fields"]:
                s.answers[f"{m['id']}.{f['id']}"] = "x"
        sync_position(s)
        assert s.phase == "completed"
