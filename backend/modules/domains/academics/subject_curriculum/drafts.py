"""Private Fundamentals draft orchestration and atomic publication."""

from __future__ import annotations

from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.academics.subject_curriculum import (
    repository,
    revision_repository,
)
from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumRevisionState,
    CurriculumVariant,
)
from backend.modules.domains.academics.subject_curriculum.draft_models import (
    build_draft_model,
    media_placements,
)
from backend.modules.domains.academics.subject_curriculum.exceptions import (
    CurriculumConflictError,
    CurriculumNotFoundError,
    CurriculumValidationError,
)
from backend.modules.domains.academics.subject_curriculum.read_models import guidance_from_row
from backend.modules.domains.academics.subject_curriculum.schemas import (
    CurriculumLessonDraft,
    FundamentalsLessonPublish,
    LessonGuidanceDocument,
)


def get_fundamentals_draft(
    subject_id: int,
    draft_id: int,
    *,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumLessonDraft:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.read() as unit_of_work:
        row = revision_repository.get_draft_row(unit_of_work.conn, draft_id)
        if (
            not row
            or int(row["subject_id"]) != subject_id
            or str(row["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
            or str(row["state"]) != CurriculumRevisionState.DRAFT
        ):
            raise CurriculumNotFoundError("Fundamentals lesson draft was not found.")
        return build_draft_model(unit_of_work.conn, row)


def start_fundamentals_draft(
    subject_id: int,
    *,
    item_id: int | None,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumLessonDraft:
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
        if item_id is None:
            item = revision_repository.insert_draft_item(
                unit_of_work.conn,
                curriculum_id=curriculum_id,
                item_order=repository.next_active_item_order(
                    unit_of_work.conn,
                    curriculum_id,
                ),
                actor_staff_id=actor_staff_id,
            )
            active_item_id = int(item["id"])
            revision = revision_repository.insert_draft_revision(
                unit_of_work.conn,
                item_id=active_item_id,
                title="Untitled Fundamentals lesson",
                guidance=LessonGuidanceDocument().model_dump(mode="json"),
                base_item_version=int(item["version"]),
                actor_staff_id=actor_staff_id,
            )
        else:
            current = repository.get_supplemental_item_row(
                unit_of_work.conn,
                item_id,
                for_update=True,
            )
            if (
                not current
                or int(current["subject_id"]) != subject_id
                or str(current["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
                or str(current["status"]) != "active"
            ):
                raise CurriculumNotFoundError("Active Fundamentals lesson was not found.")
            revision = revision_repository.get_item_draft_row(
                unit_of_work.conn,
                item_id,
                for_update=True,
            )
            if not revision:
                revision = revision_repository.insert_draft_revision(
                    unit_of_work.conn,
                    item_id=item_id,
                    title=str(current["title"]),
                    guidance=guidance_from_row(current).model_dump(mode="json"),
                    base_item_version=int(current["version"]),
                    actor_staff_id=actor_staff_id,
                )
                if current["published_revision_id"]:
                    revision_repository.copy_published_asset_placements(
                        unit_of_work.conn,
                        published_revision_id=int(current["published_revision_id"]),
                        draft_revision_id=int(revision["id"]),
                    )
            active_item_id = item_id
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_draft_started",
            entity_type="supplemental_curriculum_item",
            entity_id=active_item_id,
            detail={"subject_id": subject_id, "draft_id": int(revision["id"])},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_fundamentals_draft(
        subject_id,
        int(revision["id"]),
        unit_of_work_factory=factory,
    )


def publish_fundamentals_draft(
    subject_id: int,
    draft_id: int,
    payload: FundamentalsLessonPublish,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
):
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        draft = revision_repository.get_draft_row(
            unit_of_work.conn,
            draft_id,
            for_update=True,
        )
        if (
            not draft
            or int(draft["subject_id"]) != subject_id
            or str(draft["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
            or str(draft["state"]) != CurriculumRevisionState.DRAFT
        ):
            raise CurriculumNotFoundError("Fundamentals lesson draft was not found.")
        updated = revision_repository.update_draft(
            unit_of_work.conn,
            draft_id=draft_id,
            title=payload.title,
            guidance=payload.guidance.model_dump(mode="json"),
            expected_version=payload.expected_revision_version,
            actor_staff_id=actor_staff_id,
        )
        if not updated:
            raise CurriculumConflictError(
                "This draft changed in another session. Reload before publishing."
            )
        placements = media_placements(payload.guidance)
        attached_ids = set(
            revision_repository.list_attached_asset_ids(
                unit_of_work.conn,
                draft_id,
            )
        )
        referenced_ids = {
            int(str(placement["asset_id"])) for placement in placements
        }
        if not referenced_ids.issubset(attached_ids):
            raise CurriculumValidationError(
                "One or more lesson materials are no longer attached to this draft."
            )
        revision_repository.sync_asset_placements(
            unit_of_work.conn,
            revision_id=draft_id,
            placements=placements,
            actor_staff_id=actor_staff_id,
        )
        blocking = revision_repository.list_blocking_conversion_rows(
            unit_of_work.conn,
            draft_id,
        )
        if blocking:
            statuses = ", ".join(
                f"{row['title']} ({row['conversion_status']})" for row in blocking
            )
            raise CurriculumValidationError(
                f"Presentations must finish converting before publication: {statuses}."
            )
        curriculum_id = int(draft["curriculum_id"])
        repository.lock_supplemental_curriculum(unit_of_work.conn, curriculum_id)
        if str(draft["item_status"]) == "draft":
            revision_repository.prepare_new_item_for_publish(
                unit_of_work.conn,
                item_id=int(draft["item_id"]),
                curriculum_id=curriculum_id,
            )
        published = revision_repository.publish_draft(
            unit_of_work.conn,
            draft_id=draft_id,
            item_id=int(draft["item_id"]),
            curriculum_id=curriculum_id,
            title=payload.title,
            guidance=payload.guidance.model_dump(mode="json"),
            base_item_version=int(draft["base_item_version"]),
            actor_staff_id=actor_staff_id,
        )
        if not published:
            raise CurriculumConflictError(
                "The published lesson changed. Reload before publishing this draft."
            )
        repository.touch_curriculum(
            unit_of_work.conn,
            curriculum_id,
            actor_staff_id=actor_staff_id,
        )
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_draft_published",
            entity_type="supplemental_curriculum_item_revision",
            entity_id=draft_id,
            detail={
                "subject_id": subject_id,
                "item_id": int(draft["item_id"]),
                "asset_ids": sorted(referenced_ids),
            },
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    from backend.modules.domains.academics.subject_curriculum.contracts import (
        get_director_subject_curriculum,
    )

    return get_director_subject_curriculum(
        subject_id,
        CurriculumVariant.FUNDAMENTALS,
        unit_of_work_factory=factory,
    )


def update_fundamentals_draft(
    subject_id: int,
    draft_id: int,
    payload: FundamentalsLessonPublish,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> CurriculumLessonDraft:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        draft = revision_repository.get_draft_row(
            unit_of_work.conn,
            draft_id,
            for_update=True,
        )
        if (
            not draft
            or int(draft["subject_id"]) != subject_id
            or str(draft["curriculum_key"]) != CurriculumVariant.FUNDAMENTALS
            or str(draft["state"]) != CurriculumRevisionState.DRAFT
        ):
            raise CurriculumNotFoundError("Fundamentals lesson draft was not found.")
        placements = media_placements(payload.guidance)
        attached_ids = set(
            revision_repository.list_attached_asset_ids(
                unit_of_work.conn,
                draft_id,
            )
        )
        referenced_ids = {
            int(str(placement["asset_id"])) for placement in placements
        }
        if not referenced_ids.issubset(attached_ids):
            raise CurriculumValidationError(
                "One or more lesson materials are no longer attached to this draft."
            )
        updated = revision_repository.update_draft(
            unit_of_work.conn,
            draft_id=draft_id,
            title=payload.title,
            guidance=payload.guidance.model_dump(mode="json"),
            expected_version=payload.expected_revision_version,
            actor_staff_id=actor_staff_id,
        )
        if not updated:
            raise CurriculumConflictError(
                "This draft changed in another session. Reload before editing."
            )
        revision_repository.sync_asset_placements(
            unit_of_work.conn,
            revision_id=draft_id,
            placements=placements,
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()
    return get_fundamentals_draft(
        subject_id,
        draft_id,
        unit_of_work_factory=factory,
    )


def abandon_fundamentals_draft(
    subject_id: int,
    draft_id: int,
    *,
    actor_staff_id: int | None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> None:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        draft = revision_repository.get_draft_row(
            unit_of_work.conn,
            draft_id,
            for_update=True,
        )
        if (
            not draft
            or int(draft["subject_id"]) != subject_id
            or str(draft["state"]) != CurriculumRevisionState.DRAFT
        ):
            raise CurriculumNotFoundError("Fundamentals lesson draft was not found.")
        abandoned = revision_repository.abandon_draft(
            unit_of_work.conn,
            draft_id=draft_id,
            actor_staff_id=actor_staff_id,
        )
        if not abandoned:
            raise CurriculumConflictError("This draft is no longer editable.")
        repository.insert_audit_event(
            unit_of_work.conn,
            event_type="academic.curriculum_draft_abandoned",
            entity_type="supplemental_curriculum_item_revision",
            entity_id=draft_id,
            detail={"subject_id": subject_id, "item_id": int(draft["item_id"])},
            actor_staff_id=actor_staff_id,
        )
        unit_of_work.commit()


__all__ = [
    "abandon_fundamentals_draft",
    "get_fundamentals_draft",
    "publish_fundamentals_draft",
    "start_fundamentals_draft",
    "update_fundamentals_draft",
]
