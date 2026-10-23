# 方向A一期「选项前置」施工计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **裁决依据**: docs/plans/2026-10-08-方向A一期选项前置-施工单.md（拍板 1/2/5 落痕 + 3 暂定 + 4/6 在途）/ docs/plans/2026-10-08-灵感式访谈引导-问题说明书.md / Metis 预规划审查 2026-10-08（七缺口全数吸收，三个决策默认已定见下表）
> **目标**: 灵感从失败补偿变默认服务——每问默认附带 3 个 AI 生成选项（贴合种子+已答内容），用户可自由输入 / 序号直选 / 换一批 / 揉合；道歉话术退役。
> **架构**: 生成权 LLM（InterviewResult 增 examples 可选键，与 fills 同 prompt 同返回——拍板 2 合并单次调用）/ 执行权引擎（guide_engine 单点消费，D20 模式沿用）；**examples 缺失 = 逐字节旧行为**（降级模式照抄 suggest_examples L636-651 先例）；选项渲染 = reply 纯文本行，前端零触碰。
> **技术栈**: FastAPI + Pydantic v2 / pytest（FakeInterviewer examples 基建已就位：interviewer.py L125/L138/L147）。
> **门禁**: pytest 全量 ≥1588+新增全绿；tsc 零新增（存量 20 条不增）；vitest 310+全绿；C1-C11 存量契约不删改（唯一例外见红线第 8 条）。

---

## 红线（Must NOT——施工单边界七条 + Metis 加固三条）

1. 不动 D19 配方边界（本计划仅配方内体验层）。
2. 不动 D21 单问句铁律——规则块 8.5（interviewer.py L574-587）本体与编号零改动；新规则块 8.6 自带防火墙条款。
3. 不动 D23 语义合并 / AnswerNode / 撤销。
4. 不动问题文案本体与静态模板 question/hint 字段结构（个性化走选项注入）。
5. 不做 B 的镜子三拍 / 抛回通道，不做 C 的 playbook 化，不动收尾三连问。
6. 前端零触碰：选项必须是 reply 纯文本行——禁止顺手加选项卡片组件、禁止改前端渲染正则。后端 next_question payload **additive** 加 `options` 键不算触碰（前端不消费即无感）。
7. 不动 stall≥3 forced_allocate；只删 stall==2 的示例+道歉分支。禁止顺手重构 stall 守卫其余部分。
8. 既有测试断言不删改——**唯一例外**：直接断言"我没能准确理解你的回答"/stall==2 示例分支的存量测试（施工单 §2.2 明令删除道歉话术，产品方拍板优先）。T1 第一步先 grep 逐条列出报产品方备案，再改写。
9. 埋点不扩 impulse_coords 信号闭集（拍板 6 未拍）——只落结构化日志。
10. T0（D23 遗留 E2E 冒烟）未出证据前，禁动 T2 及以后（施工单 §5 落锤顺序 + "两个 LLM 特性同场调试无法归因"）。

---

## 设计决策（默认已定 · 产品方保留改口权——依据 Metis 建议 + 施工单"禁范围膨胀"精神）

| # | 决策点 | 默认裁决 | 依据与改口代价 |
|---|---|---|---|
| D-1 | 序号歧义 | 维持确定性精确匹配：`text.strip()` 恰为 `1`/`2`/`3` 且 `current_options` 非空才直选；非精确引用（"选2吧"/"1和3揉一起"/"第1点对"）走 LLM 理解路径（8.6 含引用理解条款） | Metis 方案 b。误劫持率交 E0 观察台，二期再议升级 LLM 判别。改口=只动一个 if |
| D-2 | reroll 通道 | 确定性关键词闭集 `{"换一批","再来一批","换组"}` 触发（`current_options` 非空才生效）→ 复用 `suggest_examples` 独立调用（**例外于合并单次承诺，按次 +1**）；**不计 stall**；连续上限 2 次（第三次提示改用自由输入/直选，不再生成） | Metis：纯生成轮与 interview"理解本轮输入"职责冲突，不可复用。改口=换触发词表或上限值 |
| D-3 | 选项存储 | 新字段 `A1Session.current_options: list[str]`（additive）；`pending_suggestions` 随 stall==2 分支退役为死字段（不删不写）；序号直选路径改读新字段 | Metis：pending_suggestions 有 7+ 清偿点（L912/987/1036/1076/1142/1161/1262-1264），复用会"选项闪现即消失"。改口=T3 返工一天 |
| D-4 | pick 真值闸 | 直选选项文本直填、不过占位词真值闸（豁免留痕：选项来自受控生成、天然非占位词；与空字段首填自动写入同权——D23 法理先例） | 现状 L1259 先例维持。改口=pick 改走 fills 确认流，UX 变重 |
| D-5 | stall 阈值 | 阈值不动（≥3 forced_allocate 照旧）；选项在场本身即缓冲，且 stall 计数保留供埋点观察 | Metis 提示的决策点，从简处理。改口=阈值改 4，一行 |
| D-6 | 揉合 | = 用户自由输入，零特殊通道：走完整 fills 理解管线（含 D23 语义分流 / write-guard / confirm），选项只是素材 | Metis：最安全。无改口必要 |
| D-7 | 调用数口径 | 施工单拍板 2 的承诺修正表述为："**默认路径调用数不变；reroll 按次 +1（上限 2）**" | Metis 假设 1 校正。已在计划留痕，无需产品方再拍 |

---

## T0 [清偿 · 前置闸门] D23 遗留 E2E 冒烟（施工单 §5 第一锤）

**Files:**
- Evidence: `.sisyphus/evidence/d23-e2e-smoke/`（截图 + 网络日志 + 回执 md，untracked 不入库）

**Steps:**
1. 前置检查：`backend\.env` 是否有 `ACTIVE_PROVIDER` 对应密钥（`Test-Path` + Select-String 键名，**不回显值**）。无密钥 → 记 BLOCKED 项，转 TestClient 级重放（引擎级 C10 已覆盖，浏览器级标注"待真机"），BLOCKED 留痕不阻塞后续锤。
2. 起栈：后端 `backend\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000`；前端 `cd frontend && npm run dev`（README 方法一）。验证 `/api/health` 200 + `/a1` 可达。
3. Playwright 重放 IP0065 四撞墙路径（D23 验收的四条）：
   - S1 等价新说法（"平凡的度过一生"类换述）→ 期望：自动合并 + 轻披露条 + 可撤销；
   - S2 补充新信息（"老父亲"）→ 期望：key_relations 子条目追加；
   - S3 澄清回复（九关键词外的人话）→ 期望：意图分类生效不复读；
   - S4 AutoMergeBar 撤销 → 期望：恢复旧值。
4. 每路径截图 + 关键网络请求（/api/a1/chat 响应体）存证据目录；`d23-e2e-smoke-report.md` 逐条记 过/不过/BLOCKED。
5. 回执：四路径结论表 + BLOCKED 清单。**证据齐 = T2 解锁**。

**Commit**: 无（纯证据，.sisyphus 不入库）。

---

## T1 [后端] 契约测试先红 + 存量断言备案

**Files:**
- Create: `backend/tests/unit/a1/test_option_forward.py`

**Step 1: 存量断言备案（红线 8 例外清单）**
- `Select-String -Path backend\tests -Pattern '我没能准确理解|示例方向' -Recurse` → 逐条列出文件:行号 → 写进本计划执行回执（报产品方备案），这些是唯一允许改写的存量测试。

**Step 2: 写契约测试（16 条，FakeInterviewer 注入三态：正常/缺失/畸形）**
1. `test_examples_default_attached`：interview 返回 examples=["a","b","c"] → reply 含邀请话术常量 + 三行 `1. a` 格式选项。
2. `test_examples_missing_degrades`：examples=[] → reply 与现行行为逐字节一致（无选项、无道歉、无新话术）。
3. `test_examples_malformed_degrades`：LLM 返回 examples 非 list（构造畸形 JSON 路径）→ 同上降级。
4. `test_no_options_on_deflect_turn`：deflect=True 轮 → reply 无选项。
5. `test_no_options_on_story_material_turn`：story_material 轮 → 无选项。
6. `test_no_options_when_no_current_subfield`：completed 阶段 → 无选项。
7. `test_no_options_on_proposal_pending_turn`：write-guard 拦截成提案轮 → 无选项。
8. `test_pick_option_fills`：current_options=["x","y","z"] + 输入 "1" → 直填 x + stall 清零 + 埋点 option_pick 事件。
9. `test_reroll_keyword_regenerates`：current_options 非空 + 输入 "换一批" → suggest_examples 被调 + 选项替换 + **stall_count 不变** + 埋点 option_reroll。
10. `test_reroll_cap_two`：连续第三次 "换一批" → 不调生成、提示改用自由输入/直选。
11. `test_skip_then_next_question_has_options`：跳过 → 下一问 reply 带新字段选项（无死路）。
12. `test_apology_path_removed`：构造 stall==2 场景 → reply **无**"我没能准确理解"（stall 计数照常累计）。
13. `test_merge_reference_goes_understanding`：输入 "把1和3揉一起" → 走 interview 理解（FakeInterviewer 返回 fills）而非直选劫持。
14. `test_options_refreshed_on_advance`：字段推进后 current_options 为新字段的选项（非上字段残留）。
15. `test_prompt_firewall_clause`：interview system prompt 字符串断言含防火墙条款文本 + 引用理解条款 + 8.5 原文未动。
16. `test_telemetry_events_emitted`：pick / skip / stall 三事件各断言 JSON-lines 具体 key-value（含 session id、module.subfield、option_index / stall_count）。

**Step 3:** `pytest backend/tests/unit/a1/test_option_forward.py -v` → 全红（功能未实现）→ 进入 T2。

**Commit:** `test(a1): option-forward contract tests (16 red)`

---

## T2 [后端] interviewer：InterviewResult.examples + 合并 prompt（规则块 8.6）

**Files:**
- Modify: `backend/app/domains/creation/a1/interviewer.py`（InterviewResult L75-97；规则区 L560-587 一带；LLM 实现的 interview 主实现在 L883+）

**Step 1: InterviewResult 增可选键（契约豁免先例 G10/G6b——新增可选键向前兼容，旧解析器忽略未知键）**
```python
# 方向A一期（2026-10-08 施工单拍板 2）：默认选项生成通道——与 fills
# 同 prompt 同返回（合并单次调用）。空 list = 降级（reply 行为与改造前
# 逐字节一致，降级模式照抄 suggest_examples L636-651 先例）。
examples: list[str] = Field(default_factory=list)
```

**Step 2: 规则块 8.6（编号衔接 8.5 之后，8.5 本体零改动）——三段：**
1. **生成任务**（约束逐字搬运 suggest_examples prompt L601-633 的既有纪律，不新造文案）：
   > 8.6 默认示例生成：除理解用户输入外，同时为【当前问题】所指字段生成 3 个具体的中文示例方向——必须贴合【种子起点】基调、与【用户已确定的内容】兼容、彼此风格差异化、每个不超过 40 字。故事向会话：示例必须从用户已答的剧情、角色、情感线索延伸（引用用户已答内容里的具体关键词），严禁输出势力、政治、阵营类世界建构模板示例。
2. **引用理解条款**：
   > 用户回复若引用示例序号（如「选2吧」「把1和3揉一起」「第1点对」），结合示例内容理解并生成对应 fills，不要当作纯数字。
3. **防火墙条款（单问句铁律的 A 期防火墙）**：
   > 示例必须是陈述句；guidance_reply 与示例中严禁出现任何新的疑问句——全回复唯一疑问句仍是 8.5 规定的当前问题本身。
4. JSON 返回 schema 增键：`"examples": ["...", "...", "..."]`；解析端 `raw.get("examples")` 非 list / 元素非 str / 空 → `[]`（静默降级，不重试不报错）。

**Step 3:** 旧全量测试跑绿（可选键零破坏）→ 新契约 1/2/3/13/15 转绿。

**Step 4: Commit:** `feat(a1): merged examples generation in interview (rule 8.6 + firewall)`

**注意：** `suggest_examples` 方法**保留不删**——它转任 T4 的 reroll 引擎（纯生成轮职责，Metis D-2）。

---

## T3 [后端] guide_engine：current_options 接线 + 清偿点审计 + stall 守卫简化

**Files:**
- Modify: `backend/app/domains/creation/a1/guide_engine.py`（A1Session L316 一带；_handle_message_impl L1192+；序号直选 L1251-1280；_apply_stall_guard L883-1028；跳过路径 L1223-1247；_question_payload L435-451）

**Step 0: 清偿点审计（Metis MUST——先枚举后动手）**
- `lsp_find_references(pending_suggestions)` 或 ast_grep 枚举全部触点（已知锚点 L912/987/1036/1076/1142/1161/1262-1264）→ 列表写进执行回执 → 逐一确认新字段行为（推进=换新、reset=清空、pick=消费）。

**Step 1: A1Session 增字段（additive，D-3）**
```python
# 方向A一期：当前问的默认选项（D-3 新字段——pending_suggestions 随
# stall==2 分支退役为死字段：不删不写，零迁移）。空 = 本轮无选项。
current_options: list[str] = Field(default_factory=list)
# D-2：连续 reroll 计数（上限 2；任一非 reroll 输入清零）。
reroll_streak: int = 0
```

**Step 2: 主路径接线（_handle_message_impl）**
- interview() 返回后，**白名单判定**（Metis 白名单表——以下轮次 `current_options` 置空且不渲染选项）：deflect 轮 / story_material 轮 / write-guard 提案挂起轮（`proposals` 非空）/ forced_allocate 轮 / 无当前子字段（completed）。
- 白名单外：`result.examples` 非空 → `session.current_options = result.examples`，reply 末尾追加渲染；examples 为空 → `current_options = []`，reply 不追加任何文本（降级=旧行为）。
- 邀请式话术**单点常量**（拍板 3 暂定，产品方保留改口权——改文案只动这一处）：
```python
OPTION_INVITE_TEMPLATE = (
    "这里有几个方向，也可以直接说你的：\n{lines}\n"
    "（回复序号可直选，想换个方向就说「换一批」）"
)
```

**Step 3: 序号直选改读新字段（L1251-1280）**
- `pending_suggestions` → `current_options`（判断与消费同步替换）；pick 后 `current_options=[]`、stall 清零、埋点（T5 接线点预留 `# telemetry: option_pick` 注释锚）。

**Step 4: stall 守卫简化（只删一段）**
- 删除 `_apply_stall_guard` 中 stall==2 的示例+道歉分支（L930-959）——stall 计数逻辑保留（stall_subfield/stall_count 照常累计，供 stall≥3 forced_allocate 与埋点消费）；`pending_suggestions` 相关读写随之退役（死字段不删）。
- **禁止**触碰 stall≥3 分支（红线 7）。

**Step 5: 跳过路径（L1223-1247）**
- 零结构改动：跳过 → sync_position 推进 → 下一问经主路径默认带新字段选项（契约 11 自然满足）；`reroll_streak` 清零。

**Step 6: payload additive**
- `_question_payload` 返回 dict 增键 `"options": list(session.current_options)`（前端不消费即无感——红线 6 允许的后端 additive）。

**Step 7:** 契约 4/5/6/7/8/11/12/14 转绿；全量 pytest 门禁复跑。

**Commit:** `feat(a1): default options wired through guide_engine (stall apology path removed)`

---

## T4 [后端] reroll 通道（换一批）

**Files:**
- Modify: `backend/app/domains/creation/a1/guide_engine.py`（_handle_message_impl 判断链）

**Step 1: 触发链插入位置（顺序敏感）**
```
跳过（L1223）→ 序号直选（L1251，读 current_options）
→ 【新】reroll 关键词（"换一批"/"再来一批"/"换组"，current_options 非空才生效）
→ interview() 主路径
```
- 命中 reroll：`reroll_streak >= 2` → 提示"先试试直接选一个，或用自己的话说说"（不生成、不调 LLM）；否则 `interviewer.suggest_examples(session, mid, sid)` 独立调用（+1 次，D-2 例外留痕）→ 替换 `current_options` → `reroll_streak += 1` → **stall 计数一律不动** → reply 用换批话术常量渲染新选项。
- 任一非 reroll 输入路径 → `reroll_streak = 0`（含 pick、fills、跳过、deflect）。

**Step 2:** 契约 9/10 转绿；埋点接线点预留（`# telemetry: option_reroll`）。

**Commit:** `feat(a1): reroll channel with cap 2 (stall-neutral)`

---

## T5 [后端] 埋点：三信号源 + reroll 对账事件

**Files:**
- Create: `backend/app/domains/creation/a1/inspiration_log.py`
- Create: `scripts/inspiration_report.py`（最简聚合：读 jsonl → 计数摘要 stdout）

**Step 1: 事件模块（降级模式照抄 suggest_examples 先例——失败绝不影响主流程）**
```python
# 方向A一期埋点（施工单 §2.5：不扩 impulse_coords 闭集，只落日志）。
# 事件四类（第四类 option_reroll 为 Metis 成本对账要求，超出施工单
# 三信号源一句，计划留痕）：option_pick / option_reroll / skip / stall
def emit_event(event: str, session, **fields) -> None:
    """JSON-lines append 到 data/inspiration_log.jsonl；任何异常静默吞掉。"""
    try:
        record = {"ts": iso_now(), "session_id": ..., "event": event, **fields}
        ... append utf-8 一行 ...
    except Exception:  # noqa: BLE001 — 埋点失败绝不影响访谈主流程
        pass
```
- 字段：`option_pick{module, subfield, option_index, options_digest}` / `option_reroll{module, subfield, streak}` / `skip{module, subfield}` / `stall{module, subfield, stall_count}`。

**Step 2: 四个接线点**（T3/T4 预留的 `# telemetry:` 注释锚）：pick 后 / reroll 后 / 跳过后 / stall 计数处各 +1 行调用。

**Step 3:** 契约 8/9/16 的埋点断言转绿（具体 key-value，非"日志存在"）；`test_telemetry_failure_is_silent`（emit 抛错 → 主流程 200 正常）。

**Commit:** `feat(a1): inspiration telemetry jsonl (4 events, fail-silent)`

---

## T6 [顺带 · 阻塞则砍] 九型弹种（anchor 注入）

**Files:**
- Modify: `backend/app/domains/creation/a1/interviewer.py`（规则块 8.6 生成任务段 + suggest_examples prompt）

**Step 1:** 两处 prompt 各注入一行：`示例风格贴合该冲动类型的语气锚点：{ANCHOR_BY_TYPE[creator_primary]}`（module_registry.py L58-68 既有九句逐字引用，取 `session.creator_primary`，缺省不注入）。
**Step 2:** 测试：prompt 字符串断言注入文本 + 九型逐字（不允许改写锚点原文）。
**Step 3:** **砍线定义**：T7 真机观察若示例质量因弹种注入劣化（选项与已答内容相关性下降）→ revert 本锤，回执附原因（施工单 §2.6 + §6）。

**Commit:** `feat(a1): impulse-anchor flavor for option generation`

---

## T7 [验收] 四点自测 + E0 观察记录（施工单 §4 + §6）

**Files:**
- Evidence: `.sisyphus/evidence/option-forward-selftest/`

**Step 1: 起栈重放 IP0065 同源路径**（边缘人 / 生存 / 让渡利益 / 妻子背叛线），逐条留痕四观察点：
1. 每问带 3 选项，且选项从已答内容长出（答完"让渡利益"后，后续选项须与让渡利益相关——护栏 L621-630 生效证据：截选项文本 vs 已答内容关键词）；
2. 答"不知道"不再出现"我没能准确理解你的回答"（截 reply 全文对照）；
3. 1·2·3 直选、换一批（含上限提示）、揉合（"把1和3揉一起"走理解路径）各实操一次留痕；
4. 跳过后下一问有选项接（无死路感）。

**Step 2: E0 真机观察台记录**（Metis MUST——不只看选项展示）：
- **fills 质量对比**：同输入在改造前后的 fills 抽取结果对照（git stash 或双栈跑同 5 轮输入）；
- 选项相关性 / 误劫持率（"1" 直选被触发的轮次 vs 用户意图）记录进观察表；
- 九型弹种去留判定（T6 砍线）。

**Step 3: 完工回执三件（施工单 §6）**：四点自测逐条（过/不过/复现步骤）+ 埋点日志样例三条（选票/stall/跳过各一）+ T6 若砍附阻塞原因。存证据目录 + 回执 md。

**Commit:** 无（纯证据）。

---

## 落锤与波次（施工单"一天一锤 · 禁同日双工地"）

| 锤 | 内容 | 解锁条件 |
|---|---|---|
| 1 | T0 E2E 冒烟（D23 清偿） | 立即可锤 |
| 2 | T1 契约先红 + T2 interviewer 合并 | T0 证据落袋 |
| 3 | T3 guide_engine 接线 | T2 绿 |
| 4 | T4 reroll 通道 | T3 绿 |
| 5 | T5 埋点 | T3/T4 绿（可与锤 4 同工地但按纪律分日） |
| 6 | T6 九型弹种（可砍） | T2 绿，独立 |
| 7 | T7 四点自测 + E0 | T3+T4+T5 全绿 |

依赖链：T0 → T2 → T3 → T4 → T5 → T7；T1 随锤 2；T6 仅依赖 T2。
**并行性：刻意低**——序贯锤优先（施工单纪律），不追求 wave 并行。

## 提交策略（每锤一 commit，pre-commit 跑本锤测试子集 + 全量门禁在锤 3/锤 5/锤 7 复跑）

| 锤 | commit | 门禁复跑 |
|---|---|---|
| 2 | `test(a1): option-forward contract tests (16 red)` + `feat(a1): merged examples generation (rule 8.6)` | pytest 全量 |
| 3 | `feat(a1): default options wired through guide_engine` | pytest 全量 + tsc + vitest |
| 4 | `feat(a1): reroll channel with cap 2` | 锤内子集 |
| 5 | `feat(a1): inspiration telemetry jsonl` | pytest 全量 |
| 6 | `feat(a1): impulse-anchor flavor` | 锤内子集 |
| 7 | 无（证据） | pytest 全量 + tsc + vitest 终验 |

## 成功判据

- [x] 施工单 §4 四观察点全过（T7 证据留痕）—— 观察点 1/2/4 过；观察点 3 = 直选过 + 揉合过 + 换一批**异常留痕**（直选后首问 options 为空 → 首次「换一批」落 interview 消化、cap 后移至第 4 次；根因为 D-2 设计内行为「pick 清空 options + reroll 需 options 非空」，严格场景单元契约 test_reroll_cap_two 绿；非死路非劫持非误劫持，二期收口备案：pick 轮末补挂 options 或 streak 窗口化）
- [x] pytest 全量 ≥1588+新增全绿；tsc 零新增；vitest 310+全绿 —— 终验实测：pytest **1611 passed / 0 failed**（1588 基线 + 16 契约 + 4 锚点 + 2 埋点 + 1 笔误修缮）；tsc exit 0（0 错误）；vitest **310/310**（34 文件）
- [x] C1-C11 存量契约零删改（红线 8 备案清单除外，逐条留痕）—— 唯一例外 3 条 stall==2 分支直接断言，备案于执行回执 T3 补充备案节（施工单 §2.2 拍板授权）；另 1 条 T1 契约文件自身 f-string NameError 笔误修缮（9200456，断言零改动）
- [x] examples 降级路径三态测试绿（缺失/畸形/异常 = 旧行为逐字节）—— 契约 2/3 绿 + 契约 1 正常态绿
- [x] 埋点四事件 JSON-lines 样例各一条 + 失败静默测试绿 —— T7 报告第二节逐字引用 pick/stall/skip 三条 + 附 reroll 一条（UI 会话 a1_e992506b78c1）；test_telemetry_failure_is_silent 绿
- [x] 施工单 §6 完工回执三件齐 —— ①四点自测逐条（过/不过/复现步骤 + 截图×13 + transcript）②埋点样例三条 ③T6 未砍（KEEP 判定 + 定性证据，无阻塞原因）
- [x] 设计决策 D-1~D-7 表随回执呈交产品方（改口窗口：验收前任意时点，改口即追加小锤）—— 决策表即本计划 §设计决策 节；E0 观察补充：D-2 的「reroll 需 options 非空」在直选交错场景的体验缝隙已留痕，供产品方二期改口参考

---

## 执行回执（逐锤落痕）

- [x] T0 E2E 冒烟 — 证据齐：`.sisyphus/evidence/d23-e2e-smoke/`（报告 + 截图×4 + 响应体×5）。结论：S2/S3 过；S1 不过、S4 BLOCKED（浏览器级未命中 `relation=="equivalent"` auto-merge 分支，属 D23 域存量，红线 3 不动，已留痕备案）。T2 解锁。


- [x] T1 存量断言备案 — `我没能准确理解|示例方向` 全量扫描 `backend/tests/`（2026-10-08，UTF-8 Python 扫描）：**零命中**。生产侧命中仅 `backend/app/domains/creation/a1/guide_engine.py:943-944`（stall==2 道歉分支本体，T3 Step 4 删除目标，非测试）。红线 8 例外清单 = 空，无存量测试需要改写；T1 契约测试 16 条已落 `backend/tests/unit/a1/test_option_forward.py`（16 red 验证通过，失败原因均为功能缺失：current_options/examples 字段未落、inspiration_log 模块未建、prompt 8.6 条款缺失）。

- [x] T2 interviewer 合并生成 — commit `bfa05f5`（仅 interviewer.py，+30/−1）。InterviewResult.examples 可选键落位；规则 8.6 三段（生成任务/引用理解/防火墙）衔接 8.5 之后（8.5 本体零改动）；JSON schema 增 examples 键；解析端非 list/非 str/空 → [] 静默降级。门禁：全量 1594 passed + 10 red（均为 T3/T4/T5 待做的契约红，零存量破坏）。契约转绿：3/4/5/6/7/15（1/2/13 需 T3 的 guide_engine 字段——测试断言 reply 渲染与 session 字段，属 T3 接线范围，非 interviewer 缺陷）。

- [x] T3 guide_engine 接线 — commit `27200b0`（仅 guide_engine.py，+82/−47）。A1Session 增 `current_options`/`reroll_streak`（D-3）；`OPTION_INVITE_TEMPLATE` 单点常量；主路径轮末 `_attach_default_options` 白名单接线（deflect / story_material / write-guard 提案挂起 / forced_allocate / completed 只清零不渲染）；直选改读 current_options（D-1 精确匹配 + D-4 豁免真值闸）；`_apply_stall_guard` 仅删 stall==2 示例+道歉分支（stall 计数与 stall≥3 分支零改动，红线 7）；跳过路径 reroll_streak 清零；`_question_payload` additive `"options"` 键。Step 0 清偿点审计：L958/L1003/L1052 的 pending_suggestions=[] 写入保留（喂 stall≥3 判断的活逻辑）；L1013-1024 读取保留（红线 7）；字段退役为死字段不删。已知退化留痕：stall≥3 兜底话术仍引导"回复序号"但直选已改读 current_options——序号回复将落 interview() 理解路径，属预期内行为，待产品方后续收口。

- [x] T3 补充备案（红线 8 例外清单增补）— T1 审计 grep 词表（我没能准确理解|示例方向）漏网 3 条 stall==2 示例分支直接断言：test_guide_engine.py::test_stall_suggests_examples_then_number_pick（改写为 test_stall2_no_canned_examples_pick_reads_current_options）/ test_stall_suggest_unavailable_asks_rephrase / test_blind_recording_fix.py::test_stall_2_suggestions_unavailable_no_raw_fill。已按施工单 §2.2 拍板改写为新行为规格（无道歉/无罐头示例/直选仅认 current_options），盲填不变量全数保留。

- [x] T4 reroll 通道 — commits `8bdb3ce` + `dc8fa96`（guide_engine.py reroll 分支 + interviewer.py FakeInterviewer inject 透传 + inspiration_log.py 壳模块 no-op）。触发链 跳过→直选→reroll→interview() 落位；`REROLL_KEYWORDS` 闭集三词 + `REROLL_CAP=2` + `REROLL_CAP_REPLY`（含「直接选」「自己的话」子串）；stall/position 零触碰（D-2 stall-neutral 实证）；非 reroll 输入统一清零 streak；`option_reroll` emission 已接（壳 no-op，T5 落盘）。插曲留痕：中断派发曾留重复死代码分支，已回退合并（dc8fa96）。验证：契约 9/10 绿——14 passed / 2 failed（剩 2 全为 T5 的 pick/telemetry emission 范围）；子代理曾误报契约 10 测试 NameError，实测证伪（测试文件自 T1 后零改动，git 留痕）。

- [x] T4 reroll 通道 — commits `8bdb3ce` + `dc8fa96`（guide_engine.py reroll 分支；interviewer.py FakeInterviewer inject 透传 +5；inspiration_log.py 壳模块 +6）。触发链 跳过→直选→reroll→interview() 落位；REROLL_KEYWORDS 闭集三词 + REROLL_CAP=2 + REROLL_CAP_REPLY（含「直接选」「自己的话」子串）；stall/position 零触碰（D-2 stall-neutral，手动实证 stall_count 恒定）；非 reroll 输入统一清零 streak；option_reroll emission 已接壳（T5 落盘）。插曲留痕：中断派发曾留重复死代码分支（工作树双分支），已回退合并进 dc8fa96——此后中断恢复必须先 git diff 验残留。验证：契约 9/10 绿（14 passed / 2 failed，剩 2 全为 T5 的 pick/skip/stall emission 范围）；子代理曾误报契约 10 存在测试 NameError，实测证伪（测试文件自 T1 d39c5ca 后零改动）。

- [x] T5 埋点落盘 — commit `0e2e6dd`（inspiration_log.py 实装 36 行 + guide_engine.py 三锚点接线 30 行 + scripts/inspiration_report.py 42 行 + test_inspiration_log.py 70 行 + backend/.gitignore data/*.jsonl）。四事件齐：option_pick{module,subfield,option_index,options_digest} / option_reroll{module,subfield,streak} / skip{module,subfield} / stall{module,subfield,stall_count}；emit_event 全异常静默（noqa BLE001）；JSON-lines utf-8 ensure_ascii=False；LOG_PATH=parents[4]/data（=backend/data，实测落盘自洽）；skip 的 subfield 取自 answer_key（sync_position 先推进指针的坑，notepad 留痕）。门禁：靶向 18/18 绿（16/16 契约全绿）；全量 **1606 passed / 0 failed**（1588 基线 + 16 契约 + 2 埋点新测，严丝合缝）；报告脚本实跑 320 事件聚合正确；真机 jsonl 抽样形状正确。

- [x] T6 九型弹种锚点 — commit `b1e2327`（interviewer.py +19：8.6 段与 suggest_examples 两处条件注入「示例风格贴合该冲动类型的语气锚点：{ANCHOR_BY_TYPE[creator_primary]}」+ test_impulse_anchor.py 100 行 4 测试）。ANCHOR_BY_TYPE 实际位于 app/domains/creation/shared/module_registry.py（计划写 seed/ 系笔误，以 Grep 为准）；九句逐字消费 + is 同源断言；缺省/未命中零注入（prompt 逐字节不变）；commit body 自注 revertable unit。验证：21 passed（4 锚点新测 + 16 契约回归绿，协调者亲跑）。**砍线在途**：T7 真机观察若示例质量劣化 → 整体 revert 本 commit。另注：插曲 commit `9200456`（reroll cap 测试 f-string NameError 笔误修正，测试基建修缮，随 T4 收尾落）。

- [x] T7 四点自测 + E0 观察记录 — 证据：`.sisyphus/evidence/option-forward-selftest/`（报告 120 行 + 截图×13 + chat JSON×11 + phaseA-transcript + e0 双侧 fills + 埋点样例）。**四观察点**：1（每问 3 选项且从已答长出，三轮关键词耦合 diff）过 / 2（「不知道」无道歉无示例方向，reply 全文对照）过 / 3（直选过、揉合过、换一批异常留痕——直选后首问 options 空 → 首次换一批落 interview、cap 后移至第 4 次；D-2 设计内行为，严格场景契约绿，二期收口：pick 轮末补挂 options 或 streak 窗口化）/ 4（跳过后下一问带新选项）过。**E0**：同 5 输入 old(e2b7367) vs new(b1e2327) fills 5/5 持平略优、**零选项污染**、误劫持 0 例（含「把1和3揉一起」关键反例）。**T6 判定 KEEP**（10+ 轮选项零模板化漂移，revert 依据不成立）。遗留备案：next_question.options 序列化滞后一轮（前端不消费该键，无感）；孤儿栈清理（中断派发遗留 8000/5173 进程，协调者已杀并验证端口空）。终验三门禁（协调者亲跑）：pytest 1611/0 + tsc 0 + vitest 310/310。

- [x] T5 埋点落盘 — commit `0e2e6dd`（5 文件 +177/−3：inspiration_log.py 实装 / guide_engine.py 三锚点 emission / scripts/inspiration_report.py 42 行聚合 / test_inspiration_log.py 2 测试 / backend/.gitignore 增 data/*.jsonl）。emit_event fail-silent（异常全吞，noqa BLE001）；四事件 key 齐备（pick 含 0-based option_index + options_digest / reroll streak / skip / stall stall_count）；LOG_PATH=backend/data/inspiration_log.jsonl（parents[4] 解析，双层 gitignore 覆盖，git status 零泄漏）。关键 gotcha 留痕：skip 的 subfield 取自 answer_key（sync_position 先推进指针）；pick 的 digest 在 current_options 清空前快照。验证（协调者亲跑）：靶向 18 passed（16/16 契约全绿 + 2 新测试）+ 全量 1606 passed / 0 failed（1588 基线+18 新增，锤 5 门禁过）。

