#!/usr/bin/env python3
"""Build per-ticker timeline JSON for /ticker/[id] pages."""

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
    FEED_TODAY_PATH,
    THIRTEEN_F_BY_CIK_DIR,
    TICKERS_OUTPUT_DIR,
    load_investors,
    normalize_cik,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_feed(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"signals": []}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def build_timelines(
    portfolios: list[dict[str, Any]],
    feed: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    events_by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    names: dict[str, str] = {}

    for portfolio in portfolios:
        firm = portfolio.get("firm") or portfolio.get("cik")
        report_date = portfolio.get("filing", {}).get("reportDate", "")
        for h in portfolio.get("holdings", []):
            ticker = h.get("ticker")
            if not ticker:
                continue
            sym = str(ticker).upper()
            if h.get("nameOfIssuer"):
                names[sym] = str(h["nameOfIssuer"])
            if not h.get("passesRule2", True):
                continue
            weight = h.get("weightPct", 0)
            events_by_ticker[sym].append(
                {
                    "date": report_date,
                    "type": "13F",
                    "icon": "institution",
                    "title": f"{firm}",
                    "description": f"Holds {weight:.2f}% of portfolio ({h.get('qOqChange', '—')})",
                    "meta": {"cik": portfolio.get("cik"), "weightPct": weight},
                }
            )

    for signal in feed.get("signals", []):
        sym = str(signal.get("ticker", "")).upper()
        if not sym:
            continue
        names.setdefault(sym, signal.get("companyName", sym))
        insider = signal.get("insiderActions", {})
        events_by_ticker[sym].append(
            {
                "date": insider.get("date", ""),
                "type": "INSIDER",
                "icon": "insider",
                "title": "Insider open-market buy",
                "description": ", ".join(insider.get("recentBuyers", [])[:3]),
                "meta": {
                    "totalAmountUsd": insider.get("totalAmountUsd"),
                    "signalType": signal.get("signalType"),
                },
            }
        )

    timelines: dict[str, dict[str, Any]] = {}
    for ticker, events in events_by_ticker.items():
        events.sort(key=lambda e: e.get("date", ""), reverse=True)
        timelines[ticker] = {
            "ticker": ticker,
            "companyName": names.get(ticker, ticker),
            "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "events": events,
        }
    return timelines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--13f-dir", type=Path, default=THIRTEEN_F_BY_CIK_DIR, dest="dir_13f")
    parser.add_argument("--feed", type=Path, default=FEED_TODAY_PATH)
    parser.add_argument("-o", type=Path, default=TICKERS_OUTPUT_DIR)
    args = parser.parse_args()

    investors = load_investors()
    portfolios = []
    for inv in investors:
        path = args.dir_13f / f"{normalize_cik(inv['cik'])}.json"
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                portfolios.append(json.load(fh))

    feed = load_feed(args.feed)
    timelines = build_timelines(portfolios, feed)

    args.o.mkdir(parents=True, exist_ok=True)
    index: list[str] = []
    for ticker, payload in sorted(timelines.items()):
        out = args.o / f"{ticker}.json"
        with out.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        index.append(ticker)

    index_path = args.o / "index.json"
    with index_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tickers": index,
            },
            fh,
            indent=2,
        )
        fh.write("\n")

    logger.info("Wrote %d ticker timelines to %s", len(index), args.o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
