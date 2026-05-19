#!/usr/bin/env python3
"""
Sync superinvestor whitelist from Dataroma into config/investors.json.

Source: https://www.dataroma.com/m/home.php (tracks 80 superinvestor portfolios)
CIK map: config/dataroma_cik_map.json (SEC 13F filer IDs)
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import requests

DATAROMA_HOME = "https://www.dataroma.com/m/home.php"
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
INVESTORS_PATH = CONFIG_DIR / "investors.json"
CIK_MAP_PATH = CONFIG_DIR / "dataroma_cik_map.json"

LINK_RE = re.compile(
    r'href="/m/holdings\.php\?m=([^"]+)"[^>]*>([^<]+)<span class="portb">\s*Updated',
    re.IGNORECASE,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_cik_map() -> dict[str, str]:
    with CIK_MAP_PATH.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def fetch_dataroma_managers() -> list[tuple[str, str]]:
    resp = requests.get(
        DATAROMA_HOME,
        headers={"User-Agent": "Apex-ETL/1.0 (research; sync investors)"},
        timeout=30,
    )
    resp.raise_for_status()
    matches = LINK_RE.findall(resp.text)
    if len(matches) < 70:
        raise RuntimeError(f"Expected ~80 managers, parsed {len(matches)}")
    return [(code.strip(), unquote(name.strip())) for code, name in matches]


def parse_display_name(full: str) -> tuple[str | None, str]:
    if " - " in full:
        manager, firm = full.split(" - ", 1)
        return manager.strip(), firm.strip()
    return None, full.strip()


def build_investors(
    managers: list[tuple[str, str]],
    cik_map: dict[str, str],
) -> dict:
    investors: list[dict] = []
    missing_cik: list[str] = []

    for code, display in managers:
        manager, firm = parse_display_name(display)
        cik = cik_map.get(code)
        if not cik:
            missing_cik.append(code)

        entry: dict = {
            "dataromaCode": code,
            "displayName": display,
            "firm": firm,
            "cik": cik,
        }
        if manager:
            entry["manager"] = manager
        investors.append(entry)

    if missing_cik:
        logger.warning(
            "No CIK in dataroma_cik_map.json for: %s — add entries and re-run.",
            ", ".join(missing_cik),
        )

    return {
        "source": DATAROMA_HOME,
        "description": (
            "Superinvestor whitelist (Rule 1) aligned with Dataroma's 80 tracked portfolios. "
            "Use dataromaCode for cross-reference; cik for SEC EDGAR 13F and FMP institutional APIs."
        ),
        "lastSynced": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(investors),
        "investors": investors,
    }


def main() -> int:
    try:
        cik_map = load_cik_map()
        managers = fetch_dataroma_managers()
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Config error: %s", exc)
        return 1
    except requests.RequestException as exc:
        logger.error("Failed to fetch Dataroma: %s", exc)
        return 1

    if len(managers) != 80:
        logger.warning("Dataroma returned %d managers (expected 80).", len(managers))

    payload = build_investors(managers, cik_map)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with INVESTORS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    with_cik = sum(1 for i in payload["investors"] if i.get("cik"))
    logger.info(
        "Wrote %d investors (%d with CIK) to %s",
        payload["count"],
        with_cik,
        INVESTORS_PATH,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
