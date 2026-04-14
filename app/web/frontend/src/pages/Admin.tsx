import { FormEvent, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  BarChart3,
  BookOpen,
  GraduationCap,
  LogOut,
  Menu,
  Pencil,
  Plus,
  School,
  Search,
  Trash2,
  Trophy,
  Upload,
  Users,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/ChartCard";
import { FormAlert } from "@/components/PortalCard";
import { StatCard } from "@/components/StatCard";
import { routes } from "@/lib/routes";

type AdminTab = "overview" | "students" | "teachers" | "resources" | "chat";
type OverviewGrade = "7" | "8";

interface ResourceUploadState {
  active: boolean;
  percent: number;
  message: string;
  error: boolean;
}

interface AdminPageProps {
  authLogin?: string;
  authError?: string;
  adminNotice?: string;
  adminPanel?: AdminTab;
  adminSchool?: string;
  adminStudents?: Array<Record<string, unknown>>;
  adminTeachers?: Array<Record<string, unknown>>;
  adminTeacherOptions?: Array<{ name: string; school_codes: string[] }>;
  adminGroupOptions?: Array<{ name: string; school_codes: string[] }>;
  adminTeacherEdit?: Record<string, unknown> | null;
  adminTeacherEditSchool?: string;
  adminSchoolOptions?: Array<{ code: string; label: string }>;
  adminQuickStats?: Record<string, number>;
  adminSchoolInfo?: Array<Record<string, unknown>>;
  adminSubjectInfo?: Array<Record<string, unknown>>;
  adminGroupZones?: {
    green?: Array<Record<string, unknown>>;
    yellow?: Array<Record<string, unknown>>;
    red?: Array<Record<string, unknown>>;
  };
  adminResourceTypes?: Array<Record<string, unknown>>;
  adminResourceActiveTypes?: Array<Record<string, unknown>>;
  adminResources?: Array<Record<string, unknown>>;
  adminResourceSubjectOptions?: string[];
  adminResourceUploadEnabled?: boolean;
  csrfToken?: string;
}

const tabs: { key: AdminTab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "students", label: "Students" },
  { key: "teachers", label: "Teachers" },
  { key: "resources", label: "Resources" },
  { key: "chat", label: "Chat" },
];

function asString(value: unknown) {
  return String(value || "").trim();
}

function asNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => asString(item))
    .filter(Boolean);
}

function asPositiveNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function gradeFromGroupLabel(label: unknown): OverviewGrade | "" {
  const match = asString(label).match(/^([78])/);
  if (!match) {
    return "";
  }
  return match[1] as OverviewGrade;
}

function availableGradesForRow(row: Record<string, unknown> | null | undefined): OverviewGrade[] {
  const grades = new Set<OverviewGrade>();
  const groups = Array.isArray(row?.groups) ? (row.groups as Array<Record<string, unknown>>) : [];
  const monthlySeries = Array.isArray(row?.monthly_series) ? (row.monthly_series as Array<Record<string, unknown>>) : [];

  for (const groupRow of groups) {
    const grade = gradeFromGroupLabel(groupRow?.label);
    if (grade) {
      grades.add(grade);
    }
  }

  for (const seriesRow of monthlySeries) {
    const grade = gradeFromGroupLabel(seriesRow?.label);
    if (grade) {
      grades.add(grade);
    }
  }

  return (["7", "8"] as OverviewGrade[]).filter((grade) => grades.has(grade));
}

function filterGroupsByGrade(groups: Array<Record<string, unknown>>, grade: OverviewGrade | "") {
  if (!grade) {
    return groups;
  }
  return groups.filter((groupRow) => gradeFromGroupLabel(groupRow?.label) === grade);
}

function filterMonthlySeriesByGrade(monthlySeries: Array<Record<string, unknown>>, grade: OverviewGrade | "") {
  if (!grade) {
    return monthlySeries;
  }
  return monthlySeries.filter((seriesRow) => gradeFromGroupLabel(seriesRow?.label) === grade);
}

function trimEmptyMonthlyMonths(months: string[], monthlySeries: Array<Record<string, unknown>>) {
  if (!months.length || !monthlySeries.length) {
    return {
      months,
      series: monthlySeries,
    };
  }

  const keepIndexes = months.map((_month, monthIndex) =>
    monthlySeries.some((seriesRow) => {
      const values = Array.isArray(seriesRow?.values) ? (seriesRow.values as unknown[]) : [];
      return asPositiveNumber(values[monthIndex]) !== null;
    }),
  );
  const hasAnyMonths = keepIndexes.some(Boolean);

  return {
    months: hasAnyMonths ? months.filter((_month, monthIndex) => keepIndexes[monthIndex]) : [],
    series: monthlySeries.map((seriesRow) => {
      const values = Array.isArray(seriesRow?.values) ? (seriesRow.values as unknown[]) : [];
      return {
        ...seriesRow,
        values: hasAnyMonths ? values.filter((_value, monthIndex) => keepIndexes[monthIndex]) : [],
      };
    }),
  };
}

function formatMonthKeyLabel(monthKey: string) {
  const match = asString(monthKey).match(/^(\d{4})-(\d{2})$/);
  if (!match) {
    return asString(monthKey);
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) {
    return asString(monthKey);
  }

  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      year: "numeric",
    }).format(new Date(year, month - 1, 1));
  } catch (_error) {
    return asString(monthKey);
  }
}

function submitConfirm(event: FormEvent<HTMLFormElement>, message: string) {
  if (!window.confirm(message)) {
    event.preventDefault();
  }
}

function createUploadId() {
  const randomPart =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().replace(/-/g, "")
      : `${Date.now()}${Math.random().toString(36).slice(2, 12)}`;
  return `upload-${randomPart}`.slice(0, 64);
}

function buildUploadWebSocketUrl(uploadId: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/resource-upload/${encodeURIComponent(uploadId)}`;
}

function normalizeAdminTab(value: unknown): AdminTab {
  const normalized = asString(value).toLowerCase();
  if (normalized === "students" || normalized === "teachers" || normalized === "resources" || normalized === "chat") {
    return normalized;
  }
  return "overview";
}

function buildAdminTabUrl(tab: AdminTab, school: string) {
  const url = new URL(window.location.href);
  url.searchParams.set("panel", tab);
  url.searchParams.set("school", tab === "students" ? school || "all" : "all");
  return `${url.pathname}${url.search}${url.hash}`;
}

export default function AdminPage(props: AdminPageProps) {
  const initialTab = normalizeAdminTab(props.adminPanel);
  const [activeTab, setActiveTab] = useState<AdminTab>(initialTab);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const currentSchool = props.adminSchool || "all";
  const schoolOptions = (Array.isArray(props.adminSchoolOptions) ? props.adminSchoolOptions : []).filter(
    (option): option is { code: string; label: string } => Boolean(option && typeof option.code === "string" && typeof option.label === "string"),
  );
  const students = Array.isArray(props.adminStudents) ? props.adminStudents : [];
  const teachers = Array.isArray(props.adminTeachers) ? props.adminTeachers : [];
  const resourceTypes = Array.isArray(props.adminResourceTypes) ? props.adminResourceTypes : [];
  const activeResourceTypes = Array.isArray(props.adminResourceActiveTypes) ? props.adminResourceActiveTypes : [];
  const [resourcesList, setResourcesList] = useState<Array<Record<string, unknown>>>(Array.isArray(props.adminResources) ? props.adminResources : []);
  const quickStats = props.adminQuickStats || {};
  const schoolInfo = Array.isArray(props.adminSchoolInfo) ? props.adminSchoolInfo : [];
  const subjectInfo = Array.isArray(props.adminSubjectInfo) ? props.adminSubjectInfo : [];
  const teacherOptions = (Array.isArray(props.adminTeacherOptions) ? props.adminTeacherOptions : []).map((option) => ({
    name: asString(option?.name),
    school_codes: asStringArray(option?.school_codes),
  }));
  const groupOptions = (Array.isArray(props.adminGroupOptions) ? props.adminGroupOptions : []).map((option) => ({
    name: asString(option?.name),
    school_codes: asStringArray(option?.school_codes),
  }));
  const teacherEdit = props.adminTeacherEdit || null;

  const availableSubjectSchools = schoolOptions.filter((option) => option.code !== "all");
  const initialSchool = props.adminTeacherEditSchool || availableSubjectSchools[0]?.code || "all";
  const [teacherMode, setTeacherMode] = useState(teacherEdit ? "add" : "select");
  const [teacherSchool, setTeacherSchool] = useState(initialSchool);
  const [searchQuery, setSearchQuery] = useState("");
  const [editingTypeId, setEditingTypeId] = useState<number | null>(null);
  const [selectedOverviewSchool, setSelectedOverviewSchool] = useState(availableSubjectSchools[0]?.code || "");
  const schoolSubjectRows = subjectInfo.filter((row) => asString(row.school_key).toLowerCase() === selectedOverviewSchool);
  const [selectedSubjectName, setSelectedSubjectName] = useState(asString(schoolSubjectRows[0]?.subject_name));
  const [selectedSehriyoGrade, setSelectedSehriyoGrade] = useState<OverviewGrade | "">("");
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
  } | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [uploadFormKey, setUploadFormKey] = useState(0);
  const editResourceFileRef = useRef<HTMLInputElement>(null);
  const editThumbnailFileRef = useRef<HTMLInputElement>(null);
  const resourceUploadSocketRef = useRef<WebSocket | null>(null);
  const resourceUploadXhrRef = useRef<XMLHttpRequest | null>(null);

  // ── Chat admin state ────────────────────────────────────────────────────────
  type ChatMsg = { id: number; room: string; authorName: string; authorStudentId: string; body: string; isDeleted: boolean; editedAt: string | null; createdAt: string };
  type BlockedUser = { studentId: string; blockedBy: string; blockedAt: string; reason: string };
  const [chatRoom, setChatRoom] = useState("global");
  const [chatRooms, setChatRooms] = useState<{ room: string; active: number }[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [blockedUsers, setBlockedUsers] = useState<BlockedUser[]>([]);
  const [blockReason, setBlockReason] = useState("");

  function loadChatRooms() {
    fetch("/admin/api/chat/rooms").then((r) => r.json()).then((d) => {
      const base = [{ room: "global", active: 0 }];
      const merged = [...base];
      for (const r of (d.rooms ?? [])) {
        if (!merged.find((x) => x.room === r.room)) merged.push(r);
      }
      setChatRooms(merged);
    }).catch(() => {});
  }

  function loadChatMessages(room: string) {
    setChatLoading(true);
    fetch(`/admin/api/chat/messages?room=${encodeURIComponent(room)}`).then((r) => r.json()).then((d) => {
      setChatMessages(Array.isArray(d.messages) ? d.messages : []);
    }).catch(() => {}).finally(() => setChatLoading(false));
  }

  function loadBlocked() {
    fetch("/admin/api/chat/blocked").then((r) => r.json()).then((d) => {
      setBlockedUsers(Array.isArray(d.blocked) ? d.blocked : []);
    }).catch(() => {});
  }

  function adminDeleteMsg(id: number) {
    fetch(`/admin/api/chat/messages/${id}`, { method: "DELETE" }).then((r) => {
      if (r.ok) setChatMessages((prev) => prev.map((m) => m.id === id ? { ...m, isDeleted: true } : m));
    }).catch(() => {});
  }

  function adminBlockUser(studentId: string) {
    fetch("/admin/api/chat/block", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ studentId, reason: blockReason }),
    }).then((r) => { if (r.ok) { setBlockReason(""); loadBlocked(); } }).catch(() => {});
  }

  function adminUnblock(studentId: string) {
    fetch(`/admin/api/chat/block/${encodeURIComponent(studentId)}`, { method: "DELETE" })
      .then((r) => { if (r.ok) loadBlocked(); }).catch(() => {});
  }

  useEffect(() => {
    if (activeTab === "chat") {
      loadChatRooms();
      loadChatMessages(chatRoom);
      loadBlocked();
    }
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
      asString(student.student_id),
      asString(student.subjects),
      asString(student.school_name),
    ]
      .join(" ")
      .toLowerCase();
    return !searchQuery || haystack.includes(searchQuery.toLowerCase());
  });

  const selectedSubjectRow =
    schoolSubjectRows.find((row) => asString(row.subject_name) === selectedSubjectName) || schoolSubjectRows[0];
  const baseGroupRows = Array.isArray(selectedSubjectRow?.groups) ? (selectedSubjectRow.groups as Array<Record<string, unknown>>) : [];
  const baseMonthlyMonths = Array.isArray(selectedSubjectRow?.monthly_months) ? (selectedSubjectRow.monthly_months as string[]) : [];
  const baseMonthlySeries = Array.isArray(selectedSubjectRow?.monthly_series) ? (selectedSubjectRow.monthly_series as Array<Record<string, unknown>>) : [];
  const isSehriyoOverview = asString(selectedSubjectRow?.school_key).toLowerCase() === "sehriyo";
  const availableOverviewGrades = isSehriyoOverview ? availableGradesForRow(selectedSubjectRow) : [];
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
  const selectedGroupRows = isSehriyoOverview ? filterGroupsByGrade(baseGroupRows, activeOverviewGrade) : baseGroupRows;
  const filteredMonthlySeries = isSehriyoOverview ? filterMonthlySeriesByGrade(baseMonthlySeries, activeOverviewGrade) : baseMonthlySeries;
  const monthlyTimeline = trimEmptyMonthlyMonths(baseMonthlyMonths, filteredMonthlySeries);
  const monthlyMonths = monthlyTimeline.months;
  const monthlySeries = monthlyTimeline.series;
  const monthlyChartData = monthlyMonths.map((monthKey, index) => {
    const row: Record<string, string | number | null> = {
      month: monthKey,
      monthLabel: formatMonthKeyLabel(monthKey),
    };
    for (const seriesRow of monthlySeries) {
      row[asString(seriesRow.label)] = Array.isArray(seriesRow.values) ? (seriesRow.values[index] as number | null) : null;
    }
    return row;
  });

  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      setActiveTab(normalizeAdminTab(params.get("panel")));
      setMobileNavOpen(false);
    };
    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

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
      if (resourceUploadSocketRef.current && resourceUploadSocketRef.current.readyState < WebSocket.CLOSING) {
        resourceUploadSocketRef.current.close();
      }
      resourceUploadSocketRef.current = null;
      if (resourceUploadXhrRef.current) {
        resourceUploadXhrRef.current.abort();
      }
      resourceUploadXhrRef.current = null;
    };
  }, []);

  function switchAdminTab(nextTab: AdminTab) {
    setActiveTab(nextTab);
    setMobileNavOpen(false);
    const nextUrl = buildAdminTabUrl(nextTab, currentSchool);
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (nextUrl !== currentUrl) {
      window.history.pushState({}, "", nextUrl);
    }
  }

  async function refreshResources() {
    try {
      const res = await fetch(routes.adminResourcesApi);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.resources)) {
          setResourcesList(data.resources);
        }
      }
    } catch (_error) {
      // ignore network errors silently
    }
  }

  async function saveEditResource() {
    if (!editingResource || editSaving) return;
    setEditSaving(true);
    setEditError("");
    try {
      const formData = new FormData();
      formData.set("resource_title", editingResource.title.trim());
      formData.set("resource_description", editingResource.description.trim());
      formData.set("csrf_token", props.csrfToken || "");
      const resourceFile = editResourceFileRef.current?.files?.[0];
      if (resourceFile) formData.set("resource_file", resourceFile);
      const thumbnailFile = editThumbnailFileRef.current?.files?.[0];
      if (thumbnailFile) formData.set("thumbnail_file", thumbnailFile);
      const res = await fetch(routes.adminResourceEdit(editingResource.id), {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
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

    if (resourceUploadSocketRef.current && resourceUploadSocketRef.current.readyState < WebSocket.CLOSING) {
      resourceUploadSocketRef.current.close();
    }
    resourceUploadSocketRef.current = null;

    setIsSubmittingResource(true);
    setResourceUploadState({
      active: true,
      percent: 1,
      message: "Preparing upload...",
      error: false,
    });

    if (typeof window.WebSocket !== "undefined") {
      try {
        const socket = new WebSocket(buildUploadWebSocketUrl(uploadId));
        resourceUploadSocketRef.current = socket;
        socket.onmessage = (messageEvent) => {
          try {
            const payload = JSON.parse(String(messageEvent.data || ""));
            if (payload?.type === "heartbeat") {
              return;
            }
            setResourceUploadState((current) => ({
              active: true,
              percent: Math.max(current.percent, Math.max(0, Math.min(100, Number(payload?.percent || 0)))),
              message: asString(payload?.message) || current.message || "Uploading resource...",
              error: Boolean(payload?.error),
            }));
          } catch (_error) {
            return;
          }
        };
      } catch (_error) {
        resourceUploadSocketRef.current = null;
      }
    }

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

        if (resourceUploadSocketRef.current && resourceUploadSocketRef.current.readyState < WebSocket.CLOSING) {
          resourceUploadSocketRef.current.close();
        }
        resourceUploadSocketRef.current = null;
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
        if (resourceUploadSocketRef.current && resourceUploadSocketRef.current.readyState < WebSocket.CLOSING) {
          resourceUploadSocketRef.current.close();
        }
        resourceUploadSocketRef.current = null;
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
        resourceUploadSocketRef.current = null;
        resourceUploadXhrRef.current = null;
        setIsSubmittingResource(false);
      };

      xhr.send(formData);
    } catch (_error) {
      if (resourceUploadSocketRef.current && resourceUploadSocketRef.current.readyState < WebSocket.CLOSING) {
        resourceUploadSocketRef.current.close();
      }
      resourceUploadSocketRef.current = null;
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

  return (
    <div className="min-h-[100dvh] bg-background">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-foreground/5 bg-surface/95 backdrop-blur" style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}>
        <div className="mx-auto flex w-full max-w-6xl items-center gap-3 px-3 py-2.5 sm:px-4 md:px-6">
          <a href={`/?panel=overview&school=${encodeURIComponent(currentSchool)}`} className="flex items-center gap-2 rounded-lg px-2 py-2 font-display text-sm font-bold">
            <GraduationCap className="h-5 w-5" />
            MSI
          </a>
          <nav className="hidden min-w-0 flex-1 gap-1 overflow-x-auto sm:flex" aria-label="Admin navigation">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => switchAdminTab(tab.key)}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-bold transition-colors ${
                  activeTab === tab.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 sm:hidden">
            <button
              type="button"
              onClick={() => setMobileNavOpen((current) => !current)}
              className="relative z-50 flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-muted"
              aria-label={mobileNavOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={mobileNavOpen}
              aria-controls="admin-mobile-nav"
            >
              {mobileNavOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
          <form action={routes.logout} method="post" className="shrink-0 sm:ml-auto">
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <button type="submit" className="flex h-9 w-9 items-center justify-center rounded-lg text-destructive hover:bg-muted" aria-label="Exit">
              <LogOut className="h-4 w-4" />
            </button>
          </form>
        </div>
        {mobileNavOpen ? (
          <div id="admin-mobile-nav" className="relative z-50 border-t border-foreground/5 px-3 pb-3 pt-2 sm:hidden">
            <nav className="grid grid-cols-2 gap-2" aria-label="Admin mobile navigation">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => switchAdminTab(tab.key)}
                  className={`rounded-xl px-3 py-3 text-left text-sm font-bold transition-colors ${
                    activeTab === tab.key ? "bg-primary text-primary-foreground" : "bg-muted text-foreground hover:bg-foreground/10"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        ) : null}
      </header>

      <main className="mx-auto w-full max-w-6xl px-3 pb-4 pt-16 sm:px-4 md:px-6">
        {props.authError ? <FormAlert kind="error">{props.authError}</FormAlert> : null}
        {props.adminNotice ? <FormAlert kind="notice">{props.adminNotice}</FormAlert> : null}
        {resourceUploadState.active && activeTab !== "resources" ? (
          <div className="mb-4 rounded-xl border border-foreground/10 bg-surface px-4 py-3 shadow-card">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className={`text-xs font-semibold uppercase tracking-wide ${resourceUploadState.error ? "text-destructive" : "text-muted-foreground"}`}>
                  {resourceUploadState.message}
                </p>
              </div>
              <button
                type="button"
                onClick={() => switchAdminTab("resources")}
                className="shrink-0 rounded-lg bg-muted px-3 py-1.5 text-[11px] font-bold text-foreground hover:bg-foreground/10"
              >
                Open Upload
              </button>
            </div>
            <div className="overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(resourceUploadState.percent)}>
              <div
                className={`h-2 rounded-full transition-[width] duration-200 ${resourceUploadState.error ? "bg-destructive" : "bg-primary"}`}
                style={{ width: `${Math.max(0, Math.min(100, resourceUploadState.percent))}%` }}
              />
            </div>
          </div>
        ) : null}

        {activeTab === "overview" ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard title="Students" value={String(asNumber(quickStats.total_students))} icon={<Users className="h-3.5 w-3.5" />} />
              <StatCard title="Schools" value={String(asNumber(quickStats.total_schools))} icon={<School className="h-3.5 w-3.5" />} />
              <StatCard title="Teachers" value={String(asNumber(quickStats.total_teachers))} icon={<GraduationCap className="h-3.5 w-3.5" />} />
              <StatCard title="Subjects" value={String(asNumber(quickStats.total_subjects))} icon={<BookOpen className="h-3.5 w-3.5" />} />
            </div>

            <ChartCard title="School Info" icon={<School className="h-4 w-4 text-info" />}>
              <ul className="space-y-3">
                {schoolInfo.length ? (
                  schoolInfo.map((row) => (
                    <li key={asString(row.school_name)} className="rounded-lg border border-foreground/5 p-3">
                      <p className="text-sm font-bold">{asString(row.school_name)}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {asNumber(row.total_students)} students · {asNumber(row.total_subjects)} subjects · {asNumber(row.total_groups)} groups · AAP{" "}
                        {row.avg_aap == null ? "-" : asNumber(row.avg_aap).toFixed(1)} · AR {row.avg_ar == null ? "-" : asNumber(row.avg_ar).toFixed(1)}%
                      </p>
                    </li>
                  ))
                ) : (
                  <li className="text-sm text-muted-foreground">No school statistics available.</li>
                )}
              </ul>
            </ChartCard>

            <ChartCard
              title="Subject Overview"
              icon={<BarChart3 className="h-4 w-4 text-info" />}
              headerActions={
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={selectedOverviewSchool}
                    onChange={(event) => {
                      const nextSchool = event.target.value;
                      setSelectedOverviewSchool(nextSchool);
                      setSelectedSehriyoGrade("");
                      const nextRows = subjectInfo.filter((row) => asString(row.school_key).toLowerCase() === nextSchool);
                      setSelectedSubjectName(asString(nextRows[0]?.subject_name));
                    }}
                    className="rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-xs font-medium outline-none"
                  >
                    {availableSubjectSchools.map((option) => (
                      <option key={option.code} value={option.code}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={selectedSubjectName}
                    onChange={(event) => {
                      setSelectedSubjectName(event.target.value);
                      setSelectedSehriyoGrade("");
                    }}
                    className="rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-xs font-medium outline-none"
                  >
                    {schoolSubjectRows.map((row) => (
                      <option key={asString(row.subject_name)} value={asString(row.subject_name)}>
                        {asString(row.subject_name)}
                      </option>
                    ))}
                  </select>
                  {isSehriyoOverview && availableOverviewGrades.length ? (
                    <div className="flex items-center rounded-lg border border-foreground/10 bg-muted p-0.5">
                      {(["7", "8"] as OverviewGrade[]).map((grade) => {
                        const enabled = availableOverviewGrades.includes(grade);
                        return (
                          <button
                            key={grade}
                            type="button"
                            disabled={!enabled}
                            onClick={() => {
                              if (enabled) {
                                setSelectedSehriyoGrade(grade);
                              }
                            }}
                            className={`rounded-md px-3 py-1.5 text-[11px] font-bold transition-colors ${
                              enabled && activeOverviewGrade === grade
                                ? "bg-surface text-foreground shadow-sm"
                                : "text-muted-foreground"
                            } ${!enabled ? "cursor-not-allowed opacity-40" : ""}`}
                          >
                            {grade} Graders
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              }
            >
              {selectedSubjectRow ? (
                <div className="space-y-4">
                  <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={selectedGroupRows} margin={{ top: 8, right: 8, left: -6, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--foreground) / 0.06)" />
                          <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                          <YAxis
                            yAxisId="aap"
                            domain={[0, 9]}
                            tick={{ fontSize: 10 }}
                            width={30}
                            tickMargin={4}
                          />
                          <YAxis
                            yAxisId="ar"
                            orientation="right"
                            domain={[0, 100]}
                            tick={{ fontSize: 10 }}
                            tickFormatter={(value) => `${value}%`}
                            width={40}
                            tickMargin={4}
                          />
                          <Tooltip
                            formatter={(value, name) => {
                              const numericValue = asNumber(value);
                              if (name === "AR %") {
                                return [`${numericValue.toFixed(1)}%`, name];
                              }
                              return [numericValue.toFixed(1), name];
                            }}
                          />
                          <Legend />
                          <Bar
                            yAxisId="aap"
                            dataKey="avg_aap"
                            name="AAP"
                            fill="hsl(var(--info))"
                            radius={[4, 4, 0, 0]}
                          />
                          <Bar
                            yAxisId="ar"
                            dataKey="avg_ar"
                            name="AR %"
                            fill="hsl(var(--success))"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[320px] text-left">
                        <thead>
                          <tr className="border-b border-foreground/5">
                            {["Group", "Students", "AAP", "AR"].map((heading) => (
                              <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                                {heading}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {selectedGroupRows.map((row) => (
                            <tr key={asString(row.label)} className="border-b border-foreground/5">
                              <td className="px-3 py-2.5 text-xs font-medium">{asString(row.label)}</td>
                              <td className="px-3 py-2.5 text-xs">{asNumber(row.students_count)}</td>
                              <td className="px-3 py-2.5 text-xs">{row.avg_aap == null ? "-" : asNumber(row.avg_aap).toFixed(1)}</td>
                              <td className="px-3 py-2.5 text-xs">{row.avg_ar == null ? "-" : `${asNumber(row.avg_ar).toFixed(1)}%`}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={monthlyChartData} margin={{ top: 8, right: 8, left: -6, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--foreground) / 0.06)" />
                        <XAxis dataKey="monthLabel" tick={{ fontSize: 10 }} />
                        <YAxis domain={[0, 9]} tick={{ fontSize: 10 }} width={30} tickMargin={4} />
                        <Tooltip labelFormatter={(value) => asString(value)} />
                        <Legend />
                        {monthlySeries.map((seriesRow, index) => (
                          <Line
                            key={asString(seriesRow.label)}
                            type="monotone"
                            dataKey={asString(seriesRow.label)}
                            connectNulls
                            stroke={["#2563eb", "#f59e0b", "#1d4ed8", "#16a34a", "#7c3aed"][index % 5]}
                            strokeWidth={2}
                            dot={{ r: 3 }}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No subject statistics available.</p>
              )}
            </ChartCard>

            {[
              { label: "Green Zone", key: "green", icon: <Trophy className="h-4 w-4 text-success" /> },
              { label: "Yellow Zone", key: "yellow", icon: <AlertTriangle className="h-4 w-4 text-warning" /> },
              { label: "Red Zone", key: "red", icon: <AlertCircle className="h-4 w-4 text-destructive" /> },
            ].map((zone) => {
              const rows = Array.isArray(props.adminGroupZones?.[zone.key as keyof typeof props.adminGroupZones])
                ? (props.adminGroupZones?.[zone.key as keyof typeof props.adminGroupZones] as Array<Record<string, unknown>>)
                : [];
              return (
                <ChartCard key={zone.key} title={zone.label} icon={zone.icon}>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[520px] text-left">
                      <thead>
                        <tr className="border-b border-foreground/5">
                          {["Group", "Subject", "AAP", "AR", "School"].map((heading) => (
                            <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                              {heading}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {rows.length ? (
                          rows.map((row, index) => (
                            <tr key={`${zone.key}-${index}`} className="border-b border-foreground/5">
                              <td className="px-3 py-2.5 text-xs font-medium">{asString(row.group_name)}</td>
                              <td className="px-3 py-2.5 text-xs">{asString(row.subject_name)}</td>
                              <td className="px-3 py-2.5 text-xs">{row.aap == null ? "-" : asNumber(row.aap).toFixed(1)}</td>
                              <td className="px-3 py-2.5 text-xs">{row.ar == null ? "-" : asNumber(row.ar).toFixed(1)}</td>
                              <td className="px-3 py-2.5 text-xs text-muted-foreground">{asString(row.school_name)}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={5} className="px-3 py-4 text-sm text-muted-foreground">
                              No groups in this zone.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </ChartCard>
              );
            })}
          </div>
        ) : null}

        {activeTab === "students" ? (
          <div className="space-y-4">
            <div className="sticky top-[calc(env(safe-area-inset-top,0px)+4.5rem)] z-30 -mx-3 bg-background/95 px-3 pb-3 pt-1 backdrop-blur sm:-mx-4 sm:px-4 md:-mx-6 md:px-6">
              <div className="flex flex-col gap-3 sm:flex-row">
                <label className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder="Name, student ID, subject, or school"
                    className="w-full rounded-xl border-2 border-foreground/10 bg-surface py-2.5 pl-10 pr-4 text-sm outline-none"
                  />
                </label>
                <form action="/" method="get" className="shrink-0">
                  <input type="hidden" name="panel" value="students" />
                  <select
                    name="school"
                    defaultValue={currentSchool}
                    onChange={(event) => event.currentTarget.form?.submit()}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm font-medium outline-none sm:w-52"
                  >
                    {schoolOptions.map((option) => (
                      <option key={option.code} value={option.code}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </form>
              </div>
            </div>

            <ChartCard title="Students" subtitle={`${filteredStudents.length} results`} icon={<Users className="h-4 w-4 text-info" />}>
              <div className="max-h-[68dvh] overflow-auto">
                <table className="w-full min-w-[720px] text-left">
                  <thead>
                    <tr className="sticky top-0 z-10 border-b border-foreground/5 bg-surface">
                      {["ID", "Full Name", "Subjects", "School"].map((heading) => (
                        <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredStudents.length ? (
                      filteredStudents.map((student) => (
                        <tr key={asNumber(student.id)} className="border-b border-foreground/5 hover:bg-muted/40">
                          <td className="px-3 py-2.5 text-xs font-bold">
                            <a href={routes.adminStudentDashboard(asNumber(student.id), currentSchool)} className="text-info hover:underline">
                              {asString(student.student_id)}
                            </a>
                          </td>
                          <td className="px-3 py-2.5 text-sm font-medium">
                            <a href={routes.adminStudentProfile(asNumber(student.id))} className="hover:underline">
                              {asString(student.full_name)}
                            </a>
                          </td>
                          <td className="px-3 py-2.5 text-xs text-muted-foreground">{asString(student.subjects)}</td>
                          <td className="px-3 py-2.5 text-xs text-muted-foreground">{asString(student.school_name)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} className="px-3 py-4 text-sm text-muted-foreground">
                          No students match your search.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          </div>
        ) : null}

        {activeTab === "teachers" ? (
          <div className="grid gap-4 xl:grid-cols-[380px_minmax(0,1fr)]">
            <ChartCard title="Teacher Assignment" icon={<GraduationCap className="h-4 w-4 text-info" />}>
              <form action={routes.adminTeacherAdd} method="post" className="space-y-3">
                <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                <input type="hidden" name="teacher_mode" value={teacherMode} />
                <input type="hidden" name="teacher_edit_id" value={asString(teacherEdit?.id)} />

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setTeacherMode("select")}
                    className={`rounded-lg px-3 py-1.5 text-[11px] font-bold ${teacherMode === "select" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
                  >
                    Select
                  </button>
                  <button
                    type="button"
                    onClick={() => setTeacherMode("add")}
                    className={`rounded-lg px-3 py-1.5 text-[11px] font-bold ${teacherMode === "add" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
                  >
                    Add New
                  </button>
                  {teacherEdit ? (
                    <a href={`/?panel=teachers&school=${encodeURIComponent(currentSchool)}`} className="rounded-lg bg-muted px-3 py-1.5 text-[11px] font-bold text-muted-foreground">
                      Cancel Edit
                    </a>
                  ) : null}
                </div>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Select School</span>
                  <select
                    name="teacher_assigned_school"
                    value={teacherSchool}
                    onChange={(event) => setTeacherSchool(event.target.value)}
                    required
                    className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
                  >
                    <option value="" disabled>
                      Select school
                    </option>
                    {availableSubjectSchools.map((option) => (
                      <option key={option.code} value={option.code}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                {teacherMode === "select" ? (
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Select Teacher</span>
                    <select
                      name="teacher_selected_name"
                      defaultValue={teacherEdit ? asString(teacherEdit.full_name) : ""}
                      required
                      className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
                    >
                      <option value="" disabled>
                        Select from existing teachers
                      </option>
                      {filteredTeacherOptions.map((option) => (
                        <option key={option.name} value={option.name}>
                          {option.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <>
                    <label className="block">
                      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Teacher Full Name</span>
                      <input
                        type="text"
                        name="teacher_full_name"
                        defaultValue={teacherEdit ? asString(teacherEdit.full_name) : ""}
                        className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
                      />
                    </label>
                    <label className="block">
                      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Pay Rate</span>
                      <input
                        type="number"
                        name="teacher_pay_rate"
                        step="0.01"
                        min="0"
                        defaultValue={teacherEdit ? asString(teacherEdit.pay_rate) : ""}
                        className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
                      />
                    </label>
                  </>
                )}

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Select Group</span>
                  <select
                    name="teacher_assigned_group"
                    defaultValue={teacherEdit ? asString(teacherEdit.assigned_group) : ""}
                    required
                    className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
                  >
                    <option value="" disabled>
                      Select group
                    </option>
                    {filteredGroupOptions.map((option) => (
                      <option key={option.name} value={option.name}>
                        {option.name}
                      </option>
                    ))}
                  </select>
                </label>

                <button className="w-full rounded-xl bg-primary px-6 py-3 text-sm font-bold text-primary-foreground shadow-neo">
                  Save changes
                </button>
              </form>
            </ChartCard>

            <ChartCard title="Teachers" subtitle={`${teachers.length} total`} icon={<Users className="h-4 w-4 text-info" />}>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left">
                  <thead>
                    <tr className="border-b border-foreground/5">
                      {["ID", "Full Name", "Pay Rate", "Assigned Group", "Actions"].map((heading) => (
                        <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {teachers.length ? (
                      teachers.map((teacher) => (
                        <tr key={asNumber(teacher.id)} className="border-b border-foreground/5">
                          <td className="px-3 py-2.5 text-xs">{asNumber(teacher.id)}</td>
                          <td className="px-3 py-2.5 text-sm font-medium">{asString(teacher.full_name)}</td>
                          <td className="px-3 py-2.5 text-xs">{asString(teacher.pay_rate)}</td>
                          <td className="px-3 py-2.5 text-xs">{asString(teacher.assigned_group)}</td>
                          <td className="px-3 py-2.5">
                            <div className="flex items-center gap-2">
                              <a href={routes.adminTeacherEdit(asNumber(teacher.id), currentSchool)} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted">
                                <Pencil className="h-3.5 w-3.5" />
                              </a>
                              <form
                                action={routes.adminTeacherDelete(asNumber(teacher.id))}
                                method="post"
                                onSubmit={(event) => submitConfirm(event, "Delete this teacher?")}
                              >
                                <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                                <button type="submit" className="flex h-8 w-8 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10">
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </form>
                            </div>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="px-3 py-4 text-sm text-muted-foreground">
                          No teachers yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          </div>
        ) : null}

        {activeTab === "resources" ? (
          <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
            <div className="space-y-4">
              <ChartCard title="Resource Types" icon={<Plus className="h-4 w-4 text-info" />}>
                <form action={routes.adminResourceTypeAdd} method="post" className="space-y-3">
                  <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Type Name</span>
                    <input
                      type="text"
                      name="resource_type_name"
                      placeholder="Video, Definitions, Worksheet..."
                      required
                      className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
                    />
                  </label>
                  <button className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">Add Type</button>
                </form>

                <div className="mt-4 space-y-2">
                  {resourceTypes.length ? (
                    resourceTypes.map((typeRow) => {
                      const typeId = asNumber(typeRow.id);
                      const isEditing = editingTypeId === typeId;
                      return (
                        <div key={typeId} className="rounded-lg border border-foreground/5 p-3">
                          {isEditing ? (
                            <form action={routes.adminResourceTypeRename(typeId)} method="post" className="space-y-2">
                              <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                              <input
                                type="text"
                                name="resource_type_name"
                                defaultValue={asString(typeRow.name)}
                                required
                                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-sm outline-none"
                              />
                              <div className="flex gap-2">
                                <button className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground">Done</button>
                                <button type="button" onClick={() => setEditingTypeId(null)} className="rounded-lg bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                                  Cancel
                                </button>
                              </div>
                            </form>
                          ) : (
                            <div className="flex items-center justify-between gap-3">
                              <strong className="text-sm">{asString(typeRow.name)}</strong>
                              <div className="flex gap-2">
                                <button type="button" onClick={() => setEditingTypeId(typeId)} className="rounded-lg bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                                  Rename
                                </button>
                                <form
                                  action={routes.adminResourceTypeDelete(typeId)}
                                  method="post"
                                  onSubmit={(event) => submitConfirm(event, "Delete this resource type?")}
                                >
                                  <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                                  <button className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-bold text-destructive">Delete</button>
                                </form>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-sm text-muted-foreground">No resource types yet.</p>
                  )}
                </div>
              </ChartCard>
            </div>

            <div className="space-y-4">
              <ChartCard title="Add Resource" icon={<Upload className="h-4 w-4 text-info" />}>
                <form
                  key={uploadFormKey}
                  action={routes.adminResourceAdd}
                  method="post"
                  encType="multipart/form-data"
                  className="grid gap-3 md:grid-cols-2"
                  onSubmit={submitResourceForm}
                >
                  <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                  <input type="hidden" name="upload_id" value="" />
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Subject</span>
                    <select name="resource_subject_name" required className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none">
                      <option value="" disabled>
                        Select subject
                      </option>
                      {(props.adminResourceSubjectOptions || []).map((subjectName) => (
                        <option key={subjectName} value={subjectName}>
                          {subjectName}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Resource Type</span>
                    <select name="resource_type_id" required className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none">
                      <option value="" disabled>
                        Select type
                      </option>
                      {activeResourceTypes.map((typeRow) => (
                        <option key={asNumber(typeRow.id)} value={asNumber(typeRow.id)}>
                          {asString(typeRow.name)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block md:col-span-2">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Title</span>
                    <input type="text" name="resource_title" required className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none" />
                  </label>
                  <div className="grid gap-3 md:col-span-2 md:grid-cols-2">
                    <label className="block">
                      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Upload File</span>
                      <input
                        type="file"
                        name="resource_file"
                        required
                        disabled={!props.adminResourceUploadEnabled}
                        className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                      />
                    </label>
                    <label className="block">
                      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Thumbnail Image <span className="font-normal normal-case text-muted-foreground/60">(optional, for videos)</span>
                      </span>
                      <input
                        type="file"
                        name="thumbnail_file"
                        accept="image/jpeg,image/png,image/webp"
                        disabled={!props.adminResourceUploadEnabled}
                        className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                      />
                    </label>
                  </div>
                  {!props.adminResourceUploadEnabled ? (
                    <p className="md:col-span-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Resource upload is disabled in this environment.
                    </p>
                  ) : null}
                  <label className="block md:col-span-2">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Description</span>
                    <textarea name="resource_description" rows={4} className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none" />
                  </label>
                  {resourceUploadState.active ? (
                    <div className="md:col-span-2">
                      <div className="overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(resourceUploadState.percent)}>
                        <div
                          className={`h-2 rounded-full transition-[width] duration-200 ${resourceUploadState.error ? "bg-destructive" : "bg-primary"}`}
                          style={{ width: `${Math.max(0, Math.min(100, resourceUploadState.percent))}%` }}
                        />
                      </div>
                      <p className={`mt-2 text-xs font-semibold uppercase tracking-wide ${resourceUploadState.error ? "text-destructive" : "text-muted-foreground"}`}>
                        {resourceUploadState.message}
                      </p>
                    </div>
                  ) : null}
                  <div className="md:col-span-2">
                    <button
                      disabled={isSubmittingResource || !props.adminResourceUploadEnabled}
                      className="rounded-xl bg-primary px-6 py-3 text-sm font-bold text-primary-foreground shadow-neo disabled:opacity-50"
                    >
                      {isSubmittingResource ? "Uploading..." : props.adminResourceUploadEnabled ? "Save Resource" : "Upload Disabled"}
                    </button>
                  </div>
                </form>
              </ChartCard>

              {(() => {
                const resourceSubjects = Array.from(new Set(resourcesList.map((r) => asString(r.subject_name)).filter(Boolean)));
                const filteredResources = resourceSubjectFilter === "all"
                  ? resourcesList
                  : resourcesList.filter((r) => asString(r.subject_name) === resourceSubjectFilter);
                return (
                  <ChartCard title="Resources" subtitle={`${resourcesList.length} total`} icon={<BookOpen className="h-4 w-4 text-info" />}>
                    {/* Subject filter tabs */}
                    {resourceSubjects.length > 1 ? (
                      <div className="mb-3 flex snap-x snap-mandatory gap-2 overflow-x-auto pb-0.5">
                        <button
                          type="button"
                          onClick={() => setResourceSubjectFilter("all")}
                          className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                            resourceSubjectFilter === "all" ? "bg-foreground text-background" : "bg-muted text-foreground hover:bg-foreground/10"
                          }`}
                        >
                          All <span className="opacity-60">{resourcesList.length}</span>
                        </button>
                        {resourceSubjects.map((subject) => {
                          const count = resourcesList.filter((r) => asString(r.subject_name) === subject).length;
                          return (
                            <button
                              key={subject}
                              type="button"
                              onClick={() => setResourceSubjectFilter(subject)}
                              className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                                resourceSubjectFilter === subject ? "bg-foreground text-background" : "bg-muted text-foreground hover:bg-foreground/10"
                              }`}
                            >
                              {subject} <span className="opacity-60">{count}</span>
                            </button>
                          );
                        })}
                      </div>
                    ) : null}

                    {/* Table with vertical scroll when > 5 rows */}
                    <div className="overflow-x-auto">
                      <div className={filteredResources.length > 5 ? "max-h-80 overflow-y-auto rounded-lg" : ""}>
                        <table className="w-full min-w-[800px] text-left">
                          <thead className="sticky top-0 bg-surface">
                            <tr className="border-b border-foreground/5">
                              {["ID", "Subject", "Type", "Title", "Action"].map((heading) => (
                                <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                                  {heading}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {filteredResources.length ? (
                              filteredResources.map((resource) => (
                                <tr key={asNumber(resource.id)} className="border-b border-foreground/5">
                                  <td className="px-3 py-2.5 text-xs">{asNumber(resource.id)}</td>
                                  <td className="px-3 py-2.5 text-xs">{asString(resource.subject_name)}</td>
                                  <td className="px-3 py-2.5 text-xs">{asString(resource.resource_type_name)}</td>
                                  <td className="px-3 py-2.5 text-xs">
                                    {asString(resource.resource_file_url) ? (
                                      <a href={asString(resource.resource_file_url)} target="_blank" rel="noopener noreferrer" className="block max-w-[260px] truncate hover:underline">
                                        {asString(resource.title) || "Open file"}
                                      </a>
                                    ) : asString(resource.title) ? (
                                      <span className="block max-w-[260px] truncate">{asString(resource.title)}</span>
                                    ) : (
                                      "-"
                                    )}
                                  </td>
                                  <td className="px-3 py-2.5">
                                    <div className="flex gap-2">
                                      <button
                                        type="button"
                                        onClick={() => {
                                          setEditingResource({
                                            id: asNumber(resource.id),
                                            title: asString(resource.title),
                                            description: asString(resource.description),
                                            resourceFileKind: asString(resource.resource_file_kind),
                                            thumbnailUrl: asString(resource.thumbnail_url),
                                          });
                                          setEditError("");
                                        }}
                                        className="flex items-center gap-1 rounded-lg bg-muted px-3 py-2 text-xs font-bold text-foreground hover:bg-foreground/10"
                                      >
                                        <Pencil className="h-3 w-3" /> Edit
                                      </button>
                                      <form
                                        action={routes.adminResourceDelete(asNumber(resource.id))}
                                        method="post"
                                        onSubmit={(event) => submitConfirm(event, "Delete this resource?")}
                                      >
                                        <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                                        <button className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-bold text-destructive">Delete</button>
                                      </form>
                                    </div>
                                  </td>
                                </tr>
                              ))
                            ) : (
                              <tr>
                                <td colSpan={5} className="px-3 py-4 text-sm text-muted-foreground">
                                  No resources yet.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </ChartCard>
                );
              })()}
            </div>
          </div>
        ) : null}

        {activeTab === "chat" ? (
          <div className="space-y-4">
            {/* Room selector */}
            <div className="flex flex-wrap gap-2">
              {chatRooms.length === 0 && (
                <button type="button" className="inline-flex items-center gap-1.5 rounded-full bg-foreground px-3 py-1.5 text-xs font-semibold text-background">Global</button>
              )}
              {chatRooms.map((r) => (
                <button
                  key={r.room}
                  type="button"
                  onClick={() => { setChatRoom(r.room); loadChatMessages(r.room); }}
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${chatRoom === r.room ? "bg-foreground text-background" : "bg-muted text-foreground hover:bg-foreground/10"}`}
                >
                  {r.room} {r.active > 0 && <span className="opacity-60">({r.active})</span>}
                </button>
              ))}
            </div>

            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
              {/* Messages */}
              <ChartCard title={`Messages — ${chatRoom}`} icon={<Search className="h-4 w-4 text-info" />}>
                {chatLoading ? (
                  <p className="text-sm text-muted-foreground">Loading…</p>
                ) : chatMessages.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No messages in this room.</p>
                ) : (
                  <div className="space-y-2">
                    {chatMessages.map((msg) => (
                      <div key={msg.id} className={`flex items-start gap-3 rounded-xl border px-3 py-2.5 ${msg.isDeleted ? "border-foreground/5 opacity-40" : "border-foreground/8"}`}>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-baseline gap-1.5">
                            <span className="text-[11px] font-bold">{msg.authorName}</span>
                            <span className="text-[10px] text-muted-foreground">{msg.authorStudentId}</span>
                            <span className="text-[10px] text-muted-foreground">· {msg.createdAt}</span>
                            {msg.isDeleted && <span className="text-[10px] text-destructive">[deleted]</span>}
                            {msg.editedAt && <span className="text-[10px] text-muted-foreground">(edited)</span>}
                          </div>
                          <p className="mt-0.5 text-xs leading-relaxed">{msg.body}</p>
                        </div>
                        {!msg.isDeleted && (
                          <div className="flex shrink-0 gap-1.5">
                            <button
                              type="button"
                              onClick={() => adminDeleteMsg(msg.id)}
                              className="rounded-lg bg-destructive/10 px-2.5 py-1.5 text-[10px] font-bold text-destructive hover:bg-destructive/20"
                            >
                              Delete
                            </button>
                            <button
                              type="button"
                              onClick={() => adminBlockUser(msg.authorStudentId)}
                              className="rounded-lg bg-muted px-2.5 py-1.5 text-[10px] font-bold hover:bg-foreground/10"
                            >
                              Block
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </ChartCard>

              {/* Blocked users */}
              <div className="space-y-4">
                <ChartCard title="Block a Student" icon={<AlertTriangle className="h-4 w-4 text-warning" />}>
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={blockReason}
                      onChange={(e) => setBlockReason(e.target.value)}
                      placeholder="Block reason (optional)"
                      className="w-full rounded-xl border border-foreground/10 bg-muted px-3 py-2 text-xs outline-none"
                    />
                    <p className="text-[10px] text-muted-foreground">Click "Block" next to a message to block that student.</p>
                  </div>
                </ChartCard>

                <ChartCard title="Blocked Students" icon={<AlertCircle className="h-4 w-4 text-destructive" />}>
                  {blockedUsers.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No blocked students.</p>
                  ) : (
                    <div className="space-y-2">
                      {blockedUsers.map((u) => (
                        <div key={u.studentId} className="flex items-start gap-3 rounded-xl border border-foreground/8 px-3 py-2.5">
                          <div className="min-w-0 flex-1">
                            <p className="text-[11px] font-bold">{u.studentId}</p>
                            {u.reason && <p className="text-[10px] text-muted-foreground">{u.reason}</p>}
                            <p className="text-[10px] text-muted-foreground">Blocked by {u.blockedBy} · {u.blockedAt}</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => adminUnblock(u.studentId)}
                            className="shrink-0 rounded-lg bg-muted px-2.5 py-1.5 text-[10px] font-bold hover:bg-foreground/10"
                          >
                            Unblock
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </ChartCard>
              </div>
            </div>
          </div>
        ) : null}
      </main>

      {/* Edit resource modal */}
      {editingResource ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
          onClick={() => { setEditingResource(null); setEditError(""); }}
        >
          <div
            className="flex max-h-[88dvh] w-full max-w-md flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex shrink-0 items-center justify-between border-b border-foreground/5 px-5 py-3">
              <h3 className="text-sm font-bold">Edit Resource</h3>
              <button
                type="button"
                onClick={() => { setEditingResource(null); setEditError(""); }}
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Scrollable body */}
            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="space-y-3 px-5 py-4">
                {editError ? <p className="text-xs font-semibold text-destructive">{editError}</p> : null}

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Title</span>
                  <input
                    type="text"
                    value={editingResource.title}
                    onChange={(e) => setEditingResource((prev) => prev ? { ...prev, title: e.target.value } : null)}
                    maxLength={180}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Description</span>
                  <textarea
                    value={editingResource.description}
                    onChange={(e) => setEditingResource((prev) => prev ? { ...prev, description: e.target.value } : null)}
                    rows={3}
                    maxLength={2000}
                    className="w-full resize-none rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                {/* Swap video / file */}
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {editingResource.resourceFileKind === "video" ? "Swap Video" : "Replace File"}
                    <span className="ml-1 font-normal normal-case text-muted-foreground/60">(optional — leave empty to keep current)</span>
                  </span>
                  <input
                    ref={editResourceFileRef}
                    type="file"
                    name="resource_file"
                    accept={editingResource.resourceFileKind === "video" ? "video/mp4,video/quicktime,video/x-m4v" : undefined}
                    disabled={editSaving}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                  />
                </label>

                {/* Swap thumbnail — only for videos */}
                {editingResource.resourceFileKind === "video" ? (
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      {editingResource.thumbnailUrl ? "Swap Thumbnail" : "Add Thumbnail"}
                      <span className="ml-1 font-normal normal-case text-muted-foreground/60">(optional)</span>
                    </span>
                    {editingResource.thumbnailUrl ? (
                      <img
                        src={editingResource.thumbnailUrl}
                        alt="Current thumbnail"
                        className="mb-2 h-20 w-auto rounded-lg object-cover"
                      />
                    ) : null}
                    <input
                      ref={editThumbnailFileRef}
                      type="file"
                      name="thumbnail_file"
                      accept="image/jpeg,image/png,image/webp"
                      disabled={editSaving}
                      className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                    />
                  </label>
                ) : null}
              </div>
            </div>

            {/* Footer */}
            <div className="flex shrink-0 gap-2 border-t border-foreground/5 px-5 py-3">
              <button
                type="button"
                disabled={editSaving}
                onClick={saveEditResource}
                className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground disabled:opacity-50"
              >
                {editSaving ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={() => { setEditingResource(null); setEditError(""); }}
                className="rounded-xl bg-muted px-5 py-2.5 text-sm font-bold text-muted-foreground hover:bg-foreground/10"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
