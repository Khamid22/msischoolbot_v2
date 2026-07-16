export type RecruitmentRole =
  | "hr_manager"
  | "ceo"
  | "academic_director"
  | "head_of_department";

export type RecruitmentView = "pipeline" | "analytics" | "decisions" | "candidates" | "schedule" | "tasks" | "rejected" | "settings" | "trash" | "candidate" | "profile";

export type RecruitmentSlaState = {
  stage: string;
  status: "green" | "yellow" | "red";
  target_days: number;
  entered_at: string;
  due_at: string;
  elapsed_percentage: number;
  remaining_seconds: number;
  responsible_account_id?: number | null;
  responsible_name?: string;
};

export type RecruitmentStageHistory = {
  id: number;
  stage: string;
  entered_at: string;
  exited_at?: string | null;
  responsible_name?: string;
  comment?: string;
  transition_source: string;
  sla_target_days?: number | null;
  sla_due_at?: string | null;
};

export type RecruitmentPermissions = {
  can_edit_profile: boolean;
  can_manage_documents: boolean;
  can_manage_interviews: boolean;
  can_manage_tasks: boolean;
  can_manage_appointments: boolean;
  can_view_schedule: boolean;
  can_manage_assignments: boolean;
  can_move_stage: boolean;
  can_add_academic_evaluation: boolean;
  can_request_approval: boolean;
  can_review_approval: boolean;
  can_finalize: boolean;
  can_reject: boolean;
  can_void_evaluations: boolean;
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

export type RecruitmentAppointment = {
  id: number;
  candidate_id: number;
  candidate_name?: string;
  candidate_status?: string;
  appointment_type: "job_interview" | "demo_lesson";
  starts_at: string;
  ends_at: string;
  responsible_account_id?: number | null;
  responsible_name?: string;
  responsible_role?: string;
  appointment_format?: string;
  location_or_link?: string;
  topic?: string;
  note?: string;
  status: "scheduled" | "completed" | "cancelled" | "no_show";
  version: number;
  cancellation_reason?: string;
  completed_at?: string;
  cancelled_at?: string;
  no_show_at?: string;
  created_at?: string;
  updated_at?: string;
  subject_id?: number | null;
  subject?: string;
  is_overdue?: boolean;
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
  source_detail?: string;
  status: string;
  english_level?: string;
  motivation_expectations?: string;
  interests_hobbies?: string;
  preferred_schedule?: string;
  employment_availability?: string;
  education_background?: string;
  work_experience?: string;
  teaching_experience?: string;
  previous_workplace?: string;
  expected_salary_uzs?: number | null;
  available_start_date?: string;
  stage_changed_at?: string;
  version: number;
  final_decision?: string;
  rejection_reason?: string;
  decision_reason_detail?: string;
  decision_origin_stage?: string;
  decision_source_evaluation_type?: string;
  decision_source_evaluation_id?: number | null;
  final_decision_actor?: string;
  final_decision_at?: string;
  latest_interview_result?: string;
  latest_interview_at?: string;
  next_task?: RecruitmentTask | null;
  next_appointment?: RecruitmentAppointment | null;
  academy_teacher_id?: number | null;
  active_teacher_id?: number | null;
  permissions?: RecruitmentPermissions;
  documents?: Array<Record<string, unknown>>;
  interviews?: Array<Record<string, unknown>>;
  subject_tests?: Array<Record<string, unknown>>;
  demo_lessons?: Array<Record<string, unknown>>;
  appointments?: RecruitmentAppointment[];
  tasks?: RecruitmentTask[];
  notes?: Array<Record<string, unknown>>;
  assignments?: Array<Record<string, unknown>>;
  approvals?: Array<Record<string, unknown>>;
  decisions?: Array<Record<string, unknown>>;
  activity?: Array<Record<string, unknown>>;
  missing_document_types?: string[];
  under_review?: Record<string, unknown>;
  access_reason?: "assignment" | "approval_request";
  current_sla?: RecruitmentSlaState | null;
  stage_history?: RecruitmentStageHistory[];
  progress?: Array<{ key: string; label: string; status: "completed" | "current" | "pending" }>;
  document_progress?: {
    required_uploaded: number;
    required_total: number;
    optional_uploaded: number;
    optional_total: number;
    completion_percentage: number;
    missing_required_types: string[];
  };
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
  required_document_types: string[];
  optional_document_types: string[];
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
  is_system?: boolean;
};

export type RecruitmentSettingsData = {
  items: RecruitmentSetting[];
  sources: RecruitmentSetting[];
  rejection_reasons: RecruitmentSetting[];
  sla_rules: Array<{ stage: string; target_days: number; updated_at?: string; updated_by_name?: string }>;
  read_only: boolean;
};

export type HrAnalyticsDashboard = {
  range: { from: string; to: string; timezone: string };
  kpis: { active_candidates: number; new_this_month: number; hired_this_month: number; average_time_to_hire_days?: number | null; overall_conversion_percentage?: number | null };
  funnel: Array<{ stage: string; candidates: number; previous_stage_candidates?: number | null; conversion_percentage?: number | null }>;
  source_conversion: Array<{ source: string; candidates: number; hired: number; conversion_percentage: number }>;
  time_in_stage: Array<{ stage: string; average_days: number; sla_breaches: number; entries: number }>;
  sla: { breaches: number; bottlenecks: Array<{ stage: string; average_days: number; sla_breaches: number }> };
  overdue_actions: Array<{ id: number; candidate_id: number; candidate_name: string; title: string; due_at: string }>;
  upcoming_appointments: Array<{ id: number; candidate_id: number; candidate_name: string; appointment_type: string; starts_at: string; responsible_name?: string }>;
};

export const primaryStages = [
  "new_candidate",
  "responded",
  "job_interview",
  "test_and_demo",
  "under_review",
  "teacher_academy",
  "active_teacher",
] as const;

export const manualStages = ["new_candidate", "responded", "job_interview", "test_and_demo", "under_review"] as const;
export const alternativeStages = ["rejected", "candidate_withdrew", "trash_bin"] as const;

export const stageLabels: Record<string, string> = {
  new_candidate: "New Candidate",
  responded: "Responded",
  job_interview: "Job Interview",
  test_and_demo: "Test & Demo",
  under_review: "Under Review",
  teacher_academy: "Teacher Academy",
  active_teacher: "Active Teacher",
  rejected: "Rejected",
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
    : new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: raw.includes("T") ? "short" : undefined, timeZone: "Asia/Tashkent" }).format(parsed);
}
