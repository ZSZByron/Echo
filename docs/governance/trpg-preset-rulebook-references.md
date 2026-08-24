# TRPG 预设 × 已出版规则书权威对照表

> **用途**：8 个种子预设（见 [[seed-presets-catalog]]，数据源 `backend/experiments/trpg_presets.py`）各自匹配一款概念最相近的**已出版 TRPG 规则书**，采引其权威机制描述与基调哲学，作为预设描述的规范依据。
>
> **引用原则**：机制名称保留英文原术语 + 中文对照，确保与原规则书可追溯。描述为"采引/改写"而非逐字复制，符合合理引用范围。

---

## 概览表

| # | 预设 ID | 名称 | 匹配规则书 | 出版方 / 版本 | 核心权威机制 |
|---|---|---|---|---|---|
| 1 | lovecraftian_horror | 深渊低语 | Call of Cthulhu（克苏鲁的呼唤） | Chaosium, 7th Edition (2014) | 理智（SAN）百分比检定，0/1d6 损失公式 |
| 2 | cyberpunk_heist | 霓虹窃案 | Cyberpunk RED（赛博朋克 RED） | R. Talsorian Games (2020) | 属性+技能+d10 vs 难度值；实时并行 Netrunning |
| 3 | dark_fantasy_dungeon | 腐化深渊 | Shadow of the Demon Lord（魔主之影） | Schwalb Entertainment (2015) | 腐化值（Corruption）阈值 + 黑暗印记表 |
| 4 | wasteland_survival | 灰烬之路 | Mutant: Year Zero（变异纪元：零年） | Free League, Year Zero Engine (2014) | 骰池推送（Push）+ 创伤 + 装备退化 |
| 5 | xianxia_cultivation | 碎天录 | Legends of the Wulin（武林传奇） | Eos Press (2012) | 湖/河（Lake/River）骰池 + 涟漪（Ripples）业力机制 |
| 6 | space_opera | 群星彼岸 | Traveller（旅行者） | Mongoose Publishing, 2nd Edition (2022) | 万用世界档案（UWP）+ 星区建造 + 派系资产 |
| 7 | classic_fantasy | 破晓之剑 | Dungeons & Dragons（龙与地下城） | Wizards of the Coast, 5th/5.5 Edition (2014/2024) | 三支柱（社交/探索/战斗）+ 优势/劣势 + 魔法动作 |
| 8 | court_intrigue | 鸩酒与玫瑰 | A Song of Ice and Fire Roleplaying（冰与火之歌 RPG） | Green Ronin (2008) | 阴谋系统（Intrigue）+ 家族七属性元角色 |

---

## 预设 1：lovecraftian_horror / 深渊低语

**匹配规则书**：Call of Cthulhu, 7th Edition（Chaosium, 2014）

### 权威机制描述（采引）

- **理智属性（Sanity, SAN）**：当前理智初始等于意志（POW），代表调查员面对宇宙恐怖时的心理韧性。
- **理智检定公式**：对当前 SAN 做百分比掷骰。损失记为 "0/1d6" 或 "2/1d10" 格式——斜杠前为检定成功时的损失，斜杠后为失败时的损失。
- **临时疯狂（Temporary Insanity）**：单次损失 5+ 点 SAN 时做智力（INT）掷骰；成功则调查员陷入 1d10 小时的临时疯狂。
- **克苏鲁神话技能（Cthulhu Mythos）**：该技能每提升 1%，SAN 上限永久等量下降——"获取禁忌知识的代价即理智本身"。
- **非自愿行动（Involuntary Actions）**：任何 SAN 损失允许守秘人（Keeper）指定调查员的下一动作（尖叫、昏厥、扣动扳机）。

### 基调哲学

> "理智是调查员心理韧性的度量。失去 SAN 点数是与获取克苏鲁神话新知相伴的代价——SAN 是对人类行为、道德与人格的侵蚀。"（改写自 7 版守秘人手册）

### 与预设规则的对应

| 预设现有规则 | 规则书依据 |
|---|---|
| "目睹/触碰/阅读触发 1d10 理智损失，失败永久减少上限" | SAN 检定 0/1d6 公式 + Mythos 技能压低上限 |
| "剧情不能有好结局，真相的揭示本身就是惩罚" | "知识即代价"的 SAN 哲学 |
| 调查事件线索链（侦查/图书馆/心理学检定） | CoC 调查员技能体系（Spot Hidden / Library Use / Psychology） |

---

## 预设 2：cyberpunk_heist / 霓虹窃案

**匹配规则书**：Cyberpunk RED（R. Talsorian Games, 2020）

> 备选：Shadowrun（Catalyst Game Labs）——其 Decker 入侵是独立 Matrix 子系统、脱离队伍实时行动；而本预设强调"双线同时叙事"，与 Cyberpunk RED 的**实时并行 Netrunning** 更吻合，故选 RED 为主参考。

### 权威机制描述（采引）

- **核心判定**：属性 + 技能 + d10 对抗难度值（Difficulty Value, DV）——日常任务 DV=13，传奇级 DV=29。
- **网络架构（Netrunning Architecture）**：抽象为分层表格结构，网络潜行者（Netrunner）从第 1 层开始逐层下潜；黑冰（Black ICE）与恶魔（Demons）程序驻守层级，须摧毁才能继续。
- **行动经济**：肉体角色每轮 1 次"现实动作"；Netrunner 依接口（Interface）技能获得多次网络动作——网络与现实**同钟并行**。
- **义体与人性（Humanity Cost）**：安装义体逐件扣除人性值，人性滑向零即逼近赛博精神病（Cyberpsychosis）。

### 基调哲学

> "Netrunning 重构为与现实战斗实时同步结算——网络潜行者与所有人共用同一座钟。"（改写自 RED 核心规则书）

### 与预设规则的对应

| 预设现有规则 | 规则书依据 |
|---|---|
| "现实空间战斗 + 网络空间 ICE 突破同时进行" | 实时并行 Netrunning 行动经济 |
| "义体使用率超标 → 人性值检定 → 赛博精神病前兆" | Humanity Cost / Cyberpsychosis |
| "任务四阶段：情报→准备→执行→变故" | RED 委托（Job）结构 + 街头信誉（Street Cred）体系 |

---

## 预设 3：dark_fantasy_dungeon / 腐化深渊

**匹配规则书**：Shadow of the Demon Lord（Schwalb Entertainment, 2015）

> 备选：Warhammer Fantasy Roleplay 4e（Cubic 7）亦有 Corruption 机制，但 SotDL 的阈值+黑暗印记表与预设"力量必附代价、腐化递进不可逆"最契合。

### 权威机制描述（采引）

- **腐化值（Corruption）**：初始为 0，因恶行（谋杀、伤害无辜、习得黑暗魔法、使用邪恶造物）累积，上限等于意志（Willpower）。
- **腐化效果阶梯表**：0–3 无影响；4–6 社交掷骰承受劣势（bane）、动物敌视；7–8 濒死时命运掷骰 −1；9+ 肉体出现腐化征兆（疮疤、异常增生）。
- **阈值触发**：每次获得腐化时掷 2d6，若总数低于当前腐化值，则须掷**黑暗印记（Mark of Darkness）表**——肉体与命运的永久畸变。
- **疯狂（Insanity）**：与腐化独立。遭遇恐怖积累疯狂，达到意志值掷疯狂表；可通过接纳怪癖（Quirks，恐惧症/强迫行为）"消化"疯狂——创伤无法消除，只能转嫁。
- **致命性**：腐化 9+ 时濒死即真死，灵魂坠入地狱不可复生。

### 基调哲学

> "邪恶在凡人灵魂上留下污渍，唯有地狱深处的魔鬼能将其剥离——它们以此为食。腐化越高，你将承受的'魔鬼的殷勤'越多。"（改写自核心规则书）

### 与预设规则的对应

| 预设现有规则 | 规则书依据 |
|---|---|
| "力量必须附带腐化/诅咒，达到阈值触发后果" | Corruption 阈值表 + Mark of Darkness |
| "Boss 不是恶人，是受害者或守护者" | SotDL 的悲剧化设定笔法（陨落者/被腐蚀者） |
| "资产当前状态为退化/损坏/诅咒" | 邪恶造物（Evil Artifacts）累积腐化的设定 |

---

## 预设 4：wasteland_survival / 灰烬之路

**匹配规则书**：Mutant: Year Zero（Free League Publishing, Year Zero Engine, 2014）

> 备选：Apocalypse World（PbTA "匮乏"哲学）偏叙事抽象；MYZ 的**字面资源追踪 + 装备退化**与预设"量化描述、每段消耗资源"更吻合。

### 权威机制描述（采引）

- **零年引擎骰池**：技能骰（绿）+ 基础骰（黄）+ 装备骰（黑）；任一骰出 6（"/"符号）即成功。
- **推送（Pushing）**：可重掷未出成功/变异/损坏符号的骰子——但每次推送都有代价。
- **创伤系统（Trauma）**：推送后仍失败则按属性受创：力量→伤害、敏捷→疲劳、智力→混乱、共情→怀疑；各需不同的恢复方式（口粮/睡眠/情感亲近）。
- **装备退化（Gear Degradation）**：装备骰每出 "⚡"，装备加值降一档——装备在一次次的滥用中真实散架。
- **方舟（Ark）资源**：定居点资源有限，须推进项目（战争、食物、科技、文化）才能扩张；废土（Zone）远征永远在消耗与收益之间走钢丝。

### 基调哲学

> "资源日渐枯竭，对残余之物的争夺正变得暴力。你是人类的子嗣，却已不再是人类——强大，但不稳定。脆弱。"（改写自核心规则书）

### 与预设规则的对应

| 预设现有规则 | 规则书依据 |
|---|---|
| "所有行动消耗资源，零资源行动不存在" | MYZ 逐项资源追踪 + 推送代价 |
| "有价值的物品必有守护者或陷阱" | Zone 废墟拾荒（Scavenging）与遭遇设计 |
| "定居点以资源为核心组织，有内部矛盾" | Ark 项目制发展与派系斗争 |

---

## 预设 5：xianxia_cultivation / 碎天录

**匹配规则书**：Legends of the Wulin（Eos Press, 2012）

> 说明：西方市场无严格"修仙"大作，LoW 是最接近的已出版武侠/气功 TRPG——其内力修为、业力（karma）与宗门纠缠机制与仙侠概念高度相通。

### 权威机制描述（采引）

- **湖与河（Lake and River）**：骰池称"湖"，容量 = 5 + 河值，代表内力修为深浅；未用尽的骰子可存入"河"中留待后用——气机蓄发的机制化。
- **涟漪与气劲状态（Ripples & Chi Conditions）**：成功的攻击施加"涟漪"，累积成伤势/气劲状态——业力与修为后果的机制化表达；状态附条件惩罚，除非角色依特定方式行动。
- **秘术（Secret Arts）**：五门秘术可操纵人体、七情六欲、战局流转乃至天命预测——以条件加成实现"因果推演"。
- **传承笺（Loresheets）**：角色成长与宗门纠缠、业力义务绑定——"你的武功与你在江湖中的纠缠同涨"。
- **修为等阶（Ranks 5th→1st）**：从凡人到宗师，每进阶扩大湖/河容量——即"境界"体系。

### 基调哲学

> "抛却凡尘，加入武林——你的命运将由心火与武学修为决定。"（改写自核心规则书）

### 与预设规则的对应

| 预设现有规则 | 规则书依据 |
|---|---|
| "突破境界必引天劫，因果值加重天劫" | Rank 进阶 + Chi Conditions 的条件代价 |
| "法宝有灵智等级，可叛变" | Loresheets 传承物与纠缠义务 |
| "所有逆天行为增加因果值，不可消除只能承受" | 涟漪/业力的不可逆累积 |
| 宗门功法传承 + 派系斗争 | Loresheets 宗门纠缠结构 |

---

## 预设 6：space_opera / 群星彼岸

**匹配规则书**：Traveller, 2nd Edition（Mongoose Publishing, 2022）

> 备选：Star Wars: Edge of the Empire（FFG 叙事骰）重在个体冒险；本预设的"星际政治 + 势力平衡 + 文明史诗"与 Traveller 的**星区沙盒**更吻合。

### 权威机制描述（采引）

- **万用世界档案（Universal World Profile, UWP）**：8 位数字编码概括一颗行星（星港等级、直径、大气、水文、人口、政府、法律、科技等级）——可程序化批量生成整个星区。
- **星区建造（Sector Construction）**：每星区 16 个子星区，含政治版图、派系领土、星际冲突的正式生成流程。
- **派系资产（Faction Assets）**：势力资源分三类——武力（Force，军事）、诡诈（Cunning，谍报）、财富（Wealth，经济），各有生命值代表组织稳定性——"势力量化博弈"的直接机制化。
- **帝国官僚体系**：以文书、程序与官僚协议呈现"统治一万一千个世界的机器"——宏大政治的落地写法。
- **无轨沙盒（No rails required）**：星区自行运转，不依赖预设主线。

### 基调哲学

> "第三帝国与佐达尼领事国已打过四场边境战争——星区自行运转，无需轨道。"（改写自核心规则书）

### 与预设规则的对应

| 预设现有规则 | 规则书依据 |
|---|---|
| "每个种族有独立生物学/价值观/科技树" | UWP + 星区建造的种族/政府编码 |
| "势力有目标、实力和底线，玩家选择影响平衡" | Faction Assets（Force/Cunning/Wealth）量化博弈 |
| "远古科技不可完全理解，使用附带未知风险" | Traveller 遗迹（Ancients）设定传统 |
| "禁止地球中心主义" | Traveller 多元种族沙盒哲学 |

---

## 预设 7：classic_fantasy / 破晓之剑

**匹配规则书**：Dungeons & Dragons, 5th / 5.5 Edition（Wizards of the Coast, 2014/2024）

### 权威机制描述（采引）

- **三支柱（Three Pillars）**：社交互动（Social Interaction）、探索（Exploration）、战斗（Combat）为游戏的三大支柱——"无论身处哪个支柱，游戏都依此基本模式展开"。
- **d20 检定（d20 Tests）**：凡后果悬而未决、且成败皆有戏剧后果的行动，做 d20 检定——统一的判定术语。
- **优势/劣势（Advantage/Disadvantage）**：掷两个 d20 取高/取低，取代复杂修正值。
- **魔法动作（Magic Action，2024 版）**：施法、使用魔法物品、触发魔法特性统一为"魔法动作"——魔法系统的明确规则化。
- **熟练加值（Proficiency Bonus）**：全职业统一随等级成长的加值，适用于熟练的能力检定/攻击/豁免。

### 基调哲学

> "D&D 的三大支柱是社交、探索与战斗——游戏循环依此展开。"（改写自玩家手册）

### 与预设规则的对应

| 预设现有规则 | 规则书依据 |
|---|---|
| "施法消耗法力值，按法术等级阶梯定价" | 法术位（Spell Slots）环阶定价 + Magic Action |
| "禁止模糊的魔法系统" | D&D 明确的学派/环阶/成分（V/S/M）规则 |
| "主线三幕：召唤→试炼→决战" | D&D 官方冒险结构（如 Tyranny of Dragons） |
| "高阶装备有来历和使用条件" | 传奇物品（Legendary Items）设定传统 |

---

## 预设 8：court_intrigue / 鸩酒与玫瑰

**匹配规则书**：A Song of Ice and Fire Roleplaying（Green Ronin, 2008）

### 权威机制描述（采引）

- **阴谋系统（Intrigue System）**：社交冲突的完整战斗化——立场值（Disposition，友善→敌对）、技巧（Techniques：魅力/威吓/说服…）、以**风度（Composure）伤害**取代肉体伤害——"言语即武器，失态即败北"。
- **家族七属性（House Resources）**：防御（Defense）、影响力（Influence）、领地（Lands）、法度（Law）、人口（Population）、武力（Power）、财富（Wealth）——家族是全体玩家共同操控的"元角色（meta-character）"。
- **家族运势（House Fortunes）**：每月依总管属性做状态检定，决定影响家族资源的随机事件——持续的政治压力源。
- **联姻机制（Betrothal & Marriage）**：联姻须逐一说服每个有发言权者（各自需胜利点数），并伴随资源交换（嫁妆/同盟）——政治婚姻的完整博弈建模。
- **效忠家族（Banner Houses）**：以武力或影响力投资封臣，换取军事援助，但须持续维系忠诚——背叛有机制化空间。

### 基调哲学

> "贵族家族在某种意义上是另一个角色——由全体玩家共同操控的元角色，有历史、领地与可量化的强弱属性。"（改写自核心规则书）

### 与预设规则的对应

| 预设现有规则 | 规则书依据 |
|---|---|
| "社交事件包含情报层，可拦截/伪造/替换" | Intrigue 技巧与立场系统 |
| "派系有公开目标、隐藏目标、致命把柄" | House Resources + House Fortunes 压力 |
| "NPC 信任值隐藏，只能通过行为推断" | Disposition 隐藏立场设计 |
| "暴力是最后的、最笨的手段" | Intrigue 以 Composure 取代武力的设计哲学 |

---

## 文档版本

- **创建时间**：2026-08-21
- **上游数据源**：`docs/governance/seed-presets-catalog.md` / `backend/experiments/trpg_presets.py`
- **匹配方法**：按流派核心特征 → 已出版 TRPG 规则书的概念与机制重合度人工比对（研究由 librarian 代理完成，采引官方规则书术语）
- **用途**：预设描述的权威参照；后续 preset_loader 生成 10 板块默认值时的规则术语来源
