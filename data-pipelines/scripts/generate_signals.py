#!/usr/bin/env python3
"""
Rule 4: Join insider feed (feed_today.json) with 13F superinvestor holdings.
Updates superinvestorCount and signalType for resonance matches.
"""

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
from datetime import date, datetime, timedelta, timezone
from typing import Any

from pipeline_common import (
    FEED_TODAY_PATH,
    THIRTEEN_F_BY_CIK_DIR,
    load_investors,
    normalize_cik,
    normalize_ticker_symbol,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# PRD Rule 4: insider buy must be within the last N calendar days
INSIDER_LOOKBACK_DAYS = 7


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def filter_signals_by_insider_recency(
    feed: dict[str, Any],
    *,
    lookback_days: int = INSIDER_LOOKBACK_DAYS,
) -> dict[str, Any]:
    """Keep only signals whose latest insider action is within lookback_days."""
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=lookback_days)
    kept: list[dict[str, Any]] = []
    dropped = 0

    for signal in feed.get("signals", []):
        insider_date = _parse_iso_date(
            str(signal.get("insiderActions", {}).get("date", ""))
        )
        if insider_date is None or insider_date < cutoff:
            dropped += 1
            continue
        kept.append(signal)

    if dropped:
        logger.info(
            "Dropped %d signal(s) older than %d days (cutoff %s).",
            dropped,
            lookback_days,
            cutoff.isoformat(),
        )

    feed["signals"] = kept
    return feed


def load_feed(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_13f_portfolios(
    by_cik_dir: Path,
    investors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    portfolios: list[dict[str, Any]] = []
    for investor in investors:
        cik = normalize_cik(investor["cik"])
        path = by_cik_dir / f"{cik}.json"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            portfolios.append(json.load(fh))
    return portfolios


def build_ticker_index(
    portfolios: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    ticker (upper) -> list of holders with metadata.
    """
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for portfolio in portfolios:
        holder = {
            "cik": portfolio.get("cik"),
            "firm": portfolio.get("firm"),
            "dataromaCode": portfolio.get("dataromaCode"),
            "manager": portfolio.get("manager"),
            "reportDate": portfolio.get("filing", {}).get("reportDate"),
        }
        seen_tickers: set[str] = set()
        for h in portfolio.get("holdings", []):
            sym = normalize_ticker_symbol(h.get("ticker"))
            if not sym:
                continue
            if sym in seen_tickers:
                continue
            seen_tickers.add(sym)
            index[sym].append(
                {
                    **holder,
                    "weightPct": h.get("weightPct"),
                    "valueUsd": h.get("valueUsd"),
                    "nameOfIssuer": h.get("nameOfIssuer"),
                }
            )

    return dict(index)


def apply_resonance(
    feed: dict[str, Any],
    ticker_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    signals = feed.get("signals", [])
    resonance_count = 0

    for signal in signals:
        ticker = str(signal.get("ticker", "")).upper().strip()
        holders = ticker_index.get(ticker, [])
        count = len(holders)

        signal["superinvestorCount"] = count
        signal["superinvestors"] = [
            {
                "cik": h.get("cik"),
                "firm": h.get("firm"),
                "dataromaCode": h.get("dataromaCode"),
                "weightPct": h.get("weightPct"),
            }
            for h in holders
        ]

        if count >= 1:
            signal["signalType"] = "STRONG_RESONANCE"
            resonance_count += 1
            tags = signal.setdefault("tags", [])
            if "13F Resonance" not in tags:
                tags.append("13F Resonance")
        else:
            signal["signalType"] = "INSIDER_BUY"

    feed["signals"] = signals
    feed["resonanceMatched"] = resonance_count
    feed["lastUpdated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return feed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Rule 4 resonance signals")
    parser.add_argument(
        "--feed",
        type=Path,
        default=FEED_TODAY_PATH,
        help="Insider feed JSON (from fetch_fmp_insider.py)",
    )
    parser.add_argument(
        "--13f-dir",
        type=Path,
        default=THIRTEEN_F_BY_CIK_DIR,
        dest="thirteen_f_dir",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=FEED_TODAY_PATH,
        help="Output path (defaults to in-place update of feed)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.feed.exists():
        logger.error("Feed not found: %s — run fetch_fmp_insider.py first.", args.feed)
        return 1

    feed = load_feed(args.feed)
    feed = filter_signals_by_insider_recency(feed)

    ticker_index: dict[str, list[dict[str, Any]]] = {}
    if not args.thirteen_f_dir.exists():
        logger.warning(
            "13F directory missing (%s) — skipping resonance join; "
            "all signals remain INSIDER_BUY. Run fetch_13f_sec.py or 13F Quarterly.",
            args.thirteen_f_dir,
        )
    else:
        investors = load_investors()
        portfolios = load_13f_portfolios(args.thirteen_f_dir, investors)
        if not portfolios:
            logger.warning(
                "No 13F portfolio files under %s — skipping resonance join.",
                args.thirteen_f_dir,
            )
        else:
            logger.info("Loaded %d 13F portfolios", len(portfolios))
            ticker_index = build_ticker_index(portfolios)
            logger.info("Built ticker index with %d symbols", len(ticker_index))

    updated = apply_resonance(feed, ticker_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(updated, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    logger.info(
        "Wrote %d signals (%d STRONG_RESONANCE) to %s",
        len(updated.get("signals", [])),
        updated.get("resonanceMatched", 0),
        args.output,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
