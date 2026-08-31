"""视觉设计背景图预生成管线.

从世界观视觉设计模块生成背景图：
1. GLM-4.7 文本模型根据视觉设计字段生成生图提示词
2. 万相2.7-image-pro 生 3 张备选图
3. GLM-4.5V 视觉模型给每张图评分

用于 A1 流程的预生成（视觉设计模块填满时后台触发），
也供 experiments/visual_design_bg_pipeline.py PoC 脚本复用.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.ai.config import ProviderConfig
from app.ai.image_generator import ImageGenerator
from app.ai.provider import LLMProvider, create_provider

# -- 常量 --------------------------------------------------------------------

GLM_VISION_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_VISION_MODEL = os.environ.get("GLM_VISION_MODEL", "glm-4.5v")
GLM_TEXT_MODEL = os.environ.get("GLM_MODEL", "glm-4.7")
GLM_BASE_URL = os.environ.get(
    "GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
)

# 评分间延迟（秒），避免 GLM RPM 限制（约 1-2 RPM）
JUDGE_DELAY_SECONDS = 30


# -- GLM-4.7 文本：生成提示词 ------------------------------------------------


def _build_glm_text_provider() -> LLMProvider:
    """构造 GLM 文本模型 provider（不依赖 ACTIVE_PROVIDER，直接读 GLM_* 环境变量）."""
    api_key = os.environ.get("GLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GLM_API_KEY environment variable is not set")
    config = ProviderConfig(
        provider_type="glm",
        base_url=GLM_BASE_URL,
        api_key=api_key,
        model=GLM_TEXT_MODEL,
        temperature=0.7,
        max_tokens=2000,
    )
    return create_provider(config)


async def generate_bg_prompt(visual_design: dict[str, str]) -> str:
    """用 GLM-4.7 文本模型根据视觉设计生成一段生图提示词.

    输入视觉设计字段（keywords/architecture/material 等），
    输出 100-200 字描述世界风貌的提示词，用于万相2.7 生图.
    """
    provider = _build_glm_text_provider()
    fields_desc = "\n".join(f"- {k}：{v}" for k, v in visual_design.items())
    system_msg = (
        "你是视觉概念设计师。根据给定的世界观视觉设计字段，"
        "生成一段 100-200 字的生图提示词，展示世界风貌或玩家角色身份风采。"
        "提示词应包含：主体描述、建筑风格、材质质感、色调氛围、构图视角。"
        "直接输出提示词文本，不加前缀说明，不加引号。"
    )
    user_msg = f"视觉设计字段：\n{fields_desc}\n\n请生成生图提示词。"
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]
    return await provider.chat(messages)


# -- GLM-4.5V 视觉：图片评分 -------------------------------------------


async def glm_vision_judge(
    image_path: str,
    prompt: str,
    *,
    model: str = GLM_VISION_MODEL,
) -> dict[str, Any]:
    """用 GLM 视觉模型给图片打分，评价与提示词的匹配度.

    Args:
        image_path: 本地图片路径.
        prompt: 原始生图提示词（用于匹配度评价）.
        model: GLM 视觉模型，默认 glm-4.5v.

    Returns:
        {"score": int(0-100), "comment": str, "reasoning": str}
    """
    api_key = os.environ.get("GLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GLM_API_KEY environment variable is not set")

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    ext = Path(image_path).suffix.lower().lstrip(".")
    mime = "image/png" if ext in ("png", "") else f"image/{ext}"

    system_msg = (
        "你是视觉评审专家。给定一张图片和一段生图提示词，请评估图片与提示词的匹配度。"
        '输出 JSON 格式：{"score": 0-100整数, "comment": 简短评语, '
        '"reasoning": 评分理由}。'
        "score=100 表示完全匹配，0 表示完全不相关。"
    )
    user_text = f"生图提示词：\n{prompt}\n\n请评估这张图片与提示词的匹配度。"

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
    }

    for attempt in range(3):  # 1 次初始 + 2 次重试
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                GLM_VISION_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        if resp.status_code != 429:
            break
        wait = 5 * (2 ** attempt)
        print(f"  [429] 等待 {wait}s 后重试（attempt {attempt + 1}/3）...")
        await asyncio.sleep(wait)

    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]
    # GLM 可能返回 ```json...``` 包裹的 JSON 或纯文本
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        score_match = re.search(r"\b(\d{1,3})\b", stripped)
        score = int(score_match.group(1)) if score_match else 50
        if score > 100:
            score = 50
        return {
            "score": score,
            "comment": stripped[:200],
            "reasoning": "raw text response (JSON parse failed)",
        }


# -- 主流程 ------------------------------------------------------------------


async def run_visual_bg_pipeline(
    visual_design: dict[str, str],
    output_dir: Path,
    *,
    num_candidates: int = 3,
    size: str = "2K",
) -> dict[str, Any]:
    """完整预生成流程：GLM生提示词→万相生N图→GLM评分→输出.

    Args:
        visual_design: 视觉设计字段 dict（如 {"keywords": "...", ...}）.
        output_dir: 输出目录（图片 + report.json 存这里）.
        num_candidates: 备选图数量，默认 3.
        size: 图片尺寸，默认 "2K".

    Returns:
        {"prompt": str, "images": [...], "best_candidate": str|None,
         "cost_estimate": str, "timestamp": str}
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. GLM-4.7 生提示词
    prompt = await generate_bg_prompt(visual_design)
    if not prompt or not prompt.strip():
        raise RuntimeError("GLM-4.7 返回空提示词，无法生图")
    print(f"  [visual_bg] GLM-{GLM_TEXT_MODEL} 生成提示词（{len(prompt)}字）")

    # 2. 万相2.7 生 N 张备选图
    gen = ImageGenerator()
    images = await gen.generate(
        prompt=prompt,
        size=size,
        num_candidates=num_candidates,
        asset_id="visual_bg",
    )
    await gen.close()
    if not images:
        raise RuntimeError("万相2.7 未生成任何图片")
    print(f"  [visual_bg] 万相2.7 生成 {len(images)} 张备选图")

    # 3. GLM-4.5V 评分每张图（30s 间隔避免 RPM 限制）
    await asyncio.sleep(JUDGE_DELAY_SECONDS)
    scored: list[dict[str, Any]] = []
    for i, img in enumerate(images):
        if not img.file_path:
            print(f"  [visual_bg] 图 {i + 1} 无 file_path，跳过评分")
            continue
        dest = output_dir / f"candidate_{i + 1}.png"
        shutil.copy2(img.file_path, dest)
        if i > 0:
            await asyncio.sleep(JUDGE_DELAY_SECONDS)
        try:
            judge = await glm_vision_judge(str(dest), prompt)
        except Exception as exc:
            print(f"  [visual_bg] 图 {i + 1} 评分失败: {exc}")
            judge = {"score": 0, "comment": f"评分失败: {exc}", "reasoning": ""}
        scored.append(
            {
                "path": str(dest),
                "filename": dest.name,
                "url": f"/visual-bg/{dest.name}",
                "score": judge.get("score", 0),
                "comment": judge.get("comment", ""),
                "reasoning": judge.get("reasoning", ""),
                "closest": False,
            }
        )
        print(
            f"  [visual_bg] 图 {i + 1}: score={judge.get('score')} - "
            f"{str(judge.get('comment', ''))[:60]}"
        )

    # 4. 标注最高分为 closest
    best_filename: str | None = None
    if scored:
        best_idx = max(range(len(scored)), key=lambda x: scored[x]["score"])
        scored[best_idx]["closest"] = True
        best_filename = scored[best_idx]["filename"]

    report = {
        "prompt": prompt,
        "images": scored,
        "best_candidate": best_filename,
        "cost_estimate": (
            f"≈ {0.5 * len(images):.2f} 元"
            f"（万相 {len(images)} 张 × 0.5元，GLM 免费）"
        ),
        "timestamp": datetime.now().isoformat(),
    }

    report_path = output_dir / "report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  [visual_bg] 报告已输出：{report_path}")

    return report
