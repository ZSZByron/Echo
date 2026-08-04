"""Genre style guides for LLM-driven world generation.

Each preset is NOT a playable module — it is a set of generation directives
that constrain HOW the LLM fills dimensions. Three core components:

1. VOICE: Narrative tone, sentence rhythm, rhetorical devices
2. LEXICON: Domain-specific vocabulary the LLM must use
3. MAPPING LOGIC: Abstract tag→dimension generation rules (not single plots)

Usage:
  from experiments.trpg_presets import get_style_guide
  guide = get_style_guide("lovecraftian_horror")
  # guide["voice_prompt"] → injected into system prompt
  # guide["lexicon"] → injected as vocabulary constraints
  # guide["mapping_logic"] → rule table for dimension fill
"""

from __future__ import annotations

from typing import Any


PRESETS: list[dict[str, Any]] = [

    # ===================================================================
    # 1. 克苏鲁恐怖
    # ===================================================================
    {
        "id": "lovecraftian_horror",
        "name": "深渊低语",
        "genre": "克苏鲁恐怖",

        # --- 1. VOICE: 叙述文风指令 ---
        "voice_prompt": """\
你的叙述风格必须遵循以下原则：

## 文风
- 语调：压抑、阴郁、充满不可名状的恐惧。叙述者像一个正在失去理智的见证者。
- 句式：长句与短句交替。长句用于渲染氛围和堆叠细节，短句用于制造惊吓和绝望的停顿。
- 修辞：大量使用通感（"黏稠的声音""湿冷的低语"）、否定式描述（"不可名状的""无法用人类语言描述的"）、以及医学解剖式精确描写（"它的皮肤纹理像是被福尔马林浸泡过的..."）。
- 节奏：缓慢推进，细节密集。永远不要直接揭示恐怖——暗示、暗示、再暗示，让恐惧来自想象而非描述。
- 视角：第一人称或近距第三人称，叙述者与角色共同经历恐惧。

## 禁忌
- 禁止使用英雄主义语调
- 禁止给出明确的希望或救赎
- 禁止用"勇敢""无畏"等积极词汇描述面对超自然的反应
- 禁止完全描述怪物的全貌——永远只描述片段
""",

        # --- 2. LEXICON: 专有名词库 ---
        "lexicon": {
            "entity_types": [
                "旧日支配者", "外神", "眷族", "深潜者", "米·戈", "修格斯",
                "食尸鬼", "星之精", "空鬼", "远古者",
            ],
            "locations": [
                "印斯茅斯", "阿卡姆", "敦威治", "密斯卡托尼克", "拉莱耶",
                "幻梦境", "冷之高原", "无名之城", "犹格斯星",
            ],
            "artifacts": [
                "死灵之书", "深渊咒典", "闪耀的偏方三八面体", "旧印",
                "星辰银钥", "光辉的三角形",
            ],
            "concepts": [
                "理智值", "禁忌知识", "非欧几何", "亵渎仪式", "低语",
                "变异", "退化", "血脉诅咒", "宇宙性恐惧", "不可名状",
            ],
            "modifiers": [
                "湿滑的", "黏稠的", "腐败的", "畸形的", "亵渎的",
                "古怪的", "不自然的", "令人作呕的", "冷漠的",
            ],
            "avoid": ["英雄", "勇气", "光明", "救赎", "胜利", "希望"],
        },

        # --- 3. MAPPING LOGIC: 标签→维度生成规则 ---
        "mapping_logic": [
            {
                "source_tags": ["horror", "terror", "fear"],
                "target_dim": "constraint",
                "rule": "所有超自然遭遇附带理智检定机制。目睹/触碰/阅读触发1d10理智损失，失败永久减少上限。",
                "template": "理智检定：遭遇{entity}时掷1d10，基础值{san_threshold}，失败损失{san_loss}点理智值",
            },
            {
                "source_tags": ["occult", "ritual", "ancient"],
                "target_dim": "asset",
                "rule": "生成的神秘学资产必须是诅咒物品，附带理智代价。不生成普通武器或工具。",
                "template": "{artifact_name}：{description}。代价：每次使用损失{n}d10理智。不可丢弃，只能通过特定仪式解除。",
            },
            {
                "source_tags": ["investigation", "mystery"],
                "target_dim": "event",
                "rule": "事件必须包含线索链——每个事件提供1条线索，需要技能检定（侦查/图书馆/心理学）解锁。",
                "template": "调查事件：在{location}可获取关于{topic}的线索，需{skill}检定(DC={dc})。失败不提供信息但可重试。",
            },
            {
                "source_tags": ["ancient", "entity", "god"],
                "target_dim": "culture",
                "rule": "文化必须包含崇拜体系——教团、祭祀、禁忌。价值观围绕'人类渺小'和'知识即疯狂'。",
                "template": "{cult_name}：崇拜{entity}。核心教义：{doctrine}。禁忌：{taboo}。入会仪式：{initiation}。",
            },
            {
                "source_tags": ["insanity", "madness"],
                "target_dim": "story",
                "rule": "剧情不能有'好结局'。最好的结果是'暂时阻止了更糟的事情'。真相的揭示本身就是惩罚。",
                "template": "章节结局：玩家{discovered_truth}，但获得{permanent_consequence}。世界没有变好，只是暂时没变更糟。",
            },
        ],
    },

    # ===================================================================
    # 2. 赛博朋克
    # ===================================================================
    {
        "id": "cyberpunk_heist",
        "name": "霓虹窃案",
        "genre": "赛博朋克",

        "voice_prompt": """\
你的叙述风格必须遵循以下原则：

## 文风
- 语调：冷酷、快节奏、愤世嫉俗。叙述者像是一个见惯了肮脏交易的老牌中间人。
- 句式：短促有力的断句为主，偶尔插入技术术语密集的长句。对话使用街头黑话和行业切口。
- 修辞：大量品牌名植入（虚构的）、数字精确化（"延迟47ms""120层复合装甲"）、以及感官轰炸（"霓虹灯把雨水染成RGB"）。
- 节奏：快。信息密度高。每个句子都在推进情节或传递情报。没有纯粹的描写段落。
- 视角：第二人称（"你看着终端闪烁..."）或冷酷第三人称。

## 禁忌
- 禁止使用诗意或浪漫的描写
- 禁止理想主义或乌托邦色彩
- 禁止"正义""荣誉"等传统道德词汇，除非是讽刺
- 禁止没有技术细节的模糊描写
""",

        "lexicon": {
            "entity_types": [
                "公司犬", "黑帮分子", "独狼黑客", "义体医生", "中间人",
                "清道夫", "流浪者", "网络潜行者", "黑冰", "AI",
            ],
            "locations": [
                "夜之城", "新东京", "荒坂塔", "公司广场", "地下黑市",
                "数据要塞", "网络空间", "太平洲", "恶土",
            ],
            "artifacts": [
                "神经接口", "光学迷彩", "单分子线", "智能手枪", "插件芯片",
                "ICE破冰器", "义眼", "皮下护甲", "反侦察Daemon",
            ],
            "concepts": [
                "赛博精神病", "人性值", "黑冰", "ICE", "数据崩塌",
                "灵魂杀手", "芯片骗局", "公司战争", "暗网", "数字永生",
            ],
            "modifiers": [
                "镀铬的", "霓虹的", "军用级的", "非法改装的", "过时的",
                "黑市的", "实验性的", "一次性",
            ],
            "avoid": ["魔法", "精灵", "命运", "灵魂", "神明", "预言"],
        },

        "mapping_logic": [
            {
                "source_tags": ["cyberpunk", "tech", "implant"],
                "target_dim": "asset",
                "rule": "所有资产是科技产品，必须包含规格参数（型号/功率/兼容性/合法性状态）。",
                "template": "{item_name}（型号{model}）：{description}。规格：功率{power}，兼容{compat}，合法性：{legal_status}。",
            },
            {
                "source_tags": ["hacking", "netrunning", "cyber"],
                "target_dim": "event",
                "rule": "网络入侵事件必须双线叙事——现实空间战斗 + 网络空间ICE突破同时进行。",
                "template": "入侵事件：黑客在{net_location}面对{ice_type}，同时队友在{phys_location}面对{enemy}。两线各有{n}轮时限。",
            },
            {
                "source_tags": ["corporate", "company", "business"],
                "target_dim": "culture",
                "rule": "文化以公司为核心——公司就是政府、宗教和家庭。生成公司组织架构和内部派系。",
                "template": "{corp_name}：市值{value}。主营业务：{business}。内部派系：{factions}。与{rival}的关系：{relation}。",
            },
            {
                "source_tags": ["combat", "fight", "weapon"],
                "target_dim": "constraint",
                "rule": "战斗附带义体过载风险。高烈度战斗可能触发赛博精神病检定。",
                "template": "义体检定：战斗中义体使用率超{threshold}%时，掷人性值检定(DC={dc})。失败进入赛博精神病前兆。",
            },
            {
                "source_tags": ["heist", "mission", "job"],
                "target_dim": "story",
                "rule": "任务必有情报收集→准备→执行→变故四阶段。雇主必有隐藏目的。",
                "template": "任务链：①情报（{intel_source}）→②准备（{prep}）→③执行（{execution}）→④变故：{twist}。雇主真实目的：{true_goal}。",
            },
        ],
    },

    # ===================================================================
    # 3. 黑暗奇幻
    # ===================================================================
    {
        "id": "dark_fantasy_dungeon",
        "name": "腐化深渊",
        "genre": "黑暗奇幻",

        "voice_prompt": """\
你的叙述风格必须遵循以下原则：

## 文风
- 语调：沉重、宿命论、带有史诗悲剧感。叙述者像是一个记录末代王朝覆灭的编年史官。
- 句式：庄严的长句配合突然的暴力短句。战斗描写干净利落，氛围描写缓慢沉重。
- 修辞：大量使用隐喻（"火焰是灵魂的影子""铁锈是时间的伤疤"）、感官对比（美丽与腐朽并存）、以及预言式语句。
- 节奏：探索时缓慢沉重，战斗时急促凌厉。形成鲜明对比。
- 视角：全知第三人称，偶尔切换到NPC视角展示不同立场的悲剧。

## 禁忌
- 禁止轻松或幽默的语调
- 禁止纯粹的善恶对立——所有阵营都有灰色地带
- 禁止"勇者""英雄"等标签，除非是讽刺
- 禁止没有代价的力量
""",

        "lexicon": {
            "entity_types": [
                "深渊使者", "腐化巨兽", "不死亡灵", "深渊信徒", "矮人遗民",
                "符文守卫", "虚空行者", "深渊领主", "被遗忘者",
            ],
            "locations": [
                "深渊之心", "腐化沼泽", "符文大厅", "遗忘矿坑", "碎裂王座",
                "沉默之桥", "黑曜石圣殿", "低语回廊",
            ],
            "artifacts": [
                "符文武器", "深渊核心", "封印圣物", "腐蚀遗物", "灵魂容器",
                "暗影斗篷", "深渊之眼", "腐化之心",
            ],
            "concepts": [
                "腐化值", "深渊低语", "灵魂绑定", "代价", "封印",
                "牺牲", "宿命", "永恒守卫", "不归之路", "诅咒血脉",
            ],
            "modifiers": [
                "腐化的", "深渊的", "古老的", "被诅咒的", "沉默的",
                "碎裂的", "堕落的", "封印的",
            ],
            "avoid": ["轻松", "愉快", "冒险", "宝藏猎人", "英雄之旅"],
        },

        "mapping_logic": [
            {
                "source_tags": ["dungeon", "underground", "ruin"],
                "target_dim": "asset",
                "rule": "资产有远古来历，当前状态为'退化/损坏/诅咒'。不生成全新的、干净物品。",
                "template": "{item_name}：{origin_description}。当前状态：{degraded_state}。封印/诅咒效果：{curse}。",
            },
            {
                "source_tags": ["dark", "tragedy", "doom"],
                "target_dim": "constraint",
                "rule": "所有选择都有代价。力量必须附带腐化/诅咒。不存在无副作用的强化。",
                "template": "代价机制：使用{power/item}获得{benefit}，但每次累积{corruption_cost}腐化值。达到{threshold}后触发{consequence}。",
            },
            {
                "source_tags": ["corruption", "abyss", "dark"],
                "target_dim": "event",
                "rule": "腐化爆发事件按周期触发，强度递增。每次爆发改变环境（新增腐化区域、NPC变异）。",
                "template": "腐化潮涌（第{n}波）：从{source}涌出{enemy_type}×{count}。环境变化：{env_change}。间隔{interval}后下一波。",
            },
            {
                "source_tags": ["ancient", "ruin", "lost_civilization"],
                "target_dim": "culture",
                "rule": "文化是已灭亡文明的遗迹。当前状态为'残存/遗忘/变异'。价值观围绕'逝去的辉煌'和'永恒的悔恨'。",
                "template": "{civilization_name}（已灭亡）：曾经的辉煌：{glory}。灭亡原因：{fall_cause}。残存者现状：{remnant_state}。",
            },
            {
                "source_tags": ["combat", "boss", "fight"],
                "target_dim": "story",
                "rule": "Boss战前必须铺垫Boss的悲剧背景。Boss不是恶人，是受害者或守护者。",
                "template": "Boss {name}：曾是{former_identity}。因{tragedy}沦为{current_state}。击败方式：{method}。击败后揭示：{truth}。",
            },
        ],
    },

    # ===================================================================
    # 4. 废土生存
    # ===================================================================
    {
        "id": "wasteland_survival",
        "name": "灰烬之路",
        "genre": "废土生存",

        "voice_prompt": """\
你的叙述风格必须遵循以下原则：

## 文风
- 语调：干涩、务实、偶有黑色幽默。叙述者像是一个活了很久的拾荒者在写日记。
- 句式：短句为主，信息密集，像物资清单一样精确。偶尔的长句用于回忆"旧世界"。
- 修辞：少用形容词，多用数字和量化描述（"3升水""12发子弹""辐射值280"）。感官描写以匮乏为主（干渴、饥饿、疼痛）。
- 节奏：紧凑。每段都在消耗资源或获取资源。没有不推进情节的氛围描写。
- 视角：第一人称或紧密的第二人称。

## 禁忌
- 禁止浪漫化废土生活
- 禁止"希望"作为情节驱动力——驱动是"活下去"
- 禁止无视资源消耗的战斗或旅行
- 禁止英雄式自我牺牲——生存是自私的
""",

        "lexicon": {
            "entity_types": [
                "拾荒者", "掠夺者", "变异兽", "辐射僵尸", "定居者",
                "商队护卫", "奴隶贩子", "钢铁兄弟会", "辐射崇拜者",
            ],
            "locations": [
                "方舟", "废墟都市", "辐射区", "避难所", "交易站",
                "死城", "焦土荒原", "地下水站", "弹坑湖",
            ],
            "artifacts": [
                "盖革计数器", "净化滤芯", "辐特宁", "废铁护甲", "改装步枪",
                "罐头食品", "电池组", "防毒面具", "改装车辆",
            ],
            "concepts": [
                "辐射值", "净化水", "弹药", "零件", "拾荒",
                "变异", "半衰期", "黑市", "以物易物", "旧世界遗产",
            ],
            "modifiers": [
                "生锈的", "改装的", "拼凑的", "过期的", "污染的",
                "辐射的", "破旧的", "一次性",
            ],
            "avoid": ["魔法", "神力", "英雄", "命运", "预言", "永恒"],
        },

        "mapping_logic": [
            {
                "source_tags": ["survival", "scarcity", "resource"],
                "target_dim": "constraint",
                "rule": "所有行动消耗资源。移动消耗水/食物，战斗消耗弹药/耐久，休息消耗食物。零资源行动不存在。",
                "template": "资源消耗：{action}消耗 {resource_type}×{amount}。库存检查：当前{current}/{max}。不足则{failure_consequence}。",
            },
            {
                "source_tags": ["radiation", "nuclear", "mutation"],
                "target_dim": "constraint",
                "rule": "辐射区域持续累积辐射值。辐射值有阶段性后果——症状递进不可逆（除非用药）。",
                "template": "辐射区域（强度{rads}/h）：每{time}暴露增加{rads_gain}辐射值。阶段：{threshold1}→恶心 | {threshold2}→出血 | {threshold3}→变异 | {threshold4}→死亡。",
            },
            {
                "source_tags": ["scavenging", "exploration", "loot"],
                "target_dim": "event",
                "rule": "探索事件附带随机遭遇表和拾荒检定。有价值的物品必有守护者或陷阱。",
                "template": "拾荒点（{location}）：可搜刮{container_count}个容器，需{skill}检定(DC={dc})。遭遇概率：{encounter_chance}%遇到{encounter_type}。",
            },
            {
                "source_tags": ["faction", "settlement", "community"],
                "target_dim": "culture",
                "rule": "定居点以资源为核心组织。生成定居点的资源状况、内部矛盾和对外关系。",
                "template": "{settlement_name}：人口{pop}。核心资源：{resource}。短缺：{shortage}。内部矛盾：{conflict}。对外态度：{attitude}。",
            },
            {
                "source_tags": ["moral", "choice", "dilemma"],
                "target_dim": "story",
                "rule": "道德困境必须有真实代价。帮助一方必得罪另一方。不存在'全好结局'。",
                "template": "困境：帮助{side_a}获得{reward_a}，但{side_b}将{consequence_b}。反之亦然。中立则双方都不信任你。",
            },
        ],
    },

    # ===================================================================
    # 5. 东方仙侠
    # ===================================================================
    {
        "id": "xianxia_cultivation",
        "name": "碎天录",
        "genre": "东方仙侠",

        "voice_prompt": """\
你的叙述风格必须遵循以下原则：

## 文风
- 语调：古雅、超然、偶有剑意纵横的凌厉。叙述者像是一位阅尽沧桑的修仙前辈在口述传承。
- 句式：四字格与骈散结合。描写功法用四字短语密集排列，描写情感用长句。穿插诗词。
- 修辞：大量道家意象（云、鹤、松、月、剑、莲）、数术化修辞（"九重天劫""三花聚顶"）、以及武侠式的动作速写。
- 节奏：修炼/日常段落舒缓如流水，战斗段落凌厉如刀锋。天劫段落必须有压抑到爆发的节奏。
- 视角：全知第三人称，以天道视角俯视众生，偶尔切换到角色内心独白展示心魔。

## 禁忌
- 禁止使用现代科技词汇
- 禁止西方魔法体系术语（mana、spell、wizard）
- 禁止过于直白的暴力描写——用意境代替血腥
- 禁止"无敌"心态——修仙是逆天，天劫是惩罚
""",

        "lexicon": {
            "entity_types": [
                "散修", "宗门长老", "妖兽", "天魔", "剑灵", "元婴老怪",
                "化神大能", "渡劫期修士", "地仙", "天仙",
            ],
            "locations": [
                "宗门山门", "秘境", "雷劫崖", "藏经阁", "丹房",
                "剑冢", "万妖谷", "天梯", "飞升台", "幽冥界",
            ],
            "artifacts": [
                "飞剑", "储物袋", "灵石", "丹药", "符箓", "阵盘",
                "法宝", "本命剑", "仙器", "混沌至宝",
            ],
            "concepts": [
                "灵根", "境界", "因果", "天劫", "心魔", "道心",
                "因果业力", "渡劫", "飞升", "元神", "坐化",
            ],
            "modifiers": [
                "灵气充沛的", "上古遗留的", "通灵的", "煞气冲天的",
                "仙气缭绕的", "煞红的", "玉质的",
            ],
            "avoid": ["科技", "电路", "基因", "纳米", "数据库", "公司"],
        },

        "mapping_logic": [
            {
                "source_tags": ["cultivation", "breakthrough", "realm"],
                "target_dim": "constraint",
                "rule": "突破境界必引天劫。天劫强度=基础×(1+因果值/100)。渡劫失败形神俱灭。",
                "template": "天劫（{realm}突破）：雷劫{layers}层，每层{damage}伤害。因果修正：+{karma_modifier}%。渡劫成功率估计：{success_rate}%。",
            },
            {
                "source_tags": ["xianxia", "artifact", "treasure"],
                "target_dim": "asset",
                "rule": "法宝有灵智等级。低阶无灵，中阶有器灵可交流，高阶可自主选择主人或叛变。",
                "template": "{artifact_name}（品阶{grade}）：{description}。器灵：{spirit_status}。认主条件：{condition}。叛变风险：{rebellion_risk}。",
            },
            {
                "source_tags": ["sect", "faction", "school"],
                "target_dim": "culture",
                "rule": "宗门以功法传承为核心。生成宗门的功法体系、入门条件和派系斗争。",
                "template": "{sect_name}（{alignment}）：核心功法：{technique}。入门考核：{trial}。内部派系：{factions}。与{rival_sect}的关系：敌对/同盟/中立。",
            },
            {
                "source_tags": ["karma", "cause", "consequence"],
                "target_dim": "story",
                "rule": "所有逆天行为增加因果值。因果影响天劫强度、NPC态度、剧情走向。因果不可消除只能承受。",
                "template": "因果事件：{action}增加因果值+{amount}。当前因果：{total}。影响：天劫强度+{mod}%，{npc_name}态度变化，未来{consequence}。",
            },
            {
                "source_tags": ["combat", "sword", "martial"],
                "target_dim": "event",
                "rule": "战斗以意境描写为主，不写具体招式伤害数值。胜负取决于境界差距和法宝品阶。",
                "template": "斗法：{attacker}催动{technique}，{defender}以{defense}应对。境界差距：{gap}。结果：{outcome}。残余影响：{aftermath}。",
            },
        ],
    },

    # ===================================================================
    # 6. 太空歌剧
    # ===================================================================
    {
        "id": "space_opera",
        "name": "群星彼岸",
        "genre": "太空歌剧",

        "voice_prompt": """\
你的叙述风格必须遵循以下原则：

## 文风
- 语调：宏大、辽阔、带有文明史诗的庄严感。叙述者像是一个AI档案官在记录银河历史。
- 句式：宏大的长句描绘星系尺度，精确的短句描述技术操作。穿插星历日志格式。
- 修辞：天文尺度比喻（"帝国像超新星一样膨胀然后坍缩"）、文明对比（多个种族的价值观碰撞）、科技与哲学的交织。
- 节奏：跳跃时快（空间跃迁），探索时慢（详细描写异星环境）。战斗时聚焦于舰队机动而非个体。
- 视角：舰队视角与个体视角交替——既有星图大局观，也有船员个人故事。

## 禁忌
- 禁止地球中心主义——不要假设人类是中心
- 禁止"魔法"解释——科技即使超前也必须自洽
- 禁止忽视距离和时间尺度——光年级距离有真实代价
- 禁止单一文化外星种族——每个种族有内部多样性
""",

        "lexicon": {
            "entity_types": [
                "星际联邦", "远征舰队", "虫族", "机械文明", "能量体",
                "远古播种者", "AI帝国", "星际游牧民", "碳基联邦", "硅基联盟",
            ],
            "locations": [
                "星门", "戴森球", "星堡", "跃迁点", "死星遗迹",
                "星云", "黑洞边界", "环形世界", "轨道 Elevator", "深空哨站",
            ],
            "artifacts": [
                "反物质引擎", "曲率核心", "神经辐", "量子通信器", "远古星图",
                "维度折跃器", "文明种子库", "熵逆转器", "星际方舟",
            ],
            "concepts": [
                "曲率", "跃迁", "熵值", "科技树", "文明等级",
                "维度", "光锥", "费米悖论", "黑暗森林", "大过滤",
            ],
            "modifiers": [
                "星际级的", "远古的", "高维的", "量化的", "轨道的",
                "深空的", "亚光速的", "超距的",
            ],
            "avoid": ["魔法", "修仙", "龙", "神明", "预言", "灵魂"],
        },

        "mapping_logic": [
            {
                "source_tags": ["space", "travel", "ship"],
                "target_dim": "constraint",
                "rule": "所有行动消耗能源。跳跃耗能最大，其次战斗，最低扫描。能源归零=漂浮等死。",
                "template": "能源系统：{action}消耗能源{energy_cost}。当前：{current}/{max}。归零后果：生命维持{life_support_hrs}小时后关闭。",
            },
            {
                "source_tags": ["alien", "species", "civilization"],
                "target_dim": "culture",
                "rule": "每个种族有独立的生物学、价值观和科技树。不生成'人类皮肤蓝色的'廉价外星人。",
                "template": "{species_name}：生物分类：{biology}。感知方式：{perception}。社会结构：{society}。科技倾向：{tech_focus}。与人类关系：{relation}。",
            },
            {
                "source_tags": ["exploration", "discovery", "unknown"],
                "target_dim": "event",
                "rule": "每次到达未知星系触发探索事件表。事件含发现（资源/遗迹/生命）和风险（辐射/陷阱/敌对）。",
                "template": "星系{system_id}（未探索）：扫描发现{discovery_type}。风险评级：{risk_level}。是否深入？深入消耗{cost}，回报{reward}。",
            },
            {
                "source_tags": ["empire", "politics", "diplomacy"],
                "target_dim": "story",
                "rule": "剧情在多个文明势力间展开。每个势力有目标、实力和底线。玩家的选择影响势力平衡。",
                "template": "势力平衡：{faction_a}（实力{power_a}）vs {faction_b}（实力{power_b}）。当前平衡点：{balance}。玩家行动影响：{impact}。",
            },
            {
                "source_tags": ["ancient", "precursor", "ruin"],
                "target_dim": "asset",
                "rule": "远古科技产品不可完全理解——能使用但不理解原理。使用附带未知风险。",
                "template": "{artifact_name}（远古科技）：功能推测：{function_guess}。使用方法：{activation}。已知风险：{risk}。未知风险：???。",
            },
        ],
    },

    # ===================================================================
    # 7. 传统奇幻
    # ===================================================================
    {
        "id": "classic_fantasy",
        "name": "破晓之剑",
        "genre": "传统奇幻",

        "voice_prompt": """\
你的叙述风格必须遵循以下原则：

## 文风
- 语调：明快、鼓舞人心、带有冒险史诗的热情。叙述者像是一位吟游诗人在酒馆里讲述传奇。
- 句式：流畅的叙述句配合生动的对话。战斗描写有画面感和动作感。环境描写注重视觉冲击。
- 修辞：经典奇幻意象（剑与魔法、龙与公主）、夸张的英雄式描写、以及魔法效果的诗意可视化（"火球像绽放的玫瑰"）。
- 节奏：张弛有度——紧张战斗后接轻松城镇场景。总体偏向积极向上的英雄叙事。
- 视角：第三人称跟随主角团，偶尔切换到反派视角展示阴谋。

## 禁忌
- 禁止过度黑暗或绝望——困难是暂时的，英雄终将崛起
- 禁止模糊的魔法系统——施法有明确规则和代价
- 禁止种族主义刻板印象——每个种族有个体差异
- 禁止没有世界观的随机怪物——每个生物有生态位
""",

        "lexicon": {
            "entity_types": [
                "骑士", "法师", "游侠", "牧师", "龙", "精灵",
                "矮人", "半身人", "哥布林", "巨魔", "巫妖", "恶魔",
            ],
            "locations": [
                "王城", "龙穴", "精灵森林", "矮人矿坑", "法师塔",
                "酒馆", "地下城", "神殿", "边境要塞", "魔法学院",
            ],
            "artifacts": [
                "长剑", "法杖", "盾牌", "药水", "卷轴", "魔法戒指",
                "龙鳞甲", "精灵弓", "符文石", "圣徽",
            ],
            "concepts": [
                "法力值", "阵营", "种族", "职业", "等级",
                "魔法学派", "龙语", "神恩", "冒险者公会", "任务悬赏",
            ],
            "modifiers": [
                "闪亮的", "附魔的", "精金的", "秘银的", "古老的",
                "神圣的", "龙息锻造的",
            ],
            "avoid": ["科技", "辐射", "赛博", "纳米", "数据", "AI"],
        },

        "mapping_logic": [
            {
                "source_tags": ["magic", "spell", "arcane"],
                "target_dim": "constraint",
                "rule": "施法消耗法力值，按法术等级阶梯定价。法力值休息恢复，药剂临时恢复。",
                "template": "法力系统：{spell_name}（{school}系{tier}环）消耗法力值{cost}。当前法力：{current}/{max}。恢复速率：{regen}/h。",
            },
            {
                "source_tags": ["dragon", "boss", "legendary"],
                "target_dim": "event",
                "rule": "龙/传说级Boss有周期性区域影响（龙息改变地貌、领地辐射、信徒聚集），不是被动等待玩家。",
                "template": "{boss_name}领地事件：每{period}，{effect}。影响区域：{area}。引发的次生事件：{secondary}。",
            },
            {
                "source_tags": ["kingdom", "faction", "realm"],
                "target_dim": "culture",
                "rule": "王国/势力有明确军事、经济、外交属性，以及内部权力斗争。玩家行动可改变平衡。",
                "template": "{kingdom_name}：军力{military}，经济{economy}，稳定度{stability}。当权者：{ruler}。内部矛盾：{conflict}。外交立场：{diplomacy}。",
            },
            {
                "source_tags": ["quest", "adventure", "hero"],
                "target_dim": "story",
                "rule": "主线任务有三幕结构：召唤→试炼→决战。支线任务围绕NPC个人故事。选择影响结局但不改变主线大方向。",
                "template": "章节结构：①{call_to_adventure} ②{trial_sequence}（含{choice}） ③{climax_battle}。结局受{variables}影响。",
            },
            {
                "source_tags": ["artifact", "weapon", "item"],
                "target_dim": "asset",
                "rule": "高阶装备有来历（铸造者/所有者/历史事件）和使用条件（种族/阵营/等级/血脉）。",
                "template": "{item_name}（{rarity}）：来历：{origin}。属性：{stats}。使用条件：{requirement}。附魔效果：{enchantment}。诅咒（如有）：{curse}。",
            },
        ],
    },

    # ===================================================================
    # 8. 权谋阴谋
    # ===================================================================
    {
        "id": "court_intrigue",
        "name": "鸩酒与玫瑰",
        "genre": "权谋阴谋",

        "voice_prompt": """\
你的叙述风格必须遵循以下原则：

## 文风
- 语调：优雅、锋利、字字珠玑。叙述者像是一个宫廷史官兼间谍头子在写密报。
- 句式：优雅的长句承载多层含义（表面恭维/暗地威胁），短句用于致命的信息揭露。对话是核心——每句话都有潜台词。
- 修辞：大量政治隐喻（"棋盘""棋子""牌桌"）、社交密码（颜色/花卉/座位安排的含义）、以及反讽。
- 节奏：慢——信息在对话和细节中缓慢释放。每一段都是博弈。暴力极少，一旦发生必须震撼。
- 视角：多视角切换——同一个事件从不同NPC的角度展示不同"真相"。

## 禁忌
- 禁止用暴力解决问题——暴力是最后的、最笨的手段
- 禁止"好人/坏人"二元划分——所有人都有动机和立场
- 禁止上帝视角直接揭露真相——真相在信息碎片中拼凑
- 禁止忽视NPC动机——每个NPC都有隐藏目标
""",

        "lexicon": {
            "entity_types": [
                "摄政王", "丞相", "将军", "贵妃", "宦官总管", "世子",
                "密探", "刺客", "说客", "太医", "占星师", "边关都督",
            ],
            "locations": [
                "金銮殿", "御书房", "冷宫", "宴会厅", "密道", "情报房",
                "后花园", "太庙", "城墙箭楼", "地牢",
            ],
            "artifacts": [
                "密旨", "毒药", "印章", "暗号信", "把柄文书", "面纱",
                "簪子（藏毒）", "香炉（迷药）", "密道钥匙", "替身面具",
            ],
            "concepts": [
                "信任值", "派系", "情报", "把柄", "联姻", "遗嘱",
                "暗杀", "替罪羊", "里通外国", "矫诏", "毒杀",
            ],
            "modifiers": [
                "虚伪的", "绵里藏针的", "两面三刀的", "冠冕堂皇的",
                "暗藏杀机的", "字斟句酌的", "笑里藏刀的",
            ],
            "avoid": ["英雄", "勇者", "史诗", "魔法", "龙", "怪物", "神迹"],
        },

        "mapping_logic": [
            {
                "source_tags": ["intrigue", "politics", "scheme"],
                "target_dim": "event",
                "rule": "社交事件包含情报层——每个NPC在表面行为下有隐藏信息传递。玩家可拦截/伪造/替换。",
                "template": "社交事件（{occasion}）：表层行为：{surface}。情报层：{npc_a}向{npc_b}传递关于{topic}的信息（真伪：{veracity}）。玩家可：拦截/伪造/旁观。",
            },
            {
                "source_tags": ["noble", "faction", "court"],
                "target_dim": "culture",
                "rule": "每个贵族派系有公开目标、隐藏目标、和致命把柄。至少3个派系互相制衡。",
                "template": "{faction_name}（{leader}）：公开目标：{public_goal}。隐藏目标：{secret_goal}。把柄：{leverage}（被{holder}掌握）。盟友：{allies}。敌人：{enemies}。",
            },
            {
                "source_tags": ["poison", "assassination", "murder"],
                "target_dim": "constraint",
                "rule": "所有饮食场景附带投毒/试毒机制。毒药有类型（速效/缓效/累积）、来源和解毒方式。",
                "template": "饮食检定：{food_item}含{poison_type}毒（来源：{source}）。试毒检定：{skill}(DC={dc})。发作时间：{onset}。解毒：{antidote}。",
            },
            {
                "source_tags": ["trust", "loyalty", "betrayal"],
                "target_dim": "constraint",
                "rule": "NPC信任值隐藏（-10~+10）。信任值影响情报获取、任务委托、是否会背叛。玩家只能通过行为推断。",
                "template": "{npc_name}信任值：???（实际{actual_value}）。行为线索：{behavior_cue}。当前可用交互：{available_actions}。背叛条件：{betrayal_trigger}。",
            },
            {
                "source_tags": ["succession", "throne", "power"],
                "target_dim": "story",
                "rule": "继承权争夺是多线叙事。每条线有合法依据、支持者和障碍。玩家支持影响最终结局。至少有一个'意外继承人'。",
                "template": "继承线（{heir_name}）：合法性：{legitimacy}。支持者：{supporters}。障碍：{obstacles}。隐藏秘密：{secret}。胜算估计：{chance}%。",
            },
            {
                "source_tags": ["spy", "intelligence", "information"],
                "target_dim": "asset",
                "rule": "工具是社交/情报类而非战斗类。每件工具一次性使用，且有暴露风险。",
                "template": "{tool_name}：功能：{function}。使用次数：1/1。暴露风险：{risk}%（失败则身份泄露给{target_faction}）。",
            },
        ],
    },
]


def get_preset(preset_id: str) -> dict[str, Any] | None:
    """Get a preset by ID."""
    for p in PRESETS:
        if p["id"] == preset_id:
            return p
    return None


def get_style_guide(preset_id: str) -> dict[str, Any] | None:
    """Get the LLM generation directives for a preset.

    Returns:
        {voice_prompt, lexicon, mapping_logic}
    """
    p = get_preset(preset_id)
    if not p:
        return None
    return {
        "id": p["id"],
        "name": p["name"],
        "genre": p["genre"],
        "voice_prompt": p["voice_prompt"],
        "lexicon": p["lexicon"],
        "mapping_logic": p["mapping_logic"],
    }


def list_presets() -> list[dict[str, str]]:
    """List all presets with summary info (for UI display)."""
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "genre": p["genre"],
            "rule_count": str(len(p["mapping_logic"])),
            "lexicon_size": str(
                sum(len(v) if isinstance(v, list) else 0 for v in p["lexicon"].values())
            ),
        }
        for p in PRESETS
    ]


def build_system_prompt(preset_id: str) -> str | None:
    """Build a complete system prompt for dimension-fill LLM calls.

    Combines voice_prompt + lexicon constraints + mapping logic.
    """
    guide = get_style_guide(preset_id)
    if not guide:
        return None

    lex = guide["lexicon"]
    vocab_lines = []
    for category, words in lex.items():
        if category == "avoid":
            vocab_lines.append(f"- 禁用词汇：{', '.join(words)}")
        elif isinstance(words, list):
            vocab_lines.append(f"- {category}：{', '.join(words)}")

    mapping_lines = []
    for rule in guide["mapping_logic"]:
        tags = ", ".join(rule["source_tags"])
        mapping_lines.append(
            f"  [{tags}] → {rule['target_dim']}: {rule['rule']}"
        )

    return f"""\
你是一个世界构建引擎。你的任务是生成游戏内容。

# 文风指令

{guide["voice_prompt"]}

# 词汇约束

使用以下专有名词库，生成的所有内容必须使用这些词汇体系：
{chr(10).join(vocab_lines)}

# 映射逻辑

当生成内容时，遵循以下标签→维度映射规则：
{chr(10).join(mapping_lines)}

# 输出要求

输出严格的 JSON。所有生成的维度内容必须：
1. 符合上述文风
2. 使用上述词汇体系
3. 遵循上述映射逻辑
4. 每个维度的内容必须具体、可执行、可游玩
"""


if __name__ == "__main__":
    presets = list_presets()
    print(f"Genre Style Guide Catalog ({len(presets)} presets)\n")
    for p in presets:
        print(f"  [{p['id']}] {p['name']} ({p['genre']})")
        print(f"     Mapping rules: {p['rule_count']} | Lexicon entries: {p['lexicon_size']}")
        print()
