import { Archive, Edit3, GraduationCap, Link2, RefreshCw, ShieldCheck, Unlink, UserRound } from "lucide-react";
import type { ParentDetail as ParentDetailModel, ParentStudentLink } from "@/features/customer-support/model";
import { ActivityTimeline } from "@/features/customer-support/shared/ActivityTimeline";
import { dangerButton, DetailSection, Field, formatDate, money, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function ParentDetail({
  detail,
  onEdit,
  onLink,
  onUnlink,
  onLifecycle,
}: {
  detail: ParentDetailModel;
  onEdit: () => void;
  onLink: () => void;
  onUnlink: (student: ParentStudentLink) => void;
  onLifecycle: (reactivate: boolean) => void;
}) {
  const { profile } = detail;
  const active = profile.status === "active";
  const outstanding = detail.children.reduce((sum, child) => sum + Number(child.outstanding || 0), 0);

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="break-words text-xl font-black text-foreground">{profile.display_name || "Parent"}</h1>
              <StatusBadge status={profile.status} />
            </div>
            <p className="mt-1 break-words text-sm font-semibold text-muted-foreground">
              {profile.phone || (profile.telegram_username ? `@${profile.telegram_username}` : "No contact details")}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={onEdit} className={secondaryButton}>
              <Edit3 className="h-4 w-4" aria-hidden="true" />
              Edit profile
            </button>
            <button type="button" onClick={() => onLifecycle(!active)} className={active ? dangerButton : primaryButton}>
              {active
                ? <Archive className="h-4 w-4" aria-hidden="true" />
                : <RefreshCw className="h-4 w-4" aria-hidden="true" />}
              {active ? "Deactivate" : "Reactivate"}
            </button>
          </div>
        </div>
      </section>

      <DetailSection title="Profile and access" icon={<UserRound className="h-4 w-4" aria-hidden="true" />}>
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Field label="Full name" value={profile.display_name} />
          <Field label="Phone" value={profile.phone} />
          <Field label="Telegram" value={profile.telegram_username ? `@${profile.telegram_username}` : "Not linked"} />
          <Field label="Language" value={String(profile.preferred_language || "").toUpperCase()} />
          <Field label="Account status" value={<StatusBadge status={profile.account_status || profile.status} className="text-[0.625rem]" />} />
          <Field label="Last login" value={formatDate(profile.last_login_at, true)} />
        </dl>
      </DetailSection>

      <DetailSection
        title="Linked students"
        icon={<GraduationCap className="h-4 w-4" aria-hidden="true" />}
        action={(
          <button type="button" onClick={onLink} className={secondaryButton}>
            <Link2 className="h-4 w-4" aria-hidden="true" />
            Link student
          </button>
        )}
      >
        <div className="mb-3 flex flex-wrap gap-2">
          <span className="rounded-lg bg-muted px-3 py-2 text-xs font-black text-foreground">
            {detail.children.length} visible {detail.children.length === 1 ? "student" : "students"}
          </span>
          <span className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-black text-amber-800">Outstanding {money(outstanding)}</span>
        </div>
        {detail.hiddenChildCount > 0 ? (
          <p className="mb-3 rounded-lg border border-border bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
            {detail.hiddenChildCount} linked students are outside your assigned school scope.
          </p>
        ) : null}
        {detail.children.length ? (
          <div className="space-y-2">
            {detail.children.map((student) => (
              <article key={student.id} className="flex flex-col gap-3 rounded-lg border border-border bg-background p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="break-words text-sm font-black text-foreground">{student.full_name}</p>
                    <StatusBadge status={student.status} className="text-[0.625rem]" />
                  </div>
                  <p className="mt-1 break-words text-xs font-semibold text-muted-foreground">
                    {student.student_code} · {student.school_name} · Due {money(student.outstanding)}
                  </p>
                  {student.relationship ? <p className="mt-2 text-xs font-bold capitalize text-muted-foreground">{student.relationship}</p> : null}
                </div>
                <button type="button" onClick={() => onUnlink(student)} className={dangerButton}>
                  <Unlink className="h-4 w-4" aria-hidden="true" />
                  Unlink
                </button>
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm font-semibold text-muted-foreground">No visible linked students.</p>
        )}
      </DetailSection>

      <DetailSection title="Activity" icon={<ShieldCheck className="h-4 w-4" aria-hidden="true" />}>
        <ActivityTimeline items={detail.activity} />
      </DetailSection>
    </div>
  );
}
