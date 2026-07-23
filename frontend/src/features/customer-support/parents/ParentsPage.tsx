import { useCallback, useState } from "react";
import { deleteSupport, sendSupport, type ParentDetail as ParentDetailModel, type ParentStudentLink } from "@/features/customer-support/api";
import { EditParentDialog, type EditParentValues } from "@/features/customer-support/parents/EditParentDialog";
import { LinkStudentDialog } from "@/features/customer-support/parents/LinkStudentDialog";
import { ParentDetail } from "@/features/customer-support/parents/ParentDetail";
import { ReasonDialog } from "@/features/customer-support/shared/ReasonDialog";
import { SupportPageLayout } from "@/features/customer-support/shared/SupportPageLayout";
import { useSupportMutation } from "@/features/customer-support/shared/useSupportMutation";
import { useSupportRecords } from "@/features/customer-support/shared/useSupportRecords";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";

type ParentDialog =
  | { type: "edit" }
  | { type: "link" }
  | { type: "reason"; action: "deactivate" | "reactivate" | "unlink"; title: string; student?: ParentStudentLink }
  | null;

export function ParentsPage({
  authLogin,
  csrfToken,
  title,
  description,
}: {
  authLogin: string;
  csrfToken: string;
  title: string;
  description: string;
}) {
  const controller = useSupportRecords("parent");
  const [dialog, setDialog] = useState<ParentDialog>(null);
  const { toast, showToast, clearToast } = useFloatingToast();
  const reportMutationError = useCallback((error: Error) => {
    const supportError = controller.reportError(error);
    if (["version_conflict", "active_dependencies", "school_scope_denied", "record_not_found"].includes(supportError.code)) {
      setDialog(null);
    }
    showToast(supportError.message, "error");
  }, [controller, showToast]);
  const { saving, runMutation } = useSupportMutation({
    onChanged: controller.reloadRecords,
    onError: reportMutationError,
    onSuccessMessage: (message) => showToast(message, "success"),
  });
  const detail = controller.detail;

  function editParent(values: EditParentValues) {
    if (!detail) return;
    void runMutation(
      () => sendSupport<ParentDetailModel>(`/parents/${detail.profile.id}`, "PATCH", {
        ...values,
        expectedVersion: detail.profile.version,
        reason: "Customer Support profile correction",
      }, csrfToken),
      (result) => {
        controller.setDetail(result);
        setDialog(null);
      },
      "Parent profile updated.",
    );
  }

  function updateLifecycle(action: "deactivate" | "reactivate", reason: string) {
    if (!detail) return;
    void runMutation(
      () => sendSupport<ParentDetailModel>(`/parents/${detail.profile.id}/${action}`, "POST", {
        expectedVersion: detail.profile.version,
        reason,
      }, csrfToken),
      (result) => {
        controller.setDetail(result);
        setDialog(null);
      },
      action === "deactivate" ? "Parent deactivated." : "Parent reactivated.",
    );
  }

  function linkStudent(studentId: number) {
    if (!detail) return;
    void runMutation(
      () => sendSupport<ParentDetailModel>(`/parents/${detail.profile.id}/children`, "POST", {
        studentId,
        expectedVersion: detail.profile.version,
      }, csrfToken),
      (result) => {
        controller.setDetail(result);
        setDialog(null);
      },
      "Student linked.",
    );
  }

  function unlinkStudent(student: ParentStudentLink, reason: string) {
    if (!detail) return;
    const params = new URLSearchParams({
      reason,
      expectedVersion: String(detail.profile.version),
    });
    void runMutation(
      () => deleteSupport<ParentDetailModel>(`/parents/${detail.profile.id}/children/${student.id}?${params}`, csrfToken),
      (result) => {
        controller.setDetail(result);
        setDialog(null);
      },
      "Student unlinked.",
    );
  }

  return (
    <>
      <SupportPageLayout
        controller={controller}
        authLogin={authLogin}
        title={title}
        description={description}
        detail={detail ? (
          <ParentDetail
            detail={detail}
            onEdit={() => setDialog({ type: "edit" })}
            onLink={() => setDialog({ type: "link" })}
            onUnlink={(student) => setDialog({ type: "reason", action: "unlink", title: `Unlink ${student.full_name}`, student })}
            onLifecycle={(reactivate) => setDialog({
              type: "reason",
              action: reactivate ? "reactivate" : "deactivate",
              title: reactivate ? "Reactivate parent" : "Deactivate parent",
            })}
          />
        ) : null}
      />

      {dialog?.type === "edit" && detail ? (
        <EditParentDialog
          profile={detail.profile}
          saving={saving}
          onClose={() => setDialog(null)}
          onSubmit={editParent}
        />
      ) : null}
      {dialog?.type === "link" && detail ? (
        <LinkStudentDialog
          parentId={detail.profile.id}
          saving={saving}
          onClose={() => setDialog(null)}
          onLink={linkStudent}
        />
      ) : null}
      {dialog?.type === "reason" ? (
        <ReasonDialog
          title={dialog.title}
          saving={saving}
          constructive={dialog.action === "reactivate"}
          onClose={() => setDialog(null)}
          onSubmit={(reason) => dialog.action === "unlink" && dialog.student
            ? unlinkStudent(dialog.student, reason)
            : updateLifecycle(dialog.action as "deactivate" | "reactivate", reason)}
        />
      ) : null}

      <FloatingToast toast={toast} onClose={clearToast} />
    </>
  );
}
