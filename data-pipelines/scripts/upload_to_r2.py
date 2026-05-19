#!/usr/bin/env python3
"""
Upload Apex data-lake JSON artifacts from output/ to Cloudflare R2 (S3-compatible API).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import argparse
import logging
from dataclasses import dataclass

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from pipeline_common import (
    FEED_TODAY_PATH,
    MANIFEST_PATH,
    OUTPUT_DIR,
    SP500_GRID_PATH,
    TICKERS_OUTPUT_DIR,
    get_r2_config,
)

DEFAULT_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=60"
JSON_CONTENT_TYPE = "application/json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadTarget:
    local_path: Path
    object_key: str


def build_s3_client(account_id: str, access_key_id: str, secret_access_key: str):
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name="auto",
    )


def upload_file(
    client,
    *,
    bucket: str,
    local_path: Path,
    object_key: str,
    cache_control: str,
    dry_run: bool,
) -> None:
    if not local_path.is_file():
        raise FileNotFoundError(f"Local file not found: {local_path}")

    extra_args = {
        "ContentType": JSON_CONTENT_TYPE,
        "CacheControl": cache_control,
    }

    if dry_run:
        logger.info("[dry-run] Would upload %s → s3://%s/%s", local_path, bucket, object_key)
        return

    client.upload_file(
        Filename=str(local_path),
        Bucket=bucket,
        Key=object_key,
        ExtraArgs=extra_args,
    )
    logger.info("Uploaded %s → s3://%s/%s", local_path.name, bucket, object_key)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload output JSON files to Cloudflare R2")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory containing feed_today.json and sp500_grid.json",
    )
    parser.add_argument(
        "--cache-control",
        default=DEFAULT_CACHE_CONTROL,
        help=f"Cache-Control header (default: {DEFAULT_CACHE_CONTROL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and paths without uploading",
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip files that do not exist instead of failing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        r2 = get_r2_config()
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    prefix = r2["key_prefix"]
    targets: list[UploadTarget] = [
        UploadTarget(FEED_TODAY_PATH, f"{prefix}feed_today.json"),
        UploadTarget(SP500_GRID_PATH, f"{prefix}sp500_grid.json"),
        UploadTarget(MANIFEST_PATH, f"{prefix}manifest.json"),
        UploadTarget(TICKERS_OUTPUT_DIR / "index.json", f"{prefix}tickers/index.json"),
    ]

    if TICKERS_OUTPUT_DIR.is_dir():
        for path in sorted(TICKERS_OUTPUT_DIR.glob("*.json")):
            if path.name == "index.json":
                continue
            ticker = path.stem.upper()
            targets.append(UploadTarget(path, f"{prefix}tickers/{ticker}.json"))

    client = None
    if not args.dry_run:
        client = build_s3_client(
            r2["account_id"],
            r2["access_key_id"],
            r2["secret_access_key"],
        )

    uploaded = 0
    skipped = 0

    for target in targets:
        if not target.local_path.is_file():
            if args.skip_missing:
                logger.warning("Skipping missing file: %s", target.local_path)
                skipped += 1
                continue
            logger.error("Required file missing: %s", target.local_path)
            return 1

        try:
            upload_file(
                client,
                bucket=r2["bucket_name"],
                local_path=target.local_path,
                object_key=target.object_key,
                cache_control=args.cache_control,
                dry_run=args.dry_run,
            )
            uploaded += 1
        except (FileNotFoundError, ClientError, BotoCoreError) as exc:
            logger.error("Upload failed for %s: %s", target.local_path, exc)
            return 1

    logger.info(
        "Done: %d uploaded, %d skipped (dry_run=%s)",
        uploaded,
        skipped,
        args.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
