"""T18 超长压测脚本：graphify_llm 长文本压力测试 + 分块触发线报告。

用法（推荐 workdir = H:\\UGC\\backend）：
    H:\\UGC\\backend\\.venv\\Scripts\\python.exe H:\\UGC\\scripts\\stress_graphify.py --dry-run
    H:\\UGC\\backend\\.venv\\Scripts\\python.exe H:\\UGC\\scripts\\stress_graphify.py --rounds 3

本脚本把 backend 加入 sys.path（以脚本位置推导 ../backend），因此也可从任意
workdir 运行。真 provider 来自 backend/.env（load_provider_config）。

成本护栏：
    --rounds 默认 3，硬上限 10（真 API 调用 ≤10 次）。
    --dry-run 用内置 StubProvider 跑通全流程，0 真调用。

输出：每轮 token 估算 / 延迟 / 五字段完整率 三张表 + 触发线结论一行。
本脚本只测量，不实现分块。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---- 把 backend 加入 sys.path（脚本在 H:\UGC\scripts\，backend 在 ../backend）----
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
# Windows GBK 控制台下保证中文表输出不乱码（重定向文件也为 UTF-8）
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

def _load_backend_env() -> None:
    """手工加载 backend/.env（脚本不在 uvicorn 生命周期内，无自动加载）。"""
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_backend_env()

from app.ai.config import load_provider_config  # noqa: E402
from app.ai.provider import create_provider  # noqa: E402
from app.domains.creation.a1.graphify import (  # noqa: E402
    build_graphify_prompt,
    graphify_llm,
)
from app.domains.creation.seed.a1_question_tree import all_subfield_keys  # noqa: E402

# =============================================================================
# 超长 fixture：3-5 模块满答 × 中文长文 value（明华样本 ×3 体量 ≈ 每模块 2-3k 字）
# =============================================================================

_LORE_PARAGRAPHS = [
    "在世界的原初，混沌尚未分化，万物共享同一团无名的气息。传说中最古老的"
    "观察者睁眼的一刻，气息因被注视而凝结，形成了第一层稳固的存在——大地。"
    "大地并非静止，它像呼吸一样缓慢涨落，每一次涨落都会在表层留下新的纹路，"
    "这些纹路后来被称为脉络，是所有力量流动的河道。",
    "力量在这个世界里从来不是抽象的概念，而是一种可以被收割、被储存、被继承"
    "的实体。修炼者称之为摘取：当一个人的意志与某条脉络产生共鸣时，他可以"
    "从共鸣点摘下一枚晶核。晶核的成色取决于共鸣时的情绪纯度，愤怒摘出的核"
    "偏红且不稳定，静默摘出的核偏青且寿命极长。",
    "文明围绕脉络建立。最大的三座城邦分别坐落在三条主脉络的交汇处，城邦之间"
    "通过脉络舟往来。脉络舟不烧燃料，它靠船首一枚逆向晶核与脉络本身的流动"
    "形成推力。因此航线的时刻表随脉络的潮汐而定，错过一次潮汐，可能要在"
    "中继站滞留整月。",
    "历史被记录在一种叫碑语的介质上。碑语不是文字，而是一段被封存的共鸣："
    "把重要事件发生时的集体情绪压入石碑，后来者把手按上石碑，就能重历那段"
    "情绪。正因如此，历史学家在本文明体系中地位崇高，也正因如此，篡改一块"
    "碑语等同于篡改一个时代的记忆，是最重的罪名。",
    "外缘之地是脉络到达不了的荒原。那里没有可以共鸣的流动，摘取术完全失效，"
    "居住在边缘的族群因此发展出完全依赖手工与口传的技艺传统。他们相信混沌"
    "并未远离，只是睡着了；一旦有人在荒原中心制造出足够强烈的情绪共鸣，"
    "沉睡的混沌就会被惊醒。",
]


def _long_text(paragraph_cycle: int, extra: str) -> str:
    """拼出一段约 N 段的中文长文本（每段约 160 字）。"""
    parts = [f"【{extra}·概述】"] if extra else []
    for i in range(paragraph_cycle):
        parts.append(_LORE_PARAGRAPHS[i % len(_LORE_PARAGRAPHS)])
    return "\n".join(parts)


def build_answers() -> dict[str, str]:
    """构造 3-5 模块满答的超长 answers fixture（锚点动态取合法键）。"""
    keys = sorted(all_subfield_keys())
    if len(keys) < 5:
        raise RuntimeError(f"合法锚点不足 5 个: {len(keys)}")
    # 取前 5 个不同模块的锚点（按模块分组，每组取第一个子字段，保证跨模块满答）
    seen_modules: set[str] = set()
    chosen: list[str] = []
    for key in keys:
        module = key.split(".", 1)[0]
        if module not in seen_modules:
            seen_modules.add(module)
            chosen.append(key)
        if len(chosen) == 5:
            break
    answers: dict[str, str] = {}
    for i, key in enumerate(chosen):
        # 每模块 16-20 段 ≈ 2.6k-3.2k 字（明华样本 ×3 体量）
        answers[key] = _long_text(16 + i, extra=key)
    return answers


# =============================================================================
# Stub provider（--dry-run 用，0 真调用）
# =============================================================================


class StubProvider:
    """返回结构合法 JSON 的桩 provider（镜像 tests conftest 的 FakeProvider 范式）。"""

    def __init__(self, answers: dict[str, str]):
        anchors = list(answers.keys())
        self._anchors = anchors
        self.calls = 0

    async def chat_json(self, messages):  # noqa: ANN001
        self.calls += 1
        titles = [f"条目{i}" for i in range(3)]
        entries = [
            {
                "anchor": anchor,
                "items": [
                    {"title": t, "content": f"{anchor} 的 {t} 内容概述", "children": []}
                    for t in titles
                ],
            }
            for anchor in self._anchors
        ]
        first_anchor = self._anchors[0]
        edges = [
            {
                "from": f"d:{first_anchor}:{titles[0]}",
                "to": self._anchors[-1],
                "relation": "存在塑力",
                "rationale": "stub",
                "confidence": "semantic",
            },
            {
                "from": self._anchors[0],
                "to": self._anchors[1] if len(self._anchors) > 1 else self._anchors[0],
                "relation": "身份锚定",
                "rationale": "stub",
                "confidence": "semantic",
            },
        ]
        return {
            "module_summaries": {a.split(".")[0]: "一句话归纳" for a in self._anchors},
            "entries": entries,
            "edges": edges,
            "constraint_fields": {"LAW.world_structure": "stub 世界结构约束"},
            "open_questions": ["条目A 与 条目B 之间是否存在未被记录的盟约？"],
        }


# =============================================================================
# 测量
# =============================================================================


def _estimate_tokens(text: str) -> int:
    """token 估算：中文密度高，chars/4 会低估；这里用保守估算 max(chars/4, chars/6)。

    项目未装 tiktoken（未验证），统一采用「输入按 chars/4 估算并注明」的
    约定口径；deepseek 官方中文比例约 1 token ≈ 0.6-0.7 字，故附 chars 原始值
    供换算。
    """
    return len(text) // 4


def run_round(idx: int, session: object, provider: object, timeout: float) -> dict:
    """跑一轮 graphify_llm 并采集指标。"""
    prompt_chars = len(build_graphify_prompt(session.answers))
    t0 = time.perf_counter()
    result = graphify_llm(session, provider, timeout=timeout)
    latency = time.perf_counter() - t0
    out_chars = len(result.model_dump_json())
    completeness = {
        "module_summaries": len(result.module_summaries) > 0,
        "entries": len(result.entries) > 0,
        "edges": len(result.edges) > 0,
        "constraint_fields": len(result.constraint_fields) > 0,
        "open_questions": len(result.open_questions) > 0,
    }
    return {
        "round": idx,
        "input_tokens_est": _estimate_tokens("x" * prompt_chars),
        "input_chars": prompt_chars,
        "output_tokens_est": _estimate_tokens("x" * out_chars),
        "output_chars": out_chars,
        "latency_s": latency,
        "success": result.success,
        "warning": result.warning[:120],
        "counts": {
            "module_summaries": len(result.module_summaries),
            "entries": sum(len(g.items) for g in result.entries),
            "edges": len(result.edges),
            "constraint_fields": len(result.constraint_fields),
            "open_questions": len(result.open_questions),
        },
        "completeness": completeness,
        "completeness_score": sum(completeness.values()),
    }


def render_table(title: str, headers: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    def fmt(cells: list[str]) -> str:
        return " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells))
    sep = "-+-".join("-" * w for w in widths)
    return "\n".join([title, fmt(headers), sep] + [fmt(r) for r in rows])


# =============================================================================
# main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="graphify_llm 长文本压测")
    parser.add_argument("--rounds", type=int, default=3, help="轮数（默认 3，硬上限 10）")
    parser.add_argument("--dry-run", action="store_true", help="stub provider，0 真调用")
    parser.add_argument("--timeout", type=float, default=60.0, help="单轮超时秒数")
    parser.add_argument("--json-out", type=str, default="", help="额外输出 JSON 路径")
    args = parser.parse_args()

    if args.rounds < 1 or args.rounds > 10:
        parser.error("--rounds 必须在 1..10（成本护栏：真 API 调用 ≤10 次）")

    # 最小 session（guide_engine.A1Session 范式，graphify 只读 session.answers/session_id）
    from app.domains.creation.a1.guide_engine import A1Session

    answers = build_answers()
    session = A1Session(session_id="stress_t18", user_id="stress", ip_code="IP9001")
    session.answers = answers

    if args.dry_run:
        provider = StubProvider(answers)
        provider_label = "StubProvider (dry-run)"
    else:
        provider = create_provider(load_provider_config())
        provider_label = f"{type(provider).__name__} (real API)"

    print(f"=== T18 graphify 压测 ===")
    print(f"provider: {provider_label}")
    print(f"rounds: {args.rounds}  timeout: {args.timeout}s")
    print(f"fixture: {len(answers)} 个模块满答, 总 {sum(len(v) for v in answers.values())} 字")
    print()

    rows = []
    for i in range(1, args.rounds + 1):
        print(f"-- round {i} ...", flush=True)
        r = run_round(i, session, provider, args.timeout)
        rows.append(r)
        print(
            f"   success={r['success']} latency={r['latency_s']:.1f}s "
            f"in_est={r['input_tokens_est']} out_est={r['output_tokens_est']} "
            f"complete={r['completeness_score']}/5"
        )
        if r["warning"]:
            print(f"   warning: {r['warning']}")

    print()
    print(render_table(
        "【表1 token 估算（口径：chars/4，中文场景实际 token 数更高，原始字数见括号）】",
        ["轮次", "输入 tokens(est)", "输入字符", "输出 tokens(est)", "输出字符"],
        [
            [str(r["round"]), str(r["input_tokens_est"]), str(r["input_chars"]),
             str(r["output_tokens_est"]), str(r["output_chars"])]
            for r in rows
        ],
    ))
    print()
    print(render_table(
        "【表2 延迟】",
        ["轮次", "延迟(秒)", "success"],
        [[str(r["round"]), f"{r['latency_s']:.2f}", str(r["success"])] for r in rows],
    ))
    print()
    print(render_table(
        "【表3 五字段完整率（非空计 1，满分 5）】",
        ["轮次", "module_summaries", "entries", "edges", "constraint_fields", "open_questions", "得分"],
        [
            [str(r["round"])] + [str(r["counts"][k]) for k in
             ("module_summaries", "entries", "edges", "constraint_fields", "open_questions")]
            + [f"{r['completeness_score']}/5"]
            for r in rows
        ],
    ))
    print()

    # 触发线结论（success 且五字段 ≥4/5 视为单调用安全样本；
    # constraint_fields 依赖答案内容含可归类约束，4/5 不视为超长失败）
    ok_rows = [r for r in rows if r["success"] and r["completeness_score"] >= 4]
    if ok_rows:
        max_in = max(r["input_chars"] for r in ok_rows)
        scores = "/".join(str(r["completeness_score"]) for r in ok_rows)
        print(
            f"触发线结论：本次实测输入 ≤{max_in} 字符（约 {max_in // 4} est-tokens，"
            f"chars/4 口径）时单调用稳定（success，完整率 {scores}/5），"
            f"建议分块触发线设为输入 ≤{int(max_in * 0.8) // 1000}k 字符（80% 余量）；"
            f"超过该线再考虑分块。"
        )
    else:
        print("触发线结论：实测无完整成功轮次，结论基于 dry-run/失败数据，需复测校准。")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"provider": provider_label, "rows": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nJSON 已写: {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
