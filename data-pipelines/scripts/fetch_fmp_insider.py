#!/usr/bin/env python3
"""
Fetch FMP Premium insider-trading data, apply Rule 3 (Insider Buy Filter),
and emit feed_today.json for Cloudflare R2 / static API hosting.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants (PRD Rule 3)
# ---------------------------------------------------------------------------
MIN_TRANSACTION_USD = 50_000
ACQUIRE_CODE = "A"
PURCHASE_TYPE = "P"
COMMON_STOCK_KEYWORD = "common stock"

FMP_BASE_URL = "https://financialmodelingprep.com/api/v4/insider-trading"
DEFAULT_LIMIT = 1000
DEFAULT_PAGE_SIZE = 100
MAX_RETRIES = 5
INITIAL_BACKOFF_SEC = 2.0
REQUEST_TIMEOUT_SEC = 30
RATE_LIMIT_DELAY_SEC = 0.25  # ~240 req/min — conservative for Premium tier

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT = PIPELINE_ROOT / "output" / "feed_today.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class InsiderTransaction:
    symbol: str
    company_name: str
    reporting_name: str
    transaction_date: str
    amount_usd: float
    securities_transacted: float
    price: float
    security_name: str
    type_of_owner: str | None


class FMPClientError(Exception):
    """Base error for FMP client failures."""


class FMPRateLimitError(FMPClientError):
    """Raised when API returns 429."""


class FMPAuthError(FMPClientError):
    """Raised when API key is missing or invalid."""


def _load_api_key() -> str:
    load_dotenv(PIPELINE_ROOT.parent / ".env")
    load_dotenv(PIPELINE_ROOT / ".env")
    key = os.environ.get("FMP_API_KEY", "").strip()
    if not key:
        raise FMPAuthError(
            "FMP_API_KEY is not set. Copy .env.example to .env and add your Premium key."
        )
    return key


def _normalize_acq_or_disp(record: dict[str, Any]) -> str | None:
    """FMP may return acqOrDisp or the misspelled acquistionOrDisposition."""
    raw = record.get("acqOrDisp") or record.get("acquistionOrDisposition")
    if raw is None:
        return None
    return str(raw).strip().upper()


def _normalize_transaction_type(record: dict[str, Any]) -> str | None:
    raw = record.get("transactionType")
    if raw is None:
        return None
    # API may return "P", "P-Purchase", "S-Sale", etc.
    code = str(raw).strip().upper()
    if code.startswith("P"):
        return PURCHASE_TYPE
    return code[:1] if code else None


def _transaction_amount_usd(record: dict[str, Any]) -> float:
    """Compute USD notional; prefer explicit value, else shares * price."""
    for key in ("value", "transactionValue", "totalValue"):
        val = record.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass

    try:
        shares = float(record.get("securitiesTransacted") or 0)
        price = float(record.get("price") or 0)
    except (TypeError, ValueError):
        return 0.0

    return shares * price


def passes_rule_3_insider_buy_filter(record: dict[str, Any]) -> bool:
    """
    PRD Rule 3: acqOrDisp == 'A', transactionType == 'P',
    securityName contains 'Common Stock', amount >= $50,000.
    """
    if _normalize_acq_or_disp(record) != ACQUIRE_CODE:
        return False

    if _normalize_transaction_type(record) != PURCHASE_TYPE:
        return False

    security_name = str(record.get("securityName") or "").lower()
    if COMMON_STOCK_KEYWORD not in security_name:
        return False

    if _transaction_amount_usd(record) < MIN_TRANSACTION_USD:
        return False

    symbol = (record.get("symbol") or "").strip()
    if not symbol:
        return False

    return True


def _parse_transaction(record: dict[str, Any]) -> InsiderTransaction | None:
    if not passes_rule_3_insider_buy_filter(record):
        return None

    amount = _transaction_amount_usd(record)
    tx_date = str(record.get("transactionDate") or record.get("filingDate") or "")[:10]
    if not tx_date:
        tx_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return InsiderTransaction(
        symbol=str(record.get("symbol", "")).upper().strip(),
        company_name=str(record.get("companyName") or record.get("issuerName") or "").strip(),
        reporting_name=str(record.get("reportingName") or "Unknown Insider").strip(),
        transaction_date=tx_date,
        amount_usd=amount,
        securities_transacted=float(record.get("securitiesTransacted") or 0),
        price=float(record.get("price") or 0),
        security_name=str(record.get("securityName") or ""),
        type_of_owner=record.get("typeOfOwner"),
    )


def _request_with_retry(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    backoff = INITIAL_BACKOFF_SEC

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT_SEC)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise FMPClientError(f"Network error after {MAX_RETRIES} attempts: {exc}") from exc
            logger.warning("Request failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            time.sleep(backoff)
            backoff *= 2
            continue

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else backoff
            logger.warning("Rate limited (429). Sleeping %.1fs before retry.", wait)
            if attempt == MAX_RETRIES:
                raise FMPRateLimitError("FMP rate limit exceeded after retries.")
            time.sleep(wait)
            backoff *= 2
            continue

        if response.status_code in (401, 403):
            raise FMPAuthError(f"FMP authentication failed ({response.status_code}). Check FMP_API_KEY.")

        if response.status_code >= 500:
            if attempt == MAX_RETRIES:
                raise FMPClientError(f"FMP server error {response.status_code}: {response.text[:200]}")
            logger.warning("Server error %d, retrying...", response.status_code)
            time.sleep(backoff)
            backoff *= 2
            continue

        if not response.ok:
            raise FMPClientError(f"FMP HTTP {response.status_code}: {response.text[:300]}")

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise FMPClientError("Invalid JSON from FMP") from exc

        if isinstance(payload, dict) and "Error Message" in payload:
            raise FMPClientError(payload["Error Message"])

        if not isinstance(payload, list):
            raise FMPClientError(f"Unexpected response type: {type(payload).__name__}")

        return payload

    raise FMPClientError("Unreachable")


def fetch_insider_trading(
    api_key: str,
    *,
    limit: int = DEFAULT_LIMIT,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[dict[str, Any]]:
    """Paginate through FMP /v4/insider-trading with rate limiting."""
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "Apex-ETL/1.0"})

    all_records: list[dict[str, Any]] = []
    page = 0

    while len(all_records) < limit:
        batch_limit = min(page_size, limit - len(all_records))
        params: dict[str, Any] = {
            "apikey": api_key,
            "page": page,
            "limit": batch_limit,
        }

        logger.info("Fetching insider-trading page=%d limit=%d", page, batch_limit)
        batch = _request_with_retry(session, FMP_BASE_URL, params)

        if not batch:
            logger.info("No more records at page %d.", page)
            break

        all_records.extend(batch)
        logger.info("Retrieved %d records (total %d).", len(batch), len(all_records))

        if len(batch) < batch_limit:
            break

        page += 1
        time.sleep(RATE_LIMIT_DELAY_SEC)

    return all_records[:limit]


def _infer_tags(transactions: list[InsiderTransaction]) -> list[str]:
    tags: list[str] = []
    if len(transactions) >= 2:
        tags.append("Cluster Buy")
    owners = {t.type_of_owner for t in transactions if t.type_of_owner}
    if any(o and "officer" in o.lower() for o in owners):
        tags.append("Officer Buy")
    return tags or ["Insider Buy"]


def build_feed_today(transactions: list[InsiderTransaction]) -> dict[str, Any]:
    """Aggregate filtered insider buys into feed_today.json schema."""
    by_symbol: dict[str, list[InsiderTransaction]] = defaultdict(list)
    company_names: dict[str, str] = {}

    for tx in transactions:
        by_symbol[tx.symbol].append(tx)
        if tx.company_name:
            company_names[tx.symbol] = tx.company_name

    signals: list[dict[str, Any]] = []

    for symbol, group in sorted(by_symbol.items()):
        group.sort(key=lambda t: t.transaction_date, reverse=True)
        latest_date = group[0].transaction_date
        total_amount = sum(t.amount_usd for t in group)
        buyers = list(dict.fromkeys(t.reporting_name for t in group))  # preserve order, unique

        signals.append(
            {
                "id": f"{symbol}-{latest_date.replace('-', '')}",
                "ticker": symbol,
                "companyName": company_names.get(symbol) or symbol,
                # Rule 4 (STRONG_RESONANCE) is applied in generate_signals.py
                "signalType": "INSIDER_BUY",
                "superinvestorCount": 0,
                "insiderActions": {
                    "recentBuyers": buyers[:5],
                    "totalAmountUsd": round(total_amount, 2),
                    "date": latest_date,
                },
                "tags": _infer_tags(group),
            }
        )

    signals.sort(
        key=lambda s: s["insiderActions"]["totalAmountUsd"],
        reverse=True,
    )

    return {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signals": signals,
    }


def write_feed(output_path: Path, feed: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(feed, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    logger.info("Wrote %d signals to %s", len(feed.get("signals", [])), output_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch FMP insider trades → feed_today.json")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Max raw records to fetch from FMP",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter but only log stats (no file write)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        api_key = _load_api_key()
    except FMPAuthError as exc:
        logger.error("%s", exc)
        return 1

    try:
        raw = fetch_insider_trading(api_key, limit=args.limit)
    except FMPClientError as exc:
        logger.error("FMP fetch failed: %s", exc)
        return 1

    logger.info("Fetched %d raw insider records.", len(raw))

    transactions: list[InsiderTransaction] = []
    for record in raw:
        parsed = _parse_transaction(record)
        if parsed:
            transactions.append(parsed)

    logger.info(
        "Rule 3 filter: %d / %d records passed (%.1f%%).",
        len(transactions),
        len(raw),
        (100.0 * len(transactions) / len(raw)) if raw else 0.0,
    )

    feed = build_feed_today(transactions)

    if args.dry_run:
        logger.info("Dry run — would write %d signals.", len(feed["signals"]))
        return 0

    try:
        write_feed(args.output, feed)
    except OSError as exc:
        logger.error("Failed to write output: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
