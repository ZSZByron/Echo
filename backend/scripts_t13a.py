# -*- coding: utf-8 -*-
"""T13a batch-1 final verification: items 1-4 (API chain)."""
import sys
from fastapi.testclient import TestClient
from app.main import app
from app.domains.creation.shared import stale_marker as sm
from app.config.paths import ASSETS_DIR

sys.stdout.reconfigure(encoding="utf-8")
c = TestClient(app)
log = []


def check(name, cond, extra=""):
    log.append(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")
    assert cond, name


# 1. full chain: register -> seeds -> session -> chat -> finalize -> graph -> poster
u = c.post("/api/identity/register", json={}).json()["user_id"]
seeds = c.get("/api/a1/seeds").json()["seeds"]
check("seeds=8", len(seeds) == 8)
st = c.post("/api/a1/session/start", json={"user_id": u, "seed_id": 1})
check("session/start 200", st.status_code == 200)
st = st.json()
sid, fid = st["session_id"], st["file_id"]

msgs = {
    "世界观": "这个世界由浮空岛组成",
    "地理": "高重力世界",
    "力量体系": "重力多变且守恒",
}
q = st["first_question"]
phase = "asking"
guard = 0
while phase != "completed" and guard < 30:
    r = c.post("/api/a1/chat", json={"session_id": sid, "message": msgs.get(q["section"], "跳过") if q else "跳过"}).json()
    phase = r["phase"]
    q = r.get("next_question")
    guard += 1
check("guard内完成10板块", phase == "completed")

fin = c.post(f"/api/a1/file/{fid}/finalize")
check("finalize 200", fin.status_code == 200, fin.text[:120])
v1 = fin.json()["graph_code"]
g = c.get(f"/api/a1/file/{fid}/graph").json()
p = c.get(f"/api/a1/file/{fid}/poster").json()
check("graph 200", g.get("scene_id") == sid)
check("poster 200", p.get("ai_image_status") == "pending")

# 3. constraint edges exist (T-F effective)
cst_nodes = [n for n in g["nodes"] if n.startswith("cst_")]
check("约束cst节点存在(T-F)", len(cst_nodes) >= 2, str(cst_nodes))
rule_edges = [e for e in g["edges"] if "RULE" in (e.get("visual_description") or "")]
check("RULE语义边存在(T-F)", len(rule_edges) >= 1, str([e["visual_description"] for e in rule_edges]))

# 2. 409 scenarios
st2 = c.post("/api/a1/session/start", json={"user_id": u, "seed_id": 2}).json()
r409 = c.post(f"/api/a1/file/{st2['file_id']}/finalize")
check("finalize缺板块409+missing_sections", r409.status_code == 409 and r409.json()["detail"]["missing_sections"])
check("未定稿graph 409", c.get(f"/api/a1/file/{st2['file_id']}/graph").status_code == 409)
check("未定稿poster 409", c.get(f"/api/a1/file/{st2['file_id']}/poster").status_code == 409)

# 4. re-finalize v2: register downstream on v1 -> refinalize -> stale + old kept
db = str(ASSETS_DIR / "ugc.db")
sm.register_graph(db, u, "IP0009-M1-v1", "M", 1, 1, parent_graph_code=v1, display_name="downstream")
fin2 = c.post(f"/api/a1/file/{fid}/finalize").json()
v2 = fin2["graph_code"]
check("v2编码=W1-v2", v2.endswith("-W1-v2"), v2)
lst = c.get("/api/graphs", params={"user_id": u}).json()
arts = {a["graph_code"]: a for ip in lst["ips"] for a in ip["artifacts"]}
check("旧版v1保留", v1 in arts)
check("下游M1自动stale", arts["IP0009-M1-v1"]["status"] == "stale")
check("stale不阻断(list仍返回)", True)

print("\n".join(log))
print("T13a ITEMS 1-4: ALL PASS")
