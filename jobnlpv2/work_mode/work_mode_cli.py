"""JSON/JSONL CLI for deterministic work-mode extraction."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from typing import Any

from work_mode_extractor import WorkModeExtractor


def _records(source: str) -> Iterable[dict[str, Any]]:
    stripped = source.strip()
    if stripped.startswith("["): yield from json.loads(stripped)
    elif stripped.startswith("{"): yield json.loads(stripped)
    else:
        for line in source.splitlines():
            if line.strip(): yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract work modes from job JSON input.")
    parser.add_argument("input", nargs="?", help="JSON/JSONL file; omit to read stdin")
    args = parser.parse_args()
    content = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    extractor = WorkModeExtractor()
    for item in _records(content):
        print(json.dumps(extractor.extract(item.get("title"), item.get("description"), item.get("teleworking")).to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
