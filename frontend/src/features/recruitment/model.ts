export type RecruitmentRole =
  | "hr_manager"
  | "ceo"
  | "academic_director"
  | "head_of_department";

export type RecruitmentView = "pipeline" | "teachers" | "analytics" | "decisions" | "candidates" | "schedule" | "tasks" | "rejected" | "settings" | "trash" | "candidate" | "profile";

export type RecruitmentOption = {
  id: number;
  category: string;
  value: string;
  label: string;
  parent_id?: number | null;
  is_active?: boolean;
  sort_order?: number;
  is_legacy?: boolean;
};

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
  can_add_subject_test: boolean;
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
  evaluated_by_name?: string;
  appointment_format?: string;
  location_or_link?: string;
  topic?: string;
  note?: string;
  status: "scheduled" | "in_progress" | "completed" | "cancelled" | "no_show";
  version: number;
  cancellation_reason?: string;
  completed_at?: string;
  cancelled_at?: string;
  no_show_at?: string;
  started_at?: string;
  started_by_account_id?: number | null;
  started_by_name?: string;
  start_available_at?: string | null;
  overdue_at?: string | null;
  can_start?: boolean;
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
  email?: string;
  telegram_username?: string;
  linked_account_id?: number | null;
  is_application_received?: boolean;
  profile_origin?: "application" | "academy_direct";
  exact_identity?: {
    has_phone: boolean;
    has_email: boolean;
    has_telegram: boolean;
    has_linked_account: boolean;
  };
  subject_id?: number | null;
  subject?: string;
  position_option_id?: number | null;
  applied_position?: string;
  application_date?: string;
  age?: number | null;
  address?: string;
  source?: string;
  source_option_id?: number | null;
  subsource?: string;
  subsource_option_id?: number | null;
  source_detail?: string;
  status: string;
  english_level?: string;
  english_level_option_id?: number | null;
  motivation_expectations?: string;
  interests_hobbies?: string;
  preferred_schedule?: string;
  schedule_option_id?: number | null;
  employment_availability?: string;
  availability_option_id?: number | null;
  education_background?: string;
  work_experience?: string;
  teaching_experience?: string;
  teaching_experience_option_id?: number | null;
  previous_workplace?: string;
  expected_salary_uzs?: number | null;
  expected_salary?: string;
  expected_salary_option_id?: number | null;
  available_start_date?: string;
  stage_changed_at?: string;
  version: number;
  final_decision?: string;
  rejection_reason?: string;
  decision_reason_detail?: string;
  restore_stage?: string;
  decision_origin_stage?: string;
  decision_source_evaluation_type?: string;
  decision_source_evaluation_id?: number | null;
  final_decision_actor?: string;
  final_decision_at?: string;
  latest_interview_result?: string;
  latest_interview_at?: string;
  latest_subject_test_result?: string;
  latest_subject_test_at?: string;
  latest_demo_result?: string;
  latest_demo_at?: string;
  evaluation_states?: {
    interview: string;
    demo: string;
    subject_test: "passed" | "not_passed" | "missing";
  };
  next_task?: RecruitmentTask | null;
  next_appointment?: RecruitmentAppointment | null;
  academy_teacher_id?: number | null;
  academy?: {
    id: number;
    status?: string;
    start_date?: string | null;
    onboarding_status?: string;
    subject_id?: number | null;
    subject?: string;
    subject_program_id?: number | null;
    curriculum?: string;
    staff_id?: number | null;
    login?: string;
    lesson_count?: number;
    assessment_count?: number;
    lessons?: Array<Record<string, unknown>>;
    assessments?: Array<Record<string, unknown>>;
    account_state?: "connected" | "onboarding_pending";
  } | null;
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
  sources: RecruitmentOption[];
  subsources: RecruitmentOption[];
  option_categories: Record<string, RecruitmentOption[]>;
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
  category: "source" | "subsource" | "rejection_reason" | "position" | "english_level" | "schedule" | "availability" | "expected_salary" | "teaching_experience";
  value: string;
  label: string;
  parent_id?: number | null;
  is_active: boolean;
  sort_order: number;
  is_system?: boolean;
};

export type RecruitmentSettingsData = {
  items: RecruitmentSetting[];
  sources: RecruitmentSetting[];
  subsources: RecruitmentSetting[];
  rejection_reasons: RecruitmentSetting[];
  positions: RecruitmentSetting[];
  english_levels: RecruitmentSetting[];
  schedules: RecruitmentSetting[];
  availabilitys: RecruitmentSetting[];
  expected_salarys: RecruitmentSetting[];
  teaching_experiences: RecruitmentSetting[];
  sla_rules: Array<{ stage: string; target_days: number; updated_at?: string; updated_by_name?: string }>;
  read_only: boolean;
};

export type HrAnalyticsDashboard = {
  role: "hr_manager" | "ceo";
  as_of: string;
  range: {
    from: string;
    to: string;
    timezone: string;
    period: "today" | "week" | "month" | "quarter" | "year" | "custom";
    comparison_from: string;
    comparison_to: string;
    bucket: "day" | "week" | "month";
  };
  filters: {
    source: string;
    subsource: string;
    position: string;
    subject_id?: number | null;
    responsible_account_id?: number | null;
  };
  summary_cards: Record<"applications" | "shortlisted" | "hired" | "rejected", {
    value: number;
    total: number;
    previous: number;
    delta_percentage?: number | null;
  }>;
  secondary_kpis: {
    academy_accepted: number;
    academy_total: number;
    withdrawn: number;
    withdrawn_total: number;
    active_candidates: number;
    average_time_to_hire_days?: number | null;
    overall_conversion_percentage?: number | null;
    sla_breaches: number;
    sla_overdue_now: number;
    cohort_sla_breaches: number;
  };
  kpis: { active_candidates: number; new_this_month: number; hired_this_month: number; average_time_to_hire_days?: number | null; overall_conversion_percentage?: number | null };
  funnel: Array<{ stage: string; candidates: number; previous_stage_candidates?: number | null; conversion_percentage?: number | null }>;
  journey: Array<{ stage: string; candidates: number; previous_stage_candidates?: number | null; conversion_percentage?: number | null }>;
  outcomes: Array<{ outcome: string; candidates: number }>;
  activity_trend: Array<{ bucket: string; applications: number; shortlisted: number; hired: number; rejected: number }>;
  position_distribution: Array<{ position: string; candidates: number }>;
  source_distribution: Array<{ source: string; candidates: number; shortlisted: number; hired: number; percentage: number }>;
  source_quality: Array<{ source: string; subsource: string; candidates: number; shortlisted: number; hired: number; conversion_percentage: number }>;
  source_conversion: Array<{ source: string; candidates: number; hired: number; conversion_percentage: number }>;
  time_in_stage: Array<{ stage: string; average_days: number; sla_target_days?: number | null; sla_breaches: number; entries: number }>;
  sla: { breaches: number; overdue_now: number; bottlenecks: Array<{ stage: string; average_days: number; sla_breaches: number }> };
  overdue_actions: Array<{ id: number; candidate_id: number; candidate_name: string; title: string; due_at: string }>;
  upcoming_appointments: Array<{ id: number; candidate_id: number; candidate_name: string; appointment_type: string; starts_at: string; responsible_name?: string }>;
  recent_candidates: Array<{
    id: number;
    full_name: string;
    position: string;
    source: string;
    subsource?: string;
    application_date?: string;
    status: string;
    next_action?: string;
  }>;
  recent_activity: Array<{
    id: number;
    event_type: string;
    detail_json?: Record<string, unknown>;
    created_at: string;
    candidate_id: number;
    candidate_name: string;
    actor: string;
  }>;
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

export const boardStages = ["new_candidate", "responded", "job_interview", "test_and_demo", "under_review"] as const;
export const manualStages = boardStages;
export const alternativeStages = ["rejected", "candidate_withdrew", "trash_bin"] as const;

export const stageLabels: Record<string, string> = {
  new_candidate: "Application Received",
  responded: "Interview Schedule",
  job_interview: "Job Interview",
  test_and_demo: "Test & Demo",
  under_review: "Final Decision",
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
    : new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: /[T ]\d{2}:\d{2}/.test(raw) ? "short" : undefined, timeZone: "Asia/Tashkent" }).format(parsed);
}

export function dateTimeLabel(value: unknown) {
  const parsed = new Date(String(value || ""));
  return Number.isNaN(parsed.getTime())
    ? String(value || "Not set")
    : new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Tashkent" }).format(parsed);
}
