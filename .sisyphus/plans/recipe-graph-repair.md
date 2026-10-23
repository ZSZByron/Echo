# 配方定稿图谱修复施工单（B1/B2/B3，2026-10-19 真机病理）

## TL;DR
> 故事向配方（剧情+角色）定稿后三视图空白——graph_json 仅剩 bg 根。三病灶：
> B1 `_build_graph` 硬编码世界观 MODULES（致命）/ B2 graphify 对 AnswerNode len() 崩 / B3 图数据无大陆归属。
> 修法全部已定位到行级，红测已起草。执行代理按本单施工，主会话验证收锤。

## 病理证据（已实证，2026-10-19）
- 真机会话 a1_de6af146e371（recipe=剧情,角色，15 答案，角色.key_relations 为 AnswerNode）
- finalize_warnings: `graphify failed: object of type 'AnswerNode' has no len()`
- graph_json：仅 bg_a1_de6af level=1，0 边
- 复现脚本：MODULES（10 世界观模块）不含 剧情/角色 → assemble 零匹配

## 修复清单

### B1（致命）：a1_routes.py L573
```python
# 旧（错误）：
        assemble_background_tree(
            _answers_view(session), MODULES, session.ip_code, session.session_id,
# 新（正确）：
        assemble_background_tree(
            _answers_view(session),
            [m for m in (get_module(mid) for mid in _recipe_module_ids(session)) if m],
            session.ip_code, session.session_id,
```
- `get_module` 已在 L105 导入；`_recipe_module_ids` 在 L1325（运行时解析，定义序无碍）
- 若 MODULES（L102 导入）在全文件再无使用 → 从导入清单移除（防 ruff F401）

### B2：graphify.py graphify_llm 入口摊平（L636-641 循环内）
```python
        raw_answers = getattr(session, "answers", {}) or {}
        answers: dict[str, str] = {}
        n_clips = 0
        for k, v in raw_answers.items():
            # D23 契约：prompt 只收 plain strings（AnswerNode 先摊平）
            if not isinstance(v, str):
                from app.domains.creation.a1.guide_engine import answer_view
                v = answer_view(v)
            clipped_value, was_clipped = clip_answer(v)
```
- 惰性导入防层级问题（guide_engine 不 import graphify，无循环）

### B3 后端：
1. `app/models/knowledge_graph.py` GraphNode additive 加字段：
```python
    continent: str = ""  # L1 大陆归属（THREE_TIER_TREE；活地图消费，旧载荷缺省空串）
```
2. `live_projection.py` 加纯函数 + L2 装配处（L65-71 GraphNode(...)）填 continent：
```python
def module_continent(module_id: str) -> str:
    """旧/新模块 id → THREE_TIER_TREE L1 归属；未知返回空串（诚实降级）。"""
    from app.domains.creation.seed.story_modules import THREE_TIER_TREE
    for l1 in THREE_TIER_TREE:
        for l2 in l1.get("l2", []):
            if l2.get("id") == module_id:
                return str(l1.get("id", ""))
    return ""
```
   L2 节点构造加 `continent=module_continent(module_id),`

### B3 前端：
1. `frontend/src/types/graph.ts` GraphNode 加 `continent?: string;`（tier 注释附近）
2. `frontend/src/components/graph/WorldMap.tsx` 重写 buildContinentMap：
   - L2 判定只认 `n.level === 2`（废弃 `n.tier === 2` 误用与 serial 首段虚构映射）
   - 归属用 `n.continent`；无归属/未知 id 不点亮（诚实）
   - `totalAnswered` 改为各大陆集合 size 之和
3. `WorldMap.test.tsx` fixture 的 L2 节点加 continent 字段（worldview 两个 → 断言不变）
4. `tests/e2e/a1-wave3-frontend.spec.ts` GRAPH_RESPONSE 的 m-1-1/m-2-1 加 `continent: 'worldview'`（幕三断言不变）

## 红测（新文件，内容已全文起草——见委派 prompt）
`backend/tests/unit/a1/test_recipe_graph_repair.py`：三类（故事配方定稿集成 / graphify 摊平单元 / module_continent 单元）

## 验证门禁
- 新测试文件全绿；pytest 全量 ≥1838+5 全绿
- vitest 全量 ≥330 全绿（WorldMap 测试更新后计数不变或 +0）
- tsc -b delta=0（相对 21 处存量）
- Playwright scene 3（活地图）重跑绿
- 真机补救：POST /api/a1/file/278d7114b0ab4990bee1de95a1894ed4/finalize（重定稿 v2）→ GET graph 断言 L2≥2/L3≥15/边≥17/continent 在

## 红线
- 不动 guide_engine / interviewer / story_modules 业务逻辑
- GraphNode 加字段必须 additive（默认空串，旧 JSON 兼容）
- 不顺手修 21 处 pre-wave3 前端存量类型错误
- 提交分原子笔：B1+B2 后端修复+红测一笔 / B3 后端一笔 / B3 前端一笔 / 治理一笔（主会话收锤时代理只做前三笔，治理归主会话）
