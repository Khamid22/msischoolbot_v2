import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const teacherHome = readFileSync(new URL("./pages/Home.tsx", import.meta.url), "utf8");
const teacherCurriculum = readFileSync(
  new URL("../../features/academics/subject-curriculum/TeacherSubjectCurriculum.tsx", import.meta.url),
  "utf8",
);
const directorCurriculum = readFileSync(
  new URL("../../features/academics/subject-curriculum/DirectorSubjectCurriculum.tsx", import.meta.url),
  "utf8",
);
const curriculumTable = readFileSync(
  new URL("../../features/academics/subject-curriculum/CurriculumTable.tsx", import.meta.url),
  "utf8",
);
const fundamentalsGuidance = readFileSync(
  new URL(
    "../../features/academics/subject-curriculum/FundamentalsGuidance.tsx",
    import.meta.url,
  ),
  "utf8",
);
const fundamentalsEditor = readFileSync(
  new URL(
    "../../features/academics/subject-curriculum/FundamentalsItemEditor.tsx",
    import.meta.url,
  ),
  "utf8",
);
const fundamentalsIdentity = readFileSync(
  new URL(
    "../../features/academics/subject-curriculum/FundamentalsLessonIdentity.tsx",
    import.meta.url,
  ),
  "utf8",
);
const guidanceBlockEditor = readFileSync(
  new URL(
    "../../features/academics/subject-curriculum/GuidanceBlockEditor.tsx",
    import.meta.url,
  ),
  "utf8",
);
const mediaRenderer = readFileSync(
  new URL(
    "../../features/academics/subject-curriculum/CurriculumMediaBlock.tsx",
    import.meta.url,
  ),
  "utf8",
);
const presentationCarousel = readFileSync(
  new URL(
    "../../features/academics/subject-curriculum/PresentationCarousel.tsx",
    import.meta.url,
  ),
  "utf8",
);

test("Teacher Academy uses its own responsive cabinet instead of an Admin preview", () => {
  assert.doesNotMatch(teacherHome, /AcademyTeacherPreview/);
  assert.doesNotMatch(teacherHome, /Default password|password equals login/i);
  assert.match(teacherHome, /Teacher Academy navigation/);
  assert.match(teacherHome, /fixed inset-x-0 bottom-0/);
  assert.match(teacherHome, /sticky top-0 hidden h-dvh w-\[var\(--workspace-sidebar-width\)\]/);
  assert.match(teacherHome, /overflow-x-hidden/);
  assert.match(teacherHome, /var\(--app-bottom-inset\)/);
});

test("Teacher Academy restores its operational tabs and assessment details", () => {
  for (const tab of ["overview", "lessons", "timetable", "updates", "profile"]) {
    assert.match(teacherHome, new RegExp(`key: "${tab}"`));
  }
  assert.match(teacherHome, /Lessons & reports/);
  assert.match(teacherHome, /Assessment report/);
  assert.match(teacherHome, /Lesson schedule/);
  assert.match(teacherHome, /Recent activity/);
  assert.match(teacherHome, /Change password/);
});

test("Teacher Academy navigation and account actions keep accessible touch targets", () => {
  assert.match(teacherHome, /min-h-12/);
  assert.match(teacherHome, /min-h-11/);
  assert.match(teacherHome, /aria-current/);
  assert.match(teacherHome, /focus-visible:ring-2/);
  assert.match(teacherHome, /motion-reduce:transition-none/);
});

test("active teachers receive assigned-subject curriculum without an Academy dependency", () => {
  assert.match(teacherHome, /teacherProfile/);
  assert.match(teacherHome, /subjectCurriculumCatalog/);
  assert.match(teacherHome, /key: "curriculum"/);
  assert.match(teacherHome, /key !== "updates"/);
  assert.match(teacherCurriculum, /No subject curriculum assigned/);
  assert.match(teacherCurriculum, /\/api\/v1\/teacher\/subject-curricula/);
  assert.doesNotMatch(teacherCurriculum, /create_fundamentals|update_fundamentals/i);
});

test("ESL curriculum uses Fundamentals first and keeps Primary read-only", () => {
  assert.match(teacherCurriculum, /defaultVariant/);
  assert.match(directorCurriculum, /defaultVariant/);
  assert.match(directorCurriculum, /Add lesson/);
  assert.match(directorCurriculum, /The canonical Primary Curriculum is read-only/);
  assert.match(directorCurriculum, /expectedCurriculumVersion/);
  assert.match(directorCurriculum, /Archive/);
  assert.match(directorCurriculum, /onRestore/);
});

test("curriculum lesson content renders typed safe blocks and private materials", () => {
  assert.match(curriculumTable, /blockType === "heading"/);
  assert.match(curriculumTable, /blockType === "bullets"/);
  assert.match(curriculumTable, /downloadUrl/);
  assert.doesNotMatch(curriculumTable, /dangerouslySetInnerHTML/);
});

test("Fundamentals lesson details use the teacher-guidance interaction design", () => {
  assert.match(curriculumTable, /useGuidanceLayout/);
  assert.match(teacherCurriculum, /curriculumKey === "fundamentals"/);
  assert.match(directorCurriculum, /useGuidanceLayout=\{isEditable\}/);
  assert.match(fundamentalsGuidance, /Teacher Guidance/);
  assert.match(fundamentalsGuidance, /Before You Teach/);
  assert.match(fundamentalsGuidance, /Planning/);
  assert.match(fundamentalsGuidance, /Teaching/);
  assert.match(fundamentalsGuidance, /Expand all/);
  assert.match(fundamentalsGuidance, /Collapse all/);
  assert.match(fundamentalsGuidance, /role="switch"/);
  assert.match(fundamentalsGuidance, /aria-expanded/);
  assert.doesNotMatch(fundamentalsGuidance, /dangerouslySetInnerHTML/);
});

test("Fundamentals is a lesson constructor rather than a curriculum-row form", () => {
  assert.match(fundamentalsIdentity, /Lesson identity/);
  assert.match(fundamentalsEditor, /Before You Teach/);
  assert.match(fundamentalsEditor, /Lesson flow/);
  assert.match(fundamentalsEditor, /Planning content/);
  assert.match(fundamentalsEditor, /Teaching content/);
  assert.match(fundamentalsEditor, /Teacher Preview/);
  assert.match(fundamentalsEditor, /beforeunload/);
  for (const blockLabel of [
    "Heading",
    "Text",
    "Bullet list",
    "Checklist",
    "Teaching note",
    "Quote",
    "Image",
    "Video",
    "Audio",
    "File",
    "Slides",
    "Embed",
    "Link",
  ]) {
    assert.match(guidanceBlockEditor, new RegExp(blockLabel));
  }
  assert.match(guidanceBlockEditor, /Replace file/);
  assert.match(guidanceBlockEditor, /role="progressbar"/);
  assert.match(mediaRenderer, /sandbox=/);
  assert.match(mediaRenderer, /allowFullScreen/);
  assert.match(presentationCarousel, /Previous slide/);
  assert.match(presentationCarousel, /Original PowerPoint/);
  assert.doesNotMatch(
    fundamentalsIdentity,
    /Student book|Book pages|\bTerm\b|\bWeek\b|Specification|\bExam\b/i,
  );
  assert.doesNotMatch(fundamentalsGuidance, /termLabel|weekLabel|bookPages|specificationPoints/);
});
