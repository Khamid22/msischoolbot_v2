import { BookOpen, ContactRound, School, ShieldCheck, UsersRound } from "lucide-react";
import type { TeacherDetail as TeacherDetailModel } from "@/features/customer-support/model";
import { DetailSection, Field } from "@/features/customer-support/shared/ui";
import { StatusBadge } from "@/shared/ui/StatusBadge";

function AssignmentTags({
  items,
  emptyLabel,
}: {
  items: string[];
  emptyLabel: string;
}) {
  if (!items.length) {
    return <p className="text-sm font-semibold text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full border border-border bg-background px-3 py-1.5 text-xs font-black text-foreground"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export function TeacherDetail({ detail }: { detail: TeacherDetailModel }) {
  const { teacher } = detail;

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="break-words text-xl font-black text-foreground">
                {teacher.fullName || "Teacher"}
              </h1>
              <StatusBadge status={teacher.accountStatus} />
            </div>
            <p className="mt-1 break-words text-sm font-semibold text-muted-foreground">
              {teacher.login || teacher.phone || "No account contact"}
            </p>
          </div>
          <span className="inline-flex min-h-10 items-center gap-2 self-start rounded-lg border border-sky-200 bg-sky-50 px-3 text-xs font-black text-sky-800">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Read-only support view
          </span>
        </div>
      </section>

      <DetailSection
        title="Account and contact"
        icon={<ContactRound className="h-4 w-4" aria-hidden="true" />}
      >
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Field label="Full name" value={teacher.fullName} />
          <Field label="Login" value={teacher.login || "Not provisioned"} mono />
          <Field
            label="Account status"
            value={(
              <StatusBadge
                status={teacher.accountStatus}
                className="text-[0.625rem]"
              />
            )}
          />
          <Field label="Phone" value={teacher.phone || "Not set"} />
          <Field
            label="Telegram"
            value={teacher.telegramUsername ? `@${teacher.telegramUsername}` : "Not linked"}
          />
          <Field
            label="Assigned groups"
            value={String(teacher.assignedGroupCount)}
          />
        </dl>
      </DetailSection>

      <DetailSection
        title="Schools"
        icon={<School className="h-4 w-4" aria-hidden="true" />}
      >
        <AssignmentTags
          items={teacher.schoolNames}
          emptyLabel="No school assignment is available."
        />
      </DetailSection>

      <DetailSection
        title="Subjects"
        icon={<BookOpen className="h-4 w-4" aria-hidden="true" />}
      >
        <AssignmentTags
          items={teacher.subjectNames}
          emptyLabel="No active subject assignment is available."
        />
      </DetailSection>

      <DetailSection
        title="Groups"
        icon={<UsersRound className="h-4 w-4" aria-hidden="true" />}
      >
        <AssignmentTags
          items={detail.assignedGroupNames}
          emptyLabel="No active group assignment is available."
        />
      </DetailSection>
    </div>
  );
}
