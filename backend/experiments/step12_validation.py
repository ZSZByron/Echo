"""3×3 验证实验 — 先跑通再写标准

核心目标：
    验证 LLM 在不同权重约束下能否生成差异化内容。
    使用 3 个种子 × 3 个层级 = 9 次调用，验证 5 项判定标准。

实验设计：
    种子1「古代水晶祭坛」→ world / asset / scene 层
    种子2「星辉教派」→ region / npc / world 层
    种子3「魔法消耗理智值」→ world / asset / npc 层

判定标准：
    1. 权重表完整性: 6层×6维, 每行和=100, 全部整数, 无负值
    2. prompt 组装正确性: 含全部6维名称 + 条形图字符(█░) + 高权重★标记
    3. LLM 返回6维JSON: 全部6维键存在 (RED/LAW/ACT/NAR/WST/SOC)
    4. 密度差异验证: 高权重(≥25%)平均内容量 vs 低权重(≤5%)平均内容量, 比值 ≥2.0x
    5. 层级侧重验证: 同一种子在不同层级的高权重维度不同

Usage:
    cd H:\\UGC\\backend
    .venv\\Scripts\\python -m experiments.step12_validation
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
# 导入现有实验的配置和函数
# ---------------------------------------------------------------------------
from experiments.layered_weight_experiment import (
    WEIGHT_MATRIX,
    DIMENSION_INFO,
    LAYER_NAMES,
    build_system_prompt,
    build_user_prompt,
)

# ---------------------------------------------------------------------------
# 3×3 验证实验用例
# ---------------------------------------------------------------------------

VALIDATION_TEST_CASES: list[dict[str, Any]] = [
    # 种子1: 古代水晶祭坛 → world / asset / scene
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
    # 种子2: 星辉教派 → region / npc / world
    {
        "seed_id": "seed_star_sect",
        "seed_input": "星辉教派",
        "seed_description": "崇拜星辰力量的宗教组织，认为星光是宇宙真理的具象",
        "runs": [
            {"layer": "region", "intent": "在区域文化层定义这个教派的社会关系和制度"},
            {"layer": "npc", "intent": "在NPC层定义一个星辉教派的祭司角色"},
            {"layer": "world", "intent": "在世界观层定义这个教派代表的全球叙事风格"},
        ],
    },
    # 种子3: 魔法消耗理智值 → world / asset / npc
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
# 验证函数
# ---------------------------------------------------------------------------

def validate_weight_matrix() -> dict[str, Any]:
    """验证标准1: 权重表完整性"""
    errors = []
    
    # 检查6层
    if len(WEIGHT_MATRIX) != 6:
        errors.append(f"权重表层级数错误: 期望6层, 实际{len(WEIGHT_MATRIX)}层")
    
    for layer, weights in WEIGHT_MATRIX.items():
        # 检查6维
        if len(weights) != 6:
            errors.append(f"{layer}层维度数错误: 期望6维, 实际{len(weights)}维")
        
        # 检查每行和=100
        total = sum(weights.values())
        if total != 100:
            errors.append(f"{layer}层权重和错误: 期望100, 实际{total}")
        
        # 检查全部整数
        for dim, weight in weights.items():
            if not isinstance(weight, int):
                errors.append(f"{layer}.{dim}权重非整数: {weight}")
            
            # 检查无负值
            if weight < 0:
                errors.append(f"{layer}.{dim}权重为负数: {weight}")
    
    return {
        "criterion": "权重表完整性",
        "passed": len(errors) == 0,
        "errors": errors,
    }

def validate_prompt_structure(system_prompt: str, weights: dict[str, int]) -> dict[str, Any]:
    """验证标准2: prompt 组装正确性"""
    errors = []
    
    # 检查含全部6维名称
    for dim_code in ["RED", "LAW", "ACT", "NAR", "WST", "SOC"]:
        dim_name = DIMENSION_INFO[dim_code]["name"]
        if dim_name not in system_prompt:
            errors.append(f"缺少维度名称: {dim_name}")
    
    # 检查条形图字符
    if "█" not in system_prompt or "░" not in system_prompt:
        errors.append("缺少条形图字符 (█░)")
    
    # 检查高权重★标记
    has_star = False
    for dim, weight in weights.items():
        if weight >= 25:
            if "★" in system_prompt:
                has_star = True
                break
    if not has_star:
        errors.append("缺少高权重★标记")
    
    return {
        "criterion": "prompt组装正确性",
        "passed": len(errors) == 0,
        "errors": errors,
    }

def validate_llm_response(result: dict[str, Any]) -> dict[str, Any]:
    """验证标准3: LLM 返回6维JSON"""
    errors = []
    
    if not result:
        errors.append("LLM返回为空")
        return {
            "criterion": "LLM返回6维JSON",
            "passed": False,
            "errors": errors,
        }
    
    # 检查全部6维键存在
    required_dims = ["RED", "LAW", "ACT", "NAR", "WST", "SOC"]
    for dim in required_dims:
        if dim not in result:
            errors.append(f"缺少维度: {dim}")
    
    return {
        "criterion": "LLM返回6维JSON",
        "passed": len(errors) == 0,
        "errors": errors,
    }

def calculate_density_ratio(result: dict[str, Any], weights: dict[str, int]) -> dict[str, Any]:
    """验证标准4: 密度差异验证"""
    if not result:
        return {
            "criterion": "密度差异验证",
            "passed": False,
            "ratio": 0.0,
            "error": "LLM返回为空",
        }
    
    high_weight_dims = []
    low_weight_dims = []
    
    for dim, weight in weights.items():
        if weight >= 25:
            high_weight_dims.append(dim)
        elif weight <= 5:
            low_weight_dims.append(dim)
    
    if not high_weight_dims or not low_weight_dims:
        return {
            "criterion": "密度差异验证",
            "passed": True,  # 如果没有高低权重维度，此标准不适用
            "ratio": None,
            "note": "此权重表无高/低权重维度对比",
        }
    
    # 计算内容量（用JSON字符串长度作为近似）
    high_weights_total = 0
    for dim in high_weight_dims:
        content = result.get(dim, {})
        content_str = json.dumps(content, ensure_ascii=False)
        high_weights_total += len(content_str)
    
    low_weights_total = 0
    for dim in low_weight_dims:
        content = result.get(dim, {})
        content_str = json.dumps(content, ensure_ascii=False)
        low_weights_total += len(content_str)
    
    high_avg = high_weights_total / len(high_weight_dims) if high_weight_dims else 0
    low_avg = low_weights_total / len(low_weight_dims) if low_weight_dims else 0
    
    ratio = high_avg / low_avg if low_avg > 0 else 0
    
    return {
        "criterion": "密度差异验证",
        "passed": ratio >= 2.0,
        "ratio": round(ratio, 2),
        "high_avg": round(high_avg, 0),
        "low_avg": round(low_avg, 0),
        "high_dims": high_weight_dims,
        "low_dims": low_weight_dims,
    }

def validate_layer_focus(all_results: list[dict[str, Any]]) -> dict[str, Any]:
    """验证标准5: 层级侧重验证"""
    errors = []
    
    # 按种子分组
    seed_results: dict[str, list[dict]] = {}
    for result in all_results:
        seed_id = result["seed_id"]
        if seed_id not in seed_results:
            seed_results[seed_id] = []
        seed_results[seed_id].append(result)
    
    # 对每个种子，检查不同层级的高权重维度是否不同
    for seed_id, results in seed_results.items():
        if len(results) < 2:
            continue  # 只有一个层级无法比较
        
        # 收集每个层级的最高权重维度
        high_weight_dims_per_layer = []
        for result in results:
            weights = result["weights"]
            high_dims = [dim for dim, w in weights.items() if w >= 25]
            high_weight_dims_per_layer.append(set(high_dims))
        
        # 检查至少有一对不同
        has_difference = False
        for i in range(len(high_weight_dims_per_layer)):
            for j in range(i + 1, len(high_weight_dims_per_layer)):
                if high_weight_dims_per_layer[i] != high_weight_dims_per_layer[j]:
                    has_difference = True
                    break
            if has_difference:
                break
        
        if not has_difference:
            errors.append(f"{seed_id}的所有层级高权重维度相同")
    
    return {
        "criterion": "层级侧重验证",
        "passed": len(errors) == 0,
        "errors": errors,
    }

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

async def run_validation() -> dict[str, Any]:
    """运行完整验证实验。"""
    
    config = load_provider_config()
    provider = create_provider(config)
    
    print(f"[验证实验] Provider: {config.provider_type} / {config.model}")
    print(f"[验证实验] 种子数: {len(VALIDATION_TEST_CASES)}, 每种子 {len(VALIDATION_TEST_CASES[0]['runs'])} 个层级")
    print(f"[验证实验] 总调用数: {sum(len(s['runs']) for s in VALIDATION_TEST_CASES)}")
    print()
    
    all_results = []
    validation_results = {
        "criteria_validations": [],
        "summary": {},
    }
    
    # 验证标准1: 权重表完整性
    print("[验证] 标准1: 权重表完整性...")
    weight_validation = validate_weight_matrix()
    validation_results["criteria_validations"].append(weight_validation)
    print(f"  {'[PASS] 通过' if weight_validation['passed'] else '[FAIL] 失败'}")
    if weight_validation["errors"]:
        for err in weight_validation["errors"]:
            print(f"    - {err}")
    
    for seed in VALIDATION_TEST_CASES:
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
                print(f"    [ERROR] 错误: {data['error'][:80]}")
            else:
                print(f"    [OK] {data['elapsed_seconds']}s")
                
                # 验证标准2: prompt组装正确性
                prompt_validation = validate_prompt_structure(data["system_prompt"], weights)
                print(f"    [标准2] {'[PASS]' if prompt_validation['passed'] else '[FAIL]'} prompt组装")
                
                # 验证标准3: LLM返回6维JSON
                response_validation = validate_llm_response(data["result"])
                print(f"    [标准3] {'[PASS]' if response_validation['passed'] else '[FAIL]'} 6维JSON")
                
                # 验证标准4: 密度差异验证
                density_validation = calculate_density_ratio(data["result"], weights)
                if density_validation["passed"]:
                    print(f"    [标准4] [PASS] 密度比 {density_validation['ratio']}x >= 2.0x")
                else:
                    print(f"    [标准4] [FAIL] 密度比 {density_validation.get('ratio', 0)}x < 2.0x")
                
                # 打印每个维度的内容量
                result = data["result"] or {}
                print(f"    内容量:")
                for dim_code in ["RED", "LAW", "ACT", "NAR", "WST", "SOC"]:
                    w = weights[dim_code]
                    content = result.get(dim_code, {})
                    content_str = json.dumps(content, ensure_ascii=False)
                    length = len(content_str)
                    marker = "★" if w >= 25 else ("·" if w <= 5 else " ")
                    print(f"      {dim_code} {marker} {w:>3}%: {length:>4} chars")
    
    # 验证标准5: 层级侧重验证
    print(f"\n[验证] 标准5: 层级侧重验证...")
    layer_validation = validate_layer_focus(all_results)
    validation_results["criteria_validations"].append(layer_validation)
    print(f"  {'[PASS] 通过' if layer_validation['passed'] else '[FAIL] 失败'}")
    if layer_validation["errors"]:
        for err in layer_validation["errors"]:
            print(f"    - {err}")
    
    # 汇总结果
    total_calls = len(all_results)
    successful_calls = sum(1 for r in all_results if not r["error"])
    
    validation_results["summary"] = {
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "success_rate": round(successful_calls / total_calls, 2) if total_calls > 0 else 0,
        "criteria_passed": sum(1 for v in validation_results["criteria_validations"] if v["passed"]),
        "criteria_total": len(validation_results["criteria_validations"]),
    }
    
    return {
        "validation_results": validation_results,
        "all_results": all_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

async def main() -> None:
    """主入口。"""
    
    output_dir = _BACKEND_DIR / "experiments" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 运行验证实验
    experiment_data = await run_validation()
    
    # 保存 JSON
    json_path = output_dir / f"step12_validation_{timestamp}.json"
    json_path.write_text(
        json.dumps(experiment_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[保存] {json_path}")
    
    # 打印摘要
    summary = experiment_data["validation_results"]["summary"]
    print(f"\n{'='*60}")
    print("验证实验完成！")
    print(f"{'='*60}")
    print(f"总调用数: {summary['total_calls']}")
    print(f"成功调用: {summary['successful_calls']}")
    print(f"成功率: {summary['success_rate']:.0%}")
    print(f"标准通过: {summary['criteria_passed']}/{summary['criteria_total']}")
    
    # 检查成功率
    if summary['successful_calls'] >= 7:
        print(f"\n[PASS] 验证成功: 成功调用 >= 7/9")
    else:
        print(f"\n[FAIL] 验证失败: 成功调用 < 7/9")
    
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
