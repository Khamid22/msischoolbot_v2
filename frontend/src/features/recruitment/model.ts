export type RecruitmentRole =
  | "hr_manager"
  | "ceo"
  | "academic_director"
  | "head_of_department";

export type RecruitmentView = "pipeline" | "decisions" | "candidates" | "tasks" | "settings" | "candidate" | "profile";

export type RecruitmentPermissions = {
  can_edit_profile: boolean;
  can_manage_documents: boolean;
  can_manage_interviews: boolean;
  can_manage_tasks: boolean;
  can_manage_assignments: boolean;
  can_move_stage: boolean;
  can_add_academic_evaluation: boolean;
  can_request_approval: boolean;
  can_review_approval: boolean;
  can_finalize: boolean;
  can_reject: boolean;
  can_add_note: boolean;
};

export type RecruitmentTask = {
  id: number;
  candidate_id: number;
  candidate_name?: string;
  title: string;
  due_at?: string;
  status: string;
  effective_status: string;
  note?: string;
  responsible_account_id?: number | null;
  responsible_name?: string;
};

export type RecruitmentCandidate = {
  id: number;
  full_name: string;
  phone?: string;
  telegram_username?: string;
  subject_id?: number | null;
  subject?: string;
  applied_position?: string;
  application_date?: string;
  age?: number | null;
  address?: string;
  source?: string;
  status: string;
  english_level?: string;
  motivation_expectations?: string;
  interests_hobbies?: string;
  preferred_schedule?: string;
  employment_availability?: string;
  work_experience?: string;
  teaching_experience?: string;
  previous_workplace?: string;
  expected_salary_uzs?: number | null;
  available_start_date?: string;
  stage_changed_at?: string;
  version: number;
  final_decision?: string;
  rejection_reason?: string;
  next_task?: RecruitmentTask | null;
  academy_teacher_id?: number | null;
  active_teacher_id?: number | null;
  permissions?: RecruitmentPermissions;
  documents?: Array<Record<string, unknown>>;
  interviews?: Array<Record<string, unknown>>;
  subject_tests?: Array<Record<string, unknown>>;
  demo_lessons?: Array<Record<string, unknown>>;
  tasks?: RecruitmentTask[];
  notes?: Array<Record<string, unknown>>;
  assignments?: Array<Record<string, unknown>>;
  approvals?: Array<Record<string, unknown>>;
  decisions?: Array<Record<string, unknown>>;
  activity?: Array<Record<string, unknown>>;
  missing_document_types?: string[];
  under_review?: Record<string, unknown>;
  access_reason?: "assignment" | "approval_request";
  actionable_approval?: {
    id: number;
    requested_outcome: string;
    status: string;
    request_note?: string;
    created_at?: string;
  } | null;
};

export type RecruitmentOptions = {
  stages: string[];
  sources: string[];
  document_types: string[];
  rejection_reasons: string[];
  rejection_reason_options: Array<{ value: string; label: string }>;
  subjects: Array<{ id: number; name: string }>;
  staff: Array<{ id: number; role: string; name: string; login: string }>;
  document_upload_enabled: boolean;
};

export type RecruitmentSetting = {
  id: number;
  category: "source" | "rejection_reason";
  value: string;
  label: string;
  is_active: boolean;
  sort_order: number;
};

export type RecruitmentSettingsData = {
  items: RecruitmentSetting[];
  sources: RecruitmentSetting[];
  rejection_reasons: RecruitmentSetting[];
};

export const primaryStages = [
  "new_candidate",
  "job_interview",
  "test_and_demo",
  "under_review",
  "teacher_academy",
  "active_teacher",
] as const;

export const manualStages = ["new_candidate", "job_interview", "test_and_demo", "under_review"] as const;
export const alternativeStages = ["rejected", "on_hold", "candidate_withdrew", "trash_bin"] as const;

export const stageLabels: Record<string, string> = {
  new_candidate: "New Candidate",
  job_interview: "Job Interview",
  test_and_demo: "Test & Demo",
  under_review: "Under Review",
  teacher_academy: "Teacher Academy",
  active_teacher: "Active Teacher",
  rejected: "Rejected",
  on_hold: "On Hold",
  candidate_withdrew: "Candidate Withdrew",
  trash_bin: "Trash Bin",
};

export function humanize(value: unknown) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter: string) => letter.toUpperCase());
}

export function dateLabel(value: unknown) {
  const raw = String(value || "");
  if (!raw) return "Not set";
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime())
    ? raw
    : new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: raw.includes("T") ? "short" : undefined }).format(parsed);
}
