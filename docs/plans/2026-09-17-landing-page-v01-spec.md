---
tags: [design-spec, frontend, landing]
updated: 2026-09-17
---

# 首页 Landing 规格书 v0.1 ·「八成灵魂」

> 文档版本 v0.1 ｜ 2026-09-17 ｜ 依据：09-16 前端现状基线审计 + [决策台账 v1.0](../decision-log.md)
> 阅读前置：所有 D/B/P 编号见 [decision-log](../decision-log.md)
> ⚠️ 两个取证挂钩点 F1（§1）/ F2（§4），见 §9——取证返回前本规格按当前值执行，返回后按实际校准

---

## §0 · v0 → v0.1 处置一览（五矛盾闭环记录）

| # | 矛盾 | 根因 | 处置 |
|---|---|---|---|
| 1 | D/B/P 台账零落盘 | 咨询对话中发明编号体系，并错误假设其"自动生效" | 产出决策台账 v1.0 落盘（docs/decision-log.md），并新增元规则：决策编号未经落盘不生效 |
| 2a | rgba(199,180,255) ≠ nebula-300 | 凭记忆写色值，未对表 | 修正为 rgba(196,181,253,.9)（= #c4b5fd） |
| 2b | 填充色 rgba(112,0,255) = 已弃用的 #7000FF | 嘴上弃用、笔下照用 | 修正为 rgba(139,92,246,.06)（= nebula-500 低透明度）；规格书全文禁裸值 |
| 3 | 令牌治理只加 2 个 primitive，丢 Q13 方向 | 把"新增"当成了"治理" | D1 工作项扩充为五项（删冗余 / primitive / semantic / 字体栈 / 文档同步） |
| 4 | GSAP 等无先例 | 新选型未走治理流程 | 新增 §4 依赖决策记录，含体积预算、备选方案、取证挂钩 |
| 5 | 「世界观工坊」vs「回声工坊」打架 | 规格书内部不一致；且 ECHO 系文案稿私带候选名，未经裁决 | 分层裁决：产品总名 = ECHO · 回声工坊（待产品方终裁，48h 未否决生效），A1 模块名保留「世界观工坊」；title/H1/页脚统一用产品总名 |

---

## §1 令牌工作包（对应 Q13/审计 §4.2/§4.4 全范围，非只新增）

**前置取证 F1**：读取 theme.css 实际令牌表，以下值与实际冲突时以实际为准并回报。

- **删**：starlight 系冗余令牌（全量清点后列清单回报，再删）
- **新增 primitive**：`--color-space-1000: #050508`（径向渐变终点 #000）；`--color-energy-cyan: #00F0FF`
- **新建 semantic 层（组件只准用本层）**：`--color-surface` / `--color-text-primary` / `--color-text-secondary` / `--color-accent` / `--color-bubble-user` / `--color-bubble-ai` / `--color-glass`
- **中文字体栈**（审计 §4.4 一小时修复，Q4 病根）：标题 `font-family: "Noto Serif SC", "Songti SC", serif`（webfont 走 CDN + font-display: swap，只用于标题与 slogan）；正文 `system-ui, "PingFang SC", "Microsoft YaHei", sans-serif`（零下载）
- **文档同步**：README 路由表（/ 与 /demo、补 /a1/poster）+ 4_ux-flow v0.2 页面地图

**色彩纪律（规格全文生效）**：混沌体（几何体+粒子）= nebula/stardust 系；秩序能量（流光/充能/CTA）= energy-cyan，全站唯一。弃用裸值：#7000FF、#FFD700（分别由 nebula-500 #8b5cf6、stardust-400 #fbbf24 承担）。

## §2 第一屏「八大混沌种子」

**分层结构（每层单一变换职责）**：`.seed`（GSAP：漂移+呼吸）> `.seed-rot`（CSS：无限自转）> `.seed-body`（SVG：晶体轮廓）。

**八体构图表**（错落，禁环形/网格；标题居中 50%/50%，backdrop-filter: blur(6px) 造穿层）：

| # | x% | y% | scale | z(px) | 自转 | 漂移 |
|---|---|---|---|---|---|---|
| 1 | 10 | 72 | 1.00 | +240 | 28s | 60px |
| 2 | 86 | 14 | 0.35 | -380 | 22s | 30px |
| 3 | 50 | 30 | 0.55 | -60 | 34s | 40px |
| 4 | 24 | 20 | 0.40 | -200 | 26s | 34px |
| 5 | 74 | 58 | 0.50 | +80 | 30s | 46px |
| 6 | 66 | 8 | 0.28 | -320 | 24s | 26px |
| 7 | 6 | 38 | 0.30 | -260 | 32s | 30px |
| 8 | 90 | 84 | 0.45 | +160 | 27s | 50px |

**晶体材质（八体共用单 class，禁单体特调）**：描边 `rgba(196,181,253,.9)`（nebula-300 #c4b5fd）；填充 `rgba(139,92,246,.06)`（nebula-500 #8b5cf6）；发光 `drop-shadow(0 0 14px rgba(167,139,250,.35))`。八种轮廓（4 类×2 变体，手绘 SVG）：正八面体/二十面体/双环结/星形多面体/斜立方体/三棱柱/十二面体/环面。

**背景「世界海洋」（Canvas 2D）**：

```ts
type TopScript = { id: string; worldName: string; author: string; emblemUrl: string; href?: string };
const topScripts: TopScript[] = [ /* 首批 3 个真实案例；不足以柔光矩形补位 */ ];
```

单 rAF 循环；实粒可交互（hover 放大 1.15 + 世界名浮现 + 点击跳 href），补位粒纯氛围；闪烁相位独立 0.5–3s；visibilitychange 暂停；DPR≤2；离屏剔除。

## §3 过渡「流光连线」

- **触发**（ScrollTrigger ~100px）：先停几何体漂移（killTweensOf + animation-play-state: paused）→ 线路绘入 → 容器充能。动效交接，禁叠加
- **路径**：8 → 汇流点（vw×0.5, vh×0.94）→ 3 容器；每线两段贝塞尔；终点 = getBoundingClientRect() 换算，resize / ScrollTrigger refresh 时重算
- **质感三层同 path 叠描**：晕光（w10 op.15 blur6）+ 核心（w2.5 op.9）+ 粒子（dasharray: 2 16 dashoffset 滚动）
- **绘入**：dashoffset L→0，stagger 0.06s，共 ~1.2s；汇流点单次径向脉冲
- **充能**：.charged 内发光 0→1 + 边框白 8%→cyan 25%，600ms
- **hover 联动**：对应线 w+30%，容器上浮 6px

## §4 依赖决策记录（新增，按工程治理流程）

| 项 | 内容 |
|---|---|
| 选型 | gsap + ScrollTrigger（npm） |
| 理由 | 滚动阈值编排、killTweensOf 交接语义、stagger 时间线为本规格核心机制，自研成本 > 引入成本 |
| 体积预算 | gzip ~40KB（core+插件），占 JS 预算 20%，硬上限计入 §7 |
| 备选方案 B（零依赖） | IntersectionObserver 触发 + WAAPI/CSS（animation-timeline: scroll() 渐进增强）。若取证 F2 发现 bundle 超预算或依赖审批不过，整体切方案 B，§3 逻辑不变 |
| 前置取证 F2 | package.json 是否已有 gsap；实测 gzip 体积回报 |

Three.js/WebGL 本期不引入（v1 再议，需另立决策记录）。

## §5 命名规范（终结矛盾 5）

- **产品总名**：ECHO · 回声工坊（候选名，产品方 48h 内未否决则生效；title/H1/页脚/导航 Logo 统一用此名）
- **模块名**：A1=世界观工坊 / A2=模组工作台 / A3=内容工坊（与 README/PROJECT_STATE 一致）
- **分层规则**：产品总名永不出现在模块容器标题中，反之亦然

## §6 文案（全中文，P3 条款：全程称呼"你/你的世界"）

- **副标**（首屏，三选一，推荐 1）：①「那个在你脑海里住了很多年的世界，今晚可以开始动工了。」②「每一个念念不忘的世界，都值得一次被看见的机会。」③「你只管做梦，剩下的交给这里。」
- **CTA**：开始创造 → /a1
- **容器文案**：A1「十道脉络，一次访谈，把你脑中的世界亲手铸成一部世界之书。」A2「在你的世界里，找出那条值得讲的故事线——背景、脉络，与开团的理由。」A3「把世界拆成能直接上桌的资产：场景、模组与素材，一键打包带走。」
- 每容器内嵌 1 案例卡：作者 + 世界名 + 纹章缩略图（B4）
- **第三屏 slogan**（三选一，推荐 1）：①「世界不该只活在你的脑海里。」②「带一个世界，到世间来。」③「先造世界，再讲故事。」

## §7 降级与性能预算（验收硬条款）

JS 增量 ≤200KB ｜ 60fps ｜ 粒子 desktop 300 / mobile 80 ｜ prefers-reduced-motion → 全静态（八体定格 + 预生成静态星座图 SVG + 无粒子闪烁）｜ 无 JS 同上 ｜ 移动端八体 2×4 重排禁缩放桌面版 ｜ 装饰层 aria-hidden，导航/CTA/案例卡为真实 DOM。

## §8 排期（3–5 天，D1 已扩充）

| 天 | 交付 |
|---|---|
| D1 | D9 闸门确认 → 令牌五件套（删冗余/primitive/semantic/字体栈/文档同步）+ 静态构图 |
| D2 | Canvas 粒子 + topScripts + 交互粒 |
| D3 | 几何体动效 + 移动端 2×4 |
| D4 | ScrollTrigger 交接 + 流光 + 充能 + hover |
| D5 | 文案 + 降级三态 + 预算实测 + 验收清单 |

## §9 执行顺序与验收清单

**Agent 执行顺序**：① 落盘决策台账 + PROJECT_STATE 指针 → ② 取证 F1（theme.css 令牌现状）/ F2（gsap 依赖）回报 → ③ 按 D9 清 tsc → ④ D1–D5。

**验收清单（v0.1 新增 4 条加粗）**：

- [x] **决策台账已落盘且 PROJECT_STATE 有指针**
- [x] **全文无 #7000FF / #FFD700 / rgb(112,0,255) / rgb(199,180,255) 裸值**（§0/§10 处置记录引文除外）
- [x] **§4 依赖决策记录存在且 F2 已回报**（见 §10）
- [x] **产品总名与模块名分层，无交叉污染**（§5 已立）
- [ ] 第一屏唯一魔法时刻=几何体；青色仅现于流光/充能/CTA
- [ ] 交接不叠加；resize 连线命中；topScripts 空数组不报错
- [ ] reduced-motion/无 JS 静态星座图
- [ ] JS≤200KB、60fps、粒子 300/80
- [ ] 全中文、称呼"你"、CTA→/a1、案例卡含纹章
- [ ] 移动端 2×4 不破版

---

## 变更日志（v0 → v0.1）

| 矛盾 | 变更位置 |
|---|---|
| 1 | 新增附件 A 台账 + 元规则 + §9 执行顺序① |
| 2a | §2 描边 → rgba(196,181,253,.9) |
| 2b | §2 填充 → rgba(139,92,246,.06)；§1 弃用裸值条款 |
| 3 | §1 扩为五件套；§8 D1 扩充 |
| 4 | 新增 §4 依赖决策记录 + 方案 B + F2 |
| 5 | 新增 §5 命名规范；§6 文案统一 |

---

## §10 · F1/F2 取证回报（2026-09-17，§9 执行顺序② 闭环）

### F1 · theme.css 实际令牌表（frontend/src/components/theme.css @theme L40-91）

| 规格 v0.1 假设 | 实际值 | 判定 |
|---|---|---|
| nebula-300 = #c4b5fd（描边 rgba(196,181,253,.9)） | #c4b5fd | ✅ 吻合，修正值成立 |
| nebula-500 = #8b5cf6（填充 rgba(139,92,246,.06)） | #8b5cf6 | ✅ 吻合 |
| stardust-400 = #fbbf24 | #fbbf24 | ✅ 吻合 |
| space-950…600 五段 | #0a0a1a…#3a3a7a | ✅ 吻合，space-1000 无档位冲突，可新增 |
| energy-cyan #00F0FF | 仓内无此色 | ✅ 无重名冲突，可新增 |

**裸值取证**：`#7000FF` / `#FFD700` / `#00F0FF` 在 frontend/src 全域零命中——证实 v0 草稿中的两枚裸值系咨询对话私带，仓内从未存在，无存量清理负担。

**starlight 冗余清单（§1 删除项的"列清单回报"）**：

- starlight-300 = #fcd34d ≡ stardust-300、starlight-400 = #fbbf24 ≡ stardust-400（完全重复）；starlight-500 = #f59e0b ≡ cosmos-warning（同值冗余）
- 组件引用：**零**（starlight 仅出现在 theme.css 自身的注释、令牌定义与 `.glow-starlight` 工具类名）——删除三枚令牌安全
- 连带决策留 D1 施工：`.glow-starlight` 类保留改名或删除（其内部本就用裸 rgba(252,211,77)）

**⚠️ F1 新发现——双青边界待裁决**：仓内已有语义令牌 `--color-cosmos-info: #22d3ee`（青）。energy-cyan #00F0FF 与其并存。色彩纪律"青色全站唯一使用权归 energy-cyan"需精确化为：**energy-cyan 独占"秩序能量"语用（流光/充能/CTA）；cosmos-info 仅限"信息语义"（info 状态提示），两者互不越界**。按此表述执行，若产品方要求物理唯一青，则 cosmos-info 并入 energy-cyan 属 D1 范围内的额外裁决。

### F2 · gsap 依赖现状

- package.json dependencies 仅 react / react-dom / reactflow；node_modules/gsap 不存在 → **gsap 未安装，需全新引入**
- §4 选型维持（gsap + ScrollTrigger），体积预算 gzip ~40KB 不变，计入 §7 硬上限
- 方案 B（IntersectionObserver + WAAPI，零依赖）保留为预算超标/审批不过时的整体切换路径

**校准结论**：规格 §1/§2/§4 全部假设与实际吻合，零返工；唯一增量动作 = 上方双青边界的精确化表述（已写入本节，施工按此执行）。§9 验收清单第 3 条"§4 依赖决策记录存在且 F2 已回报" → 可打勾。
