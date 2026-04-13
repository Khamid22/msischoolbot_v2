"""
Re-process all existing video resources in R2 to add the +faststart flag.

Without faststart the browser must download the entire file before it can
start playing. This script remuxes each video in-place (same R2 key,
no re-encoding) using ffmpeg so the moov atom moves to the front.

Usage (run from the project root):
    python scripts/faststart_existing_videos.py

Dry-run (shows what would be processed without changing anything):
    python scripts/faststart_existing_videos.py --dry-run
"""

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

# ── Load .env ──────────────────────────────────────────────────────────────────

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOTENV_PATH = os.path.join(_PROJECT_ROOT, ".env")


def _load_dotenv(path):
    if not os.path.isfile(path):
        return
    with open(path) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv(_DOTENV_PATH)

# ── Add project root to sys.path so we can import app modules ─────────────────

sys.path.insert(0, _PROJECT_ROOT)

# ── Imports after path setup ───────────────────────────────────────────────────

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    print("ERROR: boto3 is not installed. Run: pip install boto3")
    sys.exit(1)


# ── R2 helpers (mirrors r2_storage_service.py) ────────────────────────────────

def _env(name, default=""):
    return str(os.environ.get(name, default) or "").strip()


def _endpoint_url():
    explicit = _env("R2_ENDPOINT_URL")
    if explicit:
        return explicit
    account_id = _env("R2_ACCOUNT_ID")
    if not account_id:
        return ""
    return f"https://{account_id}.r2.cloudflarestorage.com"


def _build_r2_client():
    endpoint = _endpoint_url()
    if not endpoint:
        return None
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("R2_SECRET_ACCESS_KEY"),
        region_name=_env("R2_REGION", "auto"),
    )


def _bucket():
    return _env("R2_BUCKET_NAME")


_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}


def _file_ext(key):
    dot = key.rfind(".")
    return key[dot:].lower() if dot > 0 else ""


def _cache_control():
    v = _env("R2_CACHE_CONTROL") or _env("RESOURCE_CACHE_CONTROL")
    return v or "public, max-age=31536000, immutable"


# ── DB helpers ────────────────────────────────────────────────────────────────

def _connect_db():
    database_url = _env("DATABASE_URL") or _env("POSTGRES_URL")
    if database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
        try:
            import psycopg
            conn = psycopg.connect(database_url)
            conn.autocommit = False
            return conn, "postgres"
        except ImportError:
            print("ERROR: psycopg not installed for PostgreSQL.")
            sys.exit(1)

    # SQLite fallback
    db_path = _env("AUTH_DB_PATH") or os.path.join(_PROJECT_ROOT, "utils", "app_data.sqlite3")
    if not os.path.isfile(db_path):
        print(f"ERROR: SQLite database not found at {db_path}")
        sys.exit(1)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def _list_video_resources(conn, backend):
    placeholder = "%s" if backend == "postgres" else "?"
    sql = f"""
        SELECT r.id, r.resource_file_path, r.title
        FROM resources r
        WHERE trim(coalesce(r.resource_file_path, '')) <> ''
          AND r.is_active = 1
        ORDER BY r.id ASC
    """
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    # Filter to video extensions
    return [
        {"id": row[0], "resource_file_path": row[1], "title": row[2]}
        for row in rows
        if _file_ext(str(row[1])) in _VIDEO_EXTENSIONS
    ]


def _update_resource_updated_at(conn, backend, resource_id, now):
    placeholder = "%s" if backend == "postgres" else "?"
    conn.execute(
        f"UPDATE resources SET updated_at = {placeholder} WHERE id = {placeholder}",
        (now, resource_id),
    )
    conn.commit()


# ── ffmpeg faststart remux ────────────────────────────────────────────────────

def _ffmpeg():
    return shutil.which("ffmpeg") or ""


def _remux_faststart(payload, source_ext, ffmpeg_path, timeout=120):
    """
    Stream-copy the video payload into a new MP4 container with +faststart.
    Returns (new_payload_bytes, ".mp4") on success, or (None, error_message) on failure.
    """
    input_tmp = output_tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=source_ext) as f:
            input_tmp = f.name
            f.write(payload)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            output_tmp = f.name

        result = subprocess.run(
            [
                ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
                "-i", input_tmp,
                "-map", "0:v:0", "-map", "0:a?",
                "-c", "copy",
                "-movflags", "+faststart",
                output_tmp,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace").strip()
            return None, f"ffmpeg error (code {result.returncode}): {err[:200]}"

        with open(output_tmp, "rb") as f:
            out = f.read()
        if not out:
            return None, "ffmpeg produced empty output"
        return out, None
    except subprocess.TimeoutExpired:
        return None, "ffmpeg timed out"
    except Exception as exc:
        return None, str(exc)
    finally:
        for p in (input_tmp, output_tmp):
            if p:
                try:
                    os.remove(p)
                except OSError:
                    pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Re-process existing videos with ffmpeg +faststart")
    parser.add_argument("--dry-run", action="store_true", help="List videos without processing them")
    args = parser.parse_args()
    dry_run = args.dry_run

    # Check ffmpeg
    ffmpeg_path = _ffmpeg()
    if not ffmpeg_path:
        print("ERROR: ffmpeg is not installed or not in PATH.")
        sys.exit(1)
    print(f"ffmpeg: {ffmpeg_path}")

    # Connect R2
    r2 = _build_r2_client()
    if r2 is None:
        print("ERROR: R2 is not configured. Check R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME.")
        sys.exit(1)
    bucket = _bucket()
    print(f"R2 bucket: {bucket}")

    # Connect DB
    conn, backend = _connect_db()
    print(f"DB backend: {backend}\n")

    # Find video resources
    videos = _list_video_resources(conn, backend)
    if not videos:
        print("No video resources found in the database.")
        return

    print(f"Found {len(videos)} video resource(s):\n")
    for v in videos:
        print(f"  [{v['id']}] {v['title']!r}  →  {v['resource_file_path']}")
    print()

    if dry_run:
        print("Dry-run mode — no changes made.")
        return

    confirm = input(f"Re-process {len(videos)} video(s)? This overwrites the R2 files in-place. [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    from datetime import datetime
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    ok_count = 0
    fail_count = 0

    for idx, v in enumerate(videos, start=1):
        key = v["resource_file_path"]
        title = v["title"]
        rid = v["id"]
        ext = _file_ext(key)
        print(f"[{idx}/{len(videos)}] ID={rid} — {title!r}")

        # Download
        print(f"  Downloading from R2 ({key})...")
        try:
            resp = r2.get_object(Bucket=bucket, Key=key)
            payload = resp["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            print(f"  SKIP — download failed: {exc}\n")
            fail_count += 1
            continue

        original_size = len(payload)
        print(f"  Downloaded {original_size / 1024 / 1024:.1f} MB — running ffmpeg faststart remux...")

        # Remux
        new_payload, err = _remux_faststart(payload, ext, ffmpeg_path)
        if err:
            print(f"  SKIP — ffmpeg failed: {err}\n")
            fail_count += 1
            continue

        new_size = len(new_payload)
        print(f"  Remuxed: {original_size / 1024 / 1024:.1f} MB → {new_size / 1024 / 1024:.1f} MB — uploading...")

        # Re-upload (same key, overwrite)
        content_type = "video/mp4"
        try:
            r2.put_object(
                Bucket=bucket,
                Key=key,
                Body=new_payload,
                ContentType=content_type,
                ContentDisposition=f'inline; filename="{os.path.basename(key)}"',
                CacheControl=_cache_control(),
            )
        except (BotoCoreError, ClientError) as exc:
            print(f"  SKIP — upload failed: {exc}\n")
            fail_count += 1
            continue

        # Update updated_at in DB so cache-busting works
        try:
            _update_resource_updated_at(conn, backend, rid, now_iso)
        except Exception as exc:
            print(f"  WARNING — DB update failed: {exc}")

        print(f"  Done.\n")
        ok_count += 1

    conn.close()
    print(f"Finished — {ok_count} processed, {fail_count} failed.")


if __name__ == "__main__":
    main()
