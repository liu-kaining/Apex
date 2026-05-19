#!/usr/bin/env python3
"""Write output/manifest.json summarizing ETL run for observability."""

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

from pipeline_common import (
    FEED_TODAY_PATH,
    MANIFEST_PATH,
    OUTPUT_DIR,
    SP500_GRID_PATH,
    THIRTEEN_F_DIR,
    THIRTEEN_F_BY_CIK_DIR,
    TICKERS_OUTPUT_DIR,
)


def file_meta(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    stat = path.stat()
    meta: dict[str, Any] = {
        "path": str(path.relative_to(OUTPUT_DIR.parent)),
        "bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }
    if path.suffix == ".json":
        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                if "signals" in data:
                    meta["signalCount"] = len(data.get("signals", []))
                    meta["resonanceMatched"] = data.get("resonanceMatched")
                if "grid" in data:
                    meta["gridRows"] = len(data.get("grid", []))
                if "tickers" in data and path.name == "index.json":
                    meta["tickerCount"] = len(data.get("tickers", []))
        except json.JSONDecodeError:
            meta["parseError"] = True
    return meta


def build_manifest() -> dict[str, Any]:
    thirteen_f_index = THIRTEEN_F_DIR / "index.json"
    thirteen_f_stats: dict[str, Any] = {}
    if thirteen_f_index.is_file():
        with thirteen_f_index.open(encoding="utf-8") as fh:
            thirteen_f_stats = json.load(fh)

    by_cik_files = list(THIRTEEN_F_BY_CIK_DIR.glob("*.json")) if THIRTEEN_F_BY_CIK_DIR.exists() else []

    return {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifacts": {
            "feed_today": file_meta(FEED_TODAY_PATH),
            "sp500_grid": file_meta(SP500_GRID_PATH),
            "thirteen_f_index": file_meta(thirteen_f_index),
            "ticker_index": file_meta(TICKERS_OUTPUT_DIR / "index.json"),
        },
        "counts": {
            "thirteenFPortfoliosOnDisk": len(by_cik_files),
            "thirteenFSucceeded": thirteen_f_stats.get("succeeded"),
            "thirteenFFailed": thirteen_f_stats.get("failed"),
            "tickerTimelineFiles": len(list(TICKERS_OUTPUT_DIR.glob("*.json")))
            - (1 if (TICKERS_OUTPUT_DIR / "index.json").exists() else 0),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    manifest = build_manifest()
    args.o.parent.mkdir(parents=True, exist_ok=True)
    with args.o.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Wrote manifest to {args.o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
