"""Candidate document capability for Recruitment."""

from backend.modules.hr.recruitment.documents.service import (
    document_url,
    remove_document,
    upload_document,
)

__all__ = ["document_url", "remove_document", "upload_document"]
