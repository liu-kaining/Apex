#!/usr/bin/env python3
"""Merge per-shard 13F artifact directories into output/13f/by_cik/."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from pipeline_common import THIRTEEN_F_BY_CIK_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_portfolio_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        if "Extra data" not in str(exc):
            raise
        decoder = json.JSONDecoder()
        data, end = decoder.raw_decode(text.lstrip())
        trailing = text.lstrip()[end:].strip()
        if trailing:
            logger.warning(
                "Trimmed trailing JSON in %s (kept first object only, %d extra chars)",
                path.name,
                len(trailing),
            )
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def merge_shard_dirs(shard_dirs: list[Path], dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for shard_dir in shard_dirs:
        if not shard_dir.is_dir():
            logger.warning("Skip missing shard dir: %s", shard_dir)
            continue
        files = sorted(shard_dir.glob("*.json"))
        logger.info("Shard %s: %d portfolio file(s)", shard_dir.name, len(files))
        for src in files:
            data = load_portfolio_json(src)
            out = dest / src.name
            with out.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            copied += 1
    return copied


def discover_shard_dirs(root: Path) -> list[Path]:
    """Find thirteen-f-shard-* directories under root (GHA artifact layout)."""
    shards = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("thirteen-f-shard-"))
    if shards:
        return shards
    if list(root.glob("*.json")):
        return [root]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge 13F shard artifacts into by_cik/")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("data-pipelines/output/13f"),
        help="Directory containing thirteen-f-shard-* subdirs or loose JSON files",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=THIRTEEN_F_BY_CIK_DIR,
    )
    args = parser.parse_args()

    shard_dirs = discover_shard_dirs(args.artifact_root)
    if not shard_dirs:
        logger.error("No shard directories under %s", args.artifact_root)
        return 1

    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True, exist_ok=True)

    count = merge_shard_dirs(shard_dirs, args.output)
    logger.info("Merged %d portfolio file(s) into %s", count, args.output)
    return 0 if count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
