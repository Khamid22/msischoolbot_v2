import {
  Archive,
  BookOpen,
  Edit3,
  GraduationCap,
  KeyRound,
  RefreshCw,
  Send,
  ShieldCheck,
  UserRound,
  UsersRound,
} from "lucide-react";
import type { PaymentRecord, StudentDetail as StudentDetailModel } from "@/features/customer-support/model";
import { ActivityTimeline } from "@/features/customer-support/shared/ActivityTimeline";
import { dangerButton, DetailSection, Field, formatDate, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { StudentPaymentsSection } from "@/features/customer-support/students/StudentPaymentsSection";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function StudentDetail({
  detail,
  onEdit,
  onReset,
  onLifecycle,
  onInvite,
  onAddPayment,
  onEditPayment,
  onSettle,
  onVoid,
}: {
  detail: StudentDetailModel;
  onEdit: () => void;
  onReset: () => void;
  onLifecycle: (reactivate: boolean) => void;
  onInvite: () => void;
  onAddPayment: () => void;
  onEditPayment: (payment: PaymentRecord) => void;
  onSettle: (payment: PaymentRecord, paid: boolean) => void;
  onVoid: (payment: PaymentRecord) => void;
}) {
  const { profile } = detail;
  const archived = profile.status === "archived";
  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            {profile.photo_url ? (
              <img src={profile.photo_url} alt={profile.full_name} className="h-14 w-14 shrink-0 rounded-lg border border-border object-cover" />
            ) : (
              <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <GraduationCap className="h-6 w-6" aria-hidden="true" />
              </span>
            )}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="break-words text-xl font-black text-foreground">{profile.full_name}</h1>
                <StatusBadge status={profile.status} />
              </div>
              <p className="mt-1 break-words text-sm font-semibold text-muted-foreground">
                {profile.student_code} · {profile.school_name || "School not set"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onEdit}
              className={secondaryButton}
              disabled={archived}
              title={archived ? "Reactivate the student before editing the profile." : undefined}
            >
              <Edit3 className="h-4 w-4" aria-hidden="true" />
              Edit profile
            </button>
            <button type="button" onClick={() => onLifecycle(archived)} className={archived ? primaryButton : dangerButton}>
              {archived
                ? <RefreshCw className="h-4 w-4" aria-hidden="true" />
                : <Archive className="h-4 w-4" aria-hidden="true" />}
              {archived ? "Reactivate" : "Archive"}
            </button>
          </div>
        </div>
      </section>

      <DetailSection title="Profile" icon={<UserRound className="h-4 w-4" aria-hidden="true" />}>
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Field label="Full name" value={profile.full_name} />
          <Field label="Student code" value={profile.student_code} mono />
          <Field label="School" value={profile.school_name} />
          <Field label="Phone" value={profile.phone} />
          <Field label="Telegram" value={profile.telegram_username ? `@${profile.telegram_username}` : "Not linked"} />
          <Field label="Updated" value={formatDate(profile.updated_at, true)} />
        </dl>
        {profile.profile_description ? (
          <p className="mt-3 rounded-lg bg-muted px-3 py-2 text-sm leading-6 text-foreground">{profile.profile_description}</p>
        ) : null}
      </DetailSection>

      <DetailSection
        title="Account access"
        icon={<KeyRound className="h-4 w-4" aria-hidden="true" />}
        action={(
          <button type="button" onClick={onReset} className={secondaryButton}>
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            Reset access
          </button>
        )}
      >
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <Field label="Login" value={profile.login || profile.student_code} mono />
          <Field label="Account status" value={<StatusBadge status={profile.account_status || profile.status} className="text-[0.625rem]" />} />
          <Field label="Last login" value={formatDate(profile.last_login_at, true)} />
          <Field label="Password change required" value={profile.must_change_password ? "Yes" : "No"} />
        </dl>
        <p className="mt-3 text-xs font-semibold leading-5 text-muted-foreground">
          Passwords are protected and cannot be viewed. A reset creates a temporary password, invalidates existing sessions, and forces a password change.
        </p>
      </DetailSection>

      <DetailSection
        title="Family"
        icon={<UsersRound className="h-4 w-4" aria-hidden="true" />}
        action={(
          <button type="button" onClick={onInvite} className={secondaryButton}>
            <Send className="h-4 w-4" aria-hidden="true" />
            Create parent invite
          </button>
        )}
      >
        {detail.parents.length ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {detail.parents.map((parent) => (
              <article key={parent.id} className="rounded-lg border border-border bg-background p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="break-words text-sm font-black text-foreground">{parent.display_name || "Parent"}</p>
                  <StatusBadge status={parent.status} className="text-[0.625rem]" />
                </div>
                <p className="mt-1 break-words text-xs font-semibold text-muted-foreground">
                  {parent.phone || (parent.telegram_username ? `@${parent.telegram_username}` : "No contact")}
                </p>
                {parent.relationship ? <p className="mt-2 text-xs font-bold capitalize text-muted-foreground">{parent.relationship}</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm font-semibold text-muted-foreground">No parent is linked. Create an invitation to establish a verified link.</p>
        )}
      </DetailSection>

      <DetailSection title="Academic snapshot — read only" icon={<BookOpen className="h-4 w-4" aria-hidden="true" />}>
        {detail.academic.length ? (
          <div className="grid gap-2 md:grid-cols-2">
            {detail.academic.map((item) => (
              <article key={`${item.id}-${item.subject_id}`} className="rounded-lg border border-border bg-background p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="break-words text-sm font-black text-foreground">{item.subject_name}</p>
                    <p className="mt-1 break-words text-xs font-semibold text-muted-foreground">{item.group_name}</p>
                  </div>
                  <StatusBadge status={item.status} className="text-[0.625rem]" />
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
                  <div><dt className="text-[0.625rem] font-bold text-muted-foreground">HOMEWORK</dt><dd className="mt-1 text-sm font-black">{Number(item.homework_average || 0).toFixed(1)}</dd></div>
                  <div><dt className="text-[0.625rem] font-bold text-muted-foreground">EXAM</dt><dd className="mt-1 text-sm font-black">{Number(item.exam_average || 0).toFixed(1)}</dd></div>
                  <div><dt className="text-[0.625rem] font-bold text-muted-foreground">ATTENDANCE</dt><dd className="mt-1 text-sm font-black">{Number(item.attendanceRate || 0)}%</dd></div>
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm font-semibold text-muted-foreground">Not enrolled. Academic Department assigns subjects and groups.</p>
        )}
      </DetailSection>

      <StudentPaymentsSection detail={detail} onAdd={onAddPayment} onEdit={onEditPayment} onSettle={onSettle} onVoid={onVoid} />
      <DetailSection title="Activity" icon={<ShieldCheck className="h-4 w-4" aria-hidden="true" />}>
        <ActivityTimeline items={detail.activity} />
      </DetailSection>
    </div>
  );
}
