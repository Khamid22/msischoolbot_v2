"""Generalized private R2 document storage."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from backend.platform.storage import r2

ALLOWED_PRIVATE_DOCUMENT_EXTENSIONS = frozenset(
    {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
)
_DOCUMENT_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".docx": (b"PK\x03\x04",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def _has_expected_signature(extension: str, header: bytes) -> bool:
    signatures = _DOCUMENT_SIGNATURES.get(extension, ())
    return any(header.startswith(signature) for signature in signatures)


def _object_key(
    namespace: str,
    record_id: int,
    document_type: str,
    original_name: str,
) -> str:
    now = datetime.now(UTC)
    safe_namespace = r2._slugify(namespace) or "documents"
    safe_name = r2._safe_file_name(original_name)
    extension = r2._file_extension(original_name)
    if extension and not safe_name.endswith(extension):
        safe_name = f"{safe_name or 'document'}{extension}"
    return (
        f"private/{safe_namespace}/{int(record_id)}/"
        f"{r2._slugify(document_type) or 'document'}/"
        f"{now.strftime('%Y%m%d%H%M%S%f')}-{safe_name}"
    )


def upload_private_document(
    uploaded_file: Any,
    *,
    namespace: str,
    record_id: int,
    document_type: str,
    max_bytes: int = 20 * 1024 * 1024,
) -> tuple[dict[str, Any], str]:
    original_name = str(getattr(uploaded_file, "filename", "") or "").strip()
    if not original_name:
        return {}, "No file was uploaded."
    extension = r2._file_extension(original_name)
    if extension not in ALLOWED_PRIVATE_DOCUMENT_EXTENSIONS:
        return {}, "Documents must be PDF, DOC, DOCX, JPG, or PNG files."
    if not r2.is_r2_configured():
        return {}, "Private document storage is not configured."
    stream = getattr(uploaded_file, "file", None) or getattr(uploaded_file, "stream", None)
    if stream is None:
        return {}, "Unable to read the uploaded file."
    with suppress(Exception):
        stream.seek(0)

    descriptor, temp_path = tempfile.mkstemp(suffix=extension)
    os.close(descriptor)
    size_bytes = 0
    header = b""
    try:
        with open(temp_path, "wb") as output:
            while chunk := stream.read(256 * 1024):
                if not header:
                    header = bytes(chunk[:16])
                size_bytes += len(chunk)
                if size_bytes > max(1, int(max_bytes)):
                    return {}, "The document exceeds the configured upload limit."
                output.write(chunk)
        if size_bytes <= 0:
            return {}, "Uploaded file is empty."
        if not _has_expected_signature(extension, header):
            return {}, "The document content does not match its file extension."
        object_key = _object_key(
            namespace,
            record_id,
            document_type,
            original_name,
        )
        content_type = (
            r2.infer_resource_mime_type(original_name)
            or str(
                getattr(uploaded_file, "content_type", "")
                or getattr(uploaded_file, "mimetype", "")
                or ""
            ).strip()
            or "application/octet-stream"
        )
        client = r2._get_r2_client()
        if client is None:
            return {}, "Unable to connect to private document storage."
        with open(temp_path, "rb") as payload:
            client.upload_fileobj(
                payload,
                r2._resource_bucket_name(),
                object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "ContentDisposition": (
                        f'inline; filename="{r2._safe_file_name(original_name)}"'
                    ),
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
        return {}, "Failed to upload the private document."
    finally:
        with suppress(OSError):
            os.remove(temp_path)


def build_private_document_url(
    object_key: str,
    *,
    namespace: str,
    original_file_name: str = "",
    download: bool = False,
    expires_in: int = 300,
) -> str:
    normalized_key = str(object_key or "").strip()
    expected_prefix = f"private/{r2._slugify(namespace) or 'documents'}/"
    if not normalized_key.startswith(expected_prefix) or not r2.is_r2_configured():
        return ""
    client = r2._get_r2_client()
    if client is None:
        return ""
    safe_name = r2._safe_file_name(
        original_file_name or normalized_key.rsplit("/", 1)[-1]
    )
    disposition = "attachment" if download else "inline"
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": r2._resource_bucket_name(),
                "Key": normalized_key,
                "ResponseContentDisposition": f'{disposition}; filename="{safe_name}"',
                "ResponseCacheControl": "private, no-store, max-age=0",
            },
            ExpiresIn=max(60, min(int(expires_in or 300), 900)),
        )
    except (r2.BotoCoreError, r2.ClientError):
        return ""


__all__ = [
    "ALLOWED_PRIVATE_DOCUMENT_EXTENSIONS",
    "build_private_document_url",
    "upload_private_document",
]
