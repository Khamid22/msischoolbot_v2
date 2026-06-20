type AnyRecord = Record<string, unknown>;

function asNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function asString(value: unknown): string {
  return String(value || "").trim();
}

const EXAM_ORDER = [
  "HFT1",
  "ET1",
  "HFT2",
  "ET2",
  "HFT3",
  "ET3",
  "HFT4",
];

const EXAM_SHORT: Record<string, string> = {
  "Half-term Test 1": "HFT1",
  "End-of-term Test 1": "ET1",
  "Half-term Test 2": "HFT2",
  "End-of-term Test 2": "ET2",
  "Half-term Test 3": "HFT3",
  "End-of-term Test 3": "ET3",
  "Half-term Test 4": "HFT4",
};

function shortExamName(label: string): string {
  const normalized = label.replace(/\s+/g, " ").trim();
  const compact = normalized.replace(/[\s_-]+/g, "").toUpperCase();
  if (/^HFT\d+$/.test(compact) || /^ET\d+$/.test(compact)) return compact;
  return EXAM_SHORT[normalized] ?? normalized;
}

export function buildExamChartData(payload: AnyRecord) {
  const rawExamResults = Array.isArray(payload.examResults) ? payload.examResults : [];
  const examNames: string[] = [];
  const attemptToScores = new Map<string, Record<string, number>>();

  for (const item of rawExamResults) {
    if (!item || typeof item !== "object") continue;
    const rawExamName = asString((item as AnyRecord).examName || (item as AnyRecord).label) || "Exam";
    const examName = shortExamName(rawExamName);
    const attempt = asString((item as AnyRecord).attempt) || "Attempt";
    const score = asNumber((item as AnyRecord).score, Number.NaN);
    if (!Number.isFinite(score)) continue;
    if (!examNames.includes(examName)) examNames.push(examName);
    if (!attemptToScores.has(attempt)) attemptToScores.set(attempt, {});
    const scoreMap = attemptToScores.get(attempt)!;
    scoreMap[examName] = Math.max(scoreMap[examName] ?? Number.NEGATIVE_INFINITY, score);
  }

  // Sort exams in canonical timeline order
  examNames.sort((a, b) => {
    const ai = EXAM_ORDER.indexOf(shortExamName(a));
    const bi = EXAM_ORDER.indexOf(shortExamName(b));
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });

  return examNames.map((examName) => {
    const scores: number[] = [];
    const row: Record<string, string | number | null> = {
      examName,
      shortName: examName,
    };
    for (const [attempt, scoreMap] of attemptToScores.entries()) {
      const score = Object.prototype.hasOwnProperty.call(scoreMap, examName)
        ? scoreMap[examName]
        : null;
      row[attempt] = score;
      if (typeof score === "number" && Number.isFinite(score)) {
        scores.push(score);
      }
    }
    row.bestScore = scores.length ? Math.max(...scores) : null;
    return row;
  });
}

export function buildHomeworkChartData(payload: AnyRecord) {
  const rawHomeworkGrades = Array.isArray(payload.homeworkGrades) ? payload.homeworkGrades : [];

  return rawHomeworkGrades
    .map((item, index) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const score = asNumber((item as AnyRecord).score, Number.NaN);
      if (!Number.isFinite(score) || score < 1 || score > 9) {
        return null;
      }
      const lessonCandidates = [
        asString((item as AnyRecord).lessonLabel),
        asString((item as AnyRecord).lessonNumber),
        asString((item as AnyRecord).lesson),
        asString((item as AnyRecord).label),
      ];
      let label = "";
      for (const candidate of lessonCandidates) {
        if (!candidate) {
          continue;
        }
        const lessonMatch = candidate.match(/(?:lesson\s*)?(\d{1,3})/i);
        if (lessonMatch && lessonMatch[1]) {
          label = `L${lessonMatch[1]}`;
          break;
        }
        if (candidate.length <= 8) {
          label = candidate;
          break;
        }
      }
      return {
        label: label || `L${index + 1}`,
        score,
      };
    })
    .filter(Boolean) as Array<{ label: string; score: number }>;
}

export function buildAttendanceDonutData(payload: AnyRecord) {
  const attendanceRecord =
    payload.attendanceRecord && typeof payload.attendanceRecord === "object"
      ? (payload.attendanceRecord as AnyRecord)
      : {};

  return [
    { name: "Present", value: asNumber(attendanceRecord.presentCount) },
    { name: "Absent", value: asNumber(attendanceRecord.absentCount) },
    { name: "Justified", value: asNumber(attendanceRecord.justifiedAbsentCount) },
  ].filter((item) => item.value > 0);
}

export function buildStudentDisplayName(student: AnyRecord) {
  const surname = asString(student.surname);
  const name = asString(student.name);
  const fullName = asString(student.fullName);
  if (surname && name) {
    return `${surname} ${name}`.trim();
  }
  return fullName;
}
