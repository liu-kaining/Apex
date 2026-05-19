#!/usr/bin/env python3
"""Build sp500_grid.json from aggregated superinvestor 13F holdings."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from pipeline_common import (
    normalize_ticker_symbol,
    SP500_GRID_PATH,
    SP500_TICKERS_PATH,
    THIRTEEN_F_BY_CIK_DIR,
    load_investors,
    normalize_cik,
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_sp500_universe(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    tickers = data.get("tickers", data) if isinstance(data, dict) else data
    return {str(t).upper().strip() for t in tickers if t}


def load_portfolios(by_cik_dir: Path, investors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for inv in investors:
        cik = normalize_cik(inv["cik"])
        path = by_cik_dir / f"{cik}.json"
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                out.append(json.load(fh))
    return out


def build_grid(
    portfolios: list[dict[str, Any]],
    universe: set[str],
) -> list[dict[str, Any]]:
    """
    Aggregate by ticker across all superinvestor portfolios.
    Only includes rows where at least one holder passes Rule 2 (or all if no flag).
    """
    by_ticker: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "heldBy": [],
            "totalWeight": 0.0,
            "qOqVotes": defaultdict(int),
        }
    )

    for portfolio in portfolios:
        cik = portfolio.get("cik")
        for h in portfolio.get("holdings", []):
            sym = normalize_ticker_symbol(h.get("ticker"))
            if not sym:
                continue
            if universe and sym not in universe:
                continue

            passes = h.get("passesRule2", True)
            if passes is False:
                continue

            weight = float(h.get("weightPct", 0))
            cell = by_ticker[sym]
            if cik and cik not in cell["heldBy"]:
                cell["heldBy"].append(cik)
            cell["totalWeight"] = round(cell["totalWeight"] + weight, 4)
            qoq = str(h.get("qOqChange", "UNCHANGED"))
            cell["qOqVotes"][qoq] += 1

    grid: list[dict[str, Any]] = []
    for ticker, cell in by_ticker.items():
        votes = cell["qOqVotes"]
        qoq_change = max(votes, key=lambda k: votes[k]) if votes else "UNCHANGED"
        grid.append(
            {
                "ticker": ticker,
                "heldBy": cell["heldBy"],
                "totalWeight": round(min(cell["totalWeight"], 100.0), 2),
                "qOqChange": qoq_change,
                "holderCount": len(cell["heldBy"]),
            }
        )

    grid.sort(key=lambda r: (r["holderCount"], r["totalWeight"]), reverse=True)
    return grid


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sp500_grid.json")
    parser.add_argument("--13f-dir", type=Path, default=THIRTEEN_F_BY_CIK_DIR, dest="dir_13f")
    parser.add_argument("-o", type=Path, default=SP500_GRID_PATH)
    parser.add_argument("--universe", type=Path, default=SP500_TICKERS_PATH)
    parser.add_argument("--all-tickers", action="store_true", help="Ignore S&P universe filter")
    args = parser.parse_args()

    investors = load_investors()
    portfolios = load_portfolios(args.dir_13f, investors)
    if not portfolios:
        logger.error("No 13F portfolios in %s", args.dir_13f)
        return 1

    universe: set[str] = set()
    if not args.all_tickers:
        universe = load_sp500_universe(args.universe)
        if not universe:
            logger.warning("No S&P universe file; including all tickers from 13F data.")

    grid = build_grid(portfolios, universe)
    payload = {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sourcePortfolios": len(portfolios),
        "grid": grid,
    }
    args.o.parent.mkdir(parents=True, exist_ok=True)
    with args.o.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    logger.info("Wrote %d grid rows to %s", len(grid), args.o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
