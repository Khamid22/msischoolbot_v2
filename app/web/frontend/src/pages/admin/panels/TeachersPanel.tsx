import { GraduationCap, Pencil, Trash2, Users } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { routes } from "@/lib/routes";
import { asNumber, asString, submitConfirm } from "../shared";

export default function TeachersPanel({ state }: { state: any }) {
  const {
    teacherEdit,
    props,
    teacherMode,
    setTeacherMode,
    currentSchool,
    teacherSchool,
    setTeacherSchool,
    availableSubjectSchools,
    filteredTeacherOptions,
    filteredGroupOptions,
    teachers,
  } = state;

  return (
    <div className="grid gap-4 xl:grid-cols-[380px_minmax(0,1fr)]">
      <ChartCard title="Teacher Assignment" icon={<GraduationCap className="h-4 w-4 text-info" />}>
        <form
          action={
            teacherEdit
              ? routes.adminTeacherUpdate(asNumber(teacherEdit.id))
              : routes.adminTeacherCreate
          }
          method="post"
          className="space-y-3"
        >
          <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
          <input type="hidden" name="teacher_mode" value={teacherMode} />

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setTeacherMode("select")}
              className={`rounded-lg px-3 py-1.5 text-[11px] font-bold ${
                teacherMode === "select"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              Select
            </button>
            <button
              type="button"
              onClick={() => setTeacherMode("add")}
              className={`rounded-lg px-3 py-1.5 text-[11px] font-bold ${
                teacherMode === "add"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              Add New
            </button>
            {teacherEdit ? (
              <a
                href={`/?panel=teachers&school=${encodeURIComponent(currentSchool)}`}
                className="rounded-lg bg-muted px-3 py-1.5 text-[11px] font-bold text-muted-foreground"
              >
                Cancel Edit
              </a>
            ) : null}
          </div>

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Select School
            </span>
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
              {availableSubjectSchools.map((option: { code: string; label: string }) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {teacherMode === "select" ? (
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Select Teacher
              </span>
              <select
                name="teacher_selected_name"
                defaultValue={teacherEdit ? asString(teacherEdit.full_name) : ""}
                required
                className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select from existing teachers
                </option>
                {filteredTeacherOptions.map((option: { name: string }) => (
                  <option key={option.name} value={option.name}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Teacher Full Name
                </span>
                <input
                  type="text"
                  name="teacher_full_name"
                  defaultValue={teacherEdit ? asString(teacherEdit.full_name) : ""}
                  className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Pay Rate
                </span>
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
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Select Group
            </span>
            <select
              name="teacher_assigned_group"
              defaultValue={teacherEdit ? asString(teacherEdit.assigned_group) : ""}
              required
              className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
            >
              <option value="" disabled>
                Select group
              </option>
              {filteredGroupOptions.map((option: { name: string }) => (
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
                teachers.map((teacher: Record<string, unknown>) => (
                  <tr key={asNumber(teacher.id)} className="border-b border-foreground/5">
                    <td className="px-3 py-2.5 text-xs">{asNumber(teacher.id)}</td>
                    <td className="px-3 py-2.5 text-sm font-medium">{asString(teacher.full_name)}</td>
                    <td className="px-3 py-2.5 text-xs">{asString(teacher.pay_rate)}</td>
                    <td className="px-3 py-2.5 text-xs">{asString(teacher.assigned_group)}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <a
                          href={routes.adminTeacherEdit(asNumber(teacher.id), currentSchool)}
                          className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </a>
                        <form
                          action={routes.adminTeacherDelete(asNumber(teacher.id))}
                          method="post"
                          onSubmit={(event) => submitConfirm(event, "Delete this teacher?")}
                        >
                          <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                          <button
                            type="submit"
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10"
                          >
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
  );
}
