"""Candidate document capability for Recruitment."""

from backend.modules.domains.recruitment.documents.service import (
    document_url,
    remove_document,
    upload_document,
)

__all__ = ["document_url", "remove_document", "upload_document"]
