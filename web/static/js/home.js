(function () {
  function readJsonScript(id, fallbackValue) {
    const node = document.getElementById(id);
    if (!node) {
      return fallbackValue;
    }

    try {
      return JSON.parse(node.textContent || "");
    } catch (_error) {
      return fallbackValue;
    }
  }

  const subjectSelect = document.getElementById("subject-select");
  const groupSelect = document.getElementById("group-select");
  const studentSelect = document.getElementById("student-select");
  const searchForm = document.querySelector(".login-form");

  if (!subjectSelect || !groupSelect || !studentSelect) {
    return;
  }

  const groupsBySubject = window.groupsBySubject || readJsonScript("groupsBySubjectJson", {});
  const studentsBySubjectGroup =
    window.studentsBySubjectGroup || readJsonScript("studentsBySubjectGroupJson", {});
  const initialFormData = window.initialFormData || readJsonScript("initialFormDataJson", {});
  const LAST_SELECTION_STORAGE_KEY = "msi:lastSelection:v1";
  const groupPlaceholder = "Select morning or afternoon group";
  const studentPlaceholder = "Select student";

  function loadStoredSelection() {
    try {
      const raw = window.localStorage.getItem(LAST_SELECTION_STORAGE_KEY);
      if (!raw) {
        return {};
      }
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_error) {
      return {};
    }
  }

  function persistSelection(value) {
    try {
      window.localStorage.setItem(LAST_SELECTION_STORAGE_KEY, JSON.stringify(value));
    } catch (_error) {
      // Ignore local storage failures.
    }
  }

  function persistCurrentSelection() {
    persistSelection({
      subject: subjectSelect.value || "",
      group: groupSelect.value || "",
      student_id: studentSelect.value || "",
    });
  }

  function createPlaceholderOption(label, selected) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = label;
    option.disabled = true;
    option.selected = selected;
    return option;
  }

  function renderGroupOptions(subject, selectedGroup) {
    const groups = Array.isArray(groupsBySubject[subject]) ? groupsBySubject[subject] : [];

    groupSelect.innerHTML = "";
    groupSelect.appendChild(createPlaceholderOption(groupPlaceholder, !selectedGroup));

    for (const groupName of groups) {
      const option = document.createElement("option");
      option.value = groupName;
      option.textContent = groupName;
      option.selected = selectedGroup === groupName;
      groupSelect.appendChild(option);
    }

    const hasSubject = Boolean(subject);
    const hasGroups = groups.length > 0;
    groupSelect.disabled = !hasSubject || !hasGroups;

    if (!groups.includes(selectedGroup)) {
      groupSelect.value = "";
    }
  }

  function renderStudentOptions(subject, group, selectedStudentId) {
    const subjectData =
      studentsBySubjectGroup && typeof studentsBySubjectGroup === "object"
        ? studentsBySubjectGroup[subject]
        : null;
    const students =
      subjectData && typeof subjectData === "object" && Array.isArray(subjectData[group])
        ? subjectData[group]
        : [];

    studentSelect.innerHTML = "";
    studentSelect.appendChild(createPlaceholderOption(studentPlaceholder, !selectedStudentId));

    for (const student of students) {
      if (!student || typeof student !== "object") {
        continue;
      }

      const studentId = String(student.id || "").trim();
      if (!studentId) {
        continue;
      }

      const option = document.createElement("option");
      option.value = studentId;
      option.textContent = String(student.fullName || `Student ${studentId}`);
      option.selected = selectedStudentId === studentId;
      studentSelect.appendChild(option);
    }

    const hasSubject = Boolean(subject);
    const hasGroup = Boolean(group);
    const hasStudents = students.length > 0;
    studentSelect.disabled = !hasSubject || !hasGroup || !hasStudents;

    const selectedExists = students.some((student) => String(student && student.id) === selectedStudentId);
    if (!selectedExists) {
      studentSelect.value = "";
    }
  }

  subjectSelect.addEventListener("change", function () {
    renderGroupOptions(subjectSelect.value, "");
    renderStudentOptions(subjectSelect.value, "", "");
    persistCurrentSelection();
  });

  groupSelect.addEventListener("change", function () {
    renderStudentOptions(subjectSelect.value, groupSelect.value, "");
    persistCurrentSelection();
  });

  studentSelect.addEventListener("change", function () {
    persistCurrentSelection();
  });

  if (searchForm) {
    searchForm.addEventListener("submit", function () {
      persistCurrentSelection();
    });
  }

  const storedSelection = loadStoredSelection();
  const initialSubject =
    initialFormData.subject || storedSelection.subject || subjectSelect.value || "";
  const initialGroup = initialFormData.group || storedSelection.group || "";
  const initialStudentId = String(
    initialFormData.student_id || storedSelection.student_id || ""
  );

  renderGroupOptions(initialSubject, initialGroup);
  renderStudentOptions(initialSubject, groupSelect.value || "", initialStudentId);
  persistCurrentSelection();
})();
