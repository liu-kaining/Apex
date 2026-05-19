#!/usr/bin/env python3
"""
Fetch latest 13F-HR filings from SEC EDGAR for superinvestors in config/investors.json.
Parses informationTable XML and writes per-CIK JSON under output/13f/by_cik/.
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
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests

from map_cusip import CusipTickerMapper
from pipeline_common import (
    THIRTEEN_F_BY_CIK_DIR,
    THIRTEEN_F_DIR,
    accession_no_dashes,
    cik_for_edgar_path,
    get_sec_user_agent,
    load_investors,
    normalize_cik,
)
from rule2 import annotate_holdings_with_qoq_and_rule2

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
SEC_REQUEST_DELAY_SEC = 0.12
MAX_RETRIES = 5
INITIAL_BACKOFF_SEC = 2.0
REQUEST_TIMEOUT_SEC = 45

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class SecClientError(Exception):
    pass


def local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _sec_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": get_sec_user_agent(),
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }
    )
    return session


def _request_json(session: requests.Session, url: str) -> dict[str, Any]:
    backoff = INITIAL_BACKOFF_SEC
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT_SEC)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise SecClientError(f"SEC request failed: {exc}") from exc
            time.sleep(backoff)
            backoff *= 2
            continue

        if resp.status_code in (429, 503):
            if attempt == MAX_RETRIES:
                raise SecClientError(f"SEC rate limited ({resp.status_code})")
            time.sleep(backoff)
            backoff *= 2
            continue

        if not resp.ok:
            raise SecClientError(f"SEC HTTP {resp.status_code} for {url}")

        return resp.json()

    raise SecClientError("Unreachable")


def _request_text(session: requests.Session, url: str) -> str:
    backoff = INITIAL_BACKOFF_SEC
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT_SEC)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise SecClientError(f"SEC request failed: {exc}") from exc
            time.sleep(backoff)
            backoff *= 2
            continue

        if resp.status_code in (429, 503):
            if attempt == MAX_RETRIES:
                raise SecClientError(f"SEC rate limited ({resp.status_code})")
            time.sleep(backoff)
            backoff *= 2
            continue

        if not resp.ok:
            raise SecClientError(f"SEC HTTP {resp.status_code} for {url}")

        return resp.text

    raise SecClientError("Unreachable")


def _is_13f_hr(form: str) -> bool:
    return form == "13F-HR" or (isinstance(form, str) and form.startswith("13F-HR"))


def find_nth_13f_hr(submissions: dict[str, Any], n: int = 0) -> dict[str, str] | None:
    """Return the n-th most recent 13F-HR filing (0 = latest)."""
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    if not forms:
        return None

    seen = 0
    for idx, form in enumerate(forms):
        if not _is_13f_hr(form):
            continue
        if seen == n:
            return {
                "form": form,
                "accessionNumber": recent["accessionNumber"][idx],
                "filingDate": recent["filingDate"][idx],
                "reportDate": recent.get("reportDate", [None] * len(forms))[idx],
            }
        seen += 1
    return None


def find_latest_13f_hr(submissions: dict[str, Any]) -> dict[str, str] | None:
    return find_nth_13f_hr(submissions, 0)


def fetch_holdings_for_filing(
    session: requests.Session,
    cik: str,
    filing: dict[str, str],
) -> tuple[list[dict[str, Any]], str, str]:
    xml_url, xml_name = resolve_infotable_xml(session, cik, filing["accessionNumber"])
    time.sleep(SEC_REQUEST_DELAY_SEC)
    xml_text = _request_text(session, xml_url)
    raw = parse_13f_xml(xml_text)
    return add_weights(aggregate_by_cusip(raw)), xml_url, xml_name


def list_filing_xml_files(session: requests.Session, cik: str, accession: str) -> list[str]:
    cik_path = cik_for_edgar_path(cik)
    folder = accession_no_dashes(accession)
    index_url = f"{SEC_ARCHIVES_BASE}/{cik_path}/{folder}/index.json"
    time.sleep(SEC_REQUEST_DELAY_SEC)
    index = _request_json(session, index_url)
    items = index.get("directory", {}).get("item", [])
    names: list[str] = []
    if isinstance(items, dict):
        items = [items]
    for item in items:
        name = item.get("name", "")
        if name.endswith(".xml") and name != "primary_doc.xml":
            names.append(name)
    return names


def resolve_infotable_xml(
    session: requests.Session,
    cik: str,
    accession: str,
) -> tuple[str, str]:
    """Return (xml_url, xml_filename) for the holdings informationTable."""
    cik_path = cik_for_edgar_path(cik)
    folder = accession_no_dashes(accession)
    base = f"{SEC_ARCHIVES_BASE}/{cik_path}/{folder}/"

    candidates = [
        f"{accession}-infoTable.xml",
        "form13fInfoTable.xml",
    ]
    for name in candidates:
        url = urljoin(base, name)
        time.sleep(SEC_REQUEST_DELAY_SEC)
        resp = session.head(url, timeout=REQUEST_TIMEOUT_SEC)
        if resp.status_code == 200:
            return url, name

    for name in list_filing_xml_files(session, cik, accession):
        url = urljoin(base, name)
        time.sleep(SEC_REQUEST_DELAY_SEC)
        try:
            snippet = _request_text(session, url)[:4096]
        except SecClientError:
            continue
        if "informationTable" in snippet or "<infoTable>" in snippet:
            return url, name

    raise SecClientError(f"No informationTable XML found for {cik} accession {accession}")


def _text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _float(text: str) -> float:
    try:
        return float(text.replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def parse_13f_xml(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    holdings: list[dict[str, Any]] = []

    for node in root.iter():
        if local_tag(node.tag) != "infoTable":
            continue

        row: dict[str, Any] = {}
        for child in node:
            tag = local_tag(child.tag)
            if tag == "shrsOrPrnAmt":
                for sub in child:
                    if local_tag(sub.tag) == "sshPrnamt":
                        row["sshPrnamt"] = _float(_text(sub))
            else:
                row[tag] = _text(child)

        if not row.get("cusip"):
            continue

        # SEC infoTable <value> is market value in USD (see filing total vs portfolio MV).
        value_usd = _float(str(row.get("value", "0")))
        holdings.append(
            {
                "nameOfIssuer": row.get("nameOfIssuer", ""),
                "cusip": row.get("cusip", "").upper(),
                "valueUsd": round(value_usd, 2),
                "sshPrnamt": row.get("sshPrnamt", 0.0),
                "titleOfClass": row.get("titleOfClass"),
            }
        )

    return holdings


def aggregate_by_cusip(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge duplicate CUSIP rows (multiple managers/discretion lines)."""
    merged: dict[str, dict[str, Any]] = {}
    for h in holdings:
        cusip = h["cusip"]
        if cusip not in merged:
            merged[cusip] = dict(h)
            continue
        merged[cusip]["valueUsd"] = round(merged[cusip]["valueUsd"] + h["valueUsd"], 2)
        merged[cusip]["sshPrnamt"] = round(merged[cusip]["sshPrnamt"] + h["sshPrnamt"], 4)
    return sorted(merged.values(), key=lambda x: x["valueUsd"], reverse=True)


def add_weights(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = sum(h["valueUsd"] for h in holdings)
    if total <= 0:
        return holdings
    for h in holdings:
        h["weightPct"] = round(100.0 * h["valueUsd"] / total, 4)
    return holdings


def enrich_with_tickers(
    holdings: list[dict[str, Any]],
    mapper: CusipTickerMapper | None,
) -> list[dict[str, Any]]:
    if mapper is None:
        return holdings
    for h in holdings:
        ticker = mapper.map_cusip(h["cusip"])
        h["ticker"] = ticker
    return holdings


def fetch_investor_13f(
    session: requests.Session,
    investor: dict[str, Any],
    *,
    mapper: CusipTickerMapper | None,
) -> dict[str, Any]:
    cik = normalize_cik(investor["cik"])
    submissions_url = SEC_SUBMISSIONS_URL.format(cik=cik)
    time.sleep(SEC_REQUEST_DELAY_SEC)
    submissions = _request_json(session, submissions_url)

    filing = find_latest_13f_hr(submissions)
    if not filing:
        raise SecClientError(f"No 13F-HR filing for CIK {cik}")

    holdings, xml_url, xml_name = fetch_holdings_for_filing(session, cik, filing)
    previous_filing = find_nth_13f_hr(submissions, 1)
    if previous_filing:
        try:
            prev_holdings, _, _ = fetch_holdings_for_filing(session, cik, previous_filing)
            holdings = annotate_holdings_with_qoq_and_rule2(holdings, prev_holdings)
        except SecClientError as exc:
            logger.warning("QoQ skipped for CIK %s: %s", cik, exc)
            for h in holdings:
                h.setdefault("qOqChange", "UNCHANGED")
                h["passesRule2"] = float(h.get("weightPct", 0)) > 1.0
    else:
        for h in holdings:
            h["qOqChange"] = "NEW"
            h["passesRule2"] = float(h.get("weightPct", 0)) > 1.0

    holdings = enrich_with_tickers(holdings, mapper)

    return {
        "cik": cik,
        "dataromaCode": investor.get("dataromaCode"),
        "firm": investor.get("firm"),
        "manager": investor.get("manager"),
        "displayName": investor.get("displayName"),
        "filing": {
            **filing,
            "infoTableUrl": xml_url,
            "infoTableFile": xml_name,
        },
        "holdingCount": len(holdings),
        "totalValueUsd": round(sum(h["valueUsd"] for h in holdings), 2),
        "holdings": holdings,
    }


def write_portfolio(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch SEC 13F-HR holdings for superinvestors")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max investors to process (0 = all)",
    )
    parser.add_argument(
        "--cik",
        action="append",
        default=[],
        help="Process only these CIKs (repeatable)",
    )
    parser.add_argument(
        "--skip-cusip-map",
        action="store_true",
        help="Do not call FMP for CUSIP→ticker mapping",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=THIRTEEN_F_BY_CIK_DIR,
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="Shard index for parallel CI (0-based)",
    )
    parser.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Total number of shards",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    investors = load_investors()

    if args.cik:
        wanted = {normalize_cik(c) for c in args.cik}
        investors = [i for i in investors if normalize_cik(i["cik"]) in wanted]

    if args.limit > 0:
        investors = investors[: args.limit]

    if args.shard_count > 1:
        investors = [
            inv for i, inv in enumerate(investors) if i % args.shard_count == args.shard_index
        ]
        logger.info(
            "Shard %d/%d — processing %d investors",
            args.shard_index + 1,
            args.shard_count,
            len(investors),
        )

    mapper: CusipTickerMapper | None = None
    if not args.skip_cusip_map:
        try:
            mapper = CusipTickerMapper(autosave=True)
        except ValueError as exc:
            logger.warning("CUSIP mapping disabled: %s", exc)

    session = _sec_session()
    ok, failed = 0, 0
    index_entries: list[dict[str, Any]] = []

    for investor in investors:
        if not investor.get("cik"):
            logger.warning("Skipping investor without CIK: %s", investor.get("displayName"))
            continue
        cik = normalize_cik(investor["cik"])
        label = investor.get("firm") or cik
        try:
            portfolio = fetch_investor_13f(session, investor, mapper=mapper)
            portfolio["fetchedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            out_path = args.output_dir / f"{cik}.json"
            write_portfolio(out_path, portfolio)
            tickers = [h["ticker"] for h in portfolio["holdings"] if h.get("ticker")]
            index_entries.append(
                {
                    "cik": cik,
                    "firm": investor.get("firm"),
                    "dataromaCode": investor.get("dataromaCode"),
                    "holdingCount": portfolio["holdingCount"],
                    "reportDate": portfolio["filing"].get("reportDate"),
                    "tickers": sorted(set(tickers)),
                }
            )
            ok += 1
            logger.info("OK %s — %d holdings", label, portfolio["holdingCount"])
        except (SecClientError, ET.ParseError) as exc:
            failed += 1
            logger.error("FAIL %s (CIK %s): %s", label, cik, exc)

    if mapper:
        mapper.save_cache()

    if args.shard_count > 1:
        logger.info(
            "Shard mode: skipped writing %s (run rebuild_13f_index.py after merging shards).",
            THIRTEEN_F_DIR / "index.json",
        )
    else:
        summary = {
            "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "processed": ok + failed,
            "succeeded": ok,
            "failed": failed,
            "portfolios": index_entries,
        }
        THIRTEEN_F_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = THIRTEEN_F_DIR / "index.json"
        with summary_path.open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        logger.info("Wrote index: %s", summary_path)

    logger.info("Done: %d ok, %d failed.", ok, failed)
    if ok == 0:
        logger.error("No 13F portfolios fetched successfully.")
        return 1
    if failed:
        logger.warning(
            "%d investor(s) failed; continuing with partial data for downstream jobs.",
            failed,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
