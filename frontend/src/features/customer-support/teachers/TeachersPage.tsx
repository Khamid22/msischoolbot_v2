import { ArrowLeft, ContactRound, ShieldCheck } from "lucide-react";
import { DetailSkeleton, secondaryButton } from "@/features/customer-support/shared/ui";
import { SupportErrorAlert } from "@/features/customer-support/shared/SupportErrorAlert";
import { TeacherDetail } from "@/features/customer-support/teachers/TeacherDetail";
import { TeacherFilters } from "@/features/customer-support/teachers/TeacherFilters";
import { TeacherList } from "@/features/customer-support/teachers/TeacherList";
import { useTeacherDirectory } from "@/features/customer-support/teachers/useTeacherDirectory";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";

export function TeachersPage({
  authLogin,
  title,
  description,
}: {
  authLogin: string;
  title: string;
  description: string;
}) {
  const controller = useTeacherDirectory();

  return (
    <div className="flex min-w-0 flex-col gap-4 overflow-x-hidden">
      <PageHeader
        title={title}
        subtitle={description}
        badge={(
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase tracking-wide text-primary">
            Customer Support
          </span>
        )}
        actions={authLogin ? (
          <span className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-black text-muted-foreground">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
            <span className="truncate">{authLogin}</span>
          </span>
        ) : undefined}
      />

      <TeacherFilters
        context={controller.context}
        loadingContext={controller.loadingContext}
        query={controller.query}
        status={controller.status}
        schoolId={controller.schoolId}
        onQueryChange={controller.setQuery}
        onStatusChange={controller.setStatus}
        onSchoolChange={controller.setSchoolId}
      />

      <SupportErrorAlert
        state={controller.errorState}
        onDismiss={controller.dismissError}
      />

      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.55fr)]">
        <TeacherList
          items={controller.teachers}
          selectedId={controller.selectedId}
          loading={controller.loadingTeachers}
          loadingMore={controller.loadingMore}
          hasMore={Boolean(controller.nextCursor)}
          scrollRef={controller.listScrollRef}
          onSelect={controller.selectTeacher}
          onLoadMore={() => void controller.loadMore()}
        />

        <section
          className={`${controller.selectedId ? "block" : "hidden lg:block"} min-w-0`}
          aria-label="Selected teacher"
        >
          {controller.selectedId ? (
            <button
              type="button"
              onClick={controller.closeDetail}
              className={`${secondaryButton} mb-3 lg:hidden`}
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to teachers
            </button>
          ) : null}
          {controller.loadingDetail ? (
            <DetailSkeleton />
          ) : controller.detail ? (
            <TeacherDetail detail={controller.detail} />
          ) : controller.detailUnavailable ? (
            <EmptyState
              title="Teacher unavailable"
              detail="This teacher could not be loaded from your assigned schools."
              icon={<ContactRound className="h-5 w-5" />}
            />
          ) : !controller.selectedId ? (
            <EmptyState
              title="Select a teacher"
              detail="Search and open an assigned-school teacher to review support information."
              icon={<ContactRound className="h-5 w-5" />}
            />
          ) : null}
        </section>
      </div>
    </div>
  );
}
