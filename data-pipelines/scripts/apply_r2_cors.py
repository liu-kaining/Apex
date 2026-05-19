#!/usr/bin/env python3
"""Apply CORS policy to Cloudflare R2 bucket from infrastructure/r2-cors.json."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import argparse
import json
import logging

import boto3
from botocore.exceptions import ClientError

from pipeline_common import REPO_ROOT, get_r2_config

CORS_FILE = REPO_ROOT / "infrastructure" / "r2-cors.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CORS_TOKEN_HELP = """
PutBucketCors requires an R2 API token with **Admin Read & Write** (not Object Read & Write only).

Fix (pick one):
  A) Cloudflare Dashboard → R2 → your bucket → Settings → CORS Policy → paste JSON from:
     infrastructure/r2-cors.json
     Then Purge Cache for apex-data.thetamind.ai

  B) R2 → Manage API Tokens → Create token → Admin Read & Write (this bucket)
     Update GitHub Secrets: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
     Re-run this step.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply R2 bucket CORS from infrastructure/r2-cors.json")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Log failure but exit 0 (for CI when token cannot edit bucket policy)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r2 = get_r2_config()
    with CORS_FILE.open(encoding="utf-8") as fh:
        cors = json.load(fh)

    client = boto3.client(
        "s3",
        endpoint_url=f"https://{r2['account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=r2["access_key_id"],
        aws_secret_access_key=r2["secret_access_key"],
        region_name="auto",
    )
    try:
        client.put_bucket_cors(Bucket=r2["bucket_name"], CORSConfiguration=cors)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("AccessDenied", "AccessDeniedException"):
            logger.error("Access denied for PutBucketCors on bucket %s.", r2["bucket_name"])
            logger.error(CORS_TOKEN_HELP)
            if args.warn_only:
                logger.warning("Continuing (--warn-only); configure CORS in dashboard manually.")
                return 0
            return 1
        raise

    print(f"Applied CORS to bucket {r2['bucket_name']} from {CORS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
