"""Source-level guards for the shared modal/bottom-sheet system."""

from pathlib import Path


def test_shared_modal_component_uses_portal_backdrop_scroll_lock_and_top_z_index():
    source = Path("frontend/src/shared/ui/Modal.tsx").read_text()
    layers_source = Path("frontend/src/shared/ui/layers.ts").read_text()

    assert "export function Modal" in source
    assert 'import { createPortal } from "react-dom";' in source
    assert "return createPortal(" in source
    assert "document.body" in source
    # z-index comes from the shared layer scale; the overlay layer stays high.
    assert "fixed inset-0 ${uiLayers.overlay}" in source
    assert 'overlay: "z-[100]"' in layers_source
    assert "export function BottomSheet" in source
    assert "bg-foreground/60" in source
    assert "backdrop-blur-[2px]" in source
    assert "document.body.style.overflow = \"hidden\"" in source
    assert "document.body.style.overflow = previousBodyOverflow" in source
    assert "bodyLockCount" in source
    assert "keydown" in source
    assert "Escape" in source
    assert "onPointerDown" in source
    assert "closeOnOutsideClick" in source
    assert 'role="dialog"' in source
    assert 'aria-modal="true"' in source
    assert "slide-in-from-bottom-4" in source
    assert "zoom-in-95" in source
    assert "aria-label=\"Close\"" in source


def test_teacher_academy_modals_use_shared_modal_system_and_keep_assignment_selectors():
    source = Path("frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx").read_text()

    assert 'import { Modal } from "@/shared/ui/Modal";' in source
    assert "function ModalShell" in source
    assert "<Modal" in source
    assert "fixed inset-0 z-[80]" not in source
    assert "document.body.style.overflow" not in source
    assert "useDismissibleLayer" not in source
    assert 'title="New Academy Teacher"' in source
    assert 'title="New Head of Department"' in source
    assert 'title="Schedule Academy Lesson"' in source
    assert 'title="Assessment Report"' in source
    assert "Promote to Active Teacher" in source
    assert "size={wide ? \"wide\" : \"lg\"}" in source
    assert "name=\"assignment_id\"" in source
    assert "name=\"lesson_assignment_id\"" in source
    assert source.count("Select lesson assignment") >= 2


def test_announcement_composer_uses_shared_modal_system():
    source = Path("frontend/src/roles/admin/panels/AnnouncementsPanel.tsx").read_text()

    assert 'import { Modal } from "@/shared/ui/Modal";' in source
    assert "<Modal" in source
    assert 'size="md"' in source
    assert "fixed inset-0 z-50" not in source
    assert 'role="dialog"' not in source
    assert "useDismissibleLayer" not in source
    assert "New Announcement" in source
    assert "Edit Announcement" in source
