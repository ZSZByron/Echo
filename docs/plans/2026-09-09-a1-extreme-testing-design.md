# A1 IP 生成器极限实验设计（刑讯室 · Interrogation Room）

- 日期：2026-09-09
- 状态：approved（用户锁定配置后开工）
- 范围：A1 全流程（上传→访谈→定稿）→ B 定稿图谱链路，先整体后局部
- 锁定配置：弹药轴向 ①输入病理 ③LLM输出畸形 ④语义陷阱 全选 + ②定稿循环 + ⑤答案炸弹；LLM 策略 = 混合（Mock 打解析层，真跑打统计层）；判据 B/C/D 为主、E 附带

## 1. 三层架构

| 层 | 载体 | 打击面 | 特性 |
|----|------|--------|------|
| Layer M | `backend/tests/xt/`（pytest，`-m xt`） | 解析/校验/id 铸造层的确定性缺陷 | 可复现、可断言、进 CI |
| Layer R | `scripts/xt/real_run.py`（HTTP 直调 :8000） | 跨轮统计不一致、版权摇摆、divergent 失效 | 证据 JSON 落 `%TEMP%\opencode\a1_xt\` |
| Layer C | `scripts/xt/make_corpus.py` 生成的对抗语料 | 两层共用 | 可再生、不入库大体量文件 |

隔离：`A1_STORE_PATH` 环境变量覆盖（store.py 原生支持）+ 每测试清空 `_SESSIONS`/`_FILES` 内存态。

## 2. 判据定义

- **B 静默丢失**：预期数据缺失且警告未落库（`finalize_warnings`/`assemble_warnings`/响应体）才算确诊；有警告 = 降级契约生效，记录不算 bug
- **C 契约违反**：D4 部分接受语义、id 稳定性不变量（v0.5 §9）、409 门禁语义被打破
- **D 统计异常**：同输入 N 次结果方差超阈值
- **E 安全穿透**：零宽/注入文本到达展示层或图谱 id

## 3. 实验矩阵

### 组 E1 · 输入病理学（worldview_upload.py）

| ID | 实验 | 判定 | 方式 | P0 |
|----|------|------|------|----|
| E1.1 | 零宽幽灵：40% U+200B/U+202E/同形字文档过 `validate_text`，零宽字符渗入 prompt | E（gate 层）+ B | Mock | |
| E1.2 | 9.9% 临界：floor(0.099N) 个 `\x01` 精确卡阈值下方通过 | E | Mock | |
| E1.3 | 边界三明治：199/200/201 字符门禁；19999/20000/20001 截断线 | 基线锚定 | Mock | |
| E1.4 | 截断失忆症：25k 文档，哨兵B（只属于后半部的独特概念）仅出现在 20000 字之后 → **永不进入 parse_modules 的 prompt**（FakeProvider 捕获断言） | **B** | Mock 确定性变体 + 真跑复核 | ★ |
| E1.5 | 专名洪水：extract_entities 返回 30 项 → cap=10，**20 项静默丢弃且响应无截断披露** | **B** | Mock（cap 确定性） | |
| E1.6 | 同形字绕过：check_copyright term 精确匹配变体失配 | D | 真跑 | |
| E1.7 | convert 炸弹：100k 文档 → `convert_text` 用户消息含**全文**（唯一不截断的入口） | A/B | Mock 捕获 + 真跑 | |

### 组 E2 · 答案炸弹与门禁

| ID | 实验 | 判定 | 方式 | P0 |
|----|------|------|------|----|
| E2.1 | 答案炸弹：35×5000 字注入 session → finalize → graphify prompt 实测 >100k 字符；provider 失败时降级链路 | **B/C** | Mock（量 prompt）+ 真跑（超时） | ★ |
| E2.2 | 占位值木马：全字段 `"缺少依据"` → `is_finalizable`=True → **finalize 200 放行**（409 不触发）+ 降级空图谱 | **C（已知病灶实锤）** | Mock | ★ |
| E2.3 | 50% 整边界：恰 50% 拒（strict >），50%+1 字段过 | 基线锚定 | Mock | |
| E2.4 | 单字段黑洞：100k 单答案经 chat 端点 | 第一个断裂点 | 真跑 | |

### 组 E3 · LLM 输出畸形（canned graphify 回放）

| ID | 实验 | 判定 | 方式 | P0 |
|----|------|------|------|----|
| E3.1 | 32字双胞胎：同锚点两条目前 32 字相同 → sanitize 同 id → dedupe 丢第二条；引用其 id 的边按幻觉端点再丢 | **B+C（双重丢失）** | Mock 纯函数 + 路由层 | ★ |
| E3.2 | 未命名挤兑：纯空白标题全变"未命名"→ 互相挤兑剩 1 | **B** | Mock | |
| E3.3 | 锚点幻觉：`力量体系.fake` 组 + 引用边 → 组丢边也丢，警告链完整性 | C | Mock | |
| E3.4 | 开放问题洪水：50 条词表外关系（各差 1 字）+ from/to 注入文本 → 50 个 open_questions、注入原文拼进问句 | C+E | Mock | ★ |
| E3.5 | JSON 断腰：provider 返回半截 JSON 字符串 → parse 失败**不重试**（calls==1）→ 降级；provider 抛超时 → **重试恰好 1 次**（calls==2）→ 降级 | C | Mock | ★ |
| E3.6 | 容器错位：entries=dict / module_summaries=list → ValueError → 降级，报错信息可定位 | C | Mock | |
| E3.7 | 幻影端点全家桶：`d:锚:不存在题`、`cst_RED_黑名单外`、概念树幽灵 id、自环边、对倒边 → 逐类断言丢弃与警告；**自环/对倒无校验 = 契约缺口记录** | C | Mock | |

### 组 E4 · 语义对抗（真 LLM 为主）

| ID | 实验 | 判定 | 方式 | P0 |
|----|------|------|------|----|
| E4.1 | 自相矛盾设定：source=能量无限 vs cost=严格守恒 → 无矛盾检测则两互斥边共存 | D | 真跑 | |
| E4.2 | 同名标签回归（后端范围）：标题==锚点显示名（含尾空格变体）→ 后端 id 稳定性断言；前端 depthNodeLabel 回退改手工冒烟 | C | Mock + 手工 | |
| E4.3 | 跨轮 N 重奏：同文档上传×10 / 同答案 finalize×5 → 字段数分布、占位值率、同 key 异值数、节点/边数方差 | **D（核心交付：分布报告）** | 真跑 | ★ |
| E4.4 | 循环依赖设定：A↔B → CROSS 边是否过环检测 | C | 真跑 | |

### 组 E5 · 状态机酷刑

| ID | 实验 | 判定 | 方式 | P0 |
|----|------|------|------|----|
| E5.1 | 定稿循环耐力：finalize→补答→finalize ×N → 版本递增、stale 标记、dead_edges 累积、confirmed 边因 id 漂移坠落死区（C7 三元组精确匹配脆断） | **C** | Mock 路由层 | ★ |
| E5.2 | 秒定稿：预填 >50% 直接 finalize → visual_bg daemon 线程注册一致性 | 状态一致性 | Mock | |
| E5.3 | 记忆蒸发：定稿后写坏 store JSON → 重载 → 空状态（文档化蒸发半径） | B（by design，记录半径） | Mock | |

（砍掉项：E3.8 重复键覆盖——`chat_json` 返回已解析 dict，JSON 重复键在 `json.loads` 层 last-wins，无法在目标层构造。）

## 4. 统计阈值（锁定）

- 跨轮字段数方差 > ±1 → 判不稳定（35 vs 34 即触发）
- divergent_question 非空率 < 10%（10 轮中 0-1 次）→ 判失效
- risk_level 翻转 ≥ 2/10 → 判摇摆

## 5. 运行方式

```powershell
# Mock 层（确定性，12 用例）
cd backend
python -m pytest tests/xt -m xt -v -o addopts=""   # addopts 清空以跳过全局覆盖率门禁

# 语料生成（真跑前置，确定性可再生）
python ../scripts/xt/make_corpus.py

# 真跑层（需 uvicorn :8000 + .env provider）
python scripts/xt/real_run.py --suite cross-run --n 10   # E4.3 跨轮统计（35 vs 34）
python scripts/xt/real_run.py --suite noun-flood --n 3   # E1.5 版权漏检/risk 摇摆
python scripts/xt/real_run.py --suite truncation         # E1.4 截断盲区复核
```

真跑证据目录：`%TEMP%\opencode\a1_xt\<suite>_<timestamp>.json`（沿用 8-28 实测范式）。

## 5.1 v1.1 定案（用户委托投票，2026-09-10 实施完成）

用户将优先级投票委托给本会话后收敛为 **8 项**（6 主攻 + 2 搭车）：#7 标题碰撞、#8 占位值门禁、#2 截断失忆、#6 答案炸弹、#12 重定稿断链、跨轮统计（真跑）；搭车 #4 专名 cap、#3 convert 不截断。砍掉：E 类（#1/#9）、线程竞态（#11）、基线锚定类（不猎 bug）、#10 store 蒸发（设计行为）。

实施落点：`backend/tests/xt/`（conftest + helpers + 4 个测试文件，12 用例全绿）；`scripts/xt/`（make_corpus.py + real_run.py）。首轮跑出的证据见 §7。

## 6. 预期结果分类

| 分类 | 含义 |
|------|------|
| 确诊 bug | 判据 B/C/D 命中 |
| 降级契约生效 | 数据丢失但有警告落库——记录，不算 bug |
| 基线锚定 | 边界行为与设计一致 |
| 契约缺口 | 行为无校验但文档未承诺（自环/对倒、immutable 无代码强制）|

## 7. 首轮 Mock 层证据（2026-09-10，12/12 绿 + 存量 398/398 无回归）

| 实验 | 判定 | 证据 |
|------|------|------|
| #7 标题碰撞（3 层） | **B 确诊（边层）** | 层1 碰撞实锤（34 字标题→同 32 字 id）；层2 条目去重**有**警告；层3 引用边在 graphify 校验层被丢弃，其警告"引用了不存在的节点"只存在于 `llm_result.warning`——finalize 仅在 `success=False` 时并入 `finalize_warnings`，`assemble_warnings`/`dead_edges` 均无记录 → **边蒸发且警告链断裂** |
| #8 占位值门禁（3 用例） | **C 确诊** | `"缺少依据"` 与空串（"跳过"产物）全字段通过 `is_finalizable`；路由层 finalize 200 放行 + 降级空图谱照样 `status="finalized"` |
| #2 截断失忆（2 用例） | **B 确诊（内容层）+ 弱披露记录** | 哨兵 B（20000 字后）从未到达 parse_modules 的 prompt；响应携带 `truncated: true` 布尔（后端尽责的弱披露），但无逐字段补捞 |
| #6 答案炸弹 | **C 确诊** | 35×~5000 字注入后 graphify system prompt 实测 >100k 字符，全链路无长度护栏；finalize 照常 200 |
| #12 重定稿断链 | **C 确诊（契约矛盾）** | 标题一字漂移 → 旧 confirmed 边坠 `dead_edges`（有记录=契约生效），同语义新边 `confirmed=False` 复活——内容锚定 id 与跨版本确认延续天然互斥 |
| #4 专名 cap | **B 确诊（披露缺失）** | 30→10 截断确定性生效，返回结构无任何丢弃披露字段 |
| #3 convert 不截断 | **C 确诊** | 104k 文档全文进入 convert user prompt（实测 >100k 字符） |

待真跑补证：E4.3 跨轮统计（`--suite cross-run --n 10`）、E1.5 版权漏检、E1.4 真跑复核。

## 8. 真跑层证据（2026-09-10 深夜，provider=deepseek）

### 8.1 显式文档对照（cross-run ×10）：STABLE
10/10 轮全部 35 字段，spread=0，无存在性/内容翻转。证据：`%TEMP%\opencode\a1_xt\cross-run_*.json`（用户本机执行）。

### 8.2 边缘证据文档（borderline ×10）：**UNSTABLE，spread=3（32↔35）**——35 vs 34 病灶成功复现并解剖

语料三档梯度：显式 8 / 可推断 8 / 无依据 19。结果 `borderline_20260910_234246.json`：

| 病理形态 | 证据字段 | 机制 |
|---------|---------|------|
| **① 边界字段三态漂移**（32 vs 35 的直接元凶） | 地理空间.vertical / 玩法设计DNA.growth_end / 视觉设计.architecture | 无依据字段在三轮次间随机落三态：`<key缺失>`（run8，3 个同时缺失→计数 32）/ `"未提及"`占位值 / 编造内容（run6 vertical 凭空写出"海面岛屿与海底礁脉深处"） |
| **② 编造 vs 占位双头违规** | 骰子设定.cost_mech（文中零骰子内容） | 铁律"无依据→缺省 key"**从未发生**：8/10 轮编造机制变体（"记忆代价→临界失败触发反噬"…每轮措辞不同），2/10 轮写"未提及"——而占位值是 truthy，**照常入库、照常过门禁、照常进 graphify prompt** |
| **③ 显式字段轻度改写** | 世界本体.origin | 原文逐字句 8/10 轮保真，2/10 轮换序改写——同文档上传得到不同的"已确定答案"，下游图谱随之漂移 |
| **④ 内容方差 pervasive** | 31/35 字段值跨轮不一致 | 计数方差只是可见冰山；即使 key 全部在场，值级方差仍是系统性的 |

**结论**：parse_modules 的不确定性 = 边界证据密度 × 字段三态随机（缺/占位/编造）。显式文档方差为零证明这不是 provider 抖动，而是"证据不足时 LLM 行为无锚点"的结构性问题。占位值天然产生且直通门禁（与 Mock 层 #8 确诊闭环）。
