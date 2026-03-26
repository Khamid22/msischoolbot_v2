import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from urllib.parse import quote

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - optional dependency guard
    boto3 = None
    BotoCoreError = Exception
    ClientError = Exception

_R2_LOCK = threading.Lock()
_R2_CLIENT = None
_SIGNED_URL_CACHE_LOCK = threading.Lock()
_SIGNED_URL_CACHE = {}
_FFMPEG_MISSING_LOGGED = False

_ALLOWED_RESOURCE_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".txt",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".mp4",
    ".mov",
    ".m4v",
    ".mp3",
    ".wav",
    ".zip",
}

_RESOURCE_EXTENSION_MIME_MAP = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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


def _env(name, default=""):
    return str(os.environ.get(name, default) or "").strip()


def _required_r2_env():
    return {
        "R2_ACCOUNT_ID": _env("R2_ACCOUNT_ID"),
        "R2_ACCESS_KEY_ID": _env("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": _env("R2_SECRET_ACCESS_KEY"),
        "R2_BUCKET_NAME": _env("R2_BUCKET_NAME"),
    }


def _normalize(value):
    return " ".join(str(value or "").strip().casefold().split())


def _slugify(value):
    normalized = _normalize(value)
    if not normalized:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


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


def _max_upload_bytes():
    raw_value = _env("RESOURCE_UPLOAD_MAX_MB", "200")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 200
    parsed = max(parsed, 1)
    parsed = min(parsed, 1024)
    return parsed * 1024 * 1024


def _video_optimize_enabled():
    raw_value = _env("RESOURCE_VIDEO_OPTIMIZE", "1").strip().lower()
    return raw_value not in {"0", "false", "no", "off"}


def _video_optimize_timeout_seconds():
    raw_value = _env("RESOURCE_VIDEO_OPTIMIZE_TIMEOUT_SECONDS", "240")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 240
    return max(20, min(parsed, 1800))


def _video_faststart_timeout_seconds():
    raw_value = _env("RESOURCE_VIDEO_FASTSTART_TIMEOUT_SECONDS", "90")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 90
    return max(10, min(parsed, 600))


def _video_max_width():
    raw_value = _env("RESOURCE_VIDEO_MAX_WIDTH", "960")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 960
    return max(320, min(parsed, 3840))


def _video_crf():
    raw_value = _env("RESOURCE_VIDEO_CRF", "26")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 26
    return max(18, min(parsed, 32))


def _video_preset():
    preset = _env("RESOURCE_VIDEO_PRESET", "ultrafast").strip().lower()
    allowed = {
        "ultrafast",
        "superfast",
        "veryfast",
        "faster",
        "fast",
        "medium",
        "slow",
        "slower",
        "veryslow",
    }
    if preset not in allowed:
        return "ultrafast"
    return preset


def _video_faststart_remux_enabled():
    raw_value = _env("RESOURCE_VIDEO_FASTSTART_REMUX", "1").strip().lower()
    return raw_value not in {"0", "false", "no", "off"}


def _signed_url_ttl():
    raw_value = _env("R2_SIGNED_URL_TTL_SECONDS", "21600")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 21600
    return max(60, min(parsed, 604800))


def _public_base_url():
    raw_value = (
        _env("R2_PUBLIC_BASE_URL")
        or _env("RESOURCE_PUBLIC_BASE_URL")
        or _env("R2_DEV_PUBLIC_URL")
    )
    if not raw_value:
        return ""
    normalized = str(raw_value).strip().rstrip("/")
    if not normalized:
        return ""
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return normalized
    return f"https://{normalized}"


def _endpoint_url():
    explicit = _env("R2_ENDPOINT_URL")
    if explicit:
        return explicit
    account_id = _env("R2_ACCOUNT_ID")
    if not account_id:
        return ""
    return f"https://{account_id}.r2.cloudflarestorage.com"


def is_r2_configured():
    if boto3 is None:
        return False
    values = _required_r2_env()
    return all(values.values()) and bool(_endpoint_url())


def _build_r2_client():
    if not is_r2_configured():
        return None

    region_name = _env("R2_REGION", "auto")
    endpoint_url = _endpoint_url()
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("R2_SECRET_ACCESS_KEY"),
        region_name=region_name,
    )


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
    normalized = str(configured or "").strip()
    if normalized:
        return normalized
    return "public, max-age=31536000, immutable"


def _build_object_key(subject_name, original_name):
    now = datetime.utcnow()
    subject_slug = _slugify(subject_name) or "general"
    safe_name = _safe_file_name(original_name)
    dot_index = safe_name.rfind(".")
    ext = safe_name[dot_index:] if dot_index > 0 else ""
    stem = safe_name[:dot_index] if dot_index > 0 else safe_name
    unique_token = now.strftime("%Y%m%d%H%M%S%f")
    return (
        f"resources/"
        f"{now.strftime('%Y/%m')}/"
        f"{subject_slug}/"
        f"{stem}-{unique_token}{ext}"
    )


def _read_limited_bytes(uploaded_file, limit_bytes):
    stream = uploaded_file.stream
    try:
        stream.seek(0)
    except Exception:
        pass

    total = 0
    chunks = []
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit_bytes:
            return None, total
        chunks.append(chunk)
    return b"".join(chunks), total


def _optimize_video_payload(payload, source_extension):
    global _FFMPEG_MISSING_LOGGED
    if not payload:
        return payload, source_extension
    if not _video_optimize_enabled():
        return payload, source_extension

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        if not _FFMPEG_MISSING_LOGGED:
            _FFMPEG_MISSING_LOGGED = True
            print(
                "[resources] ffmpeg is not installed; uploading video without optimization."
            )
        return payload, source_extension

    input_extension = source_extension if source_extension in _VIDEO_EXTENSIONS else ".mp4"
    input_temp = None
    output_temp = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=input_extension) as input_file:
            input_temp = input_file.name
            input_file.write(payload)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as output_file:
            output_temp = output_file.name

        if (
            _video_faststart_remux_enabled()
            and source_extension in {".mp4", ".m4v"}
        ):
            try:
                remux_command = [
                    ffmpeg_path,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    input_temp,
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    output_temp,
                ]
                subprocess.run(
                    remux_command,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=_video_faststart_timeout_seconds(),
                )
                with open(output_temp, "rb") as optimized_file:
                    optimized_payload = optimized_file.read()
                if optimized_payload:
                    return optimized_payload, ".mp4"
            except Exception:
                pass

        scale_filter = f"scale='min({_video_max_width()},iw)':-2"
        command = [
            ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            input_temp,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            _video_preset(),
            "-crf",
            str(_video_crf()),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-vf",
            scale_filter,
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            output_temp,
        ]
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_video_optimize_timeout_seconds(),
        )

        with open(output_temp, "rb") as optimized_file:
            optimized_payload = optimized_file.read()

        if optimized_payload:
            return optimized_payload, ".mp4"
    except Exception:
        return payload, source_extension
    finally:
        for temp_path in (input_temp, output_temp):
            if not temp_path:
                continue
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return payload, source_extension


def upload_resource_file(uploaded_file, subject_name=""):
    if uploaded_file is None or not str(uploaded_file.filename or "").strip():
        return "", "No file was uploaded."
    if not is_r2_configured():
        return "", "R2 storage is not configured."

    original_name = str(uploaded_file.filename or "").strip()
    safe_name = _safe_file_name(original_name)
    extension = _file_extension(safe_name)
    if extension not in _ALLOWED_RESOURCE_EXTENSIONS:
        return "", "File type is not supported for resources."

    max_upload_size = _max_upload_bytes()
    payload, payload_size = _read_limited_bytes(uploaded_file, max_upload_size)
    if payload is None:
        return "", (
            "Uploaded file is too large. "
            f"Max upload size is {max_upload_size // (1024 * 1024)} MB."
        )
    if payload_size <= 0:
        return "", "Uploaded file is empty."
    if payload_size > max_upload_size:
        return "", (
            "Uploaded file is too large or empty. "
            f"Max upload size is {max_upload_size // (1024 * 1024)} MB."
        )

    dot_index = safe_name.rfind(".")
    stem = safe_name[:dot_index] if dot_index > 0 else safe_name

    if extension in _VIDEO_EXTENSIONS:
        payload, extension = _optimize_video_payload(payload, extension)
        safe_name = f"{stem}{extension}"

    content_type = (
        infer_resource_mime_type(safe_name)
        or str(uploaded_file.mimetype or "").strip()
        or "application/octet-stream"
    )
    object_key = _build_object_key(subject_name, safe_name)
    client = _get_r2_client()
    if client is None:
        return "", "Unable to initialize R2 client."

    try:
        client.put_object(
            Bucket=_resource_bucket_name(),
            Key=object_key,
            Body=payload,
            ContentType=content_type,
            ContentDisposition=f'inline; filename="{safe_name}"',
            CacheControl=_cache_control_header(),
        )
    except (BotoCoreError, ClientError):
        return "", "Failed to upload resource file to R2."

    return object_key, ""


def build_resource_file_url(resource_file_path):
    object_key = str(resource_file_path or "").strip()
    if not object_key or not is_r2_configured():
        return ""

    public_base = _public_base_url()
    if public_base:
        escaped_key = quote(object_key, safe="/-_.~")
        return f"{public_base}/{escaped_key}"

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
    file_name = _safe_file_name(object_key.split("/")[-1] if "/" in object_key else object_key)
    if not file_name:
        file_name = "resource"

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
        client.delete_object(
            Bucket=_resource_bucket_name(),
            Key=object_key,
        )
    except (BotoCoreError, ClientError):
        return


__all__ = [
    "is_r2_configured",
    "upload_resource_file",
    "build_resource_file_url",
    "delete_resource_file",
    "infer_resource_mime_type",
]
