import { useEffect, useState } from "react";
import { CenteredPage, FormAlert } from "@/components/PortalCard";

interface StudentOption {
  id: number | string;
  fullName: string;
}

interface HomePageProps {
  subjects?: string[];
  groupsBySubject?: Record<string, string[]>;
  studentsBySubjectGroup?: Record<string, Record<string, StudentOption[]>>;
  formData?: {
    subject?: string;
    group?: string;
    student_id?: string;
  };
  error?: string;
  authLogin?: string;
  csrfToken?: string;
  logoutUrl?: string;
  searchUrl?: string;
}

export default function HomePage(props: HomePageProps) {
  const [subject, setSubject] = useState(props.formData?.subject || "");
  const [group, setGroup] = useState(props.formData?.group || "");
  const [studentId, setStudentId] = useState(props.formData?.student_id || "");

  const subjects = Array.isArray(props.subjects) ? props.subjects : [];
  const groups = subject ? props.groupsBySubject?.[subject] || [] : [];
  const students = group ? props.studentsBySubjectGroup?.[subject]?.[group] || [] : [];

  useEffect(() => {
    if (group && !groups.includes(group)) {
      setGroup("");
      setStudentId("");
    }
  }, [group, groups]);

  useEffect(() => {
    if (studentId && !students.some((student) => String(student.id) === String(studentId))) {
      setStudentId("");
    }
  }, [studentId, students]);

  return (
    <CenteredPage title="MSI School Portal" subtitle="Select stream, group, and student">
      {props.authLogin ? (
        <div className="mb-4 flex justify-end">
          <form action={props.logoutUrl || "/logout"} method="post">
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <button type="submit" className="rounded-lg px-3 py-1.5 text-xs font-bold hover:bg-foreground/5">
              Logout
            </button>
          </form>
        </div>
      ) : null}

      {props.error ? <FormAlert kind="error">{props.error}</FormAlert> : null}

      <form action={props.searchUrl || "/search"} method="post" className="space-y-4">
        <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Subject
          </span>
          <select
            name="subject"
            value={subject}
            onChange={(event) => {
              setSubject(event.target.value);
              setGroup("");
              setStudentId("");
            }}
            required
            className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-3 text-sm font-medium outline-none transition-colors focus:border-foreground/30"
          >
            <option value="" disabled>
              Select subject stream
            </option>
            {subjects.map((subjectName) => (
              <option key={subjectName} value={subjectName}>
                {subjectName === "English" ? "General English" : subjectName}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Group
          </span>
          <select
            name="group"
            value={group}
            onChange={(event) => {
              setGroup(event.target.value);
              setStudentId("");
            }}
            disabled={!subject}
            required
            className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-3 text-sm font-medium outline-none transition-colors focus:border-foreground/30 disabled:opacity-50"
          >
            <option value="" disabled>
              Select morning or afternoon group
            </option>
            {groups.map((groupName) => (
              <option key={groupName} value={groupName}>
                {groupName}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Student
          </span>
          <select
            name="student_id"
            value={studentId}
            onChange={(event) => setStudentId(event.target.value)}
            disabled={!group}
            required
            className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-3 text-sm font-medium outline-none transition-colors focus:border-foreground/30 disabled:opacity-50"
          >
            <option value="" disabled>
              Select student
            </option>
            {students.map((student) => (
              <option key={student.id} value={student.id}>
                {student.fullName}
              </option>
            ))}
          </select>
        </label>

        <button
          type="submit"
          disabled={!studentId}
          className="w-full rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-primary-foreground shadow-neo transition-all active:translate-x-[1px] active:translate-y-[1px] active:shadow-none disabled:opacity-50"
        >
          Open Dashboard
        </button>
      </form>
    </CenteredPage>
  );
}
