#!/usr/bin/env python3
"""
Map CUSIP identifiers to stock tickers via FMP Premium API with local JSON cache.
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
import sys
import time
from pathlib import Path
from typing import Any

import requests

from pipeline_common import (
    CUSIP_CACHE_PATH,
    THIRTEEN_F_BY_CIK_DIR,
    get_fmp_api_key,
    load_dotenv_files,
)

FMP_CUSIP_URL = "https://financialmodelingprep.com/stable/search-cusip"
OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
MAX_RETRIES = 4
INITIAL_BACKOFF_SEC = 2.0
REQUEST_TIMEOUT_SEC = 30
RATE_LIMIT_DELAY_SEC = 0.2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class CusipTickerMapper:
    """FMP-backed CUSIP → ticker mapper with persistent cache."""

    def __init__(
        self,
        api_key: str | None = None,
        cache_path: Path = CUSIP_CACHE_PATH,
        *,
        autosave: bool = True,
    ) -> None:
        load_dotenv_files()
        self.api_key = api_key or get_fmp_api_key()
        self.cache_path = cache_path
        self.autosave = autosave
        self._cache: dict[str, dict[str, Any]] = {}
        self._dirty = False
        self._load_cache()

    def _load_cache(self) -> None:
        if not self.cache_path.exists():
            self._cache = {}
            return
        with self.cache_path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        entries = raw.get("entries", raw) if isinstance(raw, dict) else raw
        if isinstance(entries, dict):
            self._cache = {self._normalize_key(k): v for k, v in entries.items()}
        else:
            self._cache = {}

    def save_cache(self) -> None:
        if not self._dirty:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "description": "CUSIP → ticker cache (FMP stable /search-cusip)",
            "entries": self._cache,
        }
        with self.cache_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        self._dirty = False
        logger.info("Saved CUSIP cache (%d entries) to %s", len(self._cache), self.cache_path)

    @staticmethod
    def _normalize_key(cusip: str) -> str:
        return cusip.strip().upper()

    def get_cached(self, cusip: str) -> dict[str, Any] | None:
        return self._cache.get(self._normalize_key(cusip))

    def map_cusip(self, cusip: str, *, force_refresh: bool = False) -> str | None:
        """
        Resolve a CUSIP to a ticker symbol. Returns None if FMP has no match.
        """
        key = self._normalize_key(cusip)
        if not key:
            return None

        if not force_refresh:
            cached = self._cache.get(key)
            if cached is not None:
                ticker = cached.get("ticker")
                return str(ticker).upper() if ticker else None

        result = self._fetch_from_fmp(key)
        if not result.get("ticker"):
            figi = self._fetch_from_openfigi(key)
            if figi.get("ticker"):
                result = figi

        self._cache[key] = result
        self._dirty = True
        if self.autosave:
            self.save_cache()

        ticker = result.get("ticker")
        return str(ticker).upper() if ticker else None

    def _fetch_from_openfigi(self, cusip: str) -> dict[str, Any]:
        """Free OpenFIGI fallback when FMP has no mapping."""
        try:
            resp = requests.post(
                OPENFIGI_URL,
                json=[{"idType": "ID_CUSIP", "idValue": cusip}],
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT_SEC,
            )
        except requests.RequestException as exc:
            return {"ticker": None, "source": "openfigi", "error": str(exc)}

        if not resp.ok:
            return {"ticker": None, "source": "openfigi", "httpStatus": resp.status_code}

        try:
            payload = resp.json()
        except json.JSONDecodeError:
            return {"ticker": None, "source": "openfigi", "error": "invalid_json"}

        if not payload or not isinstance(payload, list):
            return {"ticker": None, "source": "openfigi"}

        block = payload[0] if payload else {}
        data = block.get("data") or []
        if not data:
            return {"ticker": None, "source": "openfigi"}

        row = data[0]
        ticker = row.get("ticker")
        name = row.get("name")
        time.sleep(0.15)
        return {
            "ticker": str(ticker).upper() if ticker else None,
            "companyName": name,
            "source": "openfigi",
        }

    def _fetch_from_fmp(self, cusip: str) -> dict[str, Any]:
        params = {"cusip": cusip, "apikey": self.api_key}
        backoff = INITIAL_BACKOFF_SEC

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(
                    FMP_CUSIP_URL, params=params, timeout=REQUEST_TIMEOUT_SEC
                )
            except requests.RequestException as exc:
                if attempt == MAX_RETRIES:
                    logger.error("FMP CUSIP lookup failed for %s: %s", cusip, exc)
                    return {"ticker": None, "companyName": None, "error": str(exc)}
                time.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code == 429:
                time.sleep(backoff)
                backoff *= 2
                continue

            if not resp.ok:
                logger.warning("FMP HTTP %s for CUSIP %s", resp.status_code, cusip)
                return {"ticker": None, "companyName": None, "httpStatus": resp.status_code}

            try:
                payload = resp.json()
            except json.JSONDecodeError:
                return {"ticker": None, "companyName": None, "error": "invalid_json"}

            ticker, company = self._parse_fmp_response(payload)
            time.sleep(RATE_LIMIT_DELAY_SEC)
            return {"ticker": ticker, "companyName": company, "source": "fmp"}

        return {"ticker": None, "companyName": None, "error": "max_retries"}

    @staticmethod
    def _parse_fmp_response(payload: Any) -> tuple[str | None, str | None]:
        if isinstance(payload, list) and payload:
            row = payload[0] if isinstance(payload[0], dict) else {}
        elif isinstance(payload, dict):
            row = payload
        else:
            return None, None

        ticker = row.get("symbol") or row.get("ticker")
        company = row.get("companyName") or row.get("name")
        return (
            str(ticker).upper().strip() if ticker else None,
            str(company).strip() if company else None,
        )


def _load_portfolio_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        if "Extra data" not in str(exc):
            raise
        decoder = json.JSONDecoder()
        data, end = decoder.raw_decode(text.lstrip())
        logger.warning(
            "Repaired %s: extra JSON after char %d (artifact merge glitch)",
            path.name,
            end,
        )
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def enrich_13f_directory(
    directory: Path,
    mapper: CusipTickerMapper,
) -> tuple[int, int]:
    """Add/update ticker on holdings in output/13f/by_cik/*.json. Returns (files, cusips_mapped)."""
    files = sorted(directory.glob("*.json"))
    cusips_mapped = 0
    for path in files:
        portfolio = _load_portfolio_json(path)
        changed = False
        for holding in portfolio.get("holdings", []):
            cusip = holding.get("cusip")
            if not cusip:
                continue
            ticker = mapper.map_cusip(cusip)
            if ticker:
                holding["ticker"] = ticker
                cusips_mapped += 1
                changed = True
        if changed:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(portfolio, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
    return len(files), cusips_mapped


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map CUSIPs to tickers via FMP (cached)")
    parser.add_argument("cusips", nargs="*", help="CUSIPs to resolve (omit to print cache stats)")
    parser.add_argument("--cache", type=Path, default=CUSIP_CACHE_PATH)
    parser.add_argument("--force", action="store_true", help="Bypass cache and refetch from FMP")
    parser.add_argument(
        "--enrich-13f-dir",
        type=Path,
        default=None,
        help="Enrich all portfolio JSON files in this directory with tickers",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        mapper = CusipTickerMapper(cache_path=args.cache, autosave=True)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    if args.enrich_13f_dir:
        files, mapped = enrich_13f_directory(args.enrich_13f_dir, mapper)
        mapper.save_cache()
        logger.info("Enriched %d CUSIP rows across %d files in %s", mapped, files, args.enrich_13f_dir)
        return 0

    if not args.cusips:
        logger.info("Cache contains %d CUSIP entries at %s", len(mapper._cache), args.cache)
        return 0

    for cusip in args.cusips:
        ticker = mapper.map_cusip(cusip, force_refresh=args.force)
        print(f"{cusip} -> {ticker or '(no match)'}")

    mapper.save_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
