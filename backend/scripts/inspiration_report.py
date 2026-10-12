"""inspiration_log.jsonl 最小聚合报告（stdlib only）。

用法：python scripts/inspiration_report.py [path]
默认路径 data/inspiration_log.jsonl。stdout 输出每事件计数 + 总行数；
畸形行跳过并单独计数。
"""

import collections
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path("data/inspiration_log.jsonl")
    counts: collections.Counter[str] = collections.Counter()
    total = 0
    malformed = 0
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("not a dict")
                    counts[str(record.get("event", "<unknown>"))] += 1
                except (ValueError, TypeError):
                    malformed += 1
    for event, n in sorted(counts.items()):
        print(f"{event}: {n}")
    print(f"total: {total}")
    if malformed:
        print(f"malformed: {malformed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
