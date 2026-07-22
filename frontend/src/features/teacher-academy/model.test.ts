import assert from "node:assert/strict";
import test from "node:test";

import {
  academyRosterPageSize,
  academyStatusPresentation,
  academyTeacherProgress,
  academyViewFromSearch,
  calculateTeacherAcademyStats,
  filterAndSortAcademyTeachers,
  type AcademyTeacher,
} from "./model.ts";

const teachers: AcademyTeacher[] = [
  {
    id: 1,
    full_name: "Shakhzod Karimov",
    subject_id: 10,
    subject: "Mathematics",
    academy_status: "in_training",
    academy_start_date: "2026-07-10",
    assignments: [{ id: 1 }, { id: 2 }, { id: 3 }],
    assessments: [
      { id: 1, weighted_overall_score: 8 },
      { id: 2, weighted_overall_score: 6 },
    ],
    progress: {
      assigned_count: 3,
      target_lessons: 3,
      assessed_count: 2,
      passed_count: 2,
      average_score: 7,
    },
  },
  {
    id: 2,
    full_name: "Niaz Ahmed",
    subject_id: 20,
    subject: "English",
    academy_status: "ready_for_active_teacher",
    academy_start_date: "2026-07-12",
    assignments: [{ id: 4 }],
    assessments: [{ id: 3, weighted_overall_score: 9 }],
    progress: {
      assigned_count: 1,
      target_lessons: 1,
      assessed_count: 1,
      passed_count: 1,
      average_score: 9,
    },
  },
];

test("calculates dashboard totals from real assignments and assessment weighting", () => {
  const stats = calculateTeacherAcademyStats(teachers);
  assert.equal(stats.total, 2);
  assert.equal(stats.ready, 1);
  assert.equal(stats.appointedLessons, 4);
  assert.equal(stats.weightedAverage?.toFixed(2), "7.67");
});

test("includes assessed zero scores instead of treating them as missing", () => {
  const stats = calculateTeacherAcademyStats([
    {
      id: 3,
      assessments: [
        { id: 4, weighted_overall_score: 0 },
        { id: 5, weighted_overall_score: 8 },
      ],
    },
  ]);
  assert.equal(stats.weightedAverage, 4);
});

test("uses each academy teacher's real lesson target", () => {
  const progress = academyTeacherProgress(teachers[0]);
  assert.equal(progress.passed, 2);
  assert.equal(progress.target, 3);
});

test("provides readable status labels and non-color semantics", () => {
  assert.deepEqual(academyStatusPresentation("needs_improvement"), {
    label: "Needs improvement",
    tone: "warning",
  });
  assert.equal(academyStatusPresentation("ready_for_active_teacher").tone, "success");
});

test("filters the scoped HOD roster and sorts by the selected criterion", () => {
  const filtered = filterAndSortAcademyTeachers(teachers, {
    search: "niaz",
    subjectId: "20",
    sort: "date",
  });
  assert.deepEqual(filtered.map((teacher) => teacher.id), [2]);

  const byLessons = filterAndSortAcademyTeachers(teachers, {
    search: "",
    subjectId: "",
    sort: "lessons",
  });
  assert.deepEqual(byLessons.map((teacher) => teacher.id), [1, 2]);
});

test("selects responsive page sizes at the approved breakpoints", () => {
  assert.equal(academyRosterPageSize(390), 5);
  assert.equal(academyRosterPageSize(768), 6);
  assert.equal(academyRosterPageSize(1279), 6);
  assert.equal(academyRosterPageSize(1280), 12);
});

test("rejects unavailable and invalid URL views for HOD", () => {
  assert.equal(academyViewFromSearch("?academy_view=active_teachers", "head_of_department"), "teacher_academy");
  assert.equal(academyViewFromSearch("?academy_view=appointed_lessons", "head_of_department"), "appointed_lessons");
  assert.equal(academyViewFromSearch("?academy_view=active_teachers", "academic_director"), "active_teachers");
  assert.equal(academyViewFromSearch("?academy_view=unknown", "academic_director"), "teacher_academy");
});
