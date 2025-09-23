from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Mapping
import tempfile

from .local import write_local


def write_gcs(rows: Iterable[Mapping], *, bucket_uri: str | None = None, prefix: str = "", filename: str = "listings.csv", format: str = "csv") -> str:
    """Write rows to a temp file locally, then upload to a GCS bucket.

    bucket_uri accepts either gs://BUCKET or gs://BUCKET/path. This function requires
    google-cloud-storage at runtime. If not installed or creds missing, it raises a helpful error.
    """
    bucket_uri = bucket_uri or os.getenv("GCS_BUCKET")
    if not bucket_uri:
        raise RuntimeError("GCS bucket not provided. Set GCS_BUCKET env or pass bucket_uri.")

    if not bucket_uri.startswith("gs://"):
        raise ValueError("bucket_uri must start with gs://")

    # Write temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, filename)
        write_local(rows, output_path=local_path, format=format)

        # Upload
        try:
            from google.cloud import storage  # type: ignore
        except Exception as e:
            raise RuntimeError("google-cloud-storage not installed. pip install google-cloud-storage") from e

        client = storage.Client()
        # Parse bucket and optional path
        bucket_parts = bucket_uri[len("gs://"):].split("/", 1)
        bucket_name = bucket_parts[0]
        base = bucket_parts[1] if len(bucket_parts) > 1 else ""
        blob_path = "/".join([p for p in [base, prefix.strip("/") if prefix else "", filename] if p])

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(local_path)
        return f"gs://{bucket_name}/{blob_path}"


