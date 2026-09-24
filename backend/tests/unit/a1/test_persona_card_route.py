"""人格卡 additive 端点契约测试（M4c，plan §279/284）。

契约（impulse-coords 端点先例同款 additive 模式）：
- GET /api/a1/file/{file_id}/persona-card → 确定性卡面（零 LLM）；
- 数据源 = creator_profile + impulse_coords（start_session impulse_primary
  锚点入卡）；
- 404 契约族照搬（未知 file_id）；
- 存量端点零扰动（additive-only，不动既有路由）。

TDD RED：端点接线前本文件全部失败。
"""


class TestPersonaCardEndpoint:
    def test_returns_deterministic_card(self, client):
        from app.api import a1_routes

        resp = client.post(
            "/api/a1/session/start",
            json={
                "user_id": "u_pc",
                "seed_id": 1,  # start 门禁：seed_id/custom_idea 二选一（M4a 先例）
                "impulse_primary": "plot",
            },
        )
        assert resp.status_code == 200
        file_id = resp.json()["file_id"]

        got1 = client.get(f"/api/a1/file/{file_id}/persona-card")
        got2 = client.get(f"/api/a1/file/{file_id}/persona-card")
        assert got1.status_code == 200
        assert got1.json() == got2.json()  # 确定性：同会话两次拉取同卡面
        body = got1.json()
        assert body["file_id"] == file_id
        assert body["name"] == "ECHO 创作人格"  # 未决③ 占位
        assert body["sources"]["creator_primary"] == "plot"
        assert body["sources"]["axis"] == 70  # plot 锚点（spec L309）
        assert body["one_line_reading"]

    def test_unknown_file_404(self, client):
        resp = client.get("/api/a1/file/no_such_file/persona-card")
        assert resp.status_code == 404
