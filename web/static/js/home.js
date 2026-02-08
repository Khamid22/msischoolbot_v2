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

  if (!subjectSelect || !groupSelect) {
    return;
  }

  const groupsBySubject = window.groupsBySubject || readJsonScript("groupsBySubjectJson", {});
  const initialFormData = window.initialFormData || readJsonScript("initialFormDataJson", {});
  const defaultOptionLabel = "Select your group";

  function createPlaceholderOption(selected) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = defaultOptionLabel;
    option.disabled = true;
    option.selected = selected;
    return option;
  }

  function renderGroupOptions(subject, selectedGroup) {
    const groups = Array.isArray(groupsBySubject[subject]) ? groupsBySubject[subject] : [];

    groupSelect.innerHTML = "";
    groupSelect.appendChild(createPlaceholderOption(!selectedGroup));

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

  subjectSelect.addEventListener("change", function () {
    renderGroupOptions(subjectSelect.value, "");
  });

  renderGroupOptions(initialFormData.subject || subjectSelect.value || "", initialFormData.group || "");
})();
