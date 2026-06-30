-- MSI School v2 cutover cleanup.
--
-- DO NOT RUN until all code reads from msi_v2 and every workspace is verified.
-- Before production use, take a Railway snapshot or pg_dump backup.
--
-- This removes old public tables that were replaced by msi_v2.

BEGIN;

DROP TABLE IF EXISTS
  public.academic_attendance_records,
  public.academic_coin_events,
  public.academic_exam_results,
  public.academic_homework_scores,
  public.academic_lesson_sessions,
  public.academic_schedules,
  public.academic_lessons,
  public.lesson_catalog,
  public.academic_enrollments,
  public.academic_groups,
  public.academic_subjects,
  public.academic_curriculum_items,
  public.academic_curriculum_programs,
  public.academic_schools,
  public.parent_complaint_messages,
  public.parent_complaints,
  public.parent_children,
  public.parent_student_links,
  public.parents,
  public.student_payments,
  public.student_auth,
  public.students_sheet_map,
  public.subject_summaries,
  public.students,
  public.teacher_auth,
  public.teacher_candidate_events,
  public.teacher_candidates,
  public.teachers,
  public.resource_comments,
  public.resources,
  public.resource_types,
  public.announcements,
  public.chat_blocked_users,
  public.chat_messages,
  public.office_hour_bookings,
  public.office_hour_availability,
  public.bot_users,
  public.admins,
  public.app_meta
CASCADE;

COMMIT;
