import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote

boto3 = None
_S3TransferConfig = None
BotocoreConfig = None
BotoCoreError = Exception
ClientError = Exception
_BOTO3_IMPORT_ATTEMPTED = False


def _ensure_boto3():
    global boto3, _S3TransferConfig, BotocoreConfig, BotoCoreError, ClientError
    global _BOTO3_IMPORT_ATTEMPTED
    if _BOTO3_IMPORT_ATTEMPTED:
        return boto3 is not None
    _BOTO3_IMPORT_ATTEMPTED = True
    if not _r2_enabled():
        return False
    try:
        import boto3 as _boto3
        from boto3.s3.transfer import TransferConfig as transfer_config
        from botocore.config import Config as botocore_config
        from botocore.exceptions import BotoCoreError as boto_core_error, ClientError as client_error
    except Exception:  # pragma: no cover - optional dependency guard
        return False
    boto3 = _boto3
    _S3TransferConfig = transfer_config
    BotocoreConfig = botocore_config
    BotoCoreError = boto_core_error
    ClientError = client_error
    return True

_R2_LOCK = threading.Lock()
_R2_CLIENT = None
_SIGNED_URL_CACHE_LOCK = threading.Lock()
_SIGNED_URL_CACHE = {}
_FFMPEG_MISSING_LOGGED = False

_ALLOWED_RESOURCE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".txt", ".csv", ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".mp4", ".mov", ".m4v", ".mp3", ".wav", ".zip",
}

_RESOURCE_EXTENSION_MIME_MAP = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".zip": "application/zip",
}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}

_ALLOWED_CANDIDATE_DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png",
}
_CANDIDATE_DOCUMENT_MAX_BYTES = 20 * 1024 * 1024


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _env(name, default=""):
    return str(os.environ.get(name, default) or "").strip()


def _is_false_like(value):
    return str(value or "").strip().lower() in {"0", "false", "no", "off"}


def _r2_enabled():
    return not _is_false_like(_env("R2_ENABLED", "1"))


def _required_r2_env():
    return {
        "R2_ACCOUNT_ID": _env("R2_ACCOUNT_ID"),
        "R2_ACCESS_KEY_ID": _env("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": _env("R2_SECRET_ACCESS_KEY"),
        "R2_BUCKET_NAME": _env("R2_BUCKET_NAME"),
    }


# ---------------------------------------------------------------------------
# Slug / name helpers
# ---------------------------------------------------------------------------

def _normalize(value):
    return " ".join(str(value or "").strip().casefold().split())


def _slugify(value):
    normalized = _normalize(value)
    if not normalized:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def _folder_slug_segments(folder_path):
    raw_value = str(folder_path or "").strip()
    if not raw_value:
        return []
    segments = []
    for part in re.split(r"[\\/]+", raw_value):
        segment_slug = _slugify(part)
        if segment_slug:
            segments.append(segment_slug)
    return segments


def _safe_file_name(name):
    lowered = str(name or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9._-]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-.")
    return lowered or "resource"


def _file_extension(value):
    text = str(value or "").strip().lower()
    dot_index = text.rfind(".")
    if dot_index <= 0:
        return ""
    return text[dot_index:]


def infer_resource_mime_type(file_name_or_key):
    extension = _file_extension(file_name_or_key)
    return _RESOURCE_EXTENSION_MIME_MAP.get(extension, "")


# ---------------------------------------------------------------------------
# Upload / video configuration (all env-overridable)
# ---------------------------------------------------------------------------

def _max_upload_bytes():
    """Max resource file size. Default 1 GB; hard cap 4 GB."""
    raw = _env("RESOURCE_UPLOAD_MAX_MB", "1024")
    try:
        mb = int(raw)
    except ValueError:
        mb = 1024
    return max(1, min(mb, 4096)) * 1024 * 1024


def _video_optimize_enabled():
    return not _is_false_like(_env("RESOURCE_VIDEO_OPTIMIZE", "1"))


def _video_optimize_timeout_seconds():
    raw = _env("RESOURCE_VIDEO_OPTIMIZE_TIMEOUT_SECONDS", "600")
    try:
        s = int(raw)
    except ValueError:
        s = 600
    return max(60, min(s, 3600))


def _video_faststart_timeout_seconds():
    raw = _env("RESOURCE_VIDEO_FASTSTART_TIMEOUT_SECONDS", "120")
    try:
        s = int(raw)
    except ValueError:
        s = 120
    return max(10, min(s, 600))


def _video_max_width():
    raw = _env("RESOURCE_VIDEO_MAX_WIDTH", "960")
    try:
        w = int(raw)
    except ValueError:
        w = 960
    return max(320, min(w, 3840))


def _video_crf():
    raw = _env("RESOURCE_VIDEO_CRF", "28")
    try:
        crf = int(raw)
    except ValueError:
        crf = 28
    return max(18, min(crf, 32))


def _video_preset():
    preset = _env("RESOURCE_VIDEO_PRESET", "veryfast").lower()
    allowed = {
        "ultrafast", "superfast", "veryfast", "faster", "fast",
        "medium", "slow", "slower", "veryslow",
    }
    return preset if preset in allowed else "ultrafast"


def _video_faststart_remux_enabled():
    return not _is_false_like(_env("RESOURCE_VIDEO_FASTSTART_REMUX", "1"))


def _ffmpeg_binary():
    global _FFMPEG_MISSING_LOGGED
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    if not _FFMPEG_MISSING_LOGGED:
        _FFMPEG_MISSING_LOGGED = True
        print(
            "[resources] ffmpeg not found — videos will be uploaded without processing. "
            "Add it via RAILPACK_DEPLOY_APT_PACKAGES=ffmpeg or apt install ffmpeg."
        )
    return ""


def _signed_url_ttl():
    raw = _env("R2_SIGNED_URL_TTL_SECONDS", "21600")
    try:
        s = int(raw)
    except ValueError:
        s = 21600
    return max(60, min(s, 604800))


def _public_base_url():
    raw = (
        _env("R2_PUBLIC_BASE_URL")
        or _env("RESOURCE_PUBLIC_BASE_URL")
        or _env("R2_DEV_PUBLIC_URL")
    )
    if not raw:
        return ""
    normalized = raw.rstrip("/")
    if normalized.startswith(("http://", "https://")):
        return normalized
    return f"https://{normalized}"


def _endpoint_url():
    explicit = _env("R2_ENDPOINT_URL")
    if explicit:
        return explicit
    account_id = _env("R2_ACCOUNT_ID")
    return f"https://{account_id}.r2.cloudflarestorage.com" if account_id else ""


def _r2_connect_timeout_seconds():
    raw = _env("R2_CONNECT_TIMEOUT_SECONDS", "10")
    try:
        s = int(raw)
    except ValueError:
        s = 10
    return max(3, min(s, 60))


def _r2_read_timeout_seconds():
    # Needs to be long enough for a multipart upload of 1 GB+ on slow links.
    raw = _env("R2_READ_TIMEOUT_SECONDS", "300")
    try:
        s = int(raw)
    except ValueError:
        s = 300
    return max(60, min(s, 1800))


def _r2_max_attempts():
    raw = _env("R2_MAX_ATTEMPTS", "3")
    try:
        n = int(raw)
    except ValueError:
        n = 3
    return max(1, min(n, 10))


def _r2_multipart_chunk_bytes():
    """Size of each multipart part. S3 minimum is 5 MB."""
    raw = _env("R2_MULTIPART_CHUNK_MB", "16")
    try:
        mb = int(raw)
    except ValueError:
        mb = 16
    return max(5, min(mb, 128)) * 1024 * 1024


# ---------------------------------------------------------------------------
# R2 client
# ---------------------------------------------------------------------------

def _r2_client_config():
    if not _ensure_boto3():
        return None
    if BotocoreConfig is None:
        return None
    return BotocoreConfig(
        connect_timeout=_r2_connect_timeout_seconds(),
        read_timeout=_r2_read_timeout_seconds(),
        retries={"max_attempts": _r2_max_attempts(), "mode": "standard"},
    )


def is_r2_configured():
    if not _r2_enabled() or not _ensure_boto3() or boto3 is None:
        return False
    return all(_required_r2_env().values()) and bool(_endpoint_url())


def _build_r2_client():
    if not is_r2_configured():
        return None
    client_kwargs = {
        "endpoint_url": _endpoint_url(),
        "aws_access_key_id": _env("R2_ACCESS_KEY_ID"),
        "aws_secret_access_key": _env("R2_SECRET_ACCESS_KEY"),
        "region_name": _env("R2_REGION", "auto"),
    }
    cfg = _r2_client_config()
    if cfg is not None:
        client_kwargs["config"] = cfg
    return boto3.client("s3", **client_kwargs)


def _get_r2_client():
    global _R2_CLIENT
    with _R2_LOCK:
        if _R2_CLIENT is None:
            _R2_CLIENT = _build_r2_client()
        return _R2_CLIENT


def _resource_bucket_name():
    return _env("R2_BUCKET_NAME")


def _cache_control_header():
    configured = _env("R2_CACHE_CONTROL") or _env("RESOURCE_CACHE_CONTROL")
    return configured or "public, max-age=31536000, immutable"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _report_progress(progress_callback, *, percent, stage, message, eta_seconds=None):
    if not callable(progress_callback):
        return
    try:
        progress_callback(
            percent=float(percent),
            stage=str(stage or "").strip(),
            message=str(message or "").strip(),
            eta_seconds=eta_seconds,
        )
    except Exception:
        return


def _build_object_key(subject_name, original_name, folder_path=""):
    now = datetime.now(timezone.utc)
    subject_slug = _slugify(subject_name) or "general"
    folder_slug = "/".join(_folder_slug_segments(folder_path))
    safe_name = _safe_file_name(original_name)
    dot_index = safe_name.rfind(".")
    ext = safe_name[dot_index:] if dot_index > 0 else ""
    stem = safe_name[:dot_index] if dot_index > 0 else safe_name
    unique_token = now.strftime("%Y%m%d%H%M%S%f")
    folder_prefix = f"{folder_slug}/" if folder_slug else ""
    return (
        f"resources/"
        f"{now.strftime('%Y/%m')}/"
        f"{subject_slug}/"
        f"{folder_prefix}"
        f"{stem}-{unique_token}{ext}"
    )


def _build_candidate_document_key(candidate_id, document_type, original_name):
    now = datetime.now(timezone.utc)
    safe_name = _safe_file_name(original_name)
    extension = _file_extension(original_name)
    if extension and not safe_name.endswith(extension):
        safe_name = f"{safe_name or 'document'}{extension}"
    return (
        f"private/recruitment/{int(candidate_id)}/"
        f"{_slugify(document_type) or 'other'}/"
        f"{now.strftime('%Y%m%d%H%M%S%f')}-{safe_name}"
    )


def _build_transfer_config():
    """
    Build a TransferConfig that enables parallel multipart upload.

    boto3 splits the file into chunks of _r2_multipart_chunk_bytes() and
    uploads up to 4 parts concurrently — so a 1 GB file with 16 MB chunks
    (64 parts) uses ~64 MB of peak RAM and uploads 4× faster than a single
    sequential PUT.
    """
    if not _ensure_boto3() or _S3TransferConfig is None:
        return None
    chunk = _r2_multipart_chunk_bytes()
    return _S3TransferConfig(
        multipart_threshold=chunk,
        multipart_chunksize=chunk,
        max_concurrency=4,
        use_threads=True,
    )


# ---------------------------------------------------------------------------
# Video processing  (file-path based — no bytes in Python memory)
# ---------------------------------------------------------------------------

def _process_video_file(input_path, output_path, source_extension):
    """
    Prepare a video for web delivery using ffmpeg, working entirely with files.

    Phase 1 — fast stream-copy remux (MP4/M4V only):
      Moves the moov atom to the front (faststart) without re-encoding.
      Runs in seconds even for a 1 GB file. No quality loss.

    Phase 2 — full H.264 re-encode (all other formats, or when Phase 1 fails):
      Transcodes to H.264 + AAC, scales to max width, adds faststart.
      Slower but universally compatible.

    Returns True when output_path was written successfully.
    Falls back gracefully (returns False) if ffmpeg is missing or times out
    — the caller then uploads the original file unchanged.
    """
    ffmpeg = _ffmpeg_binary()
    if not ffmpeg:
        return False

    # Phase 1: fast remux for MP4/M4V — copy codecs, add faststart moov atom
    if source_extension in {".mp4", ".m4v"} and _video_faststart_remux_enabled():
        try:
            subprocess.run(
                [
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", input_path,
                    "-map", "0:v:0", "-map", "0:a?",
                    "-c", "copy",
                    "-movflags", "+faststart",
                    output_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=_video_faststart_timeout_seconds(),
            )
            if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception:
            pass  # fall through to full re-encode

    # Phase 2: full H.264 re-encode (all formats, or Phase 1 fallback)
    if not _video_optimize_enabled():
        return False

    try:
        subprocess.run(
            [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", input_path,
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", _video_preset(),
                "-crf", str(_video_crf()),
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-vf", f"scale='min({_video_max_width()},iw)':-2",
                "-c:a", "aac", "-b:a", "128k",
                output_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_video_optimize_timeout_seconds(),
        )
        return os.path.isfile(output_path) and os.path.getsize(output_path) > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# R2 streaming upload
# ---------------------------------------------------------------------------

def _upload_file_to_r2(
    client,
    *,
    bucket,
    object_key,
    file_path,
    content_type,
    safe_name,
    progress_callback=None,
    start_pct=75.0,
    end_pct=97.0,
):
    """
    Stream a file from disk to R2 using multipart upload.

    boto3's upload_fileobj reads one chunk at a time from the open file handle
    and uploads parts in parallel.  Peak RAM = one chunk (~16 MB) regardless of
    file size — a 1 GB upload uses the same memory as a 1 MB one.
    """
    file_size = os.path.getsize(file_path)
    extra_args = {
        "ContentType": content_type,
        "ContentDisposition": f'inline; filename="{safe_name}"',
        "CacheControl": _cache_control_header(),
    }

    bytes_sent = [0]

    def _on_chunk(chunk_bytes):
        bytes_sent[0] += chunk_bytes
        ratio = min(bytes_sent[0] / file_size, 1.0) if file_size > 0 else 0.5
        _report_progress(
            progress_callback,
            percent=start_pct + ratio * (end_pct - start_pct),
            stage="cloud_upload",
            message="Uploading to storage...",
        )

    config = _build_transfer_config()
    upload_kwargs = {"ExtraArgs": extra_args, "Callback": _on_chunk}
    if config is not None:
        upload_kwargs["Config"] = config

    with open(file_path, "rb") as fh:
        client.upload_fileobj(fh, bucket, object_key, **upload_kwargs)


# ---------------------------------------------------------------------------
# Public upload functions
# ---------------------------------------------------------------------------

def upload_resource_file(
    uploaded_file,
    subject_name="",
    folder_path="",
    progress_callback=None,
):
    """
    Receive, optionally process, and stream-upload a resource file to R2.

    Memory model
    ------------
    1. werkzeug stream → disk temp file via uploaded_file.save()
       (sequential write, ~16 KB buffer — safe for 1 GB)
    2. Optional ffmpeg processing: reads from disk, writes to another temp file
       (no Python bytes object for the video content)
    3. R2 upload via upload_fileobj + TransferConfig: 4 parallel parts,
       ~16 MB chunk buffer — peak RAM is one chunk regardless of file size.

    All temp files are cleaned up in a finally block.
    """
    upload_started_at = time.time()

    if not uploaded_file or not str(uploaded_file.filename or "").strip():
        return "", "No file was uploaded."
    if not is_r2_configured():
        return "", "R2 storage is not configured."

    original_name = str(uploaded_file.filename or "").strip()
    # Extract extension from the original name before _safe_file_name can strip it.
    # Non-ASCII stems (e.g. Cyrillic/Uzbek filenames) become all dashes then get
    # stripped along with the leading dot, losing the extension entirely.
    extension = _file_extension(original_name.lower())
    if extension not in _ALLOWED_RESOURCE_EXTENSIONS:
        return "", "File type is not supported for resources."
    safe_name = _safe_file_name(original_name)
    # Restore the extension if _safe_file_name dropped it (non-ASCII stem case).
    if not safe_name.endswith(extension):
        safe_name = (safe_name or "resource") + extension

    max_bytes = _max_upload_bytes()
    _report_progress(progress_callback, percent=5.0, stage="receiving", message="Receiving uploaded file...")

    input_temp = None
    output_temp = None

    try:
        # --- Step 1: write werkzeug stream to a temp file on disk ---
        # uploaded_file.save() uses shutil.copyfileobj with a 16 KB buffer,
        # so the full file never enters Python memory.
        fd, input_temp = tempfile.mkstemp(suffix=extension)
        os.close(fd)
        uploaded_file.save(input_temp)

        file_size = os.path.getsize(input_temp)
        if file_size == 0:
            return "", "Uploaded file is empty."
        if file_size > max_bytes:
            mb = max_bytes // (1024 * 1024)
            return "", f"File too large. Max upload size is {mb} MB."

        _report_progress(
            progress_callback,
            percent=28.0,
            stage="received",
            message=f"File received ({file_size / (1024 * 1024):.1f} MB).",
        )

        # --- Step 2: optional video processing (file → file, no RAM spike) ---
        upload_path = input_temp
        if extension in _VIDEO_EXTENSIONS:
            _report_progress(
                progress_callback,
                percent=32.0,
                stage="video",
                message="Preparing video for web playback...",
            )
            fd2, output_temp = tempfile.mkstemp(suffix=".mp4")
            os.close(fd2)

            if _process_video_file(input_temp, output_temp, extension):
                upload_path = output_temp
                extension = ".mp4"
                dot_index = safe_name.rfind(".")
                stem = safe_name[:dot_index] if dot_index > 0 else safe_name
                safe_name = f"{stem}.mp4"
                _report_progress(
                    progress_callback,
                    percent=72.0,
                    stage="video",
                    message="Video optimized.",
                )
            else:
                _report_progress(
                    progress_callback,
                    percent=72.0,
                    stage="video",
                    message="Uploading original video.",
                )

        # --- Step 3: stream-upload to R2 via parallel multipart ---
        content_type = (
            infer_resource_mime_type(safe_name)
            or str(uploaded_file.mimetype or "").strip()
            or "application/octet-stream"
        )
        object_key = _build_object_key(subject_name, safe_name, folder_path=folder_path)
        client = _get_r2_client()
        if client is None:
            return "", "Unable to connect to R2 storage."

        _report_progress(
            progress_callback,
            percent=75.0,
            stage="cloud_upload",
            message="Starting upload to storage...",
        )

        try:
            _upload_file_to_r2(
                client,
                bucket=_resource_bucket_name(),
                object_key=object_key,
                file_path=upload_path,
                content_type=content_type,
                safe_name=safe_name,
                progress_callback=progress_callback,
                start_pct=75.0,
                end_pct=97.0,
            )
        except Exception:
            elapsed = round(time.time() - upload_started_at, 1)
            print(
                "[resources] R2 upload failed",
                {"file": safe_name, "bytes": file_size, "elapsed_s": elapsed},
            )
            return "", "Failed to upload resource file to R2."

        upload_size = os.path.getsize(upload_path)
        elapsed = round(time.time() - upload_started_at, 1)
        print(
            "[resources] R2 upload complete",
            {"file": safe_name, "bytes": upload_size, "elapsed_s": elapsed},
        )
        _report_progress(progress_callback, percent=97.0, stage="done", message="Upload complete.")
        return object_key, ""

    finally:
        for tmp_path in (input_temp, output_temp):
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# Thumbnail upload (small files — in-memory read is acceptable at ≤5 MB)
# ---------------------------------------------------------------------------

_ALLOWED_THUMBNAIL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_THUMBNAIL_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _read_limited_bytes(uploaded_file, limit_bytes):
    """Read a small file entirely into memory. Use only for thumbnails."""
    stream = uploaded_file.stream
    try:
        stream.seek(0)
    except Exception:
        pass

    total = 0
    chunks = []
    while True:
        chunk = stream.read(256 * 1024)  # 256 KB
        if not chunk:
            break
        total += len(chunk)
        if total > limit_bytes:
            return None, total
        chunks.append(chunk)

    return b"".join(chunks), total


def upload_thumbnail_file(uploaded_file, subject_name="", folder_path=""):
    if not uploaded_file or not str(uploaded_file.filename or "").strip():
        return "", "No thumbnail was uploaded."
    if not is_r2_configured():
        return "", "R2 storage is not configured."

    original_name = str(uploaded_file.filename or "").strip()
    safe_name = _safe_file_name(original_name)
    extension = _file_extension(safe_name)
    if extension not in _ALLOWED_THUMBNAIL_EXTENSIONS:
        return "", "Thumbnail must be a JPG, PNG, or WebP image."

    payload, payload_size = _read_limited_bytes(uploaded_file, _THUMBNAIL_MAX_BYTES)
    if payload is None:
        return "", "Thumbnail image is too large (max 5 MB)."
    if payload_size <= 0:
        return "", "Thumbnail image is empty."

    content_type = infer_resource_mime_type(safe_name) or "image/jpeg"
    object_key = _build_object_key(subject_name, f"thumb-{safe_name}", folder_path=folder_path)
    client = _get_r2_client()
    if client is None:
        return "", "Unable to connect to R2 storage."

    try:
        extra_args = {
            "ContentType": content_type,
            "ContentDisposition": f'inline; filename="{safe_name}"',
            "CacheControl": _cache_control_header(),
        }
        client.put_object(
            Bucket=_resource_bucket_name(),
            Key=object_key,
            Body=payload,
            **extra_args,
        )
    except Exception:
        return "", "Failed to upload thumbnail to R2."

    return object_key, ""


# ---------------------------------------------------------------------------
# Signed URL / public URL
# ---------------------------------------------------------------------------

def build_resource_file_url(resource_file_path):
    object_key = str(resource_file_path or "").strip()
    if not object_key:
        return ""

    public_base = _public_base_url()
    if public_base:
        escaped_key = quote(object_key, safe="/-_.~")
        return f"{public_base}/{escaped_key}"

    if not is_r2_configured():
        return ""

    client = _get_r2_client()
    if client is None:
        return ""

    now = time.time()
    with _SIGNED_URL_CACHE_LOCK:
        cached = _SIGNED_URL_CACHE.get(object_key)
        if cached and now < float(cached.get("expires_at", 0)) - 15:
            cached_url = str(cached.get("url", "")).strip()
            if cached_url:
                return cached_url

    response_content_type = infer_resource_mime_type(object_key)
    file_name = _safe_file_name(
        object_key.split("/")[-1] if "/" in object_key else object_key
    ) or "resource"
    ttl_seconds = _signed_url_ttl()
    params = {
        "Bucket": _resource_bucket_name(),
        "Key": object_key,
        "ResponseContentDisposition": f'inline; filename="{file_name}"',
        "ResponseCacheControl": _cache_control_header(),
    }
    if response_content_type:
        params["ResponseContentType"] = response_content_type

    try:
        signed_url = client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=ttl_seconds,
        )
        with _SIGNED_URL_CACHE_LOCK:
            _SIGNED_URL_CACHE[object_key] = {
                "url": signed_url,
                "expires_at": now + ttl_seconds,
            }
        return signed_url
    except (BotoCoreError, ClientError):
        return ""


def upload_private_candidate_document(uploaded_file, *, candidate_id, document_type):
    """Upload a small, private candidate document without exposing a public URL."""
    original_name = str(getattr(uploaded_file, "filename", "") or "").strip()
    if not original_name:
        return {}, "No file was uploaded."
    extension = _file_extension(original_name)
    if extension not in _ALLOWED_CANDIDATE_DOCUMENT_EXTENSIONS:
        return {}, "Candidate documents must be PDF, DOC, DOCX, JPG, or PNG files."
    if not is_r2_configured():
        return {}, "Private document storage is not configured."

    stream = getattr(uploaded_file, "file", None) or getattr(uploaded_file, "stream", None)
    if stream is None:
        return {}, "Unable to read the uploaded file."
    try:
        stream.seek(0)
    except Exception:
        pass

    fd, temp_path = tempfile.mkstemp(suffix=extension)
    os.close(fd)
    size_bytes = 0
    try:
        with open(temp_path, "wb") as output:
            while True:
                chunk = stream.read(256 * 1024)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > _CANDIDATE_DOCUMENT_MAX_BYTES:
                    return {}, "Candidate documents must be 20 MB or smaller."
                output.write(chunk)
        if size_bytes <= 0:
            return {}, "Uploaded file is empty."

        object_key = _build_candidate_document_key(candidate_id, document_type, original_name)
        content_type = (
            infer_resource_mime_type(original_name)
            or str(getattr(uploaded_file, "content_type", "") or getattr(uploaded_file, "mimetype", "") or "").strip()
            or "application/octet-stream"
        )
        client = _get_r2_client()
        if client is None:
            return {}, "Unable to connect to private document storage."
        with open(temp_path, "rb") as payload:
            client.upload_fileobj(
                payload,
                _resource_bucket_name(),
                object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "ContentDisposition": f'inline; filename="{_safe_file_name(original_name)}"',
                    "CacheControl": "private, no-store, max-age=0",
                },
            )
        return {
            "object_key": object_key,
            "original_file_name": original_name,
            "mime_type": content_type,
            "size_bytes": size_bytes,
        }, ""
    except Exception:
        return {}, "Failed to upload the candidate document."
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def build_private_candidate_document_url(
    object_key,
    *,
    original_file_name="",
    download=False,
    expires_in=300,
):
    """Return a short-lived signed URL; deliberately ignores public R2 base URLs."""
    normalized_key = str(object_key or "").strip()
    if not normalized_key.startswith("private/recruitment/") or not is_r2_configured():
        return ""
    client = _get_r2_client()
    if client is None:
        return ""
    safe_name = _safe_file_name(original_file_name or normalized_key.rsplit("/", 1)[-1])
    disposition = "attachment" if download else "inline"
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": _resource_bucket_name(),
                "Key": normalized_key,
                "ResponseContentDisposition": f'{disposition}; filename="{safe_name}"',
                "ResponseCacheControl": "private, no-store, max-age=0",
            },
            ExpiresIn=max(60, min(int(expires_in or 300), 900)),
        )
    except (BotoCoreError, ClientError):
        return ""


def delete_private_candidate_document(object_key):
    normalized_key = str(object_key or "").strip()
    if not normalized_key.startswith("private/recruitment/") or not is_r2_configured():
        return False
    client = _get_r2_client()
    if client is None:
        return False
    try:
        client.delete_object(Bucket=_resource_bucket_name(), Key=normalized_key)
        return True
    except (BotoCoreError, ClientError):
        return False


def delete_resource_file(resource_file_path):
    object_key = str(resource_file_path or "").strip()
    if not object_key or not is_r2_configured():
        return

    with _SIGNED_URL_CACHE_LOCK:
        _SIGNED_URL_CACHE.pop(object_key, None)

    client = _get_r2_client()
    if client is None:
        return

    try:
        client.delete_object(Bucket=_resource_bucket_name(), Key=object_key)
    except (BotoCoreError, ClientError):
        return


__all__ = [
    "is_r2_configured",
    "upload_resource_file",
    "upload_thumbnail_file",
    "build_resource_file_url",
    "delete_resource_file",
    "infer_resource_mime_type",
    "upload_private_candidate_document",
    "build_private_candidate_document_url",
    "delete_private_candidate_document",
]
