import { Banknote, Plus } from "lucide-react";
import { useCallback, useState } from "react";
import {
  sendSupport,
  type ParentInviteResult,
  type PaymentPayload,
  type PaymentRecord,
  type StudentDetail,
  type StudentMutationResult,
} from "@/features/customer-support/api";
import { CredentialsDialog } from "@/features/customer-support/shared/CredentialsDialog";
import { ReasonDialog } from "@/features/customer-support/shared/ReasonDialog";
import { SupportPageLayout } from "@/features/customer-support/shared/SupportPageLayout";
import { money, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { useSupportMutation } from "@/features/customer-support/shared/useSupportMutation";
import { useSupportRecords } from "@/features/customer-support/shared/useSupportRecords";
import { CreateStudentDialog, type CreateStudentValues } from "@/features/customer-support/students/CreateStudentDialog";
import { EditStudentDialog, type EditStudentValues } from "@/features/customer-support/students/EditStudentDialog";
import { PaymentDialog, type PaymentValues } from "@/features/customer-support/students/PaymentDialog";
import { StudentDetail as StudentDetailView } from "@/features/customer-support/students/StudentDetail";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type StudentDialog =
  | { type: "create" }
  | { type: "edit" }
  | { type: "credentials"; title: string; result: StudentMutationResult["credentials"] }
  | { type: "invite"; result: ParentInviteResult }
  | { type: "reason"; action: "archive" | "reactivate" | "void"; title: string; payment?: PaymentRecord }
  | { type: "payment"; payment?: PaymentRecord }
  | null;

export function StudentsPage({
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
  const controller = useSupportRecords("student", {
    fixedSchoolKey: "school5",
    fixedSchoolLabel: "School 5",
    loadAll: true,
  });
  const [dialog, setDialog] = useState<StudentDialog>(null);
  const [settlementTarget, setSettlementTarget] = useState<{ payment: PaymentRecord; paid: boolean } | null>(null);
  const { toast, showToast, clearToast } = useFloatingToast();
  const reportMutationError = useCallback((error: Error) => {
    const supportError = controller.reportError(error);
    if (["version_conflict", "active_dependencies", "school_scope_denied", "record_not_found"].includes(supportError.code)) {
      setDialog(null);
      setSettlementTarget(null);
    }
    showToast(supportError.message, "error");
  }, [controller, showToast]);
  const { saving, runMutation } = useSupportMutation({
    onChanged: controller.reloadRecords,
    onError: reportMutationError,
    onSuccessMessage: (message) => showToast(message, "success"),
  });
  const detail = controller.detail;

  function copy(value: string, label: string) {
    void navigator.clipboard.writeText(value)
      .then(() => showToast(`${label} copied.`, "success"))
      .catch(() => showToast(`Could not copy ${label.toLowerCase()}.`, "error"));
  }

  function createStudent(values: CreateStudentValues) {
    void runMutation(
      () => sendSupport<StudentMutationResult>("/students", "POST", values, csrfToken),
      (result) => {
        controller.openRecord(result.record.profile.id, result.record);
        setDialog({ type: "credentials", title: "Student account created", result: result.credentials });
      },
      "Student created.",
    );
  }

  function editStudent(values: EditStudentValues) {
    if (!detail) return;
    void runMutation(
      () => sendSupport<StudentDetail>(`/students/${detail.profile.id}`, "PATCH", {
        ...values,
        expectedVersion: detail.profile.version,
        reason: "Customer Support profile correction",
      }, csrfToken),
      (result) => {
        controller.setDetail(result);
        setDialog(null);
      },
      "Student profile updated.",
    );
  }

  function submitLifecycle(action: "archive" | "reactivate", reason: string) {
    if (!detail) return;
    void runMutation(
      () => sendSupport<StudentDetail>(`/students/${detail.profile.id}/${action}`, "POST", {
        expectedVersion: detail.profile.version,
        reason,
      }, csrfToken),
      (result) => {
        controller.setDetail(result);
        setDialog(null);
      },
      action === "archive" ? "Student archived." : "Student reactivated.",
    );
  }

  function resetAccess() {
    if (!detail) return;
    void runMutation(
      () => sendSupport<StudentMutationResult>(`/students/${detail.profile.id}/reset-access`, "POST", {
        expectedVersion: detail.profile.version,
      }, csrfToken),
      (result) => {
        controller.setDetail(result.record);
        setDialog({ type: "credentials", title: "Temporary access generated", result: result.credentials });
      },
      "Student access reset.",
    );
  }

  function createInvite() {
    if (!detail) return;
    void runMutation(
      () => sendSupport<ParentInviteResult>(`/students/${detail.profile.id}/parent-invites`, "POST", {
        expectedVersion: detail.profile.version,
      }, csrfToken),
      (result) => setDialog({ type: "invite", result }),
      "Parent invitation created.",
    );
  }

  function savePayment(values: PaymentValues, existing?: PaymentRecord) {
    if (!detail) return;
    const path = existing ? `/payments/${existing.id}` : `/students/${detail.profile.id}/payments`;
    const body = existing
      ? {
          expectedVersion: existing.version,
          monthLabel: values.monthLabel,
          amount: values.amount,
          currency: values.currency,
          dueDate: values.dueDate,
          notes: values.notes,
          reason: "Customer Support payment correction",
        }
      : {
          expectedVersion: detail.profile.version,
          subjectId: values.subjectId,
          monthLabel: values.monthLabel,
          amount: values.amount,
          currency: values.currency,
          dueDate: values.dueDate,
          paidAt: values.paidAt,
          notes: values.notes,
        };
    void runMutation(
      () => sendSupport<PaymentPayload>(path, existing ? "PATCH" : "POST", body, csrfToken),
      (payments) => {
        controller.setDetail({ ...detail, payments });
        setDialog(null);
      },
      existing ? "Payment updated." : "Payment created.",
    );
  }

  function voidPayment(payment: PaymentRecord, reason: string) {
    if (!detail) return;
    void runMutation(
      () => sendSupport<PaymentPayload>(`/payments/${payment.id}/void`, "POST", {
        expectedVersion: payment.version,
        reason,
      }, csrfToken),
      (payments) => {
        controller.setDetail({ ...detail, payments });
        setDialog(null);
      },
      "Payment voided.",
    );
  }

  function settlePayment() {
    if (!detail || !settlementTarget) return;
    const { payment, paid } = settlementTarget;
    void runMutation(
      () => sendSupport<PaymentPayload>(`/payments/${payment.id}/settlement`, "POST", {
        expectedVersion: payment.version,
        paid,
        paidAt: paid ? new Date().toISOString().slice(0, 10) : "",
        reason: paid ? "Payment confirmed by Customer Support" : "Settlement correction by Customer Support",
      }, csrfToken),
      (payments) => {
        controller.setDetail({ ...detail, payments });
        setSettlementTarget(null);
      },
      paid ? "Payment marked paid." : "Payment marked unpaid.",
    );
  }

  const activeSubjects = detail?.academic.filter((item) => item.status === "active") || [];

  return (
    <>
      <SupportPageLayout
        controller={controller}
        authLogin={authLogin}
        title={title}
        description={description}
        searchAction={(
          <button type="button" className={primaryButton} onClick={() => setDialog({ type: "create" })}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            New student
          </button>
        )}
        detail={detail ? (
          <StudentDetailView
            detail={detail}
            onEdit={() => setDialog({ type: "edit" })}
            onReset={resetAccess}
            onLifecycle={(reactivate) => setDialog({
              type: "reason",
              action: reactivate ? "reactivate" : "archive",
              title: reactivate ? "Reactivate student" : "Archive student",
            })}
            onInvite={createInvite}
            onAddPayment={() => setDialog({ type: "payment" })}
            onEditPayment={(payment) => setDialog({ type: "payment", payment })}
            onSettle={(payment, paid) => setSettlementTarget({ payment, paid })}
            onVoid={(payment) => setDialog({ type: "reason", action: "void", title: "Void payment", payment })}
          />
        ) : null}
      />

      {dialog?.type === "create" ? (
        <CreateStudentDialog
          schools={controller.context?.schools || []}
          defaultSchoolId={controller.schoolId}
          saving={saving}
          onClose={() => setDialog(null)}
          onSubmit={createStudent}
        />
      ) : null}
      {dialog?.type === "edit" && detail ? (
        <EditStudentDialog
          profile={detail.profile}
          schools={controller.context?.schools || []}
          saving={saving}
          onClose={() => setDialog(null)}
          onSubmit={editStudent}
        />
      ) : null}
      {dialog?.type === "credentials" ? (
        <CredentialsDialog
          mode="credentials"
          title={dialog.title}
          credentials={dialog.result}
          onCopy={copy}
          onClose={() => setDialog(null)}
        />
      ) : null}
      {dialog?.type === "invite" ? (
        <CredentialsDialog
          mode="invite"
          title="Parent invitation created"
          invite={dialog.result}
          onCopy={copy}
          onClose={() => setDialog(null)}
        />
      ) : null}
      {dialog?.type === "payment" && detail ? (
        <PaymentDialog
          payment={dialog.payment}
          activeSubjects={activeSubjects}
          saving={saving}
          onClose={() => setDialog(null)}
          onSubmit={(values) => savePayment(values, dialog.payment)}
        />
      ) : null}
      {dialog?.type === "reason" ? (
        <ReasonDialog
          title={dialog.title}
          saving={saving}
          constructive={dialog.action === "reactivate"}
          onClose={() => setDialog(null)}
          onSubmit={(reason) => dialog.action === "void" && dialog.payment
            ? voidPayment(dialog.payment, reason)
            : submitLifecycle(dialog.action as "archive" | "reactivate", reason)}
        />
      ) : null}
      {settlementTarget ? (
        <Modal
          title={settlementTarget.paid ? "Mark payment as paid?" : "Mark payment as unpaid?"}
          subtitle="The settlement status and audit history will be updated."
          onClose={() => setSettlementTarget(null)}
          size="sm"
          mobileMode="fullscreen"
        >
          <ModalBody>
            <div className="rounded-lg border border-border bg-muted p-4">
              <p className="font-black text-foreground">{settlementTarget.payment.subject || "Subject"} · {settlementTarget.payment.month_label || "Payment"}</p>
              <p className="mt-1 text-sm font-semibold text-muted-foreground">{money(settlementTarget.payment.amount, settlementTarget.payment.currency)}</p>
            </div>
          </ModalBody>
          <ModalFooter>
            <div className="flex justify-end gap-2">
              <button type="button" className={secondaryButton} onClick={() => setSettlementTarget(null)}>Cancel</button>
              <button type="button" disabled={saving} className={primaryButton} onClick={settlePayment}>
                <Banknote className="h-4 w-4" aria-hidden="true" />
                Confirm
              </button>
            </div>
          </ModalFooter>
        </Modal>
      ) : null}

      <FloatingToast toast={toast} onClose={clearToast} />
    </>
  );
}
