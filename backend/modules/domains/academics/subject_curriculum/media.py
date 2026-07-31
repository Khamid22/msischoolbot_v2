"""Draft-scoped curriculum media, trusted embeds, and authorized previews."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.academics.subject_curriculum import (
    presentation_repository,
    repository,
    revision_repository,
)
from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumAssetRenderKind,
    CurriculumConversionStatus,
    CurriculumRevisionState,
    CurriculumVariant,
)
from backend.modules.domains.academics.subject_curriculum.drafts import (
    get_fundamentals_draft,
)
from backend.modules.domains.academics.subject_curriculum.exceptions import (
    CurriculumConflictError,
    CurriculumNotFoundError,
    CurriculumPermissionError,
    CurriculumValidationError,
)
from backend.modules.domains.academics.subject_curriculum.schemas import (
    CurriculumExternalAssetWrite,
)
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand
from backend.platform.storage.r2 import (
    build_private_curriculum_asset_url,
    upload_private_curriculum_asset,
)

CONVERT_PRESENTATION_TOPIC = "academics.convert_curriculum_presentation"
PRESENTATION_MIME_TYPES = {
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _youtube_video_id(parsed) -> str:
    host = (parsed.hostname or "").casefold()
    if host == "youtu.be":
        return parsed.path.strip("/").split("/", 1)[0]
    if host.endswith("youtube.com"):
        if parsed.path.startswith("/watch"):
            return (parse_qs(parsed.query).get("v") or [""])[0]
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"}:
            return parts[1]
    return ""


def normalize_external_url(
    url: str,
    *,
    render_kind: CurriculumAssetRenderKind,
) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise CurriculumValidationError("External materials must use HTTPS.")
    if render_kind is CurriculumAssetRenderKind.LINK:
        return urlunparse(parsed._replace(fragment=""))

    host = parsed.hostname.casefold()
    youtube_id = _youtube_video_id(parsed)
    if youtube_id:
        return f"https://www.youtube-nocookie.com/embed/{youtube_id}"
    if host in {"vimeo.com", "www.vimeo.com", "player.vimeo.com"}:
        parts = [part for part in parsed.path.split("/") if part]
        video_id = parts[-1] if parts else ""
        if video_id.isdigit():
            return f"https://player.vimeo.com/video/{video_id}"
    if host == "docs.google.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 3 and parts[0] == "presentation" and parts[1] == "d":
            return (
                f"https://docs.google.com/presentation/d/{parts[2]}/embed"
                "?start=false&loop=false&delayms=3000"
            )
    if host in {"canva.com", "www.canva.com"} and parsed.path.startswith("/design/"):
        query = parse_qs(parsed.query)
        query["embed"] = ["1"]
        return urlunparse(
            parsed._replace(
                netloc="www.canva.com",
                query=urlencode(query, doseq=True),
                fragment="",
            )
        )
    if host == "view.genially.com":
        return urlunparse(parsed._replace(fragment=""))
    raise CurriculumValidationError(
        "Embeds support YouTube, Vimeo, Google Slides, Canva, and Genially."
    )


def _render_kind_for_upload(uploaded: dict[str, object]) -> CurriculumAssetRenderKind:
    mime_type = str(uploaded["mime_type"])
    suffix = PurePosixPath(str(uploaded["original_file_name"])).suffix.casefold()
    if mime_type in PRESENTATION_MIME_TYPES or suffix in {".ppt", ".pptx"}:
        return CurriculumAssetRenderKind.PRESENTATION
    if mime_type.startswith("image/"):
        return CurriculumAssetRenderKind.IMAGE
    if mime_type.startswith("video/"):
        return CurriculumAssetRenderKind.VIDEO
    if mime_type.startswith("audio/"):
        return CurriculumAssetRenderKind.AUDIO
    return CurriculumAssetRenderKind.DOCUMENT


def _require_draft(row, *, subject_id: int):
    if (
        not row
        or int(row["subject_id"]) != subject_id
        or str(row["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
        or str(row["state"]) != CurriculumRevisionState.DRAFT
    ):
        raise CurriculumNotFoundError("Fundamentals lesson draft was not found.")
    return row


def _enqueue_conversion(unit_of_work, *, asset_id: int, attempt: int) -> None:
    unit_of_work.enqueue(
        EnqueueJobCommand(
            topic=CONVERT_PRESENTATION_TOPIC,
            payload={"asset_id": asset_id},
            idempotency_key=f"curriculum-presentation:{asset_id}:attempt:{attempt}",
            max_attempts=5,
        )
    )


def add_draft_external_asset(
    subject_id: int,
    draft_id: int,
    payload: CurriculumExternalAssetWrite,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
):
    factory = unit_of_work_factory or UnitOfWorkFactory()
    normalized_url = normalize_external_url(
        payload.external_url,
        render_kind=payload.render_kind,
    )
    with factory.transaction() as unit_of_work:
        draft = _require_draft(
            revision_repository.get_draft_row(
                unit_of_work.conn,
                draft_id,
                for_update=True,
            ),
            subject_id=subject_id,
        )
        asset = revision_repository.insert_external_asset(
            unit_of_work.conn,
            item_id=int(draft["item_id"]),
            revision_id=draft_id,
            title=payload.title.strip(),
            external_url=normalized_url,
            render_kind=payload.render_kind,
            actor_staff_id=actor_staff_id,
        )
        asset_id = int(asset["id"])
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_draft_asset_created",
            entity_type="supplemental_curriculum_asset",
            entity_id=asset_id,
            detail={"subject_id": subject_id, "draft_id": draft_id},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_fundamentals_draft(
        subject_id,
        draft_id,
        unit_of_work_factory=factory,
    )


def upload_draft_file_asset(
    subject_id: int,
    draft_id: int,
    uploaded_file,
    *,
    title: str,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
):
    factory = unit_of_work_factory or UnitOfWorkFactory(
        job_enqueuer=enqueue_on_connection
    )
    with factory.read() as unit_of_work:
        draft = _require_draft(
            revision_repository.get_draft_row(unit_of_work.conn, draft_id),
            subject_id=subject_id,
        )
        item_id = int(draft["item_id"])
    uploaded, error = upload_private_curriculum_asset(uploaded_file, item_id=item_id)
    if error:
        raise CurriculumValidationError(error)
    render_kind = _render_kind_for_upload(uploaded)
    conversion_status = (
        CurriculumConversionStatus.PENDING
        if render_kind is CurriculumAssetRenderKind.PRESENTATION
        else CurriculumConversionStatus.NOT_REQUIRED
    )
    with factory.transaction() as unit_of_work:
        _require_draft(
            revision_repository.get_draft_row(
                unit_of_work.conn,
                draft_id,
                for_update=True,
            ),
            subject_id=subject_id,
        )
        asset = revision_repository.insert_file_asset(
            unit_of_work.conn,
            item_id=item_id,
            revision_id=draft_id,
            title=title.strip() or str(uploaded["original_file_name"]),
            object_key=str(uploaded["object_key"]),
            original_file_name=str(uploaded["original_file_name"]),
            mime_type=str(uploaded["mime_type"]),
            size_bytes=int(uploaded["size_bytes"]),
            render_kind=render_kind,
            conversion_status=conversion_status,
            actor_staff_id=actor_staff_id,
        )
        asset_id = int(asset["id"])
        if render_kind is CurriculumAssetRenderKind.PRESENTATION:
            _enqueue_conversion(
                unit_of_work,
                asset_id=asset_id,
                attempt=int(asset["conversion_attempts"]),
            )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_draft_file_uploaded",
            entity_type="supplemental_curriculum_asset",
            entity_id=asset_id,
            detail={
                "subject_id": subject_id,
                "draft_id": draft_id,
                "render_kind": render_kind,
            },
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_fundamentals_draft(
        subject_id,
        draft_id,
        unit_of_work_factory=factory,
    )


def detach_draft_asset(
    subject_id: int,
    draft_id: int,
    asset_id: int,
    *,
    expected_version: int,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
):
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        _require_draft(
            revision_repository.get_draft_row(
                unit_of_work.conn,
                draft_id,
                for_update=True,
            ),
            subject_id=subject_id,
        )
        detached = revision_repository.detach_asset(
            unit_of_work.conn,
            revision_id=draft_id,
            asset_id=asset_id,
            expected_version=expected_version,
            actor_staff_id=actor_staff_id,
        )
        if not detached:
            raise CurriculumConflictError(
                "This material changed in another session. Reload and try again."
            )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_draft_asset_detached",
            entity_type="supplemental_curriculum_asset",
            entity_id=asset_id,
            detail={"subject_id": subject_id, "draft_id": draft_id},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_fundamentals_draft(
        subject_id,
        draft_id,
        unit_of_work_factory=factory,
    )


def retry_presentation_conversion(
    subject_id: int,
    draft_id: int,
    asset_id: int,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
):
    factory = unit_of_work_factory or UnitOfWorkFactory(
        job_enqueuer=enqueue_on_connection
    )
    with factory.transaction() as unit_of_work:
        _require_draft(
            revision_repository.get_draft_row(
                unit_of_work.conn,
                draft_id,
                for_update=True,
            ),
            subject_id=subject_id,
        )
        attached_ids = revision_repository.list_attached_asset_ids(
            unit_of_work.conn,
            draft_id,
        )
        if asset_id not in attached_ids:
            raise CurriculumNotFoundError("Draft presentation was not found.")
        pending = presentation_repository.mark_conversion_pending(
            unit_of_work.conn,
            asset_id,
        )
        if not pending:
            raise CurriculumConflictError(
                "Only a failed presentation conversion can be retried."
            )
        _enqueue_conversion(
            unit_of_work,
            asset_id=asset_id,
            attempt=int(pending["conversion_attempts"]) + 1,
        )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_presentation_retry_requested",
            entity_type="supplemental_curriculum_asset",
            entity_id=asset_id,
            detail={"subject_id": subject_id, "draft_id": draft_id},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_fundamentals_draft(
        subject_id,
        draft_id,
        unit_of_work_factory=factory,
    )


def curriculum_asset_url_for_teacher(
    teacher_id: int,
    asset_id: int,
    *,
    download: bool,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> str:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.read() as unit_of_work:
        row = presentation_repository.get_asset_row(unit_of_work.conn, asset_id)
        if (
            not row
            or str(row["status"]) != "active"
            or str(row["item_status"]) != "active"
            or str(row["curriculum_status"]) != "active"
            or not bool(row["is_published"])
            or not repository.teacher_has_subject(
                unit_of_work.conn,
                teacher_id,
                int(row["subject_id"]),
            )
        ):
            raise CurriculumNotFoundError("Curriculum file was not found.")
    url = build_private_curriculum_asset_url(
        row["object_key"],
        original_file_name=row["original_file_name"],
        download=download,
    )
    if not url:
        raise CurriculumNotFoundError("Curriculum file is unavailable.")
    return url


def curriculum_asset_url_for_director(
    asset_id: int,
    *,
    download: bool,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> str:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.read() as unit_of_work:
        row = presentation_repository.get_asset_row(unit_of_work.conn, asset_id)
        if not row or str(row["status"]) != "active":
            raise CurriculumNotFoundError("Curriculum file was not found.")
    url = build_private_curriculum_asset_url(
        row["object_key"],
        original_file_name=row["original_file_name"],
        download=download,
    )
    if not url:
        raise CurriculumNotFoundError("Curriculum file is unavailable.")
    return url


def curriculum_slide_url(
    asset_id: int,
    slide_number: int,
    *,
    teacher_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> str:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.read() as unit_of_work:
        asset = presentation_repository.get_asset_row(unit_of_work.conn, asset_id)
        rendition = presentation_repository.get_rendition_row(
            unit_of_work.conn,
            asset_id,
            slide_number,
        )
        if not asset or not rendition or str(asset["conversion_status"]) != "ready":
            raise CurriculumNotFoundError("Presentation slide was not found.")
        if teacher_id is not None and (
            str(asset["status"]) != "active"
            or str(asset["item_status"]) != "active"
            or str(asset["curriculum_status"]) != "active"
            or not bool(asset["is_published"])
            or not repository.teacher_has_subject(
                unit_of_work.conn,
                teacher_id,
                int(asset["subject_id"]),
            )
        ):
            raise CurriculumPermissionError(
                "This presentation is not assigned to the teacher."
            )
    url = build_private_curriculum_asset_url(
        rendition["object_key"],
        original_file_name=f"slide-{slide_number:03d}.png",
        download=False,
    )
    if not url:
        raise CurriculumNotFoundError("Presentation slide is unavailable.")
    return url


__all__ = [
    "CONVERT_PRESENTATION_TOPIC",
    "add_draft_external_asset",
    "curriculum_asset_url_for_director",
    "curriculum_asset_url_for_teacher",
    "curriculum_slide_url",
    "detach_draft_asset",
    "normalize_external_url",
    "retry_presentation_conversion",
    "upload_draft_file_asset",
]
