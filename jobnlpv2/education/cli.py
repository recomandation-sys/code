"""JSON/JSONL command-line interface for the deterministic extractor."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from typing import Any

from .extractor import EducationExtractor


def _records(source: str) -> Iterable[dict[str, Any]]:
    stripped = source.strip()
    if stripped.startswith("["):
        yield from json.loads(stripped)
    elif stripped.startswith("{"):
        yield json.loads(stripped)
    else:
        for line in source.splitlines():
            if line.strip():
                yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract normalized education requirements from JSON input.")
    parser.add_argument("input", nargs="?", help="JSON/JSONL file; omit to read stdin")
    parser.add_argument("--country", default=None, help="Credential jurisdiction, e.g. US or UK")
    args = parser.parse_args()
    content = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    for item in _records(content):
        country = args.country or item.get("country")
        extractor = EducationExtractor(str(country) if country else None)
        print(json.dumps(extractor.extract(str(item.get("title", "")), str(item.get("description", ""))).to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
