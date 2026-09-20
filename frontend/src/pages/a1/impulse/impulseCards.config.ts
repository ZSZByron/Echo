/**
 * 冲动卡配置（E0 入口，计划 e0-impulse-entry T2）
 *
 * 类型枚举逐字锁定（spec §2 八冲动型 + 通用线 v1.2）：
 *   setting_heavy(设定-重度) / character_driven(角色驱动线) / plot(剧情) /
 *   philosophy(哲理) / exploration(探索) / romance(爱情) / nostalgia(怀旧) /
 *   healing(疗愈) / unsure(说不清)
 *
 * 文案纪律（每卡过审，审查清单见 .sisyphus/evidence/task-2-copy-review-checklist.md）：
 *   - 场景意象：第一人称"我想…"式，禁功能词（AI/算法/推荐/测评/个性化/分析）
 *   - D5 共鸣：用户看到即认领
 *   - R3 言情框架（romance 专属）：锚定"感情故事"，零暧昧措辞
 *   - R4 无诱导承诺（healing 专属）：低压力中性表述，禁陪伴承诺
 *   - unsure 宽恕式措辞，殿后弱化
 */

export type ImpulseTypeId =
  | 'setting_heavy'
  | 'character_driven'
  | 'plot'
  | 'philosophy'
  | 'exploration'
  | 'romance'
  | 'nostalgia'
  | 'healing'
  | 'unsure';

export interface ImpulseCard {
  id: ImpulseTypeId;
  /** 卡片标题，≤6 字 */
  label: string;
  /** 场景意象一句话，15-30 字（2-4 秒可读完） */
  tagline: string;
}

/** 卡片顺序 = spec §2 八型顺序 + unsure 殿后（兜底卡，视觉弱化） */
export const IMPULSE_CARDS: readonly ImpulseCard[] = [
  {
    id: 'setting_heavy',
    label: '搭一个世界',
    tagline: '我想亲手搭起一个世界的骨架，从地理到制度都清清楚楚',
  },
  {
    id: 'character_driven',
    label: '为角色造世界',
    tagline: '我心里有个角色活了起来，想给他一个能活动的舞台',
  },
  {
    id: 'plot',
    label: '讲个故事',
    tagline: '我想看故事开场，一个必须立刻做出的抉择摆在眼前',
  },
  {
    id: 'philosophy',
    label: '问个大问题',
    tagline: '我想借一个世界追问：什么算真实，什么算自由',
  },
  {
    id: 'exploration',
    label: '试试规则',
    tagline: '我想摆弄一堆规则和机制，看看推演下去会长成什么',
  },
  {
    id: 'romance',
    label: '写段感情',
    tagline: '我想写一段感情故事，让它在某个世界里慢慢发酵',
  },
  {
    id: 'nostalgia',
    label: '回到原作',
    tagline: '我想回到那个熟悉的故事里，把没写完的部分接着写',
  },
  {
    id: 'healing',
    label: '轻松待会儿',
    tagline: '我想轻松一会儿，随便写写，不想答的都可以跳过',
  },
  {
    id: 'unsure',
    label: '都不像？',
    tagline: '说不清？先聊聊你世界里发生的事也行',
  },
];

/** 卡片屏顶部引导语（E1 诚实框架，R1 缓解：明示"帮我们了解你"，不伪装个性化承诺） */
export const IMPULSE_SCREEN_INTRO =
  '先告诉我，你为什么想创造一个世界？你的答案会帮我们把访谈调成适合你的样子。';
