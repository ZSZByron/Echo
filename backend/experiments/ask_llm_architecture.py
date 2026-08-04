"""Ask LLM directly: how should chained layer generation work to avoid duplication and maintain logic?"""
from __future__ import annotations

import json
import os
import sys
import io
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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
from app.ai.provider import create_provider
import asyncio


async def main():
    config = load_provider_config()
    provider = create_provider(config)

    # Stage 1 constraints as context
    with open("H:/UGC/backend/experiments/results/v3t_stage1_constraints_20260803_131945.json", "r", encoding="utf-8") as f:
        s1 = json.load(f)

    constraints_json = json.dumps(s1["constraints"], ensure_ascii=False, indent=2)

    system_prompt = f"""\
你是一个游戏世界构建系统的架构师。

我有一个种子概念和一套6维约束框架：

种子: {s1['seed_input']}
描述: {s1['seed_description']}
意图: {s1['intent']}

6维约束框架:
```json
{constraints_json}
```

现在我要把这套约束映射到6个创作层级，生成每层的专属内容。

6个层级:
1. world — 世界观
2. region — 区域文化
3. scene — 场景/地点
4. campaign — 战役/剧情
5. npc — NPC
6. asset — 资产/物品

每个层级有权重表，决定该层级关注哪些维度:
  world:    RED=20% LAW=30% ACT=5%  NAR=35% WST=5%  SOC=5%
  region:   RED=10% LAW=10% ACT=10% NAR=20% WST=5%  SOC=45%
  scene:    RED=10% LAW=25% ACT=5%  NAR=10% WST=40% SOC=10%
  campaign: RED=10% LAW=5%  ACT=10% NAR=40% WST=5%  SOC=30%
  npc:      RED=5%  LAW=10% ACT=25% NAR=20% WST=10% SOC=30%
  asset:    RED=10% LAW=30% ACT=30% NAR=10% WST=10% SOC=10%

我之前的问题是：
1. 每层生成完整6维 → 大量重复（3层都在说"直视死人头会死"）
2. 只有约束复述，没有内容生成（asset层应该写物品外观/材质/历史，不是复述规则）

现在我要做链式生成：world → region → scene → campaign → npc → asset，每层看到前面层的内容。

请回答以下问题，用中文详细回答：

## 问题1: 防重复
每个层级应该生成什么专属内容？请逐层列出该层级应该输出的信息类型。
哪些信息是所有层级共享的（只生成一次），哪些是每层独有的？

## 问题2: 链式上下文
链式生成时，每层需要从前面的层级获取哪些关键信息？
请定义层与层之间的依赖关系（格式：Layer X 需要从 Layer Y 获取: [...]）

## 问题3: 上下文压缩
到第6层(asset)时，前面5层内容太多。如何压缩？
你建议每层提取什么关键信息传给下一层？（不要全量JSON，只保留关键事实）

## 问题4: 内容生成 vs 约束复述
约束框架（6维约束）在每层的角色是什么？
每层生成的内容应该是"约束的复述"还是"在约束下生成的具体内容"？
请举例说明 asset 层应该生成什么（基于上面的死人头种子）。

## 问题5: 权重的作用
权重在每层生成中到底控制什么？
是控制"每个维度写多少字"，还是控制"这个层级关注哪些方面"？
请给出具体例子。
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请详细回答以上5个问题。这是架构设计问题，请从系统设计的角度回答，给出具体的字段定义和数据流。"},
    ]

    print(">>> Asking LLM for architecture design ...\n")

    import time
    start = time.time()
    response = await provider.chat(messages, extra_body={"enable_thinking": True, "max_tokens": 8192})
    elapsed = time.time() - start

    print(f"<<< Done in {elapsed:.1f}s\n")
    print("=" * 70)
    print(response)
    print("=" * 70)

    # Save the response
    save_path = Path("H:/UGC/backend/experiments/results/llm_architecture_advice.json")
    save_path.write_text(json.dumps({
        "query": "How to design chained layer generation with no duplication",
        "response": response,
        "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to: {save_path}")


if __name__ == "__main__":
    asyncio.run(main())
