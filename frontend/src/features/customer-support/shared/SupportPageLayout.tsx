import { ArrowLeft, GraduationCap, ShieldCheck, UsersRound } from "lucide-react";
import type { ReactNode } from "react";
import type { SupportRecordKind } from "@/features/customer-support/model";
import {
  MasterDetailLayout,
  resolveMasterDetailCollectionState,
} from "@/features/customer-support/shared/MasterDetailLayout";
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
  const hasDetailError = Boolean(
    controller.selectedId
    && !controller.loadingDetail
    && !controller.detail
    && controller.errorState,
  );
  const collectionState = resolveMasterDetailCollectionState({
    isLoading: controller.loadingRecords,
    isError: Boolean(controller.errorState && !hasDetailError),
    itemCount: controller.records.length,
  });
  const recordList = (
    <RecordList
      kind={controller.kind}
      items={controller.records}
      selectedId={controller.selectedId}
      loading={controller.loadingRecords}
      loadingMore={controller.loadingMore}
      hasMore={Boolean(controller.nextCursor)}
      allRecordsLoaded={controller.allRecordsLoaded}
      fixedSchoolLabel={controller.fixedSchoolLabel}
      scrollRef={controller.listScrollRef}
      onSelect={controller.selectRecord}
      onLoadMore={() => void controller.loadMore()}
    />
  );

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
        fixedSchoolLabel={controller.fixedSchoolLabel}
        onQueryChange={controller.setQuery}
        onStatusChange={controller.setStatus}
        onSchoolChange={controller.setSchoolId}
        action={searchAction}
      />

      {!hasDetailError && collectionState !== "error" ? (
        <SupportErrorAlert
          state={controller.errorState}
          onReload={controller.reloadRecords}
          onDismiss={() => controller.setErrorState(null)}
        />
      ) : null}

      <MasterDetailLayout
        collectionState={collectionState}
        isDetailOpen={Boolean(controller.selectedId)}
        desktopColumnsClassName="lg:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.55fr)]"
        collection={recordList}
        fallback={collectionState === "loading" ? recordList : (
          <EmptyState
            title={collectionState === "error"
              ? `${title} could not be loaded`
              : `No matching ${noun}s`}
            detail={collectionState === "error"
              ? controller.errorState?.error.message
              : "Try another name, contact, school, or status."}
            icon={<EmptyIcon className="h-5 w-5" />}
            action={(
              <button
                type="button"
                className={secondaryButton}
                onClick={() => {
                  if (collectionState === "error") {
                    controller.reloadRecords();
                    return;
                  }
                  controller.setQuery("");
                  controller.setStatus("all");
                  controller.setSchoolId("");
                }}
              >
                {collectionState === "error" ? "Try again" : "Reset filters"}
              </button>
            )}
          />
        )}
        detail={(
          <section className="min-w-0" aria-label={`Selected ${noun}`}>
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
          ) : hasDetailError ? (
            <SupportErrorAlert
              state={controller.errorState}
              onReload={controller.reloadDetail}
              onDismiss={() => controller.setErrorState(null)}
            />
          ) : !controller.selectedId ? (
            <EmptyState
              title={`Select a ${noun}`}
              detail={`Search and open a ${noun} record to view profile details and available support actions.`}
              icon={<EmptyIcon className="h-5 w-5" />}
            />
          ) : null}
          </section>
        )}
      />
    </div>
  );
}
