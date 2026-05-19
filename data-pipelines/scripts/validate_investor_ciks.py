#!/usr/bin/env python3
"""Validate investor CIKs against SEC submissions (13F-HR present)."""

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

import requests

from fetch_13f_sec import find_latest_13f_hr
from pipeline_common import CONFIG_DIR, get_sec_user_agent, load_investors, normalize_cik

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


def validate_cik(session: requests.Session, cik: str) -> tuple[bool, str]:
    url = SEC_SUBMISSIONS_URL.format(cik=normalize_cik(cik))
    resp = session.get(url, timeout=30)
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    data = resp.json()
    filing = find_latest_13f_hr(data)
    if not filing:
        return False, "no 13F-HR"
    return True, filing.get("filingDate", "ok")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix-map", action="store_true", help="Write validation report only")
    parser.add_argument("-o", type=Path, default=CONFIG_DIR / "cik_validation_report.json")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": get_sec_user_agent(), "Accept": "application/json"})

    investors = load_investors()
    results: list[dict] = []
    invalid: list[str] = []

    for inv in investors:
        cik = inv.get("cik")
        if not cik:
            invalid.append(inv.get("dataromaCode", "?"))
            results.append({"investor": inv, "valid": False, "reason": "missing cik"})
            continue
        ok, reason = validate_cik(session, cik)
        results.append(
            {
                "cik": normalize_cik(cik),
                "dataromaCode": inv.get("dataromaCode"),
                "firm": inv.get("firm"),
                "valid": ok,
                "detail": reason,
            }
        )
        if not ok:
            invalid.append(inv.get("dataromaCode", cik))
        time.sleep(0.12)

    report = {
        "total": len(investors),
        "valid": sum(1 for r in results if r.get("valid")),
        "invalidCodes": invalid,
        "results": results,
    }
    args.o.parent.mkdir(parents=True, exist_ok=True)
    with args.o.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    logger.info("Valid %d/%d — report %s", report["valid"], report["total"], args.o)
    return 0 if not invalid else 1


if __name__ == "__main__":
    sys.exit(main())
