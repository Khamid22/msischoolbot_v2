"""Typed subject-curriculum queries and commands."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.academics.subject_curriculum import repository
from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumAssetKind,
    CurriculumItemType,
    CurriculumRecordStatus,
    CurriculumVariant,
)
from backend.modules.domains.academics.subject_curriculum.exceptions import (
    CurriculumConflictError,
    CurriculumNotFoundError,
    CurriculumPermissionError,
    CurriculumValidationError,
)
from backend.modules.domains.academics.subject_curriculum.schemas import (
    CurriculumAsset,
    CurriculumContentBlock,
    CurriculumDetail,
    CurriculumExternalAssetWrite,
    CurriculumItem,
    CurriculumItemWrite,
    CurriculumVariantSummary,
    CurriculumViewAcknowledgement,
    SubjectCurriculumCatalog,
    SubjectCurriculumSummary,
)
from backend.platform.storage.r2 import (
    build_private_curriculum_asset_url,
    upload_private_curriculum_asset,
)


def _as_iso(value: object) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _has_updates(updated_at: object, last_viewed_at: object) -> bool:
    if not updated_at:
        return False
    if not last_viewed_at:
        return True
    return _as_iso(updated_at) > _as_iso(last_viewed_at)


def _variant_from_row(row, *, is_editable: bool) -> CurriculumVariantSummary:
    return CurriculumVariantSummary(
        curriculum_id=int(row["curriculum_id"]) if row["curriculum_id"] else None,
        program_id=int(row["program_id"]) if row["program_id"] else None,
        curriculum_key=CurriculumVariant(str(row["curriculum_key"])),
        title=str(row["title"] or ""),
        item_count=int(row["item_count"] or 0),
        lesson_count=int(row["lesson_count"] or 0),
        exam_count=int(row["exam_count"] or 0),
        version=int(row["version"] or 1),
        is_editable=is_editable,
        has_updates=_has_updates(row["updated_at"], row["last_viewed_at"]),
        updated_at=_as_iso(row["updated_at"]),
    )


def _catalog_from_rows(rows, *, is_director: bool) -> SubjectCurriculumCatalog:
    subjects: dict[int, SubjectCurriculumSummary] = {}
    for row in rows:
        subject_id = int(row["subject_id"])
        if subject_id not in subjects:
            subjects[subject_id] = SubjectCurriculumSummary(
                subject_id=subject_id,
                subject_key=str(row["subject_key"] or ""),
                subject_name=str(row["subject_name"] or ""),
                subject_short=str(row["subject_short"] or ""),
            )
        variant = CurriculumVariant(str(row["curriculum_key"]))
        # A subject without an imported primary program is still visible with a
        # useful empty state, while supplemental variants remain usable.
        subjects[subject_id].variants.append(
            _variant_from_row(
                row,
                is_editable=is_director and variant is not CurriculumVariant.PRIMARY,
            )
        )
    return SubjectCurriculumCatalog(subjects=list(subjects.values()))


def _content_blocks(raw_value: object) -> list[CurriculumContentBlock]:
    if not isinstance(raw_value, list):
        return []
    blocks: list[CurriculumContentBlock] = []
    for value in raw_value:
        try:
            blocks.append(CurriculumContentBlock.model_validate(value))
        except (TypeError, ValueError):
            continue
    return blocks


def _assets_by_item(rows, url_prefix: str) -> dict[int, list[CurriculumAsset]]:
    grouped: dict[int, list[CurriculumAsset]] = defaultdict(list)
    for row in rows:
        asset_id = int(row["asset_id"])
        is_file = str(row["asset_kind"]) == CurriculumAssetKind.FILE
        grouped[int(row["item_id"])].append(
            CurriculumAsset(
                asset_id=asset_id,
                asset_kind=CurriculumAssetKind(str(row["asset_kind"])),
                title=str(row["title"] or ""),
                external_url=str(row["external_url"] or ""),
                download_url=f"{url_prefix}/{asset_id}/open" if is_file else "",
                original_file_name=str(row["original_file_name"] or ""),
                mime_type=str(row["mime_type"] or ""),
                size_bytes=int(row["size_bytes"] or 0),
                display_order=int(row["display_order"] or 1),
                status=CurriculumRecordStatus(str(row["status"])),
                version=int(row["version"] or 1),
            )
        )
    return grouped


def _items_from_rows(rows, asset_rows, *, url_prefix: str) -> list[CurriculumItem]:
    assets = _assets_by_item(asset_rows, url_prefix)
    return [
        CurriculumItem(
            item_id=int(row["item_id"]),
            item_order=int(row["item_order"]),
            lesson_number=str(row["lesson_number"] or ""),
            item_type=CurriculumItemType(str(row["item_type"])),
            title=str(row["title"] or ""),
            term_label=str(row["term_label"] or ""),
            week_label=str(row["week_label"] or ""),
            specification_points=str(row["specification_points"] or ""),
            book_pages=str(row["book_pages"] or ""),
            lesson_count=str(row["lesson_count"] or ""),
            duration_hours=str(row["duration_hours"] or ""),
            content_blocks=_content_blocks(row["content_json"]),
            assets=assets.get(int(row["item_id"]), []),
            status=CurriculumRecordStatus(str(row["status"])),
            version=int(row["version"] or 1),
            updated_at=_as_iso(row["updated_at"]),
        )
        for row in rows
    ]


def _variant_for_subject(
    catalog: SubjectCurriculumCatalog,
    subject_id: int,
    curriculum_key: CurriculumVariant,
) -> tuple[SubjectCurriculumSummary, CurriculumVariantSummary]:
    subject = next(
        (entry for entry in catalog.subjects if entry.subject_id == subject_id),
        None,
    )
    if subject is None:
        raise CurriculumNotFoundError("Subject curriculum was not found.")
    variant = next(
        (entry for entry in subject.variants if entry.curriculum_key == curriculum_key),
        None,
    )
    if variant is None:
        raise CurriculumNotFoundError("Curriculum variant was not found.")
    return subject, variant


def list_teacher_subject_curricula(
    teacher_id: int,
    *,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> SubjectCurriculumCatalog:
    if int(teacher_id or 0) <= 0:
        raise CurriculumPermissionError("An active teacher account is required.")
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.read() as unit_of_work:
        rows = repository.list_teacher_curriculum_variant_rows(
            unit_of_work.conn,
            int(teacher_id),
        )
    return _catalog_from_rows(rows, is_director=False)


def list_director_subject_curricula(
    *,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> SubjectCurriculumCatalog:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.read() as unit_of_work:
        rows = repository.list_director_curriculum_variant_rows(unit_of_work.conn)
    return _catalog_from_rows(rows, is_director=True)


def _curriculum_detail(
    conn,
    *,
    subject: SubjectCurriculumSummary,
    variant: CurriculumVariantSummary,
    include_archived: bool,
    url_prefix: str,
) -> CurriculumDetail:
    if variant.curriculum_key is CurriculumVariant.PRIMARY:
        rows = (
            repository.list_primary_item_rows(conn, variant.program_id)
            if variant.program_id
            else []
        )
        items = _items_from_rows(rows, [], url_prefix=url_prefix)
        return CurriculumDetail(subject=subject, variant=variant, items=items)

    if not variant.curriculum_id:
        raise CurriculumNotFoundError("Supplemental curriculum was not found.")
    rows = repository.list_supplemental_item_rows(
        conn,
        variant.curriculum_id,
        include_archived=include_archived,
    )
    item_ids = [int(row["item_id"]) for row in rows]
    asset_rows = repository.list_asset_rows(
        conn,
        item_ids,
        include_archived=include_archived,
    )
    mapped = _items_from_rows(rows, asset_rows, url_prefix=url_prefix)
    return CurriculumDetail(
        subject=subject,
        variant=variant,
        items=[item for item in mapped if item.status is CurriculumRecordStatus.ACTIVE],
        archived_items=[
            item for item in mapped if item.status is CurriculumRecordStatus.ARCHIVED
        ],
    )


def get_teacher_subject_curriculum(
    teacher_id: int,
    subject_id: int,
    curriculum_key: CurriculumVariant,
    *,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    catalog = list_teacher_subject_curricula(
        teacher_id,
        unit_of_work_factory=factory,
    )
    subject, variant = _variant_for_subject(catalog, subject_id, curriculum_key)
    with factory.read() as unit_of_work:
        if not repository.teacher_has_subject(
            unit_of_work.conn,
            teacher_id,
            subject_id,
        ):
            raise CurriculumPermissionError("This subject is not assigned to the teacher.")
        return _curriculum_detail(
            unit_of_work.conn,
            subject=subject,
            variant=variant,
            include_archived=False,
            url_prefix="/api/v1/teacher/subject-curricula/assets",
        )


def get_director_subject_curriculum(
    subject_id: int,
    curriculum_key: CurriculumVariant,
    *,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    catalog = list_director_subject_curricula(unit_of_work_factory=factory)
    subject, variant = _variant_for_subject(catalog, subject_id, curriculum_key)
    with factory.read() as unit_of_work:
        return _curriculum_detail(
            unit_of_work.conn,
            subject=subject,
            variant=variant,
            include_archived=curriculum_key is not CurriculumVariant.PRIMARY,
            url_prefix="/api/v1/academic-director/academic/subject-curricula/assets",
        )


def acknowledge_teacher_curriculum_view(
    teacher_id: int,
    subject_id: int,
    curriculum_key: CurriculumVariant,
    *,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumViewAcknowledgement:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    catalog = list_teacher_subject_curricula(
        teacher_id,
        unit_of_work_factory=factory,
    )
    _variant_for_subject(catalog, subject_id, curriculum_key)
    with factory.transaction() as unit_of_work:
        if not repository.teacher_has_subject(
            unit_of_work.conn,
            teacher_id,
            subject_id,
        ):
            raise CurriculumPermissionError("This subject is not assigned to the teacher.")
        row = repository.upsert_teacher_curriculum_view(
            unit_of_work.conn,
            teacher_id=teacher_id,
            subject_id=subject_id,
            curriculum_key=curriculum_key,
        )
        unit_of_work.commit()
    return CurriculumViewAcknowledgement(
        curriculum_key=curriculum_key,
        viewed_at=_as_iso(row["last_viewed_at"] if row else datetime.now(UTC)),
    )


def _write_payload(payload: CurriculumItemWrite) -> dict[str, object]:
    data = payload.model_dump(mode="json")
    data["item_type"] = payload.item_type.value
    data["content_blocks"] = [
        block.model_dump(mode="json") for block in payload.content_blocks
    ]
    return data


def create_fundamentals_item(
    subject_id: int,
    payload: CurriculumItemWrite,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        variant = repository.get_supplemental_variant_row(
            unit_of_work.conn,
            subject_id,
            CurriculumVariant.FUNDAMENTALS,
        )
        if not variant:
            raise CurriculumNotFoundError("Fundamentals curriculum was not found.")
        curriculum_id = int(variant["curriculum_id"])
        repository.lock_supplemental_curriculum(unit_of_work.conn, curriculum_id)
        item_order = repository.next_active_item_order(
            unit_of_work.conn,
            curriculum_id,
        )
        row = repository.insert_supplemental_item(
            unit_of_work.conn,
            curriculum_id=curriculum_id,
            item_order=item_order,
            payload=_write_payload(payload),
            actor_staff_id=actor_staff_id,
        )
        item_id = int(row["id"]) if row else 0
        repository.touch_curriculum(
            unit_of_work.conn,
            curriculum_id,
            actor_staff_id=actor_staff_id,
        )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_item_created",
            entity_type="supplemental_curriculum_item",
            entity_id=item_id,
            detail={"subject_id": subject_id, "curriculum_key": "fundamentals"},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_director_subject_curriculum(
        subject_id,
        CurriculumVariant.FUNDAMENTALS,
        unit_of_work_factory=factory,
    )


def update_fundamentals_item(
    subject_id: int,
    item_id: int,
    payload: CurriculumItemWrite,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    if payload.expected_version is None:
        raise CurriculumValidationError("expectedVersion is required when editing a lesson.")
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        current = repository.get_supplemental_item_row(
            unit_of_work.conn,
            item_id,
            for_update=True,
        )
        if (
            not current
            or int(current["subject_id"]) != subject_id
            or str(current["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
        ):
            raise CurriculumNotFoundError("Fundamentals lesson was not found.")
        updated = repository.update_supplemental_item(
            unit_of_work.conn,
            item_id=item_id,
            expected_version=payload.expected_version,
            payload=_write_payload(payload),
            actor_staff_id=actor_staff_id,
        )
        if not updated:
            raise CurriculumConflictError(
                "This lesson changed in another session. Reload before saving."
            )
        repository.touch_curriculum(
            unit_of_work.conn,
            int(current["curriculum_id"]),
            actor_staff_id=actor_staff_id,
        )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_item_updated",
            entity_type="supplemental_curriculum_item",
            entity_id=item_id,
            detail={"subject_id": subject_id, "previous_version": payload.expected_version},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_director_subject_curriculum(
        subject_id,
        CurriculumVariant.FUNDAMENTALS,
        unit_of_work_factory=factory,
    )


def reorder_fundamentals_items(
    subject_id: int,
    item_ids: list[int],
    expected_curriculum_version: int,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    if len(item_ids) != len(set(item_ids)):
        raise CurriculumValidationError("Lesson order contains duplicate identifiers.")
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        variant = repository.get_supplemental_variant_row(
            unit_of_work.conn,
            subject_id,
            CurriculumVariant.FUNDAMENTALS,
        )
        if not variant:
            raise CurriculumNotFoundError("Fundamentals curriculum was not found.")
        curriculum_id = int(variant["curriculum_id"])
        locked = repository.lock_supplemental_curriculum(
            unit_of_work.conn,
            curriculum_id,
        )
        if not locked or int(locked["version"]) != expected_curriculum_version:
            raise CurriculumConflictError(
                "The curriculum changed in another session. Reload before reordering."
            )
        current_ids = repository.list_active_item_ids_for_update(
            unit_of_work.conn,
            curriculum_id,
        )
        if current_ids != item_ids and set(current_ids) != set(item_ids):
            raise CurriculumConflictError(
                "The lesson list changed. Reload before reordering."
            )
        repository.reorder_active_items(unit_of_work.conn, curriculum_id, item_ids)
        touched = repository.touch_curriculum(
            unit_of_work.conn,
            curriculum_id,
            actor_staff_id=actor_staff_id,
            expected_version=expected_curriculum_version,
        )
        if not touched:
            raise CurriculumConflictError(
                "The curriculum changed in another session. Reload before reordering."
            )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_reordered",
            entity_type="supplemental_curriculum",
            entity_id=curriculum_id,
            detail={"subject_id": subject_id, "item_ids": item_ids},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_director_subject_curriculum(
        subject_id,
        CurriculumVariant.FUNDAMENTALS,
        unit_of_work_factory=factory,
    )


def set_fundamentals_item_archived(
    subject_id: int,
    item_id: int,
    *,
    expected_version: int,
    archive: bool,
    reason: str = "",
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        current = repository.get_supplemental_item_row(
            unit_of_work.conn,
            item_id,
            for_update=True,
        )
        if (
            not current
            or int(current["subject_id"]) != subject_id
            or str(current["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
        ):
            raise CurriculumNotFoundError("Fundamentals lesson was not found.")
        curriculum_id = int(current["curriculum_id"])
        if archive:
            result = repository.archive_item(
                unit_of_work.conn,
                item_id=item_id,
                expected_version=expected_version,
                reason=reason.strip(),
                actor_staff_id=actor_staff_id,
            )
        else:
            item_order = repository.next_active_item_order(
                unit_of_work.conn,
                curriculum_id,
            )
            result = repository.restore_item(
                unit_of_work.conn,
                item_id=item_id,
                expected_version=expected_version,
                item_order=item_order,
                actor_staff_id=actor_staff_id,
            )
        if not result:
            raise CurriculumConflictError(
                "This lesson changed in another session. Reload and try again."
            )
        active_ids = repository.list_active_item_ids_for_update(
            unit_of_work.conn,
            curriculum_id,
        )
        repository.reorder_active_items(unit_of_work.conn, curriculum_id, active_ids)
        repository.touch_curriculum(
            unit_of_work.conn,
            curriculum_id,
            actor_staff_id=actor_staff_id,
        )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type=(
                "academic.curriculum_item_archived"
                if archive
                else "academic.curriculum_item_restored"
            ),
            entity_type="supplemental_curriculum_item",
            entity_id=item_id,
            detail={"subject_id": subject_id, "reason": reason.strip()},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_director_subject_curriculum(
        subject_id,
        CurriculumVariant.FUNDAMENTALS,
        unit_of_work_factory=factory,
    )


def add_fundamentals_external_asset(
    subject_id: int,
    item_id: int,
    payload: CurriculumExternalAssetWrite,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        current = repository.get_supplemental_item_row(
            unit_of_work.conn,
            item_id,
            for_update=True,
        )
        if (
            not current
            or int(current["subject_id"]) != subject_id
            or str(current["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
            or str(current["status"]) != CurriculumRecordStatus.ACTIVE
        ):
            raise CurriculumNotFoundError("Active Fundamentals lesson was not found.")
        asset = repository.insert_external_asset(
            unit_of_work.conn,
            item_id=item_id,
            asset_kind=payload.asset_kind,
            title=payload.title.strip(),
            external_url=payload.external_url,
            actor_staff_id=actor_staff_id,
        )
        asset_id = int(asset["id"]) if asset else 0
        repository.touch_curriculum(
            unit_of_work.conn,
            int(current["curriculum_id"]),
            actor_staff_id=actor_staff_id,
        )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_asset_created",
            entity_type="supplemental_curriculum_asset",
            entity_id=asset_id,
            detail={"subject_id": subject_id, "item_id": item_id},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_director_subject_curriculum(
        subject_id,
        CurriculumVariant.FUNDAMENTALS,
        unit_of_work_factory=factory,
    )


def upload_fundamentals_file_asset(
    subject_id: int,
    item_id: int,
    uploaded_file,
    *,
    title: str,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.read() as unit_of_work:
        current = repository.get_supplemental_item_row(unit_of_work.conn, item_id)
        if (
            not current
            or int(current["subject_id"]) != subject_id
            or str(current["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
            or str(current["status"]) != CurriculumRecordStatus.ACTIVE
        ):
            raise CurriculumNotFoundError("Active Fundamentals lesson was not found.")
    uploaded, error = upload_private_curriculum_asset(uploaded_file, item_id=item_id)
    if error:
        raise CurriculumValidationError(error)
    with factory.transaction() as unit_of_work:
        current = repository.get_supplemental_item_row(
            unit_of_work.conn,
            item_id,
            for_update=True,
        )
        if (
            not current
            or int(current["subject_id"]) != subject_id
            or str(current["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
            or str(current["status"]) != CurriculumRecordStatus.ACTIVE
        ):
            raise CurriculumNotFoundError("Fundamentals lesson was not found.")
        asset = repository.insert_file_asset(
            unit_of_work.conn,
            item_id=item_id,
            title=title.strip() or str(uploaded["original_file_name"]),
            object_key=str(uploaded["object_key"]),
            original_file_name=str(uploaded["original_file_name"]),
            mime_type=str(uploaded["mime_type"]),
            size_bytes=int(uploaded["size_bytes"]),
            actor_staff_id=actor_staff_id,
        )
        asset_id = int(asset["id"]) if asset else 0
        repository.touch_curriculum(
            unit_of_work.conn,
            int(current["curriculum_id"]),
            actor_staff_id=actor_staff_id,
        )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_asset_uploaded",
            entity_type="supplemental_curriculum_asset",
            entity_id=asset_id,
            detail={"subject_id": subject_id, "item_id": item_id},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_director_subject_curriculum(
        subject_id,
        CurriculumVariant.FUNDAMENTALS,
        unit_of_work_factory=factory,
    )


def archive_fundamentals_asset(
    subject_id: int,
    asset_id: int,
    *,
    expected_version: int,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumDetail:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        current = repository.get_asset_row(unit_of_work.conn, asset_id)
        if not current or int(current["subject_id"]) != subject_id:
            raise CurriculumNotFoundError("Curriculum asset was not found.")
        archived = repository.archive_asset(
            unit_of_work.conn,
            asset_id=asset_id,
            expected_version=expected_version,
            actor_staff_id=actor_staff_id,
        )
        if not archived:
            raise CurriculumConflictError(
                "This material changed in another session. Reload and try again."
            )
        repository.touch_curriculum(
            unit_of_work.conn,
            int(current["curriculum_id"]),
            actor_staff_id=actor_staff_id,
        )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_asset_archived",
            entity_type="supplemental_curriculum_asset",
            entity_id=asset_id,
            detail={"subject_id": subject_id, "item_id": int(current["item_id"])},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_director_subject_curriculum(
        subject_id,
        CurriculumVariant.FUNDAMENTALS,
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
        row = repository.get_asset_row(unit_of_work.conn, asset_id)
        if (
            not row
            or str(row["status"]) != CurriculumRecordStatus.ACTIVE
            or str(row["item_status"]) != CurriculumRecordStatus.ACTIVE
            or str(row["curriculum_status"]) != CurriculumRecordStatus.ACTIVE
            or str(row["asset_kind"]) != CurriculumAssetKind.FILE
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
        row = repository.get_asset_row(unit_of_work.conn, asset_id)
        if (
            not row
            or str(row["status"]) != CurriculumRecordStatus.ACTIVE
            or str(row["asset_kind"]) != CurriculumAssetKind.FILE
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
