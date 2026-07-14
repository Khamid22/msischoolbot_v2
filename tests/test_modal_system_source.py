"""Source-level guards for the shared modal/bottom-sheet system."""

from pathlib import Path


def test_shared_modal_component_uses_portal_backdrop_scroll_lock_and_top_z_index():
    source = Path("frontend/src/shared/ui/Modal.tsx").read_text()
    hook_source = Path("frontend/src/shared/ui/useBodyScrollLock.ts").read_text()
    layers_source = Path("frontend/src/shared/ui/layers.ts").read_text()

    assert "export function Modal" in source
    assert "export function ModalHeader" in source
    assert "export function ModalBody" in source
    assert "export function ModalFooter" in source
    assert "export function useBodyScrollLock" in hook_source
    assert 'import { createPortal } from "react-dom";' in source
    assert "return createPortal(" in source
    assert "document.body" in source
    # z-index comes from the shared layer scale; the overlay layer stays high.
    assert "fixed inset-0 ${uiLayers.overlay}" in source
    assert 'toast: "z-[80]"' in layers_source
    assert 'overlay: "z-[100]"' in layers_source
    assert 'popover: "z-[120]"' in layers_source
    assert "export function BottomSheet" in source
    assert "bg-foreground/60" in source
    assert "backdrop-blur-[2px]" in source
    assert 'data-modal-backdrop="true"' in source
    assert "document.body.style.overflow = \"hidden\"" in hook_source
    assert "document.body.style.overflow = previousBodyOverflow" in hook_source
    assert "bodyLockCount" in hook_source
    assert "keydown" in source
    assert "Escape" in source
    assert "onPointerDown" in source
    assert "closeOnOutsideClick" in source
    assert 'role="dialog"' in source
    assert 'aria-modal="true"' in source
    assert 'mobileMode = "sheet"' in source
    assert 'data-mobile-mode={mobileMode}' in source
    assert 'mobileMode === "fullscreen"' in source
    assert "slide-in-from-bottom-4" in source
    assert "zoom-in-95" in source
    assert "duration-200" in source
    assert "motion-reduce:animate-none" in source
    assert "aria-label=\"Close\"" in source
    assert "pb-[calc(var(--app-bottom-inset)+0.75rem)]" in source


def test_teacher_academy_modals_use_shared_modal_system_and_keep_assignment_selectors():
    source = Path("frontend/src/features/teacher-academy/TeacherAcademyPanel.tsx").read_text()

    assert 'import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";' in source
    assert "function ModalShell" in source
    assert "<Modal" in source
    assert "<ModalBody" in source
    assert "<ModalFooter" in source
    assert "mobileMode=\"fullscreen\"" in source
    assert "fixed inset-0 z-[80]" not in source
    assert "document.body.style.overflow" not in source
    assert "sticky bottom-0" not in source
    assert "useDismissibleLayer" not in source
    assert 'title="New Academy Teacher"' in source
    assert 'title="New Head of Department"' in source
    assert 'title="Schedule Academy Lesson"' in source
    assert 'title="Assessment Report"' in source
    assert "Promote to Active Teacher" in source
    assert "size={wide ? \"wide\" : \"lg\"}" in source
    assert "name=\"assignment_id\"" in source
    # The assessment modal assesses the lesson row it was opened from, so the
    # assignment id is set programmatically instead of via a selector.
    assert "fields.lesson_assignment_id = String(asNumber(assignment.id));" in source
    assert source.count("Select lesson assignment") >= 1
    assert "const [wizardStep, setWizardStep]" in source
    assert "Teacher Info" in source
    assert "Select Academy Lessons" in source
    assert "Review & Create" in source
    assert "Select first 6" in source
    assert "Select first 12" in source
    assert "Show details" in source
    assert "fields.academy_curriculum_item_ids = selectedLessonIds.join" not in source
    assert "academy_curriculum_item_ids: selectedLessonIds.join" in source


def test_announcement_composer_uses_shared_modal_system():
    source = Path("frontend/src/features/communications/AnnouncementsPanel.tsx").read_text()

    assert 'import { Modal } from "@/shared/ui/Modal";' in source
    assert "<Modal" in source
    assert 'size="md"' in source
    assert "fixed inset-0 z-50" not in source
    assert 'role="dialog"' not in source
    assert "useDismissibleLayer" not in source
    assert "New Announcement" in source
    assert "Edit Announcement" in source
