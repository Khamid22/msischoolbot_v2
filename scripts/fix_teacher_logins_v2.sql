-- One-time cleanup after the teacher<->staff link fix.
--
-- Codex provisioned teacher login rows in msi_v2.msi_staff keyed by display_name
-- (before msi_staff.teacher_id existed), and the migration left a duplicate
-- group_teachers row. This:
--   1. removes exact-duplicate group_teachers rows,
--   2. deletes the orphan teacher login rows (role='teacher', teacher_id IS NULL).
--
-- After running this, the next admin "Teachers" page load re-provisions clean
-- teacher logins via backfill_teacher_auth, each stamped with its teacher_id
-- (so login -> teacher profile works). Default password == login (TCHNNN).
--
-- Review, then apply with:
--   psql "$DATABASE_URL" -f scripts/fix_teacher_logins_v2.sql

BEGIN;

DELETE FROM msi_v2.group_teachers gt
WHERE ctid <> (
    SELECT min(ctid)
    FROM msi_v2.group_teachers x
    WHERE x.group_id = gt.group_id
      AND x.teacher_id = gt.teacher_id
      AND x.role = gt.role
);

DELETE FROM msi_v2.msi_staff
WHERE lower(role) = 'teacher'
  AND teacher_id IS NULL;

COMMIT;
