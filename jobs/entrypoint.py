from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone


def _count_urls(csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "url" not in reader.fieldnames:
            return 0
        return sum(1 for _ in reader)


def _upload_dir_to_gcs(local_dir: Path, bucket: str, prefix: str) -> None:
    try:
        from google.cloud import storage  # type: ignore
    except Exception as e:
        print(f"google-cloud-storage not installed; skipping GCS upload: {e}")
        return
    client = storage.Client()
    b = client.bucket(bucket)
    for p in local_dir.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(local_dir)
        blob_name = f"{prefix.rstrip('/')}/{rel.as_posix()}"
        blob = b.blob(blob_name)
        blob.upload_from_filename(str(p))
        print(f"Uploaded {p} to gs://{bucket}/{blob_name}")


def main() -> int:
    task_index = int(os.getenv("CLOUD_RUN_TASK_INDEX", "0"))
    task_count = int(os.getenv("CLOUD_RUN_TASK_COUNT", "1"))
    job_name = os.getenv("CLOUD_RUN_JOB", "rightmove-job")
    execution = os.getenv("CLOUD_RUN_EXECUTION") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    shards_dir = Path(os.getenv("SHARDS_DIR", "/app/shards"))
    # Optional rerun mapping: comma-separated indices of original shards to execute in this job
    # Example: RERUN_INDEXES="1,7,9,10,..." (1-based) or "0,6,8,9,..." (0-based)
    rerun_env = os.getenv("RERUN_INDEXES")
    effective_index = task_index
    if rerun_env:
        try:
            parts = [int(x.strip()) for x in rerun_env.split(",") if x.strip()]
        except Exception:
            print(f"Invalid RERUN_INDEXES value: {rerun_env}")
            return 1
        if not parts:
            print("RERUN_INDEXES provided but empty after parsing")
            return 1
        # Infer base: if there is any 0 then treat as 0-based; otherwise assume 1-based
        is_one_based = (0 not in parts)
        if effective_index >= len(parts):
            print(f"task_index {task_index} out of range for RERUN_INDEXES (len={len(parts)})")
            return 0
        mapped = parts[effective_index]
        if is_one_based:
            mapped -= 1
        if mapped < 0:
            print(f"Mapped shard index became negative after base adjustment: {mapped}")
            return 1
        effective_index = mapped
        print(f"Rerun mapping active: task_index={task_index} -> shard_index={effective_index}")

    shard_path = shards_dir / f"shard_{effective_index:02d}.csv"
    if not shard_path.exists():
        print(f"Shard not found for task_index={task_index}: {shard_path}")
        return 0

    out_base = Path(os.getenv("OUTPUT_DIR", "/workspace/out"))
    task_out = out_base / f"task_{task_index:02d}"
    task_out.mkdir(parents=True, exist_ok=True)

    num_urls = _count_urls(shard_path)
    if num_urls <= 0:
        print(f"No URLs in shard {shard_path}; exiting.")
        return 0

    scrape_concurrency = int(os.getenv("SCRAPE_CONCURRENCY", "1"))
    timeout = int(os.getenv("REQUEST_TIMEOUT", "45"))

    cmd = [
        sys.executable,
        "-m",
        "rightmove_scraper.cli",
        "scrape-seeds",
        "--input",
        str(shard_path),
        "--out",
        str(task_out),
        "--format",
        "csv",
        "--max",
        str(num_urls),
        "--concurrency",
        str(scrape_concurrency),
        "--timeout",
        str(timeout),
        "--batch-size",
        "100",
    ]

    # Default to headless unless explicitly overridden
    env = os.environ.copy()
    env.setdefault("HEADLESS", "true")

    print(f"Starting task {task_index+1}/{task_count} using shard {shard_path}")
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print(f"Scrape process exited with code {result.returncode}")
        return result.returncode

    bucket = os.getenv("GCS_BUCKET")
    if bucket:
        prefix = f"rightmove/listings/{job_name}/exec_{execution}/task_{task_index:02d}"
        _upload_dir_to_gcs(task_out, bucket, prefix)
    else:
        print("GCS_BUCKET not set; results remain in container filesystem and will be ephemeral.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


