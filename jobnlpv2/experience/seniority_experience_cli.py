"""JSON/JSONL CLI for seniority and minimum experience extraction."""
from __future__ import annotations
import argparse, json, sys
from seniority_experience_extractor import extract_seniority_and_minimum_experience

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?")
    parser.add_argument("--contract-type", default=None)
    args = parser.parse_args()
    raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    item = json.loads(raw)
    contract_type = args.contract_type if args.contract_type is not None else item.get("contract_type")
    print(json.dumps(extract_seniority_and_minimum_experience(item.get("title"), item.get("description"), contract_type), separators=(",", ":")))
    return 0

if __name__ == "__main__": raise SystemExit(main())
