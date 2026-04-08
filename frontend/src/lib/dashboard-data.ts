type AnyRecord = Record<string, unknown>;

function asNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function asString(value: unknown): string {
  return String(value || "").trim();
}

export function buildExamChartData(payload: AnyRecord) {
  const rawExamResults = Array.isArray(payload.examResults) ? payload.examResults : [];
  const examNames: string[] = [];
  const attemptToScores = new Map<string, Record<string, number>>();

  for (const item of rawExamResults) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const examName = asString((item as AnyRecord).examName || (item as AnyRecord).label) || "Exam";
    const attempt = asString((item as AnyRecord).attempt) || "Attempt";
    const score = asNumber((item as AnyRecord).score, Number.NaN);
    if (!Number.isFinite(score)) {
      continue;
    }
    if (!examNames.includes(examName)) {
      examNames.push(examName);
    }
    if (!attemptToScores.has(attempt)) {
      attemptToScores.set(attempt, {});
    }
    attemptToScores.get(attempt)![examName] = score;
  }

  return examNames.map((examName) => {
    const row: Record<string, string | number | null> = { examName };
    for (const [attempt, scoreMap] of attemptToScores.entries()) {
      row[attempt] = Object.prototype.hasOwnProperty.call(scoreMap, examName)
        ? scoreMap[examName]
        : null;
    }
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
