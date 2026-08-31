# 视觉设计→LLM生提示词→万相生图→GLM-4V评分 PoC 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `backend/experiments/` 下实施一个 PoC 脚本，读取世界观 .txt 文件，识别"视觉设计"节，调用 GLM-4.7 生成大背景提示词，调用万相2.7-image-pro 生 3 张备选图，再用 GLM-4.6V-Flash 评分，输出图片 + JSON 报告。

**Architecture:** 单文件异步 Python 脚本。解析层用纯函数（TDD），LLM/生图/视觉调用复用现有 `ImageGenerator` 类 + 新增 httpx 直调 GLM 视觉 API（不改 provider.py）。串联在 `run_pipeline()` 主流程里。

**Tech Stack:** Python 3.11+ / asyncio / httpx / Pydantic v2 / pytest / 现有 `app.ai.image_generator.ImageGenerator` / 现有 `app.ai.provider.create_provider`

---

## 已锁定参数（用户确认）

| 项 | 值 |
|---|---|
| 范围 | A — 纯后端 PoC 脚本，不动 A1 主流程 |
| 输入文件格式 | .txt / .md，节标记 `✦`，字段 `field:value`，字段分隔 `；` |
| 生成提示词 LLM | GLM-4.7（文本，复用现有 `OpenAICompatibleProvider`） |
| 生图模型 | wan2.7-image-pro（0.5 元/张，复用现有 `ImageGenerator` wanxiang27 provider） |
| 备选图数量 | 3 张 |
| GLM 视觉评分模型 | glm-4.6v-flash（永久免费，httpx 直调 bigmodel.cn） |
| 评分形式 | 每张 0-100 分 + 文字评语 + 标注 closest |
| 图片尺寸 | 2K（2048*2048） |
| 输出目录 | `backend/experiments/results/visual_design_bg/` |
| 单次成本 | ≈ 1.5 元（万相3张图 1.5 + GLM 全免费） |

---

## 输入文件实际结构（明华修仙.txt）

文件格式特点：
- 节标记：`✦` 开头的行（如 `✦视觉设计`）
- 字段格式：`field:value`（冒号分隔，无空格）
- 字段分隔：`；`（中文分号）
- 值内可能含中文逗号 `，` 但不分割字段

"视觉设计"节实际子字段（用户文件真实结构）：
```
✦视觉设计
keywords:东方国风、少数民族风情、异域风情、奇幻种族美感；architecture:中式建筑，传统古典，未来主义；material:木质，石质，少数用金属
```

解析为：
```python
{
    "视觉设计": {
        "keywords": "东方国风、少数民族风情、异域风情、奇幻种族美感",
        "architecture": "中式建筑，传统古典，未来主义",
        "material": "木质，石质，少数用金属"
    }
}
```

---

## 完整流程

```
1. 读 明华修仙.txt
2. parse_worldview_text(content) → dict[节名, dict[字段名, 值]]
3. 提取 visual_design = result["视觉设计"]
4. generate_bg_prompt(visual_design) → str  [GLM-4.7 文本]
   - system: "你是视觉概念设计师，根据世界观视觉设计生成一段生图提示词..."
   - user: 视觉设计字段拼接
   - 输出: 一段 100-200 字的中文/英文生图提示词
5. ImageGenerator(provider=wanxiang27).generate(prompt, size="2K", num_candidates=3) → list[GeneratedImage]
   - 每张图已下载到本地 file_path
6. for img in images:
     glm_vision_judge(img.file_path, prompt) → {"score": int, "comment": str}
   - 用 GLM-4.6V-Flash 多模态调用
   - system: "你是视觉评审，给图片打分 0-100，评价与提示词的匹配度"
   - user: [image_url(base64 或 file://), text(prompt)]
7. 标注最高分为 closest
8. 输出:
   - 3 张图复制到 experiments/results/visual_design_bg/
   - JSON 报告 report.json（含 prompt, images[{path, score, comment, closest}], cost_estimate）
```

---

## Task 1: TDD 解析函数

**Files:**
- Create: `backend/experiments/visual_design_bg_pipeline.py`（解析函数部分）
- Test: `backend/tests/unit/experiments/test_visual_design_bg_pipeline.py`

**Step 1: 写失败测试**

```python
# backend/tests/unit/experiments/test_visual_design_bg_pipeline.py
import sys
from pathlib import Path

# 让测试能 import experiments 目录
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "experiments"))

from visual_design_bg_pipeline import parse_worldview_text


SAMPLE_TEXT = """✦IP定位
name:明华世界；concept:正本清源；world_type:东方仙侠

✦视觉设计
keywords:东方国风、少数民族风情；architecture:中式建筑，传统古典；material:木质，石质

✦玩法设计DNA
player_role:刚筑基入门的弟子"""


def test_parse_single_section_with_multiple_fields():
    result = parse_worldview_text(SAMPLE_TEXT)
    visual = result["视觉设计"]
    assert visual["keywords"] == "东方国风、少数民族风情"
    assert visual["architecture"] == "中式建筑，传统古典"
    assert visual["material"] == "木质，石质"


def test_parse_multiple_sections():
    result = parse_worldview_text(SAMPLE_TEXT)
    assert "IP定位" in result
    assert "视觉设计" in result
    assert "玩法设计DNA" in result


def test_parse_field_with_chinese_comma_in_value():
    """值内的中文逗号不应分割字段"""
    result = parse_worldview_text(SAMPLE_TEXT)
    assert result["视觉设计"]["architecture"] == "中式建筑，传统古典"


def test_parse_section_with_name_field():
    result = parse_worldview_text(SAMPLE_TEXT)
    assert result["IP定位"]["name"] == "明华世界"
    assert result["IP定位"]["concept"] == "正本清源"


def test_parse_empty_text_returns_empty_dict():
    assert parse_worldview_text("") == {}


def test_parse_no_section_marker_returns_empty():
    assert parse_worldview_text("just some text without markers") == {}


def test_parse_section_with_no_fields_returns_empty_dict():
    """节标记存在但无字段"""
    text = "✦空节\n"
    result = parse_worldview_text(text)
    assert result["空节"] == {}
```

**Step 2: 运行测试确认失败**

Run: `cd backend && .venv\Scripts\python -m pytest tests/unit/experiments/test_visual_design_bg_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'visual_design_bg_pipeline'`

**Step 3: 写最小实现**

```python
# backend/experiments/visual_design_bg_pipeline.py
"""视觉设计→LLM生提示词→万相生图→GLM-4V评分 PoC 管线.

实验脚本，非生产代码。读取世界观 .txt/.md 文件，识别"视觉设计"节，
调用 GLM-4.7 生成大背景提示词，万相2.7 生 3 张备选图，GLM-4.6V-Flash 评分。
"""

from __future__ import annotations


def parse_worldview_text(content: str) -> dict[str, dict[str, str]]:
    """解析 ✦ 节标记 + field:value + ；分隔的世界观文本.

    格式:
        ✦节名
        field1:value1；field2:value2；field3:value3

    值内的中文逗号"，"不分割字段，仅中文分号"；"分隔字段.

    Returns:
        dict[节名, dict[字段名, 值]]。无节标记返回 {}。
    """
    result: dict[str, dict[str, str]] = {}
    current_section: str | None = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("✦"):
            current_section = line[1:].strip()
            result[current_section] = {}
        elif current_section is not None:
            # 按 ；(中文分号) 分割字段
            fields = line.split("；")
            for field_def in fields:
                field_def = field_def.strip()
                if not field_def or ":" not in field_def:
                    continue
                # 只按第一个冒号分割（值内可能含冒号）
                key, _, value = field_def.partition(":")
                result[current_section][key.strip()] = value.strip()

    return result
```

**Step 4: 运行测试确认通过**

Run: `cd backend && .venv\Scripts\python -m pytest tests/unit/experiments/test_visual_design_bg_pipeline.py -v`
Expected: 7 passed

**Step 5: Commit**

```bash
git add backend/experiments/visual_design_bg_pipeline.py backend/tests/unit/experiments/test_visual_design_bg_pipeline.py
git commit -m "feat(experiments): add worldview text parser for visual design pipeline"
```

---

## Task 2: GLM-4.6V-Flash 视觉评分函数

**Files:**
- Modify: `backend/experiments/visual_design_bg_pipeline.py`（追加 `glm_vision_judge`）
- Test: 手动集成测试（外部 API，不写自动化单元测试）

**说明:** GLM-4.6V-Flash 是视觉模型，需多模态调用（content 数组含 image_url）。现有 `OpenAICompatibleProvider.chat` 类型注解是 `list[dict[str, str]]`（纯文本），不适合多模态。PoC 不改 provider.py，直接用 httpx 调 bigmodel.cn API。

**Step 1: 实施 `glm_vision_judge`**

```python
# 追加到 visual_design_bg_pipeline.py
import base64
import json
import os

import httpx


GLM_VISION_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


async def glm_vision_judge(
    image_path: str,
    prompt: str,
    *,
    model: str = "glm-4.6v-flash",
) -> dict:
    """用 GLM 视觉模型给图片打分，评价与提示词的匹配度.

    Args:
        image_path: 本地图片路径.
        prompt: 原始生图提示词（用于匹配度评价）.
        model: GLM 视觉模型，默认 glm-4.6v-flash（免费）.

    Returns:
        {"score": int(0-100), "comment": str, "reasoning": str}
    """
    api_key = os.environ.get("GLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GLM_API_KEY environment variable is not set")

    # 读图片转 base64
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    system_msg = (
        "你是视觉评审专家。给定一张图片和一段生图提示词，请评估图片与提示词的匹配度。"
        "输出 JSON 格式：{\"score\": 0-100整数, \"comment\": 简短评语, \"reasoning\": 评分理由}。"
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
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    {"type": "text", "text": user_text},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            GLM_VISION_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    # GLM 可能返回纯文本或 JSON，尝试解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 如果不是 JSON，提取 score
        import re
        score_match = re.search(r"(\d{1,3})", content)
        score = int(score_match.group(1)) if score_match else 50
        return {"score": score, "comment": content[:200], "reasoning": "raw text response"}
```

**Step 2: 手动集成测试**（不写自动化测试，外部 API）

```bash
# 准备一张测试图，手动调一次
cd backend
$env:GLM_API_KEY="<your-key>"
.venv\Scripts\python -c "
import asyncio
from experiments.visual_design_bg_pipeline import glm_vision_judge
# 用 experiments/results/ 下任意已有图测试
r = asyncio.run(glm_vision_judge('experiments/results/some_test.png', '东方仙侠建筑'))
print(r)
"
```

**Step 3: Commit**

```bash
git add backend/experiments/visual_design_bg_pipeline.py
git commit -m "feat(experiments): add GLM-4.6V-Flash vision judge function"
```

---

## Task 3: GLM-4.7 文本生成提示词函数

**Files:**
- Modify: `backend/experiments/visual_design_bg_pipeline.py`（追加 `generate_bg_prompt`）

**说明:** 复用现有 `OpenAICompatibleProvider` 调 glm-4.7。需要从 `app.ai.config` 读 ProviderConfig。

**Step 1: 实施 `generate_bg_prompt`**

```python
# 追加到 visual_design_bg_pipeline.py
from app.ai.config import ProviderConfig
from app.ai.provider import create_provider


async def generate_bg_prompt(visual_design: dict[str, str]) -> str:
    """用 GLM-4.7 文本模型根据视觉设计生成一段生图提示词.

    输入视觉设计字段（keywords/architecture/material 等），
    输出 100-200 字描述世界风貌的提示词，用于万相2.7 生图.
    """
    config = ProviderConfig.from_env("glm")
    provider = create_provider(config)

    fields_desc = "\n".join(
        f"- {k}：{v}" for k, v in visual_design.items()
    )
    system_msg = (
        "你是视觉概念设计师。根据给定的世界观视觉设计字段，"
        "生成一段 100-200 字的生图提示词，展示世界风貌或玩家角色身份风采。"
        "提示词应包含：主体描述、建筑风格、材质质感、色调氛围、构图视角。"
        "直接输出提示词文本，不加前缀说明。"
    )
    user_msg = f"视觉设计字段：\n{fields_desc}\n\n请生成生图提示词。"

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]
    return await provider.chat(messages, temperature=0.7, max_tokens=300)
```

**Step 2: 手动集成测试**

```bash
cd backend
.venv\Scripts\python -c "
import asyncio
from experiments.visual_design_bg_pipeline import generate_bg_prompt
r = asyncio.run(generate_bg_prompt({'keywords': '东方国风', 'architecture': '中式建筑', 'material': '木质'}))
print(r)
"
```

**Step 3: Commit**

```bash
git add backend/experiments/visual_design_bg_pipeline.py
git commit -m "feat(experiments): add GLM-4.7 bg prompt generation"
```

---

## Task 4: 主流程串联

**Files:**
- Modify: `backend/experiments/visual_design_bg_pipeline.py`（追加 `run_pipeline` + `__main__`）

**Step 1: 实施 `run_pipeline`**

```python
# 追加到 visual_design_bg_pipeline.py
import shutil
from datetime import datetime
from pathlib import Path

from app.ai.image_generator import ImageGenerator

RESULTS_DIR = Path(__file__).resolve().parent / "results" / "visual_design_bg"


async def run_pipeline(input_file: str, output_dir: Path | None = None) -> dict:
    """完整 PoC 流程：解析→GLM生提示词→万相生3图→GLM-4V评分→输出.

    Returns:
        {"prompt": str, "images": [{"path", "score", "comment", "closest"}],
         "cost_estimate": str, "timestamp": str}
    """
    out_dir = output_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 读文件 + 解析
    content = Path(input_file).read_text(encoding="utf-8")
    worldview = parse_worldview_text(content)
    visual_design = worldview.get("视觉设计")
    if not visual_design:
        raise ValueError("文件中未找到 ✦视觉设计 节")

    print(f"[1/5] 解析成功：视觉设计字段 = {list(visual_design.keys())}")

    # 2. GLM-4.7 生提示词
    prompt = await generate_bg_prompt(visual_design)
    print(f"[2/5] GLM-4.7 生成提示词（{len(prompt)}字）:\n{prompt[:100]}...")

    # 3. 万相2.7 生 3 张备选图
    gen = ImageGenerator()  # 读 .env IMAGE_PROVIDER=wanxiang27
    images = await gen.generate(
        prompt=prompt,
        size="2K",
        num_candidates=3,
        asset_id="visual_design_bg",
    )
    await gen.close()
    if not images:
        raise RuntimeError("万相2.7 未生成任何图片")
    print(f"[3/5] 万相2.7 生成 {len(images)} 张备选图")

    # 4. GLM-4.6V-Flash 评分每张图
    scored = []
    for i, img in enumerate(images):
        if not img.file_path:
            print(f"  [warn] 图 {i} 无 file_path，跳过评分")
            continue
        # 复制到输出目录
        dest = out_dir / f"candidate_{i+1}.png"
        shutil.copy2(img.file_path, dest)
        # GLM-4V 评分
        judge = await glm_vision_judge(str(dest), prompt)
        scored.append({
            "path": str(dest),
            "score": judge.get("score", 0),
            "comment": judge.get("comment", ""),
            "reasoning": judge.get("reasoning", ""),
            "closest": False,
        })
        print(f"  图 {i+1}: score={judge.get('score')} - {judge.get('comment', '')[:50]}")

    # 5. 标注最高分为 closest
    if scored:
        best = max(scored, key=lambda x: x["score"])
        best["closest"] = True

    report = {
        "prompt": prompt,
        "images": scored,
        "cost_estimate": f"≈ {0.5 * len(images):.2f} 元（万相 {len(images)} 张 × 0.5元，GLM 免费）",
        "timestamp": datetime.now().isoformat(),
    }

    # 输出 JSON 报告
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[4/5] JSON 报告已输出：{report_path}")
    print(f"[5/5] 最接近提示词的图：candidate_{scored.index(best)+1 if scored else '-'}.png")

    return report


if __name__ == "__main__":
    import asyncio
    import sys

    if len(sys.argv) < 2:
        print("用法: python -m experiments.visual_design_bg_pipeline <worldview.txt>")
        sys.exit(1)

    asyncio.run(run_pipeline(sys.argv[1]))
```

**Step 2: 确认所有 import 集中在文件顶部**（重构）

**Step 3: Commit**

```bash
git add backend/experiments/visual_design_bg_pipeline.py
git commit -m "feat(experiments): add full visual design bg pipeline main flow"
```

---

## Task 5: 启动后端实测

**Step 1: 确认 .env 配置**

```env
IMAGE_PROVIDER=wanxiang27
WANXIANG27_API_KEY=<DashScope key>
WANXIANG27_MODEL=wan2.7-image-pro
GLM_API_KEY=<BigModel key>
GLM_MODEL=glm-4.7
ACTIVE_PROVIDER=glm
```

**Step 2: 准备输入文件**

把"明华修仙.txt"放到 `backend/data/` 或 `backend/experiments/` 下。

**Step 3: 运行脚本**

```bash
cd backend
.venv\Scripts\python -m experiments.visual_design_bg_pipeline data/明华修仙.txt
```

**Step 4: 检查输出**

```bash
# 应有以下文件：
# backend/experiments/results/visual_design_bg/candidate_1.png
# backend/experiments/results/visual_design_bg/candidate_2.png
# backend/experiments/results/visual_design_bg/candidate_3.png
# backend/experiments/results/visual_design_bg/report.json
```

**Step 5: 验证 report.json 内容**

```json
{
  "prompt": "...",
  "images": [
    {"path": "...", "score": 87, "comment": "...", "closest": true},
    {"path": "...", "score": 72, "comment": "...", "closest": false},
    {"path": "...", "score": 65, "comment": "...", "closest": false}
  ],
  "cost_estimate": "≈ 1.50 元（万相 3 张 × 0.5元，GLM 免费）",
  "timestamp": "..."
}
```

---

## 成本预算

| 步骤 | 模型 | 用量 | 单价 | 小计 |
|---|---|---|---|---|
| GLM-4.7 生提示词 | glm-4.7 | ~3K tokens | 限时免费 | 0 元 |
| 万相2.7 生 3 张图 | wan2.7-image-pro | 3 张 × 2K | 0.5 元/张 | 1.5 元 |
| GLM-4.6V-Flash 评分 3 张 | glm-4.6v-flash | 3×~1.5K tokens | 永久免费 | 0 元 |
| **合计** | | | | **≈ 1.5 元/次** |

**免费额度**：万相新用户 500 张（≈166 次完整流程），GLM 新用户 2000 万 tokens。

---

## 已知风险

1. **ProviderConfig.from_env("glm")** — 需要确认 `app.ai.config.ProviderConfig` 是否有 `from_env` 类方法。如果没有，改用直接构造 `ProviderConfig(api_key=..., base_url=..., model=..., ...)`。
2. **万相2.7 size="2K"** — 需确认 `ImageGenerator.generate` 的 `size` 参数对 wanxiang27 是否支持 "2K" 简写。`_call_wanxiang27` 应该处理这个。
3. **GLM-4.6V-Flash 多模态响应** — GLM 可能返回纯文本而非 JSON，`glm_vision_judge` 有 fallback 逻辑。
4. **图片 base64 体积** — 2K PNG 可能 5-10MB，base64 后 7-13MB，HTTP 请求体较大。如果超时，考虑改用 URL 方式（先把图上传到可访问 URL）。

---

## 执行方式选择

Plan complete and saved to `docs/plans/2026-08-27-visual-design-bg-pipeline-design.md`. Two execution options:

1. **Subagent-Driven (this session)** - 我在当前会话分派 subagent 逐 task 实施，task 之间 review
2. **直接执行** - 我自己按计划逐 task 实施（PoC 脚本聚焦，单文件，我已掌握全部上下文）

**推荐：直接执行**。理由：单文件 PoC，上下文已全，委派开销 > 收益。
