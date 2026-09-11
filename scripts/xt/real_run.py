"""A1 极限实验 · 真跑器（统计层）。

只跑 Mock 层永远测不出来的东西：LLM 的随机性。

套件：
  cross-run   同一文档上传 N 次 → 字段命中数分布（35 vs 34 跨轮方差，E4.3/D）
  noun-flood  专名洪水文档上传 → 版权 matches 数 vs 30 知名 IP（E1.5 真跑）
  truncation  双哨兵长文上传 → 玄骸纹章字段是否被预填（E1.4 真跑复核）

前置：
  1. 后端已启动：uvicorn app.main:app --port 8000（workdir=backend）
  2. .env 配置了可用的 provider key（deepseek 等）
  3. 语料已生成：python scripts/xt/make_corpus.py

用法：
  python scripts/xt/real_run.py --base http://localhost:8000 --suite cross-run --n 10
  python scripts/xt/real_run.py --suite noun-flood --n 3
  python scripts/xt/real_run.py --suite truncation

证据落盘：%TEMP%\\opencode\\a1_xt\\<suite>_<timestamp>.json
判定口径（设计文档 §4）：字段数方差 >±1 = 不稳定；risk 翻转 >=2/10 = 摇摆。
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import datetime
from pathlib import Path

import httpx

CORPUS = Path(__file__).parent / "corpus"
EVIDENCE_DIR = Path(os.environ.get("TEMP", "/tmp")) / "opencode" / "a1_xt"
TIMEOUT_S = 300.0  # 单次上传 = 3 次 LLM 调用（提取/版权/解析），留足预算


def _evidence_path(suite: str) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return EVIDENCE_DIR / f"{suite}_{stamp}.json"


def _upload(client: httpx.Client, base: str, user_id: str, filename: str, content: str) -> dict:
    resp = client.post(
        f"{base}/api/a1/upload",
        json={"user_id": user_id, "filename": filename, "content": content},
        timeout=TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()


def _provider_label() -> str:
    """从 backend/.env 读 ACTIVE_PROVIDER（证据元数据，v2 补）。"""
    env = Path(__file__).resolve().parents[2] / "backend" / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("ACTIVE_PROVIDER"):
                return line.split("=", 1)[1].strip()
    return "unknown"


def _distribution_suite(base: str, n: int, doc_file: str, label: str) -> dict:
    """上传分布套件通用体：字段命中分布 + 存在性翻转 + 同 key 异值翻转。"""
    doc = (CORPUS / doc_file).read_text(encoding="utf-8")
    stamp = int(time.time())
    runs: list[dict] = []
    with httpx.Client() as client:
        for i in range(n):
            t0 = time.time()
            body = _upload(
                client, base, f"u_xt_{label}_{stamp}_{i}", f"{label}测试_{i}.txt", doc
            )
            answers = body.get("file", {}).get("answers", {})
            runs.append(
                {"run": i, "fields": len(answers), "answers": answers,
                 "seconds": round(time.time() - t0, 1)}
            )
            print(f"  run {i + 1}/{n}: {len(answers)} fields ({runs[-1]['seconds']}s)")

    counts = [r["fields"] for r in runs]
    all_keys = {k for r in runs for k in r["answers"]}
    # 存在性翻转：只在部分轮次出现/缺席的字段（35 vs 34 的元凶层）
    presence_flippers = sorted(
        k for k in all_keys if 0 < sum(1 for r in runs if k in r["answers"]) < n
    )
    # 内容翻转：所有轮次都在场、但取值不一致的字段（更隐蔽的方差形态）
    value_flippers = {
        k: sorted({r["answers"][k] for r in runs})
        for k in sorted(all_keys)
        if all(k in r["answers"] for r in runs)
        and len({r["answers"][k] for r in runs}) > 1
    }
    spread = max(counts) - min(counts)
    return {
        "suite": label,
        "provider": _provider_label(),
        "doc": doc_file,
        "n": n,
        "counts": counts,
        "mean": round(statistics.mean(counts), 2),
        "stdev": round(statistics.pstdev(counts), 2) if n > 1 else 0,
        "spread": spread,
        "fields_present_in_some_but_not_all": presence_flippers,
        "fields_with_inconsistent_values": value_flippers,
        "runs": runs,
        "verdict": "UNSTABLE (spread>1)" if spread > 1 else "STABLE (spread<=1)",
    }


def suite_cross_run(base: str, n: int) -> dict:
    """E4.3 跨轮 N 重奏：显式文档（上界对照）。"""
    return _distribution_suite(base, n, "cross_run_doc.txt", "cross-run")


def suite_borderline(base: str, n: int) -> dict:
    """E4.3-v2 边缘证据文档：显式8/可推断8/无依据19 三档梯度（病理区间）。"""
    return _distribution_suite(base, n, "borderline_doc.txt", "borderline")


def suite_noun_flood(base: str, n: int) -> dict:
    """E1.5 真跑：60 专名文档 → 版权 matches / risk_level。"""
    doc = (CORPUS / "noun_flood.txt").read_text(encoding="utf-8")
    stamp = int(time.time())
    reports: list[dict] = []
    with httpx.Client() as client:
        for i in range(n):
            body = _upload(
                client, base, f"u_xt_noun_{stamp}_{i}", f"专名洪水_{i}.txt", doc
            )
            reports.append(
                {
                    "run": i,
                    "status": body.get("status"),
                    "risk_level": body.get("report", {}).get("risk_level"),
                    "matches": [
                        m.get("term") for m in body.get("report", {}).get("matches", [])
                    ],
                }
            )
            print(f"  run {i + 1}/{n}: risk={reports[-1]['risk_level']} "
                  f"matches={len(reports[-1]['matches'])}")
    risks = [r["risk_level"] for r in reports]
    flips = sum(1 for a, b in zip(risks, risks[1:], strict=False) if a != b)
    report = {
        "suite": "noun-flood",
        "n": n,
        "runs": reports,
        "risk_flips": flips,
        "verdict": f"FLIP-FLOP ({flips} flips)" if flips >= 2 else "CONSISTENT",
    }
    return report


def suite_truncation(base: str) -> dict:
    """E1.4 真跑复核：玄骸纹章只在 20000 字后 → 其字段是否被预填。"""
    doc = (CORPUS / "long_doc_25k.txt").read_text(encoding="utf-8")
    with httpx.Client() as client:
        body = _upload(
            client, base, f"u_xt_trunc_{int(time.time())}", "长文双哨兵.txt", doc
        )
    answers = body.get("file", {}).get("answers", {})
    tail_only_fields = {
        k: v for k, v in answers.items()
        if "视觉设计" in k or "骰子设定" in k
    }
    hit = any("玄骸" in v for v in answers.values())
    print(f"  truncated={body.get('truncated')} fields={len(answers)} "
          f"tail-module-fields={len(tail_only_fields)} sentinel-hit={hit}")
    return {
        "suite": "truncation",
        "truncated_flag": body.get("truncated"),
        "fields": len(answers),
        "tail_module_fields": tail_only_fields,
        "sentinel_tail_reached_answers": hit,
        "verdict": (
            "SENTINEL-PASSED-GATE (unexpected)" if hit
            else "CONFIRMED: tail content invisible to parsing"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--suite", required=True,
                        choices=["cross-run", "borderline", "noun-flood", "truncation"])
    parser.add_argument("--n", type=int, default=3, help="重复次数（cross-run 建议 10）")
    args = parser.parse_args()

    if not CORPUS.exists():
        raise SystemExit("语料不存在，先跑: python scripts/xt/make_corpus.py")

    print(f"real-run suite={args.suite} base={args.base} n={args.n}")
    print("注意：直调真实 LLM，会产生 API 调用费用。\n")

    if args.suite == "cross-run":
        report = suite_cross_run(args.base, args.n)
    elif args.suite == "borderline":
        report = suite_borderline(args.base, args.n)
    elif args.suite == "noun-flood":
        report = suite_noun_flood(args.base, args.n)
    else:
        report = suite_truncation(args.base)

    path = _evidence_path(args.suite)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nverdict: {report['verdict']}")
    print(f"evidence: {path}")


if __name__ == "__main__":
    main()
