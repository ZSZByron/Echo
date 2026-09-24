# -*- coding: utf-8 -*-
"""E1-Lite T6 — integration smoke test: one test chain wires the three
features delivered by T1-T3 through the API layer:

1. T1: session/start carries impulse_primary/impulse_secondary -> A1Session
   creator fields persisted (store round-trip).
2. T2: type-driven forward-only queue -> plot session first question lands
   on 历史时间线.main_plot; answering advances sync_position in type order
   without backtracking.
3. T3: tone anchor injection -> _build_prompt output contains the plot
   anchor line ("节奏导向").

Plus finalize gate regression: below-half module still 409 with
missing_sections (baseline behavior preserved).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import A1Session, sync_position
from app.domains.creation.a1.interviewer import RealLLMInterviewer
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    get_subfield,
)
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


class TestE1LiteIntegrationSmoke:
    def test_impulse_session_full_chain(self, client: TestClient) -> None:
        # -- 1. start session through the API layer (T1 fields) --
        resp = client.post(
            "/api/a1/session/start",
            json={
                "user_id": "u_smoke",
                "custom_idea": "赛博朋克都市",
                "impulse_primary": "plot",
                "impulse_secondary": "romance",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()

        session = a1_routes._SESSIONS[payload["session_id"]]

        # -- 2. creator profile persisted, survives store round-trip --
        assert session.creator_primary == "plot"
        assert session.creator_secondary == "romance"
        assert session.creator_profile_source == "impulse_cards"
        restored = A1Session.model_validate(session.model_dump())
        assert restored.creator_primary == "plot"
        assert restored.creator_secondary == "romance"
        assert restored.creator_profile_source == "impulse_cards"

        # -- 3. first question lands on the story field, not time_span --
        fq = payload["first_question"]
        assert fq["section"] == "历史时间线"
        assert fq["sub_id"] == "main_plot"
        sf = get_subfield("历史时间线", "main_plot")
        assert sf is not None
        assert fq["sub_id"] != "time_span"
        time_span = get_subfield("历史时间线", "time_span")
        assert time_span is not None
        assert sf["question"] != time_span["question"]

        # -- 4. interview prompt carries the plot tone anchor (T3) --
        module_ns = SimpleNamespace(
            current_module="世界本体",
            current_subfield="origin",
            answers={},
            seed_name="",
            seed_description="",
            creator_primary="plot",
        )
        prompt = RealLLMInterviewer(provider=None)._build_prompt(
            {"id": "世界本体", "label": "世界本体", "fields": []},
            {"id": "origin", "label": "世界起源", "question": "?", "example": ""},
            module_ns,
        )
        assert '语气锚点（引导与反馈的基调，务必贯彻）：节奏导向："这个设定会制造什么事件？"' in prompt

        # -- 5a. answering advances sync_position forward-only in type order --
        # Gate-aware semantics (preexisting) may defer gate-passed modules'
        # leftover fields to a later pass, so the walk is not linearly
        # monotonic per field. The type-driven invariant tested here:
        # (a) modules are *first visited* in type order (forward-only
        #     module progression, no backtracking to a not-yet-visited
        #     earlier module), and (b) no field is ever asked twice.
        from app.domains.creation.a1.guide_engine import _type_ordered_modules

        type_order = _type_ordered_modules(session)
        order_index = {m: i for i, m in enumerate(type_order)}
        seen: set[str] = set()
        visited_modules: list[str] = []
        guard = 0
        while session.phase != "completed":
            guard += 1
            assert guard <= 40, "sync_position must terminate"
            sync_position(session)
            if session.phase == "completed":
                break
            if session.current_module not in visited_modules:
                visited_modules.append(session.current_module)
            key = f"{session.current_module}.{session.current_subfield}"
            assert key not in seen, f"field asked twice: {key}"
            seen.add(key)
            session.answers[key] = f"答-{key}"
        assert session.phase == "completed"
        # M1 配方语义（DN1）：plot 会话只走故事配方子集——遍历覆盖 =
        # 配方键集（不是全集）；且必为全集真子集（子集断言）。
        recipe_keys = all_subfield_keys(recipe=session.recipe_modules)
        assert sorted(seen) == sorted(recipe_keys)
        assert set(recipe_keys) < set(all_subfield_keys())
        first_visit_idx = [order_index[m] for m in visited_modules]
        assert first_visit_idx == sorted(first_visit_idx), (
            f"module first-visit order deviates from type order: {visited_modules}"
        )

        # -- 5b. finalize gate regression (M1 recipe-scoped, DN1): below-
        # half *in-recipe* module -> 409 with that module in
        # missing_sections; out-of-recipe modules never appear. Fresh
        # session, same impulse profile: leave the recipe's first module
        # (历史时间线, 3 fields) at 1/3 = 33% (below the >50% gate) and
        # fill every other recipe module >50%.
        resp2 = client.post(
            "/api/a1/session/start",
            json={
                "user_id": "u_smoke_gate",
                "custom_idea": "低完成度世界",
                "impulse_primary": "plot",
            },
        )
        assert resp2.status_code == 200
        p2 = resp2.json()
        s2 = a1_routes._SESSIONS[p2["session_id"]]
        assert s2.recipe_modules  # plot recipe landed at start (M1)
        for key in all_subfield_keys(recipe=s2.recipe_modules):
            s2.answers[key] = "预填内容"
        first_mid = s2.recipe_modules[0]
        first = next(m for m in MODULES if m["id"] == first_mid)
        for f in first["fields"]:
            s2.answers.pop(f"{first['id']}.{f['id']}", None)
        # 1 of 3 fields answered — strictly below the 50% gate.
        s2.answers[f"{first['id']}.{first['fields'][0]['id']}"] = "x"
        fin = client.post(f"/api/a1/file/{p2['file_id']}/finalize")
        assert fin.status_code == 409
        detail = fin.json()["detail"]["missing_sections"]
        assert first["id"] in detail
        # Out-of-recipe modules (e.g. IP定位) = 不适用, never listed (DN1).
        assert "IP定位" not in detail
