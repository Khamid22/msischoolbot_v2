import { useCallback, useEffect, useRef, useState } from "react";
import {
  getSupport,
  SupportApiError,
  type SearchPayload,
  type SupportContext,
  type SupportDetailByKind,
  type SupportRecordKind,
  type SupportRecordSummary,
} from "@/features/customer-support/api";
import type { SupportErrorState } from "@/features/customer-support/shared/SupportErrorAlert";

type LocationState = {
  query: string;
  status: string;
  schoolId: string;
  selectedId: number | null;
};

type SupportRecordsOptions = {
  fixedSchoolId?: string;
  fixedSchoolLabel?: string;
  loadAll?: boolean;
};

function readLocation(): LocationState {
  const params = new URLSearchParams(window.location.search);
  return {
    query: params.get("q") || "",
    status: params.get("status") || "all",
    schoolId: params.get("school") || "",
    selectedId: Number(params.get("recordId") || 0) || null,
  };
}

function writeLocation(state: LocationState, push = false, detailEntry = false) {
  const params = new URLSearchParams();
  if (state.query) params.set("q", state.query);
  if (state.status !== "all") params.set("status", state.status);
  if (state.schoolId) params.set("school", state.schoolId);
  if (state.selectedId) params.set("recordId", String(state.selectedId));
  const url = `${window.location.pathname}${params.size ? `?${params}` : ""}`;
  window.history[push ? "pushState" : "replaceState"](
    detailEntry ? { ...window.history.state, supportDetail: true } : window.history.state,
    "",
    url,
  );
}

export function asSupportApiError(error: unknown, fallback: string) {
  if (error instanceof SupportApiError) return error;
  if (error instanceof Error) return new SupportApiError(error.message || fallback);
  return new SupportApiError(fallback);
}

export function useSupportRecords<K extends SupportRecordKind>(
  kind: K,
  options: SupportRecordsOptions = {},
) {
  const { fixedSchoolId = "", fixedSchoolLabel = "", loadAll = false } = options;
  const initial = useRef(readLocation()).current;
  const [context, setContext] = useState<SupportContext | null>(null);
  const [query, setQuery] = useState(initial.query);
  const [debouncedQuery, setDebouncedQuery] = useState(initial.query.trim());
  const [status, setStatus] = useState(initial.status);
  const [schoolId, setSchoolId] = useState(fixedSchoolId || initial.schoolId);
  const [records, setRecords] = useState<SupportRecordSummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(initial.selectedId);
  const [detail, setDetail] = useState<SupportDetailByKind[K] | null>(null);
  const [loadingContext, setLoadingContext] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(Boolean(initial.selectedId));
  const [errorState, setErrorState] = useState<SupportErrorState | null>(null);
  const [recordsReloadKey, setRecordsReloadKey] = useState(0);
  const [detailReloadKey, setDetailReloadKey] = useState(0);
  const listScrollRef = useRef<HTMLDivElement>(null);
  const recordsRequestId = useRef(0);
  const detailRequestId = useRef(0);
  const recordsController = useRef<AbortController | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 275);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onPopState = () => {
      const state = readLocation();
      setQuery(state.query);
      setDebouncedQuery(state.query.trim());
      setStatus(state.status);
      setSchoolId(fixedSchoolId || state.schoolId);
      setSelectedId(state.selectedId);
      if (!state.selectedId) setDetail(null);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [fixedSchoolId]);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingContext(true);
    getSupport<SupportContext>("/context", controller.signal)
      .then(setContext)
      .catch((error) => {
        if ((error as Error).name !== "AbortError") {
          setErrorState({ error: asSupportApiError(error, "Could not load Customer Support.") });
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingContext(false);
      });
    return () => controller.abort();
  }, []);

  const removeSelected = useCallback(() => {
    setSelectedId(null);
    setDetail(null);
    setLoadingDetail(false);
    const current = readLocation();
    writeLocation({ ...current, selectedId: null });
  }, []);

  const fetchRecords = useCallback(async (append: boolean, cursor?: string | null) => {
    recordsController.current?.abort();
    const controller = new AbortController();
    recordsController.current = controller;
    const requestId = ++recordsRequestId.current;
    append ? setLoadingMore(true) : setLoadingRecords(true);
    if (!append) setErrorState(null);

    const params = new URLSearchParams({ type: kind, status, limit: loadAll ? "50" : "25" });
    if (debouncedQuery) params.set("q", debouncedQuery);
    if (schoolId) params.set("schoolId", schoolId);
    if (append && cursor) params.set("cursor", cursor);

    try {
      if (loadAll) {
        const allItems: SupportRecordSummary[] = [];
        const seenCursors = new Set<string>();
        let pageCursor = "";

        do {
          if (pageCursor) params.set("cursor", pageCursor);
          else params.delete("cursor");
          const payload = await getSupport<SearchPayload>(`/records?${params}`, controller.signal);
          if (requestId !== recordsRequestId.current) return;
          allItems.push(...payload.items);
          pageCursor = payload.nextCursor || "";
          if (pageCursor && seenCursors.has(pageCursor)) {
            throw new SupportApiError("Student pagination returned a repeated cursor.");
          }
          if (pageCursor) seenCursors.add(pageCursor);
        } while (pageCursor);

        setRecords(allItems);
        setNextCursor(null);
        listScrollRef.current?.scrollTo({ top: 0 });
        return;
      }

      const payload = await getSupport<SearchPayload>(`/records?${params}`, controller.signal);
      if (requestId !== recordsRequestId.current) return;
      setRecords((current) => append ? [...current, ...payload.items] : payload.items);
      setNextCursor(payload.nextCursor || null);
      if (!append) listScrollRef.current?.scrollTo({ top: 0 });
    } catch (error) {
      if ((error as Error).name !== "AbortError" && requestId === recordsRequestId.current) {
        setErrorState({ error: asSupportApiError(error, `Could not load ${kind} records.`) });
      }
    } finally {
      if (requestId === recordsRequestId.current) {
        append ? setLoadingMore(false) : setLoadingRecords(false);
      }
    }
  }, [debouncedQuery, kind, loadAll, schoolId, status]);

  useEffect(() => {
    writeLocation({
      query: debouncedQuery,
      status,
      schoolId,
      selectedId,
    });
    void fetchRecords(false);
    return () => recordsController.current?.abort();
    // selectedId belongs in the URL but must not trigger a list request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, fetchRecords, recordsReloadKey, schoolId, status]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setLoadingDetail(false);
      return;
    }

    const controller = new AbortController();
    const requestId = ++detailRequestId.current;
    setLoadingDetail(true);
    setErrorState(null);
    getSupport<SupportDetailByKind[K]>(`/${kind === "student" ? "students" : "parents"}/${selectedId}`, controller.signal)
      .then((payload) => {
        if (requestId === detailRequestId.current) setDetail(payload);
      })
      .catch((error) => {
        if ((error as Error).name === "AbortError" || requestId !== detailRequestId.current) return;
        const supportError = asSupportApiError(error, "Could not load this record.");
        setDetail(null);
        setErrorState({ error: supportError, canReload: supportError.code === "version_conflict" });
        if (supportError.code === "school_scope_denied" || supportError.code === "record_not_found") {
          removeSelected();
        }
      })
      .finally(() => {
        if (requestId === detailRequestId.current) setLoadingDetail(false);
      });
    return () => controller.abort();
  }, [detailReloadKey, kind, removeSelected, selectedId]);

  const selectRecord = useCallback((item: SupportRecordSummary) => {
    setSelectedId(item.id);
    setDetail(null);
    writeLocation({
      query: query.trim(),
      status,
      schoolId,
      selectedId: item.id,
    }, true, true);
  }, [query, schoolId, status]);

  const openRecord = useCallback((id: number, nextDetail?: SupportDetailByKind[K]) => {
    setSelectedId(id);
    setDetail(nextDetail || null);
    writeLocation({
      query: query.trim(),
      status,
      schoolId,
      selectedId: id,
    }, true, true);
  }, [query, schoolId, status]);

  const closeDetail = useCallback(() => {
    if (window.history.state?.supportDetail) {
      window.history.back();
      return;
    }
    removeSelected();
  }, [removeSelected]);

  const reloadDetail = useCallback(() => {
    setErrorState(null);
    setDetailReloadKey((current) => current + 1);
  }, []);

  const reloadRecords = useCallback(() => {
    setRecordsReloadKey((current) => current + 1);
  }, []);

  const reportError = useCallback((error: unknown, fallback = "The change could not be saved.") => {
    const supportError = asSupportApiError(error, fallback);
    setErrorState({
      error: supportError,
      canReload: supportError.code === "version_conflict",
    });
    if (supportError.code === "school_scope_denied" || supportError.code === "record_not_found") {
      removeSelected();
    }
    return supportError;
  }, [removeSelected]);

  return {
    kind,
    fixedSchoolLabel,
    allRecordsLoaded: loadAll,
    context,
    query,
    setQuery,
    status,
    setStatus,
    schoolId,
    setSchoolId,
    records,
    nextCursor,
    selectedId,
    detail,
    setDetail,
    loadingContext,
    loadingRecords,
    loadingMore,
    loadingDetail,
    errorState,
    setErrorState,
    listScrollRef,
    selectRecord,
    openRecord,
    closeDetail,
    removeSelected,
    loadMore: () => fetchRecords(true, nextCursor),
    reloadDetail,
    reloadRecords,
    reportError,
  };
}

export type SupportRecordsController<K extends SupportRecordKind> = ReturnType<typeof useSupportRecords<K>>;
