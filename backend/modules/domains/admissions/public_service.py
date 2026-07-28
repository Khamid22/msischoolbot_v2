"""Token-scoped public admission use cases."""

from __future__ import annotations

import hashlib
from typing import Any

from backend.core.runtime.config import PaymeSettings, StorageSettings
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.admissions import contracts
from backend.modules.domains.admissions.schemas import (
    ContractUploadMetadata,
    PublicAdmission,
)
from backend.platform.storage.private_documents import (
    build_private_document_url,
    upload_private_document,
)

ADMISSION_DOCUMENT_NAMESPACE = "admissions"


def _token_hash(access_token: str) -> str:
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()


class PublicAdmissions:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        payme_settings: PaymeSettings,
        storage_settings: StorageSettings,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._payme_settings = payme_settings
        self._storage_settings = storage_settings

    def get(self, access_token: str) -> PublicAdmission:
        token_hash = _token_hash(access_token)
        callback_url = (
            f"{self._payme_settings.callback_base_url.rstrip('/')}"
            f"/admissions/{access_token}"
            if self._payme_settings.callback_base_url
            else f"/admissions/{access_token}"
        )
        with self._unit_of_work_factory.transaction() as unit_of_work:
            admission = contracts.get_public_admission(
                unit_of_work.conn,
                token_hash,
                payme_is_available=self._payme_settings.is_configured,
                checkout_url=self._payme_settings.checkout_url,
                merchant_id=self._payme_settings.merchant_id,
                callback_url=callback_url,
            )
            commit_unit_of_work(unit_of_work)
        return admission

    def submit_contract(self, access_token: str, uploaded_file: Any) -> PublicAdmission:
        current = self.get(access_token)
        metadata, error = upload_private_document(
            uploaded_file,
            namespace=ADMISSION_DOCUMENT_NAMESPACE,
            record_id=current.admission_id,
            document_type="signed-contract",
            max_bytes=min(self._storage_settings.upload_max_bytes, 20 * 1024 * 1024),
        )
        if error:
            raise contracts.AdmissionError(error)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            contracts.submit_contract(
                unit_of_work.conn,
                _token_hash(access_token),
                ContractUploadMetadata.model_validate(metadata),
            )
            commit_unit_of_work(unit_of_work)
        return self.get(access_token)

    def contract_download_url(self, access_token: str) -> str:
        with self._unit_of_work_factory.transaction() as unit_of_work:
            document = contracts.get_public_contract_document(
                unit_of_work.conn,
                _token_hash(access_token),
            )
            commit_unit_of_work(unit_of_work)
        url = build_private_document_url(
            document.object_key,
            namespace=ADMISSION_DOCUMENT_NAMESPACE,
            original_file_name=document.original_file_name,
            download=True,
        )
        if not url:
            raise contracts.AdmissionError(
                "The contract document could not be opened."
            )
        return url


__all__ = ["ADMISSION_DOCUMENT_NAMESPACE", "PublicAdmissions"]
