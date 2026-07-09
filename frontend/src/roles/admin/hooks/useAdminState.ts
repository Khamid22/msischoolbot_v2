import { FormEvent, useEffect, useRef, useState } from "react";
import { routes } from "@/shared/lib/routes";
import {
  AdminPageProps,
  AdminTab,
  AdminMode,
  BlockedUser,
  ChatMsg,
  OverviewGrade,
  ResourceUploadState,
  asNumber,
  asString,
  asStringArray,
  availableGradesForRow,
  buildAdminTabUrl,
  buildUploadProgressUrl,
  compareSubjectsMathFirst,
  createUploadId,
  findPreferredMathSubject,
  filterGroupsByGrade,
  filterMonthlySeriesByGrade,
  formatMonthKeyLabel,
  normalizeAdminMode,
  normalizeAdminTab,
  sortSubjectsMathFirst,
  tabsForAdminMode,
  trimEmptyMonthlyMonths,
} from "../shared";
import { JSON_HEADERS, XHR_HEADERS, apiData } from "@/shared/lib/api";
import {
  canUseAdminPreviewForRole,
  clearRolePreviewStorage,
} from "@/shared/lib/staleUiState";

function preferredSchoolCode(schoolCodes: string[]) {
  if (schoolCodes.includes("sehriyo")) {
    return "sehriyo";
  }
  return schoolCodes[0] || "";
}

function normalizeStudentSubjects(value: unknown) {
  const subjects = asString(value)
    .replace(/;/g, ",")
    .split(",")
    .map((item: string) => asString(item))
    .filter(Boolean);
  return sortSubjectsMathFirst(subjects).join(", ");
}

function normalizeStudentRows(rows: Array<Record<string, unknown>>) {
  return rows.map((row) => ({
    ...row,
    subjects: normalizeStudentSubjects(row.subjects),
  }));
}

function preferredSubjectName(rows: Array<Record<string, unknown>>) {
  return findPreferredMathSubject(rows.map((row) => asString(row.subject_name)));
}

function urlAdminMode() {
  try {
    return asString(new URLSearchParams(window.location.search).get("mode"));
  } catch {
    return "";
  }
}

const DEV_PREVIEW_ROLE_KEY = "devPreviewRole";
const LEGACY_ADMIN_MODE_KEY = "msi_admin_mode";
const FULL_ACADEMIC_CONTEXT_TABS = new Set<AdminTab>([
  "teachers",
  "subjects",
  "groups",
  "schedule",
  "curriculum",
  "gradebook",
  "office_hours",
  "career_growth",
]);

function serverAdminMode(props: AdminPageProps) {
  const realRole = asString(props.authRole || props.adminMode);
  if (props.devPreviewEnabled && canUseAdminPreviewForRole(realRole)) {
    return normalizeAdminMode(props.previewRole || props.adminMode || props.authRole || "admin");
  }
  return normalizeAdminMode(props.adminMode || props.authRole || "admin");
}

function storedAdminMode() {
  try {
    return (
      asString(window.localStorage.getItem(DEV_PREVIEW_ROLE_KEY)) ||
      asString(window.localStorage.getItem(LEGACY_ADMIN_MODE_KEY))
    );
  } catch {
    return "";
  }
}

export function useAdminState(props: AdminPageProps) {
  const initialTab = normalizeAdminTab(props.adminPanel);
  const realRole = asString(props.authRole || props.adminMode || props.previewRole);
  const serverMode = serverAdminMode(props);
  const allowPreviewMode = Boolean(props.devPreviewEnabled) && canUseAdminPreviewForRole(realRole);
  const [activeTab, setActiveTab] = useState<AdminTab>(initialTab);
  const [previewRole, setPreviewRoleState] = useState<AdminMode>(() => {
    if (!allowPreviewMode) {
      return serverMode;
    }
    return normalizeAdminMode(urlAdminMode() || storedAdminMode() || props.previewRole || props.adminMode);
  });
  const adminMode = previewRole;
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [activeStudentRowId, setActiveStudentRowId] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      return Math.max(0, Math.floor(Number(params.get("student") || 0)));
    } catch {
      return 0;
    }
  });
  const currentSchool = props.adminSchool || "all";
  const schoolOptions = (
    Array.isArray(props.adminSchoolOptions) ? props.adminSchoolOptions : []
  ).filter(
    (option): option is { code: string; label: string } =>
      Boolean(
        option && typeof option.code === "string" && typeof option.label === "string"
      )
  );
  const [students, setStudents] = useState<Array<Record<string, unknown>>>(() =>
    normalizeStudentRows(Array.isArray(props.adminStudents) ? props.adminStudents : [])
  );
  const [parentAccounts, setParentAccounts] = useState<Array<Record<string, unknown>>>(() =>
    Array.isArray(props.adminParents) ? props.adminParents : []
  );
  const [activeParentId, setActiveParentIdState] = useState<number>(() => {
    try {
      const stored = Number(window.localStorage.getItem("msi_active_parent_id") || 0);
      return Number.isFinite(stored) && stored > 0 ? stored : 0;
    } catch {
      return 0;
    }
  });
  const [parentChildren, setParentChildren] = useState<Array<Record<string, unknown>>>(() =>
    Array.isArray(props.adminParentChildren) ? props.adminParentChildren : []
  );
  const [complaints, setComplaints] = useState<Array<Record<string, unknown>>>(() =>
    Array.isArray(props.adminComplaints) ? props.adminComplaints : []
  );
  const [teachers, setTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.adminTeachers) ? props.adminTeachers : []
  );
  const [academyTeachers, setAcademyTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.adminTeacherAcademy) ? props.adminTeacherAcademy : []
  );
  const [academicContextMode, setAcademicContextMode] = useState<"summary" | "full">(
    props.adminAcademicContextMode === "full" ? "full" : "summary"
  );
  const [academicContext, setAcademicContext] = useState(() => ({
    schools: Array.isArray(props.adminAcademicSchools) ? props.adminAcademicSchools : [],
    subjects: Array.isArray(props.adminAcademicSubjects) ? props.adminAcademicSubjects : [],
    groups: Array.isArray(props.adminAcademicGroups) ? props.adminAcademicGroups : [],
    enrollments: Array.isArray(props.adminAcademicEnrollments) ? props.adminAcademicEnrollments : [],
    lessons: Array.isArray(props.adminAcademicLessons) ? props.adminAcademicLessons : [],
    schedules: Array.isArray(props.adminAcademicSchedules) ? props.adminAcademicSchedules : [],
    sessions: Array.isArray(props.adminAcademicSessions) ? props.adminAcademicSessions : [],
    curriculumPrograms: Array.isArray(props.adminAcademicCurriculumPrograms) ? props.adminAcademicCurriculumPrograms : [],
    curriculumItems: Array.isArray(props.adminAcademicCurriculumItems) ? props.adminAcademicCurriculumItems : [],
    enrollmentSummary: props.adminAcademicEnrollmentSummary || {},
  }));
  const resourceTypes = Array.isArray(props.adminResourceTypes) ? props.adminResourceTypes : [];
  const activeResourceTypes = Array.isArray(props.adminResourceActiveTypes)
    ? props.adminResourceActiveTypes
    : [];
  const [resourcesList, setResourcesList] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.adminResources) ? props.adminResources : []
  );
  const quickStats = props.adminQuickStats || {};
  const schoolInfo = Array.isArray(props.adminSchoolInfo) ? props.adminSchoolInfo : [];
  const subjectInfo = Array.isArray(props.adminSubjectInfo) ? props.adminSubjectInfo : [];
  const teacherOptions = (
    Array.isArray(props.adminTeacherOptions) ? props.adminTeacherOptions : []
  ).map((option) => ({
    name: asString(option?.name),
    school_codes: asStringArray(option?.school_codes),
  }));
  const groupOptions = (
    Array.isArray(props.adminGroupOptions) ? props.adminGroupOptions : []
  ).map((option) => ({
    name: asString(option?.name),
    school_codes: asStringArray(option?.school_codes),
  }));
  const teacherEdit = props.adminTeacherEdit || null;

  const availableSubjectSchools = schoolOptions.filter((option) => option.code !== "all");
  const preferredSchool = preferredSchoolCode(
    availableSubjectSchools.map((option) => option.code)
  );
  const initialSchool = props.adminTeacherEditSchool || preferredSchool || "all";
  const [teacherMode, setTeacherMode] = useState(teacherEdit ? "add" : "select");
  const [teacherSchool, setTeacherSchool] = useState(initialSchool);
  const [searchQuery, setSearchQuery] = useState("");
  const [editingTypeId, setEditingTypeId] = useState<number | null>(null);
  const initialOverviewSchool =
    currentSchool !== "all" &&
    availableSubjectSchools.some((option) => option.code === currentSchool)
      ? currentSchool
      : preferredSchool;
  const [selectedOverviewSchool, setSelectedOverviewSchool] = useState(
    initialOverviewSchool
  );
  const schoolSubjectRows = subjectInfo
    .filter((row) => asString(row.school_key).toLowerCase() === selectedOverviewSchool)
    .sort((left, right) =>
      compareSubjectsMathFirst(asString(left.subject_name), asString(right.subject_name))
    );
  const [selectedSubjectName, setSelectedSubjectName] = useState(
    preferredSubjectName(schoolSubjectRows)
  );
  const [selectedSehriyoGrade, setSelectedSehriyoGrade] = useState<OverviewGrade | "">(
    ""
  );
  const [resourceUploadState, setResourceUploadState] = useState<ResourceUploadState>({
    active: false,
    percent: 0,
    message: "",
    error: false,
  });
  const [isSubmittingResource, setIsSubmittingResource] = useState(false);
  const [resourceSubjectFilter, setResourceSubjectFilter] = useState("all");
  const [editingResource, setEditingResource] = useState<{
    id: number;
    title: string;
    description: string;
    resourceFileKind: string;
    thumbnailUrl: string;
    resourceTypeId: number;
  } | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [uploadFormKey, setUploadFormKey] = useState(0);
  const [lastResourceTypeId, setLastResourceTypeId] = useState("");
  const editResourceFileRef = useRef<HTMLInputElement>(null);
  const editThumbnailFileRef = useRef<HTMLInputElement>(null);
  const resourceUploadPollTimerRef = useRef<number | null>(null);
  const resourceUploadPollUploadIdRef = useRef("");
  const resourceUploadLastSeqRef = useRef(0);
  const resourceUploadXhrRef = useRef<XMLHttpRequest | null>(null);
  const resourceUploadResetTimerRef = useRef<number | null>(null);

  const [chatRoom, setChatRoom] = useState("global");
  const [chatRooms, setChatRooms] = useState<{ room: string; active: number }[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [blockedUsers, setBlockedUsers] = useState<BlockedUser[]>([]);
  const [blockReason, setBlockReason] = useState("");
  const visibleTabs = tabsForAdminMode(adminMode);

  useEffect(() => {
    if (!allowPreviewMode) {
      clearRolePreviewStorage();
      if (serverMode !== adminMode) {
        setPreviewRoleState(serverMode);
      }
      return;
    }
    const serverPreviewMode = asString(props.previewRole || props.adminMode);
    const clientMode = urlAdminMode() || storedAdminMode();
    if (clientMode) {
      const normalizedClientMode = normalizeAdminMode(clientMode);
      if (normalizedClientMode !== adminMode) {
        setPreviewRoleState(normalizedClientMode);
      }
      return;
    }
    if (!serverPreviewMode) {
      return;
    }
    const normalizedMode = normalizeAdminMode(serverPreviewMode);
    if (normalizedMode !== adminMode) {
      setPreviewRoleState(normalizedMode);
    }
  }, [adminMode, allowPreviewMode, props.adminMode, props.previewRole, realRole, serverMode]);

  function clearResourceUploadResetTimer() {
    if (resourceUploadResetTimerRef.current !== null) {
      window.clearTimeout(resourceUploadResetTimerRef.current);
      resourceUploadResetTimerRef.current = null;
    }
  }

  function scheduleResourceUploadReset(delayMs = 2200) {
    clearResourceUploadResetTimer();
    resourceUploadResetTimerRef.current = window.setTimeout(() => {
      setResourceUploadState({
        active: false,
        percent: 0,
        message: "",
        error: false,
      });
      resourceUploadResetTimerRef.current = null;
    }, delayMs);
  }

  function clearResourceUploadPollTimer() {
    if (resourceUploadPollTimerRef.current !== null) {
      window.clearTimeout(resourceUploadPollTimerRef.current);
      resourceUploadPollTimerRef.current = null;
    }
  }

  function stopResourceUploadProgressPolling() {
    clearResourceUploadPollTimer();
    resourceUploadPollUploadIdRef.current = "";
  }

  function applyResourceUploadProgressEvent(payload: Record<string, unknown>) {
    const seq = Math.floor(Number(payload.seq || 0));
    if (seq > resourceUploadLastSeqRef.current) {
      resourceUploadLastSeqRef.current = seq;
    }
    setResourceUploadState((current) => ({
      active: true,
      percent: Math.max(
        current.percent,
        Math.max(0, Math.min(100, Number(payload.percent || 0)))
      ),
      message: asString(payload.message) || current.message || "Uploading resource...",
      error: Boolean(payload.error),
    }));
  }

  function scheduleResourceUploadProgressPoll(uploadId: string, delayMs = 700) {
    if (resourceUploadPollUploadIdRef.current !== uploadId) {
      return;
    }
    clearResourceUploadPollTimer();
    resourceUploadPollTimerRef.current = window.setTimeout(() => {
      void pollResourceUploadProgress(uploadId);
    }, delayMs);
  }

  async function pollResourceUploadProgress(uploadId: string) {
    if (resourceUploadPollUploadIdRef.current !== uploadId) {
      return;
    }

    try {
      const res = await fetch(
        buildUploadProgressUrl(uploadId, resourceUploadLastSeqRef.current),
        {
          headers: XHR_HEADERS,
          cache: "no-store",
        }
      );
      if (!res.ok || resourceUploadPollUploadIdRef.current !== uploadId) {
        scheduleResourceUploadProgressPoll(uploadId, 1400);
        return;
      }

      const payload = apiData<{ events?: unknown[]; done?: unknown }>(await res.json());
      const events: unknown[] = Array.isArray(payload.events) ? payload.events : [];
      let sawTerminalEvent = Boolean(payload.done);
      events.forEach((event) => {
        if (!event || typeof event !== "object") {
          return;
        }
        const progressEvent = event as Record<string, unknown>;
        applyResourceUploadProgressEvent(progressEvent);
        if (Boolean(progressEvent.done) || Boolean(progressEvent.error)) {
          sawTerminalEvent = true;
        }
      });

      if (sawTerminalEvent) {
        stopResourceUploadProgressPolling();
        return;
      }
    } catch (_error) {
      // Keep the upload running; XHR completion/error remains authoritative.
    }

    scheduleResourceUploadProgressPoll(uploadId);
  }

  function startResourceUploadProgressPolling(uploadId: string) {
    stopResourceUploadProgressPolling();
    resourceUploadLastSeqRef.current = 0;
    resourceUploadPollUploadIdRef.current = uploadId;
    scheduleResourceUploadProgressPoll(uploadId, 250);
  }

  function loadChatRooms() {
    fetch("/api/v1/admin/chat/rooms", { headers: XHR_HEADERS })
      .then((r) => r.json())
      .then((d) => {
        const base = [{ room: "global", active: 0 }];
        const merged = [...base];
        for (const r of d.data?.rooms ?? []) {
          if (!merged.find((x) => x.room === r.room)) merged.push(r);
        }
        setChatRooms(merged);
      })
      .catch(() => {});
  }

  function loadChatMessages(room: string) {
    setChatLoading(true);
    fetch(`/api/v1/admin/chat/messages?room=${encodeURIComponent(room)}`, { headers: XHR_HEADERS })
      .then((r) => r.json())
      .then((d) => {
        setChatMessages(Array.isArray(d.data?.messages) ? d.data.messages : []);
      })
      .catch(() => {})
      .finally(() => setChatLoading(false));
  }

  function loadBlocked() {
    fetch("/api/v1/admin/chat/blocked", { headers: XHR_HEADERS })
      .then((r) => r.json())
      .then((d) => {
        setBlockedUsers(Array.isArray(d.data?.blocked) ? d.data.blocked : []);
      })
      .catch(() => {});
  }

  function adminDeleteMsg(id: number) {
    fetch(`/api/v1/admin/chat/messages/${id}`, { method: "DELETE", headers: XHR_HEADERS })
      .then((r) => {
        if (r.ok)
          setChatMessages((prev) =>
            prev.map((m) => (m.id === id ? { ...m, isDeleted: true } : m))
          );
      })
      .catch(() => {});
  }

  function adminBlockUser(studentId: string) {
    fetch("/api/v1/admin/chat/block", {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ studentId, reason: blockReason }),
    })
      .then((r) => {
        if (r.ok) {
          setBlockReason("");
          loadBlocked();
        }
      })
      .catch(() => {});
  }

  function adminUnblock(studentId: string) {
    fetch(`/api/v1/admin/chat/block/${encodeURIComponent(studentId)}`, { method: "DELETE", headers: XHR_HEADERS })
      .then((r) => {
        if (r.ok) loadBlocked();
      })
      .catch(() => {});
  }

  async function refreshStudents() {
    try {
      const url = `${routes.adminStudentsApi}?school=${encodeURIComponent(
        String(currentSchool || "all")
      )}`;
      const res = await fetch(url, {
        cache: "no-store",
        credentials: "same-origin",
        headers: XHR_HEADERS,
      });
      if (!res.ok) {
        return;
      }
      const data = apiData<{ students?: Array<Record<string, unknown>> }>(await res.json());
      if (Array.isArray(data.students)) {
        setStudents(normalizeStudentRows(data.students));
      }
    } catch (_error) {
    }
  }

  async function refreshComplaints() {
    try {
      const res = await fetch(routes.adminComplaintsApi, {
        cache: "no-store",
        credentials: "same-origin",
        headers: XHR_HEADERS,
      });
      if (!res.ok) {
        return;
      }
      const data = apiData<{ complaints?: Array<Record<string, unknown>> }>(await res.json());
      if (Array.isArray(data.complaints)) {
        setComplaints(data.complaints);
      }
    } catch (_error) {
    }
  }

  useEffect(() => {
    setActiveTab(normalizeAdminTab(props.adminPanel));
  }, [props.adminPanel]);

  useEffect(() => {
    if (activeTab.startsWith("student_")) {
      return;
    }
    if (visibleTabs.some((tab) => tab.key === activeTab)) {
      return;
    }
    const fallbackTab = visibleTabs[0]?.key || "overview";
    setActiveTab(fallbackTab);
    const nextUrl = buildAdminTabUrl(fallbackTab, currentSchool, allowPreviewMode ? adminMode : "");
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (nextUrl !== currentUrl) {
      window.history.replaceState({}, "", nextUrl);
    }
  }, [activeTab, adminMode, currentSchool, visibleTabs]);

  useEffect(() => {
    if (Array.isArray(props.adminResources)) {
      setResourcesList(props.adminResources);
    }
  }, [props.adminResources]);

  useEffect(() => {
    if (Array.isArray(props.adminTeachers)) {
      setTeachers(props.adminTeachers);
    }
  }, [props.adminTeachers]);

  useEffect(() => {
    if (Array.isArray(props.adminTeacherAcademy)) {
      setAcademyTeachers(props.adminTeacherAcademy);
    }
  }, [props.adminTeacherAcademy]);

  useEffect(() => {
    if (academicContextMode === "full" || !FULL_ACADEMIC_CONTEXT_TABS.has(activeTab)) {
      return;
    }
    let cancelled = false;
    const loadAcademicContext = async () => {
      try {
        const res = await fetch(routes.adminAcademicContextApi, {
          cache: "no-store",
          credentials: "same-origin",
          headers: XHR_HEADERS,
        });
        if (!res.ok || cancelled) {
          return;
        }
        const data = apiData<Record<string, unknown>>(await res.json());
        if (cancelled) {
          return;
        }
        setAcademicContext({
          schools: Array.isArray(data.schools) ? data.schools as Array<Record<string, unknown>> : [],
          subjects: Array.isArray(data.subjects) ? data.subjects as Array<Record<string, unknown>> : [],
          groups: Array.isArray(data.groups) ? data.groups as Array<Record<string, unknown>> : [],
          enrollments: Array.isArray(data.enrollments) ? data.enrollments as Array<Record<string, unknown>> : [],
          lessons: Array.isArray(data.lessons) ? data.lessons as Array<Record<string, unknown>> : [],
          schedules: Array.isArray(data.schedules) ? data.schedules as Array<Record<string, unknown>> : [],
          sessions: Array.isArray(data.sessions) ? data.sessions as Array<Record<string, unknown>> : [],
          curriculumPrograms: Array.isArray(data.curriculum_programs) ? data.curriculum_programs as Array<Record<string, unknown>> : [],
          curriculumItems: Array.isArray(data.curriculum_items) ? data.curriculum_items as Array<Record<string, unknown>> : [],
          enrollmentSummary: data.enrollment_summary && typeof data.enrollment_summary === "object"
            ? data.enrollment_summary as Record<string, unknown>
            : {},
        });
        setAcademicContextMode("full");
      } catch (_error) {
      }
    };
    void loadAcademicContext();
    return () => {
      cancelled = true;
    };
  }, [academicContextMode, activeTab]);

  useEffect(() => {
    if (!parentAccounts.length) {
      if (activeParentId) {
        setActiveParentIdState(0);
      }
      return;
    }
    if (parentAccounts.some((parent) => asNumber(parent.id) === activeParentId)) {
      return;
    }
    const fallbackParentId = asNumber(parentAccounts[0]?.id);
    if (fallbackParentId > 0) {
      setActiveParentIdState(fallbackParentId);
      try {
        window.localStorage.setItem("msi_active_parent_id", String(fallbackParentId));
      } catch {
      }
    }
  }, [activeParentId, parentAccounts]);

  useEffect(() => {
    if (Array.isArray(props.adminStudents)) {
      setStudents(normalizeStudentRows(props.adminStudents));
    }
  }, [props.adminStudents]);

  useEffect(() => {
    if (Array.isArray(props.adminComplaints)) {
      setComplaints(props.adminComplaints);
    }
  }, [props.adminComplaints]);

  useEffect(() => {
    if (activeTab === "chat") {
      loadChatRooms();
      loadChatMessages(chatRoom);
      loadBlocked();
    }
  }, [activeTab, chatRoom]);

  useEffect(() => {
    if (!availableSubjectSchools.length) {
      if (selectedOverviewSchool) {
        setSelectedOverviewSchool("");
      }
      return;
    }
    const selectedSchoolIsValid = availableSubjectSchools.some(
      (option) => option.code === selectedOverviewSchool
    );
    if (selectedSchoolIsValid) {
      return;
    }
    const preferredSchool =
      currentSchool !== "all" &&
      availableSubjectSchools.some((option) => option.code === currentSchool)
        ? currentSchool
        : preferredSchoolCode(availableSubjectSchools.map((option) => option.code));
    setSelectedOverviewSchool(preferredSchool);
  }, [availableSubjectSchools, currentSchool, selectedOverviewSchool]);

  useEffect(() => {
    if (!schoolSubjectRows.length) {
      if (selectedSubjectName) {
        setSelectedSubjectName("");
      }
      return;
    }
    const selectedSubjectStillExists = schoolSubjectRows.some(
      (row) => asString(row.subject_name) === selectedSubjectName
    );
    if (!selectedSubjectStillExists) {
      setSelectedSubjectName(preferredSubjectName(schoolSubjectRows));
    }
  }, [schoolSubjectRows, selectedSubjectName]);

  useEffect(() => {
    if (activeTab !== "students") {
      return;
    }
    let cancelled = false;
    const run = async () => {
      if (cancelled || document.visibilityState === "hidden") {
        return;
      }
      await refreshStudents();
    };
    run();
    const intervalId = window.setInterval(run, 12000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [activeTab, currentSchool]);

  useEffect(() => {
    if (activeTab !== "complaints") {
      return;
    }
    void refreshComplaints();
  }, [activeTab]);

  const filteredTeacherOptions = teacherOptions.filter((option) => {
    if (!teacherSchool) {
      return true;
    }
    return !option.school_codes.length || option.school_codes.includes(teacherSchool);
  });
  const filteredGroupOptions = groupOptions.filter((option) => {
    if (!teacherSchool) {
      return true;
    }
    return !option.school_codes.length || option.school_codes.includes(teacherSchool);
  });

  const filteredStudents = students.filter((student) => {
    const haystack = [
      asString(student.full_name),
      asString(student.studentCode),
      asString(student.student_code),
      asString(student.student_id),
      asString(student.subjects),
      asString(student.school_name),
    ]
      .join(" ")
      .toLowerCase();
    return !searchQuery || haystack.includes(searchQuery.toLowerCase());
  });

  const selectedSubjectRow =
    schoolSubjectRows.find((row) => asString(row.subject_name) === selectedSubjectName) ||
    schoolSubjectRows[0];
  const baseGroupRows = Array.isArray(selectedSubjectRow?.groups)
    ? (selectedSubjectRow.groups as Array<Record<string, unknown>>)
    : [];
  const baseMonthlyMonths = Array.isArray(selectedSubjectRow?.monthly_months)
    ? (selectedSubjectRow.monthly_months as string[])
    : [];
  const baseMonthlySeries = Array.isArray(selectedSubjectRow?.monthly_series)
    ? (selectedSubjectRow.monthly_series as Array<Record<string, unknown>>)
    : [];
  const isSehriyoOverview = asString(selectedSubjectRow?.school_key).toLowerCase() === "sehriyo";
  const availableOverviewGrades = isSehriyoOverview
    ? availableGradesForRow(selectedSubjectRow)
    : [];
  let activeOverviewGrade: OverviewGrade | "" = "";
  if (isSehriyoOverview && availableOverviewGrades.length) {
    if (selectedSehriyoGrade && availableOverviewGrades.includes(selectedSehriyoGrade)) {
      activeOverviewGrade = selectedSehriyoGrade;
    } else if (availableOverviewGrades.includes("7")) {
      activeOverviewGrade = "7";
    } else if (availableOverviewGrades.includes("8")) {
      activeOverviewGrade = "8";
    } else {
      activeOverviewGrade = availableOverviewGrades[0];
    }
  }
  const selectedGroupRows = isSehriyoOverview
    ? filterGroupsByGrade(baseGroupRows, activeOverviewGrade)
    : baseGroupRows;
  const filteredMonthlySeries = isSehriyoOverview
    ? filterMonthlySeriesByGrade(baseMonthlySeries, activeOverviewGrade)
    : baseMonthlySeries;
  const baseExamSeries = Array.isArray(selectedSubjectRow?.exam_series)
    ? (selectedSubjectRow.exam_series as Array<Record<string, unknown>>)
    : [];
  const filteredExamSeries = isSehriyoOverview
    ? filterMonthlySeriesByGrade(baseExamSeries, activeOverviewGrade)
    : baseExamSeries;
  const baseMonthlyArSeries = Array.isArray(selectedSubjectRow?.monthly_ar_series)
    ? (selectedSubjectRow.monthly_ar_series as Array<Record<string, unknown>>)
    : [];
  const filteredMonthlyArSeries_base = isSehriyoOverview
    ? filterMonthlySeriesByGrade(baseMonthlyArSeries, activeOverviewGrade)
    : baseMonthlyArSeries;
  const monthlyTimeline = trimEmptyMonthlyMonths(baseMonthlyMonths, filteredMonthlySeries);
  const monthlyMonths = monthlyTimeline.months;
  const monthlySeries = monthlyTimeline.series;
  // Re-align AR series values to the trimmed month list so indices match activeMonth.index.
  // baseMonthlyMonths is the full range; monthlyMonths is a trimmed subset of it.
  const filteredMonthlyArSeries = filteredMonthlyArSeries_base.map((seriesRow) => {
    const values = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
    return {
      ...seriesRow,
      values: monthlyMonths.map((monthKey) => {
        const i = baseMonthlyMonths.indexOf(monthKey);
        return i >= 0 ? values[i] : null;
      }),
    };
  });
  const monthlyChartData = monthlyMonths.map((monthKey, index) => {
    const row: Record<string, string | number | null> = {
      month: monthKey,
      monthLabel: formatMonthKeyLabel(monthKey),
    };
    for (const seriesRow of monthlySeries) {
      const sr = seriesRow as Record<string, unknown>;
      row[asString(sr.label)] = Array.isArray(sr.values) ? (sr.values[index] as number | null) : null;
    }
    return row;
  });

  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      setActiveTab(normalizeAdminTab(params.get("panel")));
      const modeParam = params.get("mode");
      if (modeParam && allowPreviewMode) {
        setPreviewRoleState(normalizeAdminMode(modeParam));
      } else if (!allowPreviewMode) {
        setPreviewRoleState(serverMode);
      }
      setActiveStudentRowId(Math.max(0, Math.floor(Number(params.get("student") || 0))));
      setMobileNavOpen(false);
    };
    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [allowPreviewMode, serverMode]);

  useEffect(() => {
    if (!isSubmittingResource) {
      return;
    }
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [isSubmittingResource]);

  useEffect(() => {
    return () => {
      clearResourceUploadResetTimer();
      stopResourceUploadProgressPolling();
      if (resourceUploadXhrRef.current) {
        resourceUploadXhrRef.current.abort();
      }
      resourceUploadXhrRef.current = null;
    };
  }, []);

  function switchAdminTab(nextTab: AdminTab) {
    setActiveTab(nextTab);
    setMobileNavOpen(false);
    const nextUrl = buildAdminTabUrl(nextTab, currentSchool, allowPreviewMode ? adminMode : "");
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (nextUrl !== currentUrl) {
      window.history.pushState({}, "", nextUrl);
    }
  }

  function switchAdminMode(nextMode: AdminMode | string) {
    if (!allowPreviewMode) {
      setPreviewRoleState(serverMode);
      setActiveTab(tabsForAdminMode(serverMode)[0]?.key || "overview");
      setMobileNavOpen(false);
      clearRolePreviewStorage();
      return;
    }
    const normalizedMode = normalizeAdminMode(nextMode);
    const nextTabs = tabsForAdminMode(normalizedMode);
    const fallbackTab = nextTabs[0]?.key || "overview";
    setPreviewRoleState(normalizedMode);
    setActiveTab(fallbackTab);
    setMobileNavOpen(false);
    try {
      window.localStorage.setItem(DEV_PREVIEW_ROLE_KEY, normalizedMode);
      window.localStorage.removeItem(LEGACY_ADMIN_MODE_KEY);
    } catch {
    }
    const nextUrl = buildAdminTabUrl(fallbackTab, currentSchool, normalizedMode);
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (nextUrl !== currentUrl) {
      window.history.pushState({}, "", nextUrl);
    }
  }

  function setActiveParentId(parentId: number) {
    const normalizedParentId = Math.max(0, Math.floor(Number(parentId) || 0));
    setActiveParentIdState(normalizedParentId);
    try {
      if (normalizedParentId > 0) {
        window.localStorage.setItem("msi_active_parent_id", String(normalizedParentId));
      } else {
        window.localStorage.removeItem("msi_active_parent_id");
      }
    } catch {
    }
  }

  async function refreshResources() {
    try {
      const res = await fetch(routes.adminResourcesApi, { headers: XHR_HEADERS });
      if (res.ok) {
        const data = apiData<{ resources?: Array<Record<string, unknown>> }>(await res.json());
        if (Array.isArray(data.resources)) {
          setResourcesList(data.resources);
        }
      }
    } catch (_error) {
    }
  }

  useEffect(() => {
    if (activeTab !== "resources") {
      return;
    }
    void refreshResources();
  }, [activeTab]);

  async function saveEditResource() {
    if (!editingResource || editSaving) return;
    setEditSaving(true);
    setEditError("");
    try {
      const formData = new FormData();
      formData.set("resource_title", editingResource.title.trim());
      formData.set("resource_description", editingResource.description.trim());
      formData.set("resource_type_id", String(editingResource.resourceTypeId));
      formData.set("csrf_token", props.csrfToken || "");
      const resourceFile = editResourceFileRef.current?.files?.[0];
      if (resourceFile) formData.set("resource_file", resourceFile);
      const thumbnailFile = editThumbnailFileRef.current?.files?.[0];
      if (thumbnailFile) formData.set("thumbnail_file", thumbnailFile);
      const res = await fetch(routes.adminResourceEdit(editingResource.id), {
        method: "POST",
        headers: XHR_HEADERS,
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        setEditError(asString(data.message) || "Unable to update resource.");
        return;
      }
      setEditingResource(null);
      setEditError("");
      await refreshResources();
    } catch (_error) {
      setEditError("Network error. Please try again.");
    } finally {
      setEditSaving(false);
    }
  }

  async function submitResourceForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!props.adminResourceUploadEnabled) {
      setResourceUploadState({
        active: true,
        percent: 100,
        message: "Resource upload is disabled in this environment.",
        error: true,
      });
      return;
    }
    if (isSubmittingResource) {
      return;
    }

    const form = event.currentTarget;
    const uploadId = createUploadId();
    const formData = new FormData(form);
    formData.set("upload_id", uploadId);

    stopResourceUploadProgressPolling();
    clearResourceUploadResetTimer();

    setIsSubmittingResource(true);
    setResourceUploadState({
      active: true,
      percent: 1,
      message: "Preparing upload...",
      error: false,
    });
    startResourceUploadProgressPolling(uploadId);

    try {
      const xhr = new XMLHttpRequest();
      resourceUploadXhrRef.current = xhr;

      xhr.open(String(form.method || "post").toUpperCase(), form.action, true);
      xhr.withCredentials = true;
      xhr.responseType = "text";
      xhr.setRequestHeader("Accept", "text/html");
      xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

      xhr.upload.onprogress = (progressEvent) => {
        if (!progressEvent.lengthComputable) {
          return;
        }
        const ratio = progressEvent.total > 0 ? progressEvent.loaded / progressEvent.total : 0;
        const nextPercent = Math.max(4, Math.min(72, 4 + ratio * 68));
        setResourceUploadState((current) => ({
          active: true,
          percent: Math.max(current.percent, nextPercent),
          message: "Uploading file...",
          error: false,
        }));
      };

      xhr.onload = () => {
        const ok = xhr.status >= 200 && xhr.status < 300;
        const contentType = String(xhr.getResponseHeader("Content-Type") || "");

        stopResourceUploadProgressPolling();
        resourceUploadXhrRef.current = null;

        if (contentType.includes("application/json")) {
          let payload: Record<string, unknown> = {};
          try {
            payload = JSON.parse(String(xhr.responseText || ""));
          } catch (_error) {
            payload = {};
          }

          if (ok) {
            setIsSubmittingResource(false);
            setUploadFormKey((k) => k + 1);
            setResourceUploadState({
              active: true,
              percent: 100,
              message: asString(payload.message) || "Resource saved.",
              error: false,
            });
            scheduleResourceUploadReset();
            refreshResources();
            return;
          }

          setIsSubmittingResource(false);
          setResourceUploadState((current) => ({
            active: true,
            percent: Math.max(current.percent, 98),
            message: asString(payload.message) || "Unable to save resource.",
            error: true,
          }));
          return;
        }

        if (ok) {
          setIsSubmittingResource(false);
          setUploadFormKey((k) => k + 1);
          setResourceUploadState({
            active: true,
            percent: 100,
            message: "Resource saved.",
            error: false,
          });
          scheduleResourceUploadReset();
          refreshResources();
          return;
        }

        setIsSubmittingResource(false);
        setResourceUploadState((current) => ({
          active: true,
          percent: Math.max(current.percent, 98),
          message: current.message || "Unable to save resource.",
          error: true,
        }));
      };

      xhr.onerror = () => {
        stopResourceUploadProgressPolling();
        resourceUploadXhrRef.current = null;
        setIsSubmittingResource(false);
        setResourceUploadState({
          active: true,
          percent: 0,
          message: "Upload failed. Check your connection and try again.",
          error: true,
        });
      };

      xhr.onabort = () => {
        stopResourceUploadProgressPolling();
        resourceUploadXhrRef.current = null;
        setIsSubmittingResource(false);
      };

      xhr.send(formData);
    } catch (_error) {
      stopResourceUploadProgressPolling();
      resourceUploadXhrRef.current = null;
      setIsSubmittingResource(false);
      setResourceUploadState({
        active: true,
        percent: 0,
        message: "Upload failed. Check your connection and try again.",
        error: true,
      });
    }
  }

  return {
    props: {
      ...props,
      previewRole,
      adminMode,
      adminTeachers: teachers,
      adminTeacherAcademy: academyTeachers,
      adminAcademicSchools: academicContext.schools,
      adminAcademicSubjects: academicContext.subjects,
      adminAcademicGroups: academicContext.groups,
      adminAcademicEnrollments: academicContext.enrollments,
      adminAcademicLessons: academicContext.lessons,
      adminAcademicSchedules: academicContext.schedules,
      adminAcademicSessions: academicContext.sessions,
      adminAcademicCurriculumPrograms: academicContext.curriculumPrograms,
      adminAcademicCurriculumItems: academicContext.curriculumItems,
      adminAcademicEnrollmentSummary: academicContext.enrollmentSummary,
      adminAcademicContextMode: academicContextMode,
    },
    previewRole,
    adminMode,
    visibleTabs,
    activeTab,
    setActiveTab,
    activeStudentRowId,
    setActiveStudentRowId,
    mobileNavOpen,
    setMobileNavOpen,
    currentSchool,
    schoolOptions,
    students,
    parentAccounts,
    setParentAccounts,
    activeParentId,
    setActiveParentId,
    parentChildren,
    setParentChildren,
    complaints,
    setComplaints,
    teachers,
    setTeachers,
    academyTeachers,
    setAcademyTeachers,
    resourceTypes,
    activeResourceTypes,
    resourcesList,
    setResourcesList,
    quickStats,
    schoolInfo,
    subjectInfo,
    teacherOptions,
    groupOptions,
    teacherEdit,
    availableSubjectSchools,
    teacherMode,
    setTeacherMode,
    teacherSchool,
    setTeacherSchool,
    searchQuery,
    setSearchQuery,
    editingTypeId,
    setEditingTypeId,
    selectedOverviewSchool,
    setSelectedOverviewSchool,
    schoolSubjectRows,
    selectedSubjectName,
    setSelectedSubjectName,
    selectedSehriyoGrade,
    setSelectedSehriyoGrade,
    resourceUploadState,
    setResourceUploadState,
    isSubmittingResource,
    setIsSubmittingResource,
    resourceSubjectFilter,
    setResourceSubjectFilter,
    editingResource,
    setEditingResource,
    editSaving,
    setEditSaving,
    editError,
    setEditError,
    uploadFormKey,
    setUploadFormKey,
    lastResourceTypeId,
    setLastResourceTypeId,
    editResourceFileRef,
    editThumbnailFileRef,
    resourceUploadXhrRef,
    chatRoom,
    setChatRoom,
    chatRooms,
    setChatRooms,
    chatMessages,
    setChatMessages,
    chatLoading,
    setChatLoading,
    blockedUsers,
    setBlockedUsers,
    blockReason,
    setBlockReason,
    loadChatRooms,
    loadChatMessages,
    loadBlocked,
    adminDeleteMsg,
    adminBlockUser,
    adminUnblock,
    filteredTeacherOptions,
    filteredGroupOptions,
    filteredStudents,
    selectedSubjectRow,
    isSehriyoOverview,
    availableOverviewGrades,
    activeOverviewGrade,
    selectedGroupRows,
    filteredExamSeries,
    filteredMonthlyArSeries,
    monthlySeries,
    monthlyChartData,
    switchAdminTab,
    switchAdminMode,
    refreshResources,
    saveEditResource,
    submitResourceForm,
  };
}
