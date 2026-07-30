import type { ReactNode } from "react";

export type MasterDetailCollectionState = "loading" | "error" | "empty" | "ready";

export function resolveMasterDetailCollectionState({
  isLoading,
  isError,
  itemCount,
}: {
  isLoading: boolean;
  isError: boolean;
  itemCount: number;
}): MasterDetailCollectionState {
  if (itemCount > 0) return "ready";
  if (isLoading) return "loading";
  if (isError) return "error";
  return "empty";
}

export function MasterDetailLayout({
  collectionState,
  isDetailOpen,
  collection,
  detail,
  fallback,
  desktopColumnsClassName = "lg:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.55fr)]",
}: {
  collectionState: MasterDetailCollectionState;
  isDetailOpen: boolean;
  collection: ReactNode;
  detail: ReactNode;
  fallback: ReactNode;
  desktopColumnsClassName?: string;
}) {
  if (collectionState !== "ready") {
    return <div className="min-w-0">{fallback}</div>;
  }

  return (
    <div className={`grid min-w-0 gap-4 ${desktopColumnsClassName}`}>
      <div className={`${isDetailOpen ? "hidden lg:block" : "block"} min-w-0`}>
        {collection}
      </div>
      <div className={`${isDetailOpen ? "block" : "hidden lg:block"} min-w-0`}>
        {detail}
      </div>
    </div>
  );
}
