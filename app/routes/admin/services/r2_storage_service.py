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
    from botocore.config import Config as BotocoreConfig
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - optional dependency guard
    boto3 = None
    BotocoreConfig = None
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


def _is_false_like(value):
    normalized = str(value or "").strip().lower()
    return normalized in {"0", "false", "no", "off"}


def _r2_enabled():
    # Keep R2 on by default for production; local/dev can opt out with R2_ENABLED=0.
    return not _is_false_like(_env("R2_ENABLED", "1"))


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
    # Default is enabled so uploaded videos are web-optimized out of the box.
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
    # Higher CRF -> smaller file size, lower visual quality.
    raw_value = _env("RESOURCE_VIDEO_CRF", "28")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 26
    return max(18, min(parsed, 32))


def _video_preset():
    # veryfast is a practical balance between upload-time CPU and output size.
    preset = _env("RESOURCE_VIDEO_PRESET", "veryfast").strip().lower()
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


def _ffmpeg_binary():
    global _FFMPEG_MISSING_LOGGED
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    if not _FFMPEG_MISSING_LOGGED:
        _FFMPEG_MISSING_LOGGED = True
        print(
            "[resources] ffmpeg is not installed; uploading video without processing. "
            "On Railway Railpack add apt package 'ffmpeg' (or set "
            "RAILPACK_DEPLOY_APT_PACKAGES=ffmpeg)."
        )
    return ""


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


def _r2_connect_timeout_seconds():
    raw_value = _env("R2_CONNECT_TIMEOUT_SECONDS", "10")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 10
    return max(3, min(parsed, 60))


def _r2_read_timeout_seconds():
    raw_value = _env("R2_READ_TIMEOUT_SECONDS", "120")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 120
    return max(20, min(parsed, 900))


def _r2_max_attempts():
    raw_value = _env("R2_MAX_ATTEMPTS", "3")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 3
    return max(1, min(parsed, 10))


def _r2_multipart_chunk_bytes():
    raw_value = _env("R2_MULTIPART_CHUNK_MB", "8")
    try:
        parsed_mb = int(raw_value)
    except ValueError:
        parsed_mb = 8
    # S3 multipart requires minimum 5MB.
    parsed_mb = max(5, min(parsed_mb, 128))
    return parsed_mb * 1024 * 1024


def _r2_client_config():
    if BotocoreConfig is None:
        return None
    return BotocoreConfig(
        connect_timeout=_r2_connect_timeout_seconds(),
        read_timeout=_r2_read_timeout_seconds(),
        retries={
            "max_attempts": _r2_max_attempts(),
            "mode": "standard",
        },
    )


def is_r2_configured():
    if not _r2_enabled():
        return False
    if boto3 is None:
        return False
    values = _required_r2_env()
    return all(values.values()) and bool(_endpoint_url())


def _build_r2_client():
    if not is_r2_configured():
        return None

    region_name = _env("R2_REGION", "auto")
    endpoint_url = _endpoint_url()
    client_kwargs = {
        "endpoint_url": endpoint_url,
        "aws_access_key_id": _env("R2_ACCESS_KEY_ID"),
        "aws_secret_access_key": _env("R2_SECRET_ACCESS_KEY"),
        "region_name": region_name,
    }
    client_config = _r2_client_config()
    if client_config is not None:
        client_kwargs["config"] = client_config
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
    normalized = str(configured or "").strip()
    if normalized:
        return normalized
    return "public, max-age=31536000, immutable"


def _report_progress(
    progress_callback,
    *,
    percent,
    stage,
    message,
    eta_seconds=None,
):
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
    now = datetime.utcnow()
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


def _read_limited_bytes(
    uploaded_file,
    limit_bytes,
    *,
    progress_callback=None,
    stage_start_percent=12.0,
    stage_end_percent=52.0,
):
    stream = uploaded_file.stream
    try:
        stream.seek(0)
    except Exception:
        pass

    expected_total = 0
    try:
        expected_total = int(uploaded_file.content_length or 0)
    except Exception:
        expected_total = 0
    if expected_total <= 0:
        try:
            expected_total = int(getattr(stream, "content_length", 0) or 0)
        except Exception:
            expected_total = 0
    if expected_total > limit_bytes:
        expected_total = limit_bytes

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
        if expected_total > 0:
            ratio = min(total / expected_total, 1.0)
            percent = stage_start_percent + (
                (stage_end_percent - stage_start_percent) * ratio
            )
            _report_progress(
                progress_callback,
                percent=percent,
                stage="receiving",
                message="Receiving uploaded file...",
            )

    _report_progress(
        progress_callback,
        percent=stage_end_percent,
        stage="received",
        message="Uploaded file received.",
    )
    return b"".join(chunks), total


def _upload_payload_to_r2(
    client,
    *,
    bucket,
    object_key,
    payload,
    content_type,
    safe_name,
    progress_callback=None,
):
    extra_args = {
        "ContentType": content_type,
        "ContentDisposition": f'inline; filename="{safe_name}"',
        "CacheControl": _cache_control_header(),
    }
    _report_progress(
        progress_callback,
        percent=92.0,
        stage="cloud_upload",
        message="Uploading file to storage...",
    )
    client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=payload,
        **extra_args,
    )


def _faststart_remux_video_payload(payload, source_extension, ffmpeg_path=""):
    if not payload:
        return payload, source_extension
    if not _video_faststart_remux_enabled():
        return payload, source_extension
    if source_extension not in _VIDEO_EXTENSIONS:
        return payload, source_extension

    resolved_ffmpeg = str(ffmpeg_path or "").strip() or _ffmpeg_binary()
    if not resolved_ffmpeg:
        return payload, source_extension

    input_temp = None
    output_temp = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=source_extension) as input_file:
            input_temp = input_file.name
            input_file.write(payload)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as output_file:
            output_temp = output_file.name

        remux_command = [
            resolved_ffmpeg,
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


def _optimize_video_payload(payload, source_extension, ffmpeg_path=""):
    if not payload:
        return payload, source_extension
    if not _video_optimize_enabled():
        return payload, source_extension

    resolved_ffmpeg = str(ffmpeg_path or "").strip() or _ffmpeg_binary()
    if not resolved_ffmpeg:
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
                    resolved_ffmpeg,
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
            resolved_ffmpeg,
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


def upload_resource_file(
    uploaded_file,
    subject_name="",
    folder_path="",
    progress_callback=None,
):
    upload_started_at = time.time()
    _report_progress(
        progress_callback,
        percent=5.0,
        stage="validating",
        message="Checking uploaded file...",
    )
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
    _report_progress(
        progress_callback,
        percent=10.0,
        stage="receiving",
        message="Receiving uploaded file...",
    )
    payload, payload_size = _read_limited_bytes(
        uploaded_file,
        max_upload_size,
        progress_callback=progress_callback,
    )
    payload_ready_at = time.time()
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
        _report_progress(
            progress_callback,
            percent=60.0,
            stage="video",
            message="Preparing video for web playback...",
        )
        ffmpeg_path = _ffmpeg_binary()
        payload, extension = _faststart_remux_video_payload(
            payload,
            extension,
            ffmpeg_path=ffmpeg_path,
        )
        _report_progress(
            progress_callback,
            percent=75.0,
            stage="video",
            message="Optimizing video...",
        )
        payload, extension = _optimize_video_payload(
            payload,
            extension,
            ffmpeg_path=ffmpeg_path,
        )
        _report_progress(
            progress_callback,
            percent=84.0,
            stage="video",
            message="Video optimization finished.",
        )
        safe_name = f"{stem}{extension}"

    content_type = (
        infer_resource_mime_type(safe_name)
        or str(uploaded_file.mimetype or "").strip()
        or "application/octet-stream"
    )
    _report_progress(
        progress_callback,
        percent=90.0,
        stage="cloud_upload",
        message="Uploading file to storage...",
    )
    object_key = _build_object_key(subject_name, safe_name, folder_path=folder_path)
    client = _get_r2_client()
    if client is None:
        return "", "Unable to initialize R2 client."

    try:
        _upload_payload_to_r2(
            client,
            bucket=_resource_bucket_name(),
            object_key=object_key,
            payload=payload,
            content_type=content_type,
            safe_name=safe_name,
            progress_callback=progress_callback,
        )
    except Exception:
        print(
            "[resources] R2 upload failed",
            {
                "file_name": safe_name,
                "bytes": int(payload_size or 0),
                "read_seconds": round(payload_ready_at - upload_started_at, 3),
                "total_seconds": round(time.time() - upload_started_at, 3),
            },
        )
        return "", "Failed to upload resource file to R2."
    print(
        "[resources] R2 upload complete",
        {
            "file_name": safe_name,
            "bytes": int(payload_size or 0),
            "read_seconds": round(payload_ready_at - upload_started_at, 3),
            "total_seconds": round(time.time() - upload_started_at, 3),
        },
    )

    _report_progress(
        progress_callback,
        percent=97.0,
        stage="cloud_upload",
        message="File uploaded. Finalizing...",
    )
    return object_key, ""


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


_ALLOWED_THUMBNAIL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_THUMBNAIL_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def upload_thumbnail_file(uploaded_file, subject_name="", folder_path=""):
    if uploaded_file is None or not str(uploaded_file.filename or "").strip():
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
        return "", "Unable to initialize R2 client."

    try:
        _upload_payload_to_r2(
            client,
            bucket=_resource_bucket_name(),
            object_key=object_key,
            payload=payload,
            content_type=content_type,
            safe_name=safe_name,
        )
    except Exception:
        return "", "Failed to upload thumbnail to R2."

    return object_key, ""


__all__ = [
    "is_r2_configured",
    "upload_resource_file",
    "upload_thumbnail_file",
    "build_resource_file_url",
    "delete_resource_file",
    "infer_resource_mime_type",
]
