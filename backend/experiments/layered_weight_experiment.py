"""分层约束权重感知实验。

核心假设：
    同一个种子概念，在不同创作层级下（按不同权重表），
    LLM 能否生成侧重点截然不同的内容？

实验设计：
    选 3 个种子，每个种子在 3 个不同创作层级下生成。
    对比生成结果的字段密度、内容侧重、风格差异。

    种子1: "古代水晶祭坛"
        - World 层  (NAR=35%, LAW=30%, RED=20%)  → 侧重风格和法则
        - Asset 层  (LAW=30%, ACT=30%, NAR=10%)  → 侧重物理属性和使用判定
        - Scene 层  (WST=40%, LAW=25%, NAR=10%)  → 侧重环境效果

    种子2: "星辉教派"
        - Region 层 (SOC=45%, NAR=20%, LAW=10%)  → 侧重社会关系和文化
        - World 层  (NAR=35%, LAW=30%, RED=20%)  → 侧重全局风格
        - NPC 层    (SOC=30%, ACT=25%, NAR=20%)  → 侧重社交和行为

    种子3: "魔法消耗理智值"
        - World 层  (LAW=30%, NAR=35%, RED=20%)  → 侧重世界法则定义
        - Asset 层  (LAW=30%, ACT=30%)           → 侧重物品如何执行
        - NPC 层    (ACT=25%, SOC=30%, NAR=20%)  → 侧重角色承受后果

判定标准：
    - 不同层级生成的 JSON 字段是否体现了不同侧重？
    - 高权重维度的描述是否更丰富？
    - 低权重维度是否被合理压缩？
    - 内容是否自洽？

Usage:
    cd H:\\UGC\\backend
    .venv\\Scripts\\python -m experiments.layered_weight_experiment
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

_ENV_FILE = _BACKEND_DIR / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            _key = _key.strip()
            _val = _val.split("#")[0].strip()
            if _key and _key not in os.environ:
                os.environ[_key] = _val

from app.ai.config import load_provider_config
from app.ai.provider import LLMProvider, create_provider

# ---------------------------------------------------------------------------
# 6 类约束维度定义
# ---------------------------------------------------------------------------

DIMENSION_INFO: dict[str, dict[str, str]] = {
    "RED": {
        "name": "内容红线",
        "desc": "这个对象不能包含什么（禁止清单）",
        "data_essence": "禁止的内容条目",
    },
    "LAW": {
        "name": "物理法则",
        "desc": "这个对象服从什么世界规则（重力/魔法体系/科技水平）",
        "data_essence": "规则函数",
    },
    "ACT": {
        "name": "行为规则",
        "desc": "作用于这个对象的行为怎么判定（技能检定/社交反馈/伤害计算）",
        "data_essence": "判定逻辑",
    },
    "NAR": {
        "name": "叙事约束",
        "desc": "描述这个对象时遵循什么风格（文风/词汇/氛围/基调）",
        "data_essence": "风格指令文本",
    },
    "WST": {
        "name": "世界状态",
        "desc": "这个对象携带什么动态状态效果（天气/环境修正/buff/debuff）",
        "data_essence": "修正值/状态效果",
    },
    "SOC": {
        "name": "社交生态",
        "desc": "这个对象和谁有关系、什么关系（阵营/声望/亲缘/敌对）",
        "data_essence": "关系边",
    },
}

# ---------------------------------------------------------------------------
# 权重表
# ---------------------------------------------------------------------------

WEIGHT_MATRIX: dict[str, dict[str, int]] = {
    "world":    {"RED": 20, "LAW": 30, "ACT": 5,  "NAR": 35, "WST": 5,  "SOC": 5},
    "region":   {"RED": 10, "LAW": 10, "ACT": 10, "NAR": 20, "WST": 5,  "SOC": 45},
    "scene":    {"RED": 10, "LAW": 25, "ACT": 5,  "NAR": 10, "WST": 40, "SOC": 10},
    "campaign": {"RED": 10, "LAW": 5,  "ACT": 10, "NAR": 40, "WST": 5,  "SOC": 30},
    "npc":      {"RED": 5,  "LAW": 10, "ACT": 25, "NAR": 20, "WST": 10, "SOC": 30},
    "asset":    {"RED": 10, "LAW": 30, "ACT": 30, "NAR": 10, "WST": 10, "SOC": 10},
}

LAYER_NAMES: dict[str, str] = {
    "world": "世界观",
    "region": "区域文化",
    "scene": "场景/地点",
    "campaign": "战役/剧情",
    "npc": "NPC",
    "asset": "资产/物品",
}

# ---------------------------------------------------------------------------
# 实验用例设计
# ---------------------------------------------------------------------------

TEST_CASES: list[dict[str, Any]] = [
    # 种子1: 同一个物品在不同层级
    {
        "seed_id": "seed_crystal_altar",
        "seed_input": "古代水晶祭坛",
        "seed_description": "由整块水晶雕琢而成的祭坛，表面刻有星辰图案，散发着微弱的蓝色光芒",
        "runs": [
            {"layer": "world", "intent": "在世界观层定义这个祭坛代表什么世界法则和叙事风格"},
            {"layer": "asset", "intent": "在资产层定义这个祭坛的物理属性和使用判定"},
            {"layer": "scene", "intent": "在场景层定义这个祭坛所在地点的环境效果"},
        ],
    },
    # 种子2: 同一个文化概念在不同层级
    {
        "seed_id": "seed_star_sect",
        "seed_input": "星辉教派",
        "seed_description": "崇拜星辰力量的宗教组织，认为星光是宇宙真理的具象",
        "runs": [
            {"layer": "region", "intent": "在区域文化层定义这个教派的社会关系和制度"},
            {"layer": "world", "intent": "在世界观层定义这个教派代表的全球叙事风格"},
            {"layer": "npc", "intent": "在NPC层定义一个星辉教派的祭司角色"},
        ],
    },
    # 种子3: 同一条法则在不同层级
    {
        "seed_id": "seed_magic_sanity",
        "seed_input": "魔法消耗理智值",
        "seed_description": "每次施放法术，施法者的理智值会下降，下降幅度与法术威力成正比",
        "runs": [
            {"layer": "world", "intent": "在世界观层定义这条法则在世界中的地位和叙事影响"},
            {"layer": "asset", "intent": "在资产层定义一件与这条法则相关的法器/物品"},
            {"layer": "npc", "intent": "在NPC层定义一个受这条法则影响的角色"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Prompt 构建
# ---------------------------------------------------------------------------

def build_system_prompt(layer: str, weights: dict[str, int], intent: str) -> str:
    """构建 system prompt，包含权重表和创作意图。"""

    layer_name = LAYER_NAMES[layer]

    # 按权重降序排列维度
    sorted_dims = sorted(weights.items(), key=lambda x: x[1], reverse=True)

    # 构建维度描述（按权重排序，高权重在前）
    dim_lines = []
    for dim_code, weight in sorted_dims:
        info = DIMENSION_INFO[dim_code]
        bar = "█" * (weight // 5) + "░" * (20 - weight // 5)
        emphasis = ""
        if weight >= 25:
            emphasis = " ★主要约束"
        elif weight <= 5:
            emphasis = " （几乎不需要，简单提一句即可）"
        dim_lines.append(
            f"  {dim_code} ({info['name']}) [{bar} {weight}%]{emphasis}\n"
            f"    → {info['desc']}"
        )

    dims_text = "\n".join(dim_lines)

    return f"""\
你是一个分层创作系统中的世界构建引擎。

## 当前任务

DM 正在 **{layer_name}** 层创作。
创作意图: {intent}

## 这个层级的约束权重表

每一类约束在 {layer_name} 层的重要性不同。权重越高，你需要在生成内容中\
给予越多的篇幅和细节。标★的是主要约束，必须详细展开。低权重的维度\
可以简单提及甚至省略。

{dims_text}

## 生成原则

1. **按权重分配注意力** — 高权重维度的内容必须丰富、具体、有细节；低权重维度简略即可
2. **侧重差异要明显** — 如果换一个层级生成同样的种子，结果应该截然不同
3. **内容自洽** — 所有生成的维度内容必须围绕种子概念，逻辑一致
4. **具体可玩** — 不要泛泛而谈，给出具体的名称、数值、机制描述

## 输出格式

输出严格的 JSON，包含所有6个约束维度的内容。高权重维度字段内容丰富\
（多个子字段、列表、详细描述），低权重维度可以只有一句话或空列表。

```json
{{
  "RED": {{
    "forbidden": ["禁止的内容1", "禁止的内容2"],
    "note": "说明（如果没有禁忌可以留空列表）"
  }},
  "LAW": {{
    "rules": ["规则描述1", "规则描述2"],
    "mechanism": "核心运行机制描述"
  }},
  "ACT": {{
    "actions": [
      {{"trigger": "触发条件", "check": "判定方式", "success": "成功后果", "failure": "失败后果"}}
    ]
  }},
  "NAR": {{
    "style": "文风/氛围描述",
    "keywords": ["关键词1", "关键词2"],
    "tone": "基调（如：压抑/壮丽/诡异）"
  }},
  "WST": {{
    "effects": [
      {{"name": "效果名", "type": "buff/debuff/环境", "magnitude": "数值或描述"}}
    ]
  }},
  "SOC": {{
    "relations": [
      {{"target": "关系对象", "type": "关系类型", "value": "关系值/态度"}}
    ]
  }}
}}
```

只输出 JSON，不要输出任何其他内容。
"""


def build_user_prompt(seed_input: str, seed_description: str) -> str:
    """构建 user prompt。"""
    return f"""\
## 种子概念

**名称**: {seed_input}
**描述**: {seed_description}

请根据上方权重表，在当前创作层级下生成这个种子的完整约束内容。
记住：高权重维度要详细，低权重维度要简略。
"""


# ---------------------------------------------------------------------------
# 实验执行
# ---------------------------------------------------------------------------

async def run_single(
    provider: LLMProvider,
    seed: dict[str, Any],
    run_config: dict[str, Any],
) -> dict[str, Any]:
    """执行单次生成。"""

    layer = run_config["layer"]
    intent = run_config["intent"]
    weights = WEIGHT_MATRIX[layer]

    system_prompt = build_system_prompt(layer, weights, intent)
    user_prompt = build_user_prompt(
        seed["seed_input"],
        seed["seed_description"],
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    start = time.time()
    error = None
    result = None

    try:
        result = await provider.chat_json(messages)
    except Exception as e:
        error = str(e)

    elapsed = time.time() - start

    return {
        "seed_id": seed["seed_id"],
        "seed_input": seed["seed_input"],
        "layer": layer,
        "layer_name": LAYER_NAMES[layer],
        "intent": intent,
        "weights": weights,
        "result": result,
        "elapsed_seconds": round(elapsed, 1),
        "error": error,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


async def run_experiment() -> dict[str, Any]:
    """运行完整实验。"""

    config = load_provider_config()
    provider = create_provider(config)

    print(f"[实验] Provider: {config.provider_type} / {config.model}")
    print(f"[实验] 种子数: {len(TEST_CASES)}, 每种子 {len(TEST_CASES[0]['runs'])} 个层级")
    print(f"[实验] 总调用数: {sum(len(s['runs']) for s in TEST_CASES)}")
    print()

    all_results = []

    for seed in TEST_CASES:
        print(f"\n{'='*60}")
        print(f"种子: {seed['seed_input']}")
        print(f"{'='*60}")

        for run_config in seed["runs"]:
            layer = run_config["layer"]
            weights = WEIGHT_MATRIX[layer]
            top_dims = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
            top_str = ", ".join(f"{d}={w}%" for d, w in top_dims)

            print(f"\n  → [{LAYER_NAMES[layer]}] 主约束: {top_str}")
            print(f"    意图: {run_config['intent']}")

            data = await run_single(provider, seed, run_config)
            all_results.append(data)

            if data["error"]:
                print(f"    ❌ 错误: {data['error'][:80]}")
            else:
                # 简要打印每个维度的内容量
                result = data["result"] or {}
                print(f"    ✅ {data['elapsed_seconds']}s")
                for dim_code in ["RED", "LAW", "ACT", "NAR", "WST", "SOC"]:
                    w = weights[dim_code]
                    content = result.get(dim_code, {})
                    # 粗略衡量内容量
                    content_str = json.dumps(content, ensure_ascii=False)
                    length = len(content_str)
                    marker = "★" if w >= 25 else ("·" if w <= 5 else " ")
                    print(f"      {marker} {dim_code:4s} (权重{w:2d}%): {length:4d}字 — {content_str[:60]}...")

            # 避免 rate limit
            await asyncio.sleep(0.5)

    return {
        "experiment": "layered_weight_awareness",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": config.provider_type,
        "model": config.model,
        "total_calls": len(all_results),
        "results": all_results,
    }


# ---------------------------------------------------------------------------
# 分析报告
# ---------------------------------------------------------------------------

def generate_report(experiment_data: dict[str, Any]) -> str:
    """生成人类可读的分析报告。"""

    results = experiment_data["results"]

    lines = [
        "# 分层约束权重感知实验报告",
        "",
        f"> Provider: {experiment_data['provider']} / {experiment_data['model']}",
        f"> 时间: {experiment_data['timestamp']}",
        f"> 总调用: {experiment_data['total_calls']}",
        "",
        "---",
        "",
    ]

    # 按种子分组
    seeds: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        sid = r["seed_id"]
        seeds.setdefault(sid, []).append(r)

    for sid, seed_results in seeds.items():
        seed_input = seed_results[0]["seed_input"]
        lines.append(f"## 种子: {seed_input}")
        lines.append("")

        for r in seed_results:
            if r["error"]:
                lines.append(f"### {r['layer_name']} 层 — ❌ 失败: {r['error'][:50]}")
                lines.append("")
                continue

            result = r["result"] or {}
            weights = r["weights"]

            lines.append(f"### {r['layer_name']} 层 ({r['elapsed_seconds']}s)")
            lines.append(f"意图: {r['intent']}")
            lines.append("")

            # 对比表：每个维度的权重 vs 内容量
            lines.append("| 维度 | 权重 | 内容量(字) | 主要内容摘要 |")
            lines.append("|------|------|-----------|-------------|")

            for dim_code in ["RED", "LAW", "ACT", "NAR", "WST", "SOC"]:
                w = weights[dim_code]
                content = result.get(dim_code)
                if content is None:
                    content_str = ""
                    summary = "(未生成)"
                else:
                    content_str = json.dumps(content, ensure_ascii=False)
                    # 提取摘要
                    if isinstance(content, dict):
                        # 取第一个非空值的前30字
                        for v in content.values():
                            if isinstance(v, str) and v:
                                summary = v[:30]
                                break
                            elif isinstance(v, list) and v:
                                summary = str(v[0])[:30]
                                break
                        else:
                            summary = "(空)"
                    else:
                        summary = str(content)[:30]

                marker = "★" if w >= 25 else ""
                lines.append(f"| {dim_code} {marker} | {w}% | {len(content_str)} | {summary} |")

            lines.append("")

            # 详细内容
            lines.append("<details><summary>完整 JSON</summary>")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(result, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 分析结论
    lines.append("## 分析要点")
    lines.append("")
    lines.append("### 1. 高权重维度是否内容更丰富？")
    lines.append("")

    for sid, seed_results in seeds.items():
        seed_input = seed_results[0]["seed_input"]
        lines.append(f"**{seed_input}**:")
        lines.append("")

        for r in seed_results:
            if r["error"]:
                continue
            result = r["result"] or {}
            weights = r["weights"]

            # 计算高权重(>=25%)和低权重(<=5%)的平均内容量
            high_lens = []
            low_lens = []
            for dim_code in ["RED", "LAW", "ACT", "NAR", "WST", "SOC"]:
                w = weights[dim_code]
                content = result.get(dim_code)
                content_len = len(json.dumps(content, ensure_ascii=False)) if content else 0
                if w >= 25:
                    high_lens.append(content_len)
                elif w <= 5:
                    low_lens.append(content_len)

            high_avg = sum(high_lens) / len(high_lens) if high_lens else 0
            low_avg = sum(low_lens) / len(low_lens) if low_lens else 0
            ratio = high_avg / low_avg if low_avg > 0 else float('inf')

            lines.append(
                f"  - {r['layer_name']:6s}: 高权重平均 {high_avg:.0f}字, "
                f"低权重平均 {low_avg:.0f}字, "
                f"比值 {ratio:.1f}x"
            )
        lines.append("")

    lines.append("### 2. 同一种子在不同层级是否侧重点不同？")
    lines.append("")
    lines.append("对比同一种子在各层级生成的内容，观察：")
    lines.append("- 高权重维度是否随层级变化而切换？")
    lines.append("- 内容主题是否截然不同？")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

async def main() -> None:
    """主入口。"""

    output_dir = _BACKEND_DIR / "experiments" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 运行实验
    experiment_data = await run_experiment()

    # 保存 JSON
    json_path = output_dir / f"layered_weight_{timestamp}.json"
    json_path.write_text(
        json.dumps(experiment_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[保存] {json_path}")

    # 生成报告
    report = generate_report(experiment_data)
    md_path = output_dir / f"layered_weight_{timestamp}.md"
    md_path.write_text(report, encoding="utf-8")
    print(f"[保存] {md_path}")

    # 打印摘要
    print(f"\n{'='*60}")
    print("实验完成！查看报告文件分析结果。")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
