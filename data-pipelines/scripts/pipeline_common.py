"""Shared paths and env helpers for Apex data-pipelines scripts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_ROOT.parent

CONFIG_DIR = PIPELINE_ROOT / "config"
OUTPUT_DIR = PIPELINE_ROOT / "output"
INVESTORS_PATH = CONFIG_DIR / "investors.json"
FEED_TODAY_PATH = OUTPUT_DIR / "feed_today.json"
SP500_GRID_PATH = OUTPUT_DIR / "sp500_grid.json"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
THIRTEEN_F_DIR = OUTPUT_DIR / "13f"
THIRTEEN_F_BY_CIK_DIR = THIRTEEN_F_DIR / "by_cik"
TICKERS_OUTPUT_DIR = OUTPUT_DIR / "tickers"
CUSIP_CACHE_PATH = CONFIG_DIR / "cusip_ticker_cache.json"
SP500_TICKERS_PATH = CONFIG_DIR / "sp500_tickers.json"

DEFAULT_SEC_USER_AGENT = "Apex_Data_Bot/1.0 (contact@thetamind.ai)"


def load_dotenv_files() -> None:
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(PIPELINE_ROOT / ".env")


def get_sec_user_agent() -> str:
    load_dotenv_files()
    custom = os.environ.get("SEC_USER_AGENT", "").strip()
    return custom or DEFAULT_SEC_USER_AGENT


def get_r2_config() -> dict[str, str]:
    """Load Cloudflare R2 credentials from environment."""
    load_dotenv_files()
    account_id = os.environ.get("R2_ACCOUNT_ID", "").strip()
    access_key = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
    bucket = os.environ.get("R2_BUCKET_NAME", "").strip()
    missing = [
        name
        for name, val in [
            ("R2_ACCOUNT_ID", account_id),
            ("R2_ACCESS_KEY_ID", access_key),
            ("R2_SECRET_ACCESS_KEY", secret_key),
            ("R2_BUCKET_NAME", bucket),
        ]
        if not val
    ]
    if missing:
        raise ValueError(
            f"Missing R2 env vars: {', '.join(missing)}. See .env.example."
        )
    prefix = os.environ.get("R2_KEY_PREFIX", "v1/").strip()
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return {
        "account_id": account_id,
        "access_key_id": access_key,
        "secret_access_key": secret_key,
        "bucket_name": bucket,
        "key_prefix": prefix,
    }


def get_fmp_api_key() -> str:
    load_dotenv_files()
    key = os.environ.get("FMP_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "FMP_API_KEY is not set. Copy .env.example to .env and add your Premium key."
        )
    return key


def load_investors(*, require_cik: bool = True) -> list[dict[str, Any]]:
    with INVESTORS_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    investors = payload.get("investors", [])
    if not investors:
        raise ValueError(f"No investors found in {INVESTORS_PATH}")
    if require_cik:
        investors = [i for i in investors if i.get("cik")]
    return investors


def normalize_cik(cik: str) -> str:
    """10-digit zero-padded CIK for SEC submissions API."""
    digits = "".join(ch for ch in cik if ch.isdigit())
    return digits.zfill(10)


def cik_for_edgar_path(cik: str) -> str:
    """CIK without leading zeros for Archives/edgar/data/{cik}/ paths."""
    return str(int(normalize_cik(cik)))


def accession_no_dashes(accession: str) -> str:
    return accession.replace("-", "")
