#!/usr/bin/env python3
"""Apply CORS policy to Cloudflare R2 bucket from infrastructure/r2-cors.json."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import json

import boto3

from pipeline_common import REPO_ROOT, get_r2_config

CORS_FILE = REPO_ROOT / "infrastructure" / "r2-cors.json"


def main() -> int:
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
    client.put_bucket_cors(Bucket=r2["bucket_name"], CORSConfiguration=cors)
    print(f"Applied CORS to bucket {r2['bucket_name']} from {CORS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
