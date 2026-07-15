import { useEffect, useState } from "react";
import { KeyRound, Pencil, Plus, Trash2, Users } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { PaginationControls } from "@/shared/ui/RecordControls";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, buildAdminTabUrl } from "@/shared/lib/workspace";
import {
  Teacher,
  TeacherTab,
  TAB_STORAGE_KEY,
  TABLE_PAGE_SIZE,
  postForm,
  tabs,
  teacherCategoryLabel,
} from "@/features/people/teachers/model";
import { TeacherAssignmentModal } from "@/features/people/teachers/TeacherAssignmentModal";
import { TeacherAcademyPanel } from "@/features/teacher-academy/TeacherAcademyPanel";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";

export default function TeachersPanel({ state }: { state: any }) {
  const { teacherEdit, props, currentSchool } = state;
  const csrf: string = props.csrfToken || "";
  const isAcademicDirector = asString(state.adminMode).toLowerCase() === "academic_director";
  const defaultTab: TeacherTab = isAcademicDirector ? "academy" : "active";

  const [activeTab, setActiveTab] = useState<TeacherTab>(() => {
    if (typeof window !== "undefined") {
      const saved = window.sessionStorage.getItem(TAB_STORAGE_KEY);
      if (saved === "academy" || saved === "active") {
        return saved;
      }
    }
    return defaultTab;
  });
  const [teachers, setTeachers] = useState<Teacher[]>(
    Array.isArray(state.teachers) ? state.teachers : [],
  );
  const [academyTeachers, setAcademyTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(state.academyTeachers)
      ? state.academyTeachers
      : Array.isArray(props.adminTeacherAcademy)
        ? props.adminTeacherAcademy
        : [],
  );
  const [modalOpen, setModalOpen] = useState(Boolean(teacherEdit));
  const [teacherSubmitting, setTeacherSubmitting] = useState(false);
  const [modalError, setModalError] = useState("");
  const [teacherPage, setTeacherPage] = useState(1);
  const { toast, showToast } = useFloatingToast();

  useEffect(() => {
    if (Array.isArray(state.teachers)) {
      setTeachers(state.teachers as Teacher[]);
    }
  }, [state.teachers]);

  useEffect(() => {
    if (Array.isArray(state.academyTeachers)) {
      setAcademyTeachers(state.academyTeachers);
    } else if (Array.isArray(props.adminTeacherAcademy)) {
      setAcademyTeachers(props.adminTeacherAcademy);
    }
  }, [state.academyTeachers, props.adminTeacherAcademy]);

  useEffect(() => {
    setTeacherPage(1);
  }, [teachers.length]);

  function selectTab(tab: TeacherTab) {
    setActiveTab(tab);
    try {
      window.sessionStorage.setItem(TAB_STORAGE_KEY, tab);
    } catch {
      // Storage can be unavailable in restricted browser contexts.
    }
  }

  function syncTeachers(rows: Array<Record<string, unknown>>) {
    setTeachers(rows as Teacher[]);
    if (typeof state.setTeachers === "function") {
      state.setTeachers(rows);
    }
  }

  function syncAcademyTeachers(rows: Array<Record<string, unknown>>) {
    setAcademyTeachers(rows);
    if (typeof state.setAcademyTeachers === "function") {
      state.setAcademyTeachers(rows);
    }
  }

  function clearEditUrl() {
    if (teacherEdit && window.history?.replaceState) {
      window.history.replaceState(
        {},
        "",
        buildAdminTabUrl("teachers", currentSchool),
      );
    }
  }

  async function submitTeacher(fields: Record<string, string>) {
    setTeacherSubmitting(true);
    setModalError("");
    const url = teacherEdit
      ? routes.adminTeacherUpdate(asNumber(teacherEdit.id))
      : routes.adminTeacherCreate;
    const { ok, data } = await postForm(url, fields, csrf);
    setTeacherSubmitting(false);
    if (!ok) {
      setModalError(asString(data.message) || "Could not save teacher.");
      return;
    }
    if (Array.isArray(data.teachers)) {
      syncTeachers(data.teachers as Array<Record<string, unknown>>);
    }
    setModalOpen(false);
    clearEditUrl();
    showToast(asString(data.message) || "Teacher saved.");
  }

  async function deleteTeacher(teacherId: number, teacherName: string) {
    if (!window.confirm(`Delete ${teacherName || "this teacher"}?`)) {
      return;
    }
    const { ok, data } = await postForm(routes.adminTeacherDelete(teacherId), {}, csrf);
    if (!ok) {
      showToast(asString(data.message) || "Could not delete teacher.", "danger");
      return;
    }
    if (Array.isArray(data.teachers)) {
      syncTeachers(data.teachers as Array<Record<string, unknown>>);
    }
    showToast(asString(data.message) || "Teacher deleted.");
  }

  async function provisionRecruitmentTeacher(teacher: Teacher) {
    const teacherId = asNumber(teacher.id);
    if (!teacherId || !window.confirm(`Provision a teacher login for ${asString(teacher.full_name)}? Group assignment will remain manual.`)) return;
    try {
      const response = await fetch(`/api/v1/recruitment/active-teacher-intakes/${teacherId}/provision-account`, {
        method: "POST",
        credentials: "same-origin",
        headers: jsonCsrfHeaders(csrf),
        body: "{}",
      });
      const payload = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, payload)) {
        showToast(apiErrorMessage(payload, "Could not provision the teacher account."), "danger");
        return;
      }
      const data = apiData<Record<string, any>>(payload);
      const credentials = data.credentials || {};
      syncTeachers(teachers.map((row) => asNumber(row.id) === teacherId ? {
        ...row,
        login: asString(credentials.login),
        password: asString(credentials.temporary_password),
        account_onboarding_status: "complete",
      } : row));
      showToast(asString(data.message) || "Teacher account provisioned.");
    } catch {
      showToast("Network error. Please try again.", "danger");
    }
  }

  function closeTeacherModal() {
    setModalOpen(false);
    setModalError("");
    clearEditUrl();
  }

  const teacherTotalPages = Math.max(1, Math.ceil(teachers.length / TABLE_PAGE_SIZE));
  const effectiveTeacherPage = Math.min(teacherPage, teacherTotalPages);
  const pagedTeachers = teachers.slice(
    (effectiveTeacherPage - 1) * TABLE_PAGE_SIZE,
    effectiveTeacherPage * TABLE_PAGE_SIZE,
  );

  return (
    <div className="workspace-fit flex flex-col gap-3 lg:h-full lg:min-h-0">
      <FloatingToast toast={toast} />

      {modalOpen ? (
        <TeacherAssignmentModal
          state={state}
          isEdit={Boolean(teacherEdit)}
          submitting={teacherSubmitting}
          error={modalError}
          onSubmit={submitTeacher}
          onClose={closeTeacherModal}
        />
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-foreground/10 bg-surface p-1 shadow-card">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => selectTab(tab.key)}
                className={`rounded-md px-3 py-2 text-left text-xs font-bold transition-colors sm:px-4 ${
                  isActive
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <span className="block">{tab.label}</span>
                <span
                  className={`hidden text-[10px] font-semibold sm:block ${
                    isActive ? "text-background/70" : "text-muted-foreground"
                  }`}
                >
                  {tab.hint}
                </span>
              </button>
            );
          })}
        </div>

        {activeTab === "active" ? (
          <button
            type="button"
            onClick={() => {
              setModalError("");
              setModalOpen(true);
            }}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-sm font-bold text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            Assign Teacher
          </button>
        ) : null}
      </div>

      {activeTab === "academy" ? (
        <TeacherAcademyPanel
          state={state}
          academyTeachers={academyTeachers}
          onAcademyChange={syncAcademyTeachers}
          onTeachersChange={syncTeachers}
          showToast={showToast}
        />
      ) : null}

      {activeTab === "active" ? (
        <ChartCard
          title="Active Teachers"
          subtitle={`${teachers.length} assigned`}
          icon={<Users className="h-4 w-4 text-info" />}
          className="flex min-h-0 flex-1 flex-col"
          bodyClassName="flex min-h-0 flex-1 flex-col"
        >
          <div className="min-h-0 flex-1 overflow-x-auto rounded-lg border border-foreground/8">
            <table className="h-full w-full min-w-[920px] table-fixed text-left">
              <thead className="bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr className="border-b border-foreground/5">
                  {["Teacher", "Rank", "Progress", "Pay Rate", "Assigned Group", "Actions"].map((heading) => (
                    <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {teachers.length ? (
                  pagedTeachers.map((teacher) => (
                    <tr key={asNumber(teacher.id)} className="border-b border-foreground/5">
                      <td className="px-3 py-2.5">
                        <span className="block text-sm font-bold">{asString(teacher.full_name)}</span>
                        <span className="text-xs text-muted-foreground">ID {asNumber(teacher.id)}</span>
                        {asString(teacher.account_onboarding_status) === "pending" ? (
                          <span className="mt-1 block text-[10px] font-black uppercase tracking-wide text-amber-700">Onboarding pending</span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-bold text-emerald-700">
                          {teacherCategoryLabel(teacher.category)}
                        </span>
                        <span className="mt-1 block text-[11px] font-semibold text-muted-foreground">
                          Sem {asString(teacher.semester_stage) || "1-2"} · Score {asString(teacher.performance_score) || "7"}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full rounded-full bg-primary"
                              style={{ width: `${Math.min(100, Math.round((asNumber(teacher.supervised_lessons) / 120) * 100))}%` }}
                            />
                          </div>
                          <span className="text-[11px] font-semibold text-muted-foreground">
                            {asNumber(teacher.supervised_lessons)}/120
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-xs">{asString(teacher.pay_rate) || "-"}</td>
                      <td className="px-3 py-2.5 text-xs font-semibold">
                        {asString(teacher.assigned_group) || "-"}
                        {asString(teacher.login) ? (
                          <span className="mt-1 block text-[10px] font-normal text-muted-foreground">
                            Login {asString(teacher.login)} · Pass {asString(teacher.password) || "—"}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          {asString(teacher.account_onboarding_status) === "pending" ? (
                            <button
                              type="button"
                              onClick={() => provisionRecruitmentTeacher(teacher)}
                              className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-3 text-xs font-bold text-amber-800"
                            >
                              <KeyRound className="h-3.5 w-3.5" />
                              Provision account
                            </button>
                          ) : null}
                          <a
                            href={routes.adminTeacherEdit(asNumber(teacher.id), currentSchool)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
                            aria-label={`Edit ${asString(teacher.full_name)}`}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </a>
                          <button
                            type="button"
                            onClick={() => deleteTeacher(asNumber(teacher.id), asString(teacher.full_name))}
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10"
                            aria-label={`Delete ${asString(teacher.full_name)}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-sm text-muted-foreground">
                      No active teachers yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <PaginationControls
            page={effectiveTeacherPage}
            totalPages={teacherTotalPages}
            onPageChange={setTeacherPage}
            label={`Showing ${pagedTeachers.length} of ${teachers.length} teachers`}
          />
        </ChartCard>
      ) : null}
    </div>
  );
}
