import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  getSupport,
  getSupportTeacher,
  listSupportTeachers,
  type SupportContext,
  type TeacherDirectoryItem,
} from "@/features/customer-support/api";
import type { SupportErrorState } from "@/features/customer-support/shared/SupportErrorAlert";
import { asSupportApiError } from "@/features/customer-support/shared/useSupportRecords";

const TEACHER_SEARCH_DEBOUNCE_MS = 275;
const TEACHER_PAGE_SIZE = 25;

type TeacherLocationState = {
  query: string;
  status: string;
  schoolId: string;
  teacherId: number | null;
};

function readLocation(): TeacherLocationState {
  const params = new URLSearchParams(window.location.search);
  return {
    query: params.get("q") || "",
    status: params.get("status") || "all",
    schoolId: params.get("school") || "",
    teacherId: Number(params.get("teacherId") || 0) || null,
  };
}

function writeLocation(
  state: TeacherLocationState,
  push = false,
  detailEntry = false,
) {
  const params = new URLSearchParams();
  if (state.query) params.set("q", state.query);
  if (state.status !== "all") params.set("status", state.status);
  if (state.schoolId) params.set("school", state.schoolId);
  if (state.teacherId) params.set("teacherId", String(state.teacherId));
  const url = `${window.location.pathname}${params.size ? `?${params}` : ""}`;
  window.history[push ? "pushState" : "replaceState"](
    detailEntry
      ? { ...window.history.state, teacherSupportDetail: true }
      : window.history.state,
    "",
    url,
  );
}

export function useTeacherDirectory() {
  const initial = useRef(readLocation()).current;
  const [query, setQuery] = useState(initial.query);
  const [debouncedQuery, setDebouncedQuery] = useState(initial.query.trim());
  const [status, setStatus] = useState(initial.status);
  const [schoolId, setSchoolId] = useState(initial.schoolId);
  const [selectedId, setSelectedId] = useState<number | null>(initial.teacherId);
  const [dismissedError, setDismissedError] = useState<unknown>(null);
  const listScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedQuery(query.trim()),
      TEACHER_SEARCH_DEBOUNCE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onPopState = () => {
      const state = readLocation();
      setQuery(state.query);
      setDebouncedQuery(state.query.trim());
      setStatus(state.status);
      setSchoolId(state.schoolId);
      setSelectedId(state.teacherId);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    const current = readLocation();
    writeLocation({
      query: debouncedQuery,
      status,
      schoolId,
      teacherId: current.teacherId,
    });
    listScrollRef.current?.scrollTo({ top: 0 });
  }, [debouncedQuery, schoolId, status]);

  const contextQuery = useQuery({
    queryKey: ["customer-support", "context"],
    queryFn: ({ signal }) => getSupport<SupportContext>("/context", signal),
  });

  const teachersQuery = useInfiniteQuery({
    queryKey: [
      "customer-support",
      "teachers",
      debouncedQuery,
      schoolId,
      status,
    ],
    queryFn: ({ pageParam, signal }) => listSupportTeachers(
      {
        query: debouncedQuery,
        schoolId,
        status,
        cursor: pageParam,
        limit: TEACHER_PAGE_SIZE,
      },
      signal,
    ),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor || undefined,
  });

  const detailQuery = useQuery({
    queryKey: ["customer-support", "teachers", "detail", selectedId],
    enabled: Boolean(selectedId),
    queryFn: ({ signal }) => getSupportTeacher(selectedId as number, signal),
  });

  const teachers = useMemo(
    () => teachersQuery.data?.pages.flatMap((page) => page.items) || [],
    [teachersQuery.data],
  );
  const nextCursor = teachersQuery.data?.pages.at(-1)?.nextCursor || null;
  const activeError = detailQuery.error || teachersQuery.error || contextQuery.error;
  const errorState = useMemo<SupportErrorState | null>(() => {
    if (!activeError || activeError === dismissedError) return null;
    return {
      error: asSupportApiError(activeError, "Could not load teacher support."),
    };
  }, [activeError, dismissedError]);

  function selectTeacher(teacher: TeacherDirectoryItem) {
    setSelectedId(teacher.teacherId);
    writeLocation(
      {
        query: query.trim(),
        status,
        schoolId,
        teacherId: teacher.teacherId,
      },
      true,
      true,
    );
  }

  function closeDetail() {
    if (window.history.state?.teacherSupportDetail) {
      window.history.back();
      return;
    }
    setSelectedId(null);
    const current = readLocation();
    writeLocation({ ...current, teacherId: null });
  }

  function loadMore() {
    if (teachersQuery.hasNextPage && !teachersQuery.isFetchingNextPage) {
      void teachersQuery.fetchNextPage();
    }
  }

  return {
    context: contextQuery.data || null,
    query,
    setQuery,
    status,
    setStatus,
    schoolId,
    setSchoolId,
    teachers,
    nextCursor,
    selectedId,
    detail: detailQuery.data || null,
    detailUnavailable: Boolean(selectedId && detailQuery.isError),
    loadingContext: contextQuery.isPending,
    loadingTeachers: teachersQuery.isPending,
    loadingMore: teachersQuery.isFetchingNextPage,
    loadingDetail: Boolean(selectedId && detailQuery.isPending),
    errorState,
    dismissError: () => setDismissedError(activeError),
    reloadTeachers: () => void teachersQuery.refetch(),
    reloadDetail: () => void detailQuery.refetch(),
    listScrollRef,
    selectTeacher,
    closeDetail,
    loadMore,
  };
}

export type TeacherDirectoryController = ReturnType<typeof useTeacherDirectory>;
