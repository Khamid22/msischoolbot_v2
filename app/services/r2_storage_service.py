import os
import re
import threading
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - optional dependency guard
    boto3 = None
    BotoCoreError = Exception
    ClientError = Exception

_R2_LOCK = threading.Lock()
_R2_CLIENT = None

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
    raw_value = _env("RESOURCE_UPLOAD_MAX_MB", "50")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 50
    parsed = max(parsed, 1)
    return parsed * 1024 * 1024


def _signed_url_ttl():
    raw_value = _env("R2_SIGNED_URL_TTL_SECONDS", "3600")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 3600
    return max(60, min(parsed, 604800))


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
    if payload is None or payload_size <= 0:
        return "", (
            "Uploaded file is too large or empty. "
            f"Max upload size is {max_upload_size // (1024 * 1024)} MB."
        )

    content_type = str(uploaded_file.mimetype or "").strip()
    if not content_type or content_type == "application/octet-stream":
        content_type = infer_resource_mime_type(safe_name) or "application/octet-stream"
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
        )
    except (BotoCoreError, ClientError):
        return "", "Failed to upload resource file to R2."

    return object_key, ""


def build_resource_file_url(resource_file_path):
    object_key = str(resource_file_path or "").strip()
    if not object_key or not is_r2_configured():
        return ""

    client = _get_r2_client()
    if client is None:
        return ""

    response_content_type = infer_resource_mime_type(object_key)
    file_name = _safe_file_name(object_key.split("/")[-1] if "/" in object_key else object_key)
    if not file_name:
        file_name = "resource"

    params = {
        "Bucket": _resource_bucket_name(),
        "Key": object_key,
        "ResponseContentDisposition": f'inline; filename="{file_name}"',
    }
    if response_content_type:
        params["ResponseContentType"] = response_content_type

    try:
        return client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=_signed_url_ttl(),
        )
    except (BotoCoreError, ClientError):
        return ""


def delete_resource_file(resource_file_path):
    object_key = str(resource_file_path or "").strip()
    if not object_key or not is_r2_configured():
        return

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
