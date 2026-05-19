#!/usr/bin/env python3
"""Rebuild output/13f/index.json from all by_cik/*.json portfolio files."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from pipeline_common import THIRTEEN_F_BY_CIK_DIR, THIRTEEN_F_DIR


def rebuild_index(by_cik_dir: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(by_cik_dir.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            portfolio = json.load(fh)
        tickers = sorted(
            {str(h["ticker"]).upper() for h in portfolio.get("holdings", []) if h.get("ticker")}
        )
        entries.append(
            {
                "cik": portfolio.get("cik", path.stem),
                "firm": portfolio.get("firm"),
                "dataromaCode": portfolio.get("dataromaCode"),
                "holdingCount": portfolio.get("holdingCount", len(portfolio.get("holdings", []))),
                "reportDate": portfolio.get("filing", {}).get("reportDate"),
                "tickers": tickers,
            }
        )
    return {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "processed": len(entries),
        "succeeded": len(entries),
        "failed": 0,
        "portfolios": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--by-cik-dir", type=Path, default=THIRTEEN_F_BY_CIK_DIR)
    parser.add_argument("--output", type=Path, default=THIRTEEN_F_DIR / "index.json")
    args = parser.parse_args()

    if not args.by_cik_dir.is_dir():
        print(f"No directory: {args.by_cik_dir}", file=sys.stderr)
        return 1

    summary = rebuild_index(args.by_cik_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Wrote index with {summary['succeeded']} portfolios to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
