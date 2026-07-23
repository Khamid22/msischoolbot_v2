import { ArrowLeft, GraduationCap, ShieldCheck, UsersRound } from "lucide-react";
import type { ReactNode } from "react";
import type { SupportRecordKind } from "@/features/customer-support/model";
import { RecordList } from "@/features/customer-support/shared/RecordList";
import { RecordsSearchBar } from "@/features/customer-support/shared/RecordsSearchBar";
import { SupportErrorAlert } from "@/features/customer-support/shared/SupportErrorAlert";
import { DetailSkeleton, secondaryButton } from "@/features/customer-support/shared/ui";
import type { SupportRecordsController } from "@/features/customer-support/shared/useSupportRecords";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";

export function SupportPageLayout<K extends SupportRecordKind>({
  controller,
  authLogin,
  title,
  description,
  searchAction,
  detail,
}: {
  controller: SupportRecordsController<K>;
  authLogin: string;
  title: string;
  description: string;
  searchAction?: ReactNode;
  detail: ReactNode;
}) {
  const noun = controller.kind === "student" ? "student" : "parent";
  const EmptyIcon = controller.kind === "student" ? GraduationCap : UsersRound;

  return (
    <div className="flex min-w-0 flex-col gap-4 overflow-x-hidden">
      <PageHeader
        title={title}
        subtitle={description}
        badge={<span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase tracking-wide text-primary">Customer Support</span>}
        actions={authLogin ? (
          <span className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-black text-muted-foreground">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
            <span className="truncate">{authLogin}</span>
          </span>
        ) : undefined}
      />

      <RecordsSearchBar
        kind={controller.kind}
        context={controller.context}
        loadingContext={controller.loadingContext}
        query={controller.query}
        status={controller.status}
        schoolId={controller.schoolId}
        onQueryChange={controller.setQuery}
        onStatusChange={controller.setStatus}
        onSchoolChange={controller.setSchoolId}
        action={searchAction}
      />

      <SupportErrorAlert
        state={controller.errorState}
        onReload={controller.reloadDetail}
        onDismiss={() => controller.setErrorState(null)}
      />

      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.55fr)]">
        <RecordList
          kind={controller.kind}
          items={controller.records}
          selectedId={controller.selectedId}
          loading={controller.loadingRecords}
          loadingMore={controller.loadingMore}
          hasMore={Boolean(controller.nextCursor)}
          scrollRef={controller.listScrollRef}
          onSelect={controller.selectRecord}
          onLoadMore={() => void controller.loadMore()}
        />

        <section className={`${controller.selectedId ? "block" : "hidden lg:block"} min-w-0`} aria-label={`Selected ${noun}`}>
          {controller.selectedId ? (
            <button type="button" onClick={controller.closeDetail} className={`${secondaryButton} mb-3 lg:hidden`}>
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to {controller.kind === "student" ? "students" : "parents"}
            </button>
          ) : null}
          {controller.loadingDetail ? (
            <DetailSkeleton />
          ) : controller.detail ? (
            detail
          ) : !controller.selectedId ? (
            <EmptyState
              title={`Select a ${noun}`}
              detail={`Search and open a ${noun} record to view profile details and available support actions.`}
              icon={<EmptyIcon className="h-5 w-5" />}
            />
          ) : null}
        </section>
      </div>
    </div>
  );
}
