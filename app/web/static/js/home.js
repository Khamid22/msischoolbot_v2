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

  function asNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function asPositiveNumber(value) {
    const parsed = asNumber(value);
    return parsed !== null && parsed > 0 ? parsed : null;
  }

  function initStudentSearchPanel() {
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

      const selectedExists = students.some(
        (student) => String(student && student.id) === selectedStudentId
      );
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
    const initialStudentId = String(initialFormData.student_id || storedSelection.student_id || "");

    renderGroupOptions(initialSubject, initialGroup);
    renderStudentOptions(initialSubject, groupSelect.value || "", initialStudentId);
    persistCurrentSelection();
  }

  function initAdminSubjectCharts() {
    const chartLib = window.Chart;
    if (!chartLib) {
      return;
    }

    const performanceCanvas = document.getElementById("adminSubjectPerformanceChart");
    const groupsCanvas = document.getElementById("adminSubjectGroupsChart");
    const distributionTableBody = document.getElementById("adminSubjectDistributionTableBody");
    const schoolSelect = document.getElementById("adminSchoolSelect");
    const subjectSelect = document.getElementById("adminSubjectSelect");
    const selectedLabel = document.getElementById("adminSubjectSelectedLabel");
    const monthlyLegend = document.getElementById("adminSubjectGroupsLegend");
    const monthlyScrollViewport = groupsCanvas
      ? groupsCanvas.closest(".admin-chart-canvas-wrap-tall")
      : null;
    const monthlyScrollTrack = document.getElementById("adminSubjectGroupsChartTrack")
      || (groupsCanvas ? groupsCanvas.parentElement : null);
    const gradeSwitchWrap = document.getElementById("adminGradeSwitchWrap");
    const gradeSwitchButtons = gradeSwitchWrap
      ? Array.from(gradeSwitchWrap.querySelectorAll(".admin-grade-switch-btn"))
      : [];

    if (
      !performanceCanvas ||
      !groupsCanvas ||
      !distributionTableBody ||
      !schoolSelect ||
      !subjectSelect
    ) {
      return;
    }

    const rawRows = readJsonScript("adminSubjectInfoJson", []);
    const rows = Array.isArray(rawRows)
      ? rawRows
          .map(function (row) {
            if (!row || typeof row !== "object") {
              return null;
            }

            const subjectName = String(row.subject_name || "").trim();
            if (!subjectName) {
              return null;
            }

            const schoolKey = String(row.school_key || "").trim().toLowerCase();
            const schoolName = String(row.school_name || "").trim() || "School";
            if (!schoolKey) {
              return null;
            }

            const rawGroups = Array.isArray(row.groups) ? row.groups : [];
            const groups = rawGroups
              .map(function (groupRow) {
                if (!groupRow || typeof groupRow !== "object") {
                  return null;
                }
                const label = String(groupRow.label || "").trim();
                if (!label) {
                  return null;
                }
                return {
                  label,
                  students_count: Math.max(0, Math.round(asNumber(groupRow.students_count) || 0)),
                  avg_aap: asPositiveNumber(groupRow.avg_aap),
                  avg_ar: asNumber(groupRow.avg_ar),
                };
              })
              .filter(Boolean);

            const rawMonthlyMonths = Array.isArray(row.monthly_months) ? row.monthly_months : [];
            const monthlyMonths = rawMonthlyMonths
              .map(function (monthValue) {
                const monthText = String(monthValue || "").trim();
                return /^\d{4}-\d{2}$/.test(monthText) ? monthText : "";
              })
              .filter(Boolean);

            const rawMonthlySeries = Array.isArray(row.monthly_series) ? row.monthly_series : [];
            const monthlySeries = rawMonthlySeries
              .map(function (seriesRow) {
                if (!seriesRow || typeof seriesRow !== "object") {
                  return null;
                }

                const label = String(seriesRow.label || "").trim();
                if (!label) {
                  return null;
                }

                const rawValues = Array.isArray(seriesRow.values) ? seriesRow.values : [];
                const values = monthlyMonths.map(function (_monthKey, index) {
                  const value = asPositiveNumber(rawValues[index]);
                  return value === null ? null : value;
                });

                return {
                  label,
                  values,
                };
              })
              .filter(Boolean);

            return {
              school_key: schoolKey,
              school_name: schoolName,
              subject_name: subjectName,
              students_count: Math.max(0, Math.round(asNumber(row.students_count) || 0)),
              avg_aap: asPositiveNumber(row.avg_aap),
              avg_ar: asNumber(row.avg_ar),
              groups,
              monthly_months: monthlyMonths,
              monthly_series: monthlySeries,
            };
          })
          .filter(Boolean)
      : [];

    if (!rows.length) {
      return;
    }

    let selectedSehriyoGrade = "";
    let currentSelectedRow = null;
    const MONTHLY_VISIBLE_MONTHS = 10;

    const palette = [
      "#2563eb",
      "#f59e0b",
      "#1e3a8a",
      "#166534",
      "#0f766e",
    ];
    const groupColorMap = {
      mg1: "#2563eb", // blue
      mg2: "#06b6d4", // cyan
      morninggroup1: "#2563eb",
      morninggroup2: "#06b6d4",
      aft1: "#f59e0b", // orange
      aft2: "#8b5a2b", // brown
      afternoongroup1: "#f59e0b",
      afternoongroup2: "#8b5a2b",
      "7a": "#2563eb", // blue
      "7b": "#06b6d4", // cyan
      "7v": "#f59e0b", // orange
      "7d": "#8b5a2b", // brown
      "7g": "#a78bfa", // light purple
      "8a": "#2563eb", // blue
      "8b": "#06b6d4", // cyan
      "8d": "#8b5a2b", // brown
      "8g": "#a78bfa", // light purple
    };

    function colorByIndex(index) {
      return palette[index % palette.length];
    }

    function normalizeGroupColorKey(label) {
      return String(label || "")
        .trim()
        .toLowerCase()
        .replace(/[\s_-]+/g, "");
    }

    function colorByLabel(label, fallbackIndex) {
      const text = String(label || "").trim();
      if (!text) {
        return colorByIndex(fallbackIndex);
      }

      const normalizedKey = normalizeGroupColorKey(text);
      if (Object.prototype.hasOwnProperty.call(groupColorMap, normalizedKey)) {
        return groupColorMap[normalizedKey];
      }

      return colorByIndex(fallbackIndex);
    }

    function hexToRgba(color, alpha) {
      const text = String(color || "").trim();
      const safeAlpha = Math.max(0, Math.min(1, Number(alpha)));
      if (!text.startsWith("#")) {
        return text || `rgba(0,0,0,${safeAlpha})`;
      }

      const hex = text.slice(1);
      if (hex.length === 3) {
        const r = parseInt(hex[0] + hex[0], 16);
        const g = parseInt(hex[1] + hex[1], 16);
        const b = parseInt(hex[2] + hex[2], 16);
        return `rgba(${r}, ${g}, ${b}, ${safeAlpha})`;
      }

      if (hex.length === 6) {
        const r = parseInt(hex.slice(0, 2), 16);
        const g = parseInt(hex.slice(2, 4), 16);
        const b = parseInt(hex.slice(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, ${safeAlpha})`;
      }

      return text;
    }

    function formatMonthLabel(monthKey) {
      if (!/^\d{4}-\d{2}$/.test(String(monthKey || ""))) {
        return String(monthKey || "");
      }
      const year = Number(monthKey.slice(0, 4));
      const month = Number(monthKey.slice(5, 7));
      if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) {
        return monthKey;
      }
      const shortMonths = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      return `${shortMonths[month - 1]} ${String(year).slice(-2)}`;
    }

    function gradeFromGroupLabel(label) {
      const text = String(label || "").trim();
      const match = text.match(/^([78])/);
      return match ? String(match[1]) : "";
    }

    function availableGradesForRow(row) {
      const grades = new Set();
      const groups = row && Array.isArray(row.groups) ? row.groups : [];
      const monthlySeries = row && Array.isArray(row.monthly_series) ? row.monthly_series : [];

      groups.forEach(function (groupRow) {
        const grade = gradeFromGroupLabel(groupRow && groupRow.label);
        if (grade) {
          grades.add(grade);
        }
      });
      monthlySeries.forEach(function (seriesRow) {
        const grade = gradeFromGroupLabel(seriesRow && seriesRow.label);
        if (grade) {
          grades.add(grade);
        }
      });

      return ["7", "8"].filter(function (grade) {
        return grades.has(grade);
      });
    }

    function filterGroupsByGrade(groups, grade) {
      if (!grade) {
        return groups;
      }
      return groups.filter(function (groupRow) {
        return gradeFromGroupLabel(groupRow && groupRow.label) === grade;
      });
    }

    function filterMonthlySeriesByGrade(monthlySeries, grade) {
      if (!grade) {
        return monthlySeries;
      }
      return monthlySeries.filter(function (seriesRow) {
        return gradeFromGroupLabel(seriesRow && seriesRow.label) === grade;
      });
    }

    function renderGradeSwitch(row, activeGrade) {
      if (!gradeSwitchWrap) {
        return;
      }

      const schoolKey = row ? String(row.school_key || "").trim().toLowerCase() : "";
      const isSehriyo = schoolKey === "sehriyo";
      const availableGrades = isSehriyo ? availableGradesForRow(row) : [];

      if (!isSehriyo || !availableGrades.length) {
        gradeSwitchWrap.hidden = true;
        gradeSwitchWrap.classList.remove("is-visible");
        gradeSwitchButtons.forEach(function (button) {
          button.disabled = true;
          button.classList.remove("active");
        });
        return;
      }

      gradeSwitchWrap.hidden = false;
      gradeSwitchWrap.classList.add("is-visible");
      gradeSwitchButtons.forEach(function (button) {
        const buttonGrade = String(button.getAttribute("data-grade") || "").trim();
        const enabled = availableGrades.includes(buttonGrade);
        button.disabled = !enabled;
        button.classList.toggle("active", enabled && buttonGrade === activeGrade);
      });
    }

    function syncMonthlyScrollWidth(monthCount) {
      if (!monthlyScrollViewport || !monthlyScrollTrack) {
        return;
      }

      const viewportWidth = Math.max(0, Math.round(monthlyScrollViewport.clientWidth || 0));
      if (!viewportWidth) {
        window.requestAnimationFrame(function () {
          syncMonthlyScrollWidth(monthCount);
        });
        return;
      }

      const safeMonthCount = Math.max(1, Number(monthCount) || 1);
      const targetWidth = safeMonthCount > MONTHLY_VISIBLE_MONTHS
        ? Math.round((viewportWidth / MONTHLY_VISIBLE_MONTHS) * safeMonthCount)
        : viewportWidth;

      monthlyScrollTrack.style.width = `${targetWidth}px`;
      monthlyScrollTrack.style.minWidth = `${viewportWidth}px`;
      groupsCanvas.style.setProperty("width", `${targetWidth}px`, "important");
      groupsCanvas.style.setProperty("min-width", `${targetWidth}px`, "important");
    }

    function rowsForSchool(schoolKey) {
      return rows
        .filter(function (row) {
          return row.school_key === schoolKey;
        })
        .sort(function (a, b) {
          return String(a.subject_name || "").localeCompare(String(b.subject_name || ""));
        });
    }

    function findRow(schoolKey, subjectName) {
      return (
        rows.find(function (row) {
          return row.school_key === schoolKey && row.subject_name === subjectName;
        }) || null
      );
    }

    const performanceChart = new chartLib(performanceCanvas, {
      type: "bar",
      data: {
        labels: [],
        datasets: [
          {
            label: "AAP",
            data: [],
            backgroundColor: "#111827",
            borderRadius: 6,
            maxBarThickness: 24,
            yAxisID: "y",
          },
          {
            label: "AR",
            data: [],
            backgroundColor: "#94a3b8",
            borderRadius: 6,
            maxBarThickness: 24,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            align: "start",
            labels: {
              color: "#334155",
              boxWidth: 10,
              padding: 8,
              usePointStyle: true,
              font: { size: 10, weight: "700" },
            },
          },
          tooltip: {
            backgroundColor: "rgba(255,255,255,0.95)",
            titleColor: "#334155",
            bodyColor: "#0f172a",
            borderColor: "rgba(148,163,184,0.3)",
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: {
              color: "#64748b",
              maxRotation: 0,
              minRotation: 0,
              autoSkip: false,
              font: { size: 10 },
            },
            grid: {
              display: false,
            },
          },
          y: {
            min: 0,
            max: 9,
            ticks: {
              color: "#64748b",
              autoSkip: false,
              stepSize: 1,
              precision: 0,
              font: { size: 10 },
            },
            grid: {
              color: "#e2e8f0",
            },
            title: {
              display: false,
              color: "#64748b",
              font: { size: 10 },
            },
          },
          y1: {
            position: "right",
            min: 0,
            max: 100,
            ticks: {
              color: "#64748b",
              autoSkip: false,
              stepSize: 10,
              precision: 0,
              font: { size: 10 },
            },
            grid: {
              drawOnChartArea: false,
            },
            title: {
              display: false,
              color: "#64748b",
              font: { size: 10 },
            },
          },
        },
      },
    });

    function renderDistributionTable(groups) {
      distributionTableBody.innerHTML = "";

      if (!Array.isArray(groups) || !groups.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 4;
        cell.textContent = "No group data.";
        row.appendChild(cell);
        distributionTableBody.appendChild(row);
        return;
      }

      groups.forEach(function (row) {
        const tr = document.createElement("tr");

        const groupCell = document.createElement("td");
        groupCell.textContent = String(row.label || "-");
        tr.appendChild(groupCell);

        const studentsCell = document.createElement("td");
        studentsCell.textContent = String(Math.max(0, Math.round(asNumber(row.students_count) || 0)));
        tr.appendChild(studentsCell);

        const aapCell = document.createElement("td");
        aapCell.textContent = row.avg_aap === null || row.avg_aap === undefined ? "-" : String(row.avg_aap);
        tr.appendChild(aapCell);

        const arCell = document.createElement("td");
        arCell.textContent = row.avg_ar === null || row.avg_ar === undefined ? "-" : `${row.avg_ar}%`;
        tr.appendChild(arCell);

        distributionTableBody.appendChild(tr);
      });
    }

    const monthlyChart = new chartLib(groupsCanvas, {
      type: "line",
      data: {
        labels: [],
        datasets: [],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            backgroundColor: "rgba(255,255,255,0.95)",
            titleColor: "#334155",
            bodyColor: "#0f172a",
            borderColor: "rgba(148,163,184,0.3)",
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: {
              color: "#64748b",
              maxRotation: 0,
              minRotation: 0,
              autoSkip: false,
              font: { size: 10 },
            },
            grid: {
              display: false,
            },
          },
          y: {
            min: 0,
            suggestedMax: 9,
            ticks: {
              color: "#64748b",
              font: { size: 10 },
            },
            grid: {
              color: "#e2e8f0",
            },
            title: {
              display: true,
              text: "AAP",
              color: "#64748b",
              font: { size: 10 },
            },
          },
        },
      },
    });

    function renderMonthlyLegend(datasets) {
      if (!monthlyLegend) {
        return;
      }

      monthlyLegend.innerHTML = "";
      const title = document.createElement("span");
      title.className = "admin-chart-legend-title";
      title.textContent = "Classes:";
      monthlyLegend.appendChild(title);

      const rows = Array.isArray(datasets) ? datasets : [];
      if (!rows.length) {
        return;
      }

      rows.forEach(function (datasetRow) {
        const item = document.createElement("span");
        item.className = "admin-chart-legend-item";

        const swatch = document.createElement("span");
        swatch.className = "admin-chart-legend-swatch";
        swatch.style.backgroundColor = String(datasetRow.borderColor || "#334155");
        item.appendChild(swatch);

        const label = document.createElement("span");
        label.textContent = String(datasetRow.label || "");
        item.appendChild(label);

        monthlyLegend.appendChild(item);
      });
    }

    function trimEmptyMonthlyMonths(months, series) {
      const monthRows = Array.isArray(months) ? months : [];
      const seriesRows = Array.isArray(series) ? series : [];
      if (!monthRows.length || !seriesRows.length) {
        return {
          months: monthRows,
          series: seriesRows,
        };
      }

      const keepIndexes = monthRows.map(function (_month, monthIndex) {
        return seriesRows.some(function (seriesRow) {
          const values = Array.isArray(seriesRow && seriesRow.values) ? seriesRow.values : [];
          return asPositiveNumber(values[monthIndex]) !== null;
        });
      });

      const hasAnyMonths = keepIndexes.some(Boolean);
      const filteredMonths = hasAnyMonths
        ? monthRows.filter(function (_month, monthIndex) {
            return keepIndexes[monthIndex];
          })
        : [];
      const filteredSeries = seriesRows.map(function (seriesRow) {
        const rawValues = Array.isArray(seriesRow && seriesRow.values) ? seriesRow.values : [];
        const values = hasAnyMonths
          ? rawValues.filter(function (_value, monthIndex) {
              return keepIndexes[monthIndex];
            })
          : [];
        return {
          label: String(seriesRow && seriesRow.label ? seriesRow.label : ""),
          values,
        };
      });

      return {
        months: filteredMonths,
        series: filteredSeries,
      };
    }

    function renderCharts(selectedRow) {
      currentSelectedRow = selectedRow;
      const baseGroups = selectedRow && Array.isArray(selectedRow.groups) ? selectedRow.groups : [];
      const baseMonthlyMonths =
        selectedRow && Array.isArray(selectedRow.monthly_months) ? selectedRow.monthly_months : [];
      const baseMonthlySeries =
        selectedRow && Array.isArray(selectedRow.monthly_series) ? selectedRow.monthly_series : [];
      const schoolKey = selectedRow ? String(selectedRow.school_key || "").trim().toLowerCase() : "";
      const isSehriyo = schoolKey === "sehriyo";
      const availableGrades = isSehriyo ? availableGradesForRow(selectedRow) : [];

      let activeGrade = "";
      if (isSehriyo && availableGrades.length) {
        if (selectedSehriyoGrade && availableGrades.includes(selectedSehriyoGrade)) {
          activeGrade = selectedSehriyoGrade;
        } else if (availableGrades.includes("7")) {
          activeGrade = "7";
        } else if (availableGrades.includes("8")) {
          activeGrade = "8";
        } else {
          activeGrade = availableGrades[0];
        }
      }
      selectedSehriyoGrade = activeGrade;
      renderGradeSwitch(selectedRow, activeGrade);

      const groups = isSehriyo ? filterGroupsByGrade(baseGroups, activeGrade) : baseGroups;
      const monthlySeriesByGrade = isSehriyo
        ? filterMonthlySeriesByGrade(baseMonthlySeries, activeGrade)
        : baseMonthlySeries;
      const monthlyTimeline =
        isSehriyo && activeGrade === "7"
          ? trimEmptyMonthlyMonths(baseMonthlyMonths, monthlySeriesByGrade)
          : { months: baseMonthlyMonths, series: monthlySeriesByGrade };
      const monthlyMonths = monthlyTimeline.months;
      const monthlySeries = monthlyTimeline.series;
      const denseGroups = groups.length > 5;

      const classColors = groups.map(function (row, index) {
        return colorByLabel(row.label, index);
      });
      const classColorsTransparent = classColors.map(function (color) {
        return hexToRgba(color, 0.32);
      });

      performanceChart.resize();
      performanceChart.data.labels = groups.map(function (row) {
        return row.label;
      });
      performanceChart.data.datasets[0].data = groups.map(function (row) {
        return row.avg_aap;
      });
      performanceChart.data.datasets[0].backgroundColor = classColors;
      performanceChart.data.datasets[0].borderColor = classColors;
      performanceChart.data.datasets[0].borderWidth = 0;
      performanceChart.data.datasets[0].maxBarThickness = denseGroups ? 16 : 24;
      performanceChart.data.datasets[1].data = groups.map(function (row) {
        return row.avg_ar;
      });
      performanceChart.data.datasets[1].backgroundColor = classColorsTransparent;
      performanceChart.data.datasets[1].borderColor = classColors;
      performanceChart.data.datasets[1].borderWidth = 1;
      performanceChart.data.datasets[1].maxBarThickness = denseGroups ? 16 : 24;
      performanceChart.options.scales.x.ticks.maxRotation = denseGroups ? 32 : 0;
      performanceChart.options.scales.x.ticks.minRotation = denseGroups ? 18 : 0;
      performanceChart.update();
      renderDistributionTable(groups);

      monthlyChart.data.labels = monthlyMonths.map(formatMonthLabel);
      const groupDatasets = monthlySeries.map(function (seriesRow, index) {
        const stroke = colorByLabel(seriesRow.label, index);
        return {
          label: String(seriesRow.label || `Group ${index + 1}`),
          data: Array.isArray(seriesRow.values) ? seriesRow.values : [],
          borderColor: stroke,
          backgroundColor: stroke,
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 3,
          pointBackgroundColor: "#ffffff",
          pointBorderColor: stroke,
          pointBorderWidth: 1.6,
          tension: 0.45,
          cubicInterpolationMode: "monotone",
          spanGaps: true,
          order: 10,
        };
      });
      monthlyChart.data.datasets = groupDatasets;
      renderMonthlyLegend(groupDatasets);
      syncMonthlyScrollWidth(monthlyMonths.length);
      if (monthlyScrollViewport && monthlyMonths.length > MONTHLY_VISIBLE_MONTHS) {
        monthlyScrollViewport.scrollLeft = 0;
      }
      monthlyChart.resize();
      monthlyChart.update();

      if (selectedLabel) {
        const subjectName = selectedRow ? String(selectedRow.subject_name || "").trim() : "";
        selectedLabel.textContent = subjectName || "-";
      }
    }

    function renderSubjectsForSchool(schoolKey, preferredSubject) {
      const schoolRows = rowsForSchool(schoolKey);
      subjectSelect.innerHTML = "";

      if (!schoolRows.length) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "No subjects";
        option.disabled = true;
        option.selected = true;
        subjectSelect.appendChild(option);
        subjectSelect.disabled = true;
        renderCharts(null);
        return;
      }

      subjectSelect.disabled = false;
      schoolRows.forEach(function (row) {
        const option = document.createElement("option");
        option.value = row.subject_name;
        option.textContent = row.subject_name;
        subjectSelect.appendChild(option);
      });

      const selectedSubject =
        preferredSubject &&
        schoolRows.some(function (row) {
          return row.subject_name === preferredSubject;
        })
          ? preferredSubject
          : schoolRows[0].subject_name;

      subjectSelect.value = selectedSubject;
      renderCharts(findRow(schoolKey, selectedSubject));
    }

    const schoolNameByKey = {};
    const schoolKeys = [];
    rows.forEach(function (row) {
      const schoolKey = row.school_key;
      if (!schoolKey) {
        return;
      }
      if (!schoolNameByKey[schoolKey]) {
        schoolNameByKey[schoolKey] = row.school_name || schoolKey;
      }
      if (!schoolKeys.includes(schoolKey)) {
        schoolKeys.push(schoolKey);
      }
    });

    schoolSelect.innerHTML = "";
    schoolKeys.forEach(function (schoolKey) {
      const option = document.createElement("option");
      option.value = schoolKey;
      option.textContent = schoolNameByKey[schoolKey] || schoolKey;
      schoolSelect.appendChild(option);
    });

    const initialSchool =
      schoolSelect.value && schoolKeys.includes(schoolSelect.value)
        ? schoolSelect.value
        : schoolKeys[0];
    schoolSelect.value = initialSchool;
    renderSubjectsForSchool(initialSchool, subjectSelect.value || "");

    schoolSelect.addEventListener("change", function () {
      renderSubjectsForSchool(schoolSelect.value || schoolKeys[0] || "", "");
    });

    subjectSelect.addEventListener("change", function () {
      const selectedSchool = schoolSelect.value || schoolKeys[0] || "";
      renderCharts(findRow(selectedSchool, subjectSelect.value || ""));
    });

    window.addEventListener("resize", function () {
      syncMonthlyScrollWidth(monthlyChart.data.labels.length);
      monthlyChart.resize();
    });

    gradeSwitchButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        if (button.disabled) {
          return;
        }
        const grade = String(button.getAttribute("data-grade") || "").trim();
        if (!grade || grade === selectedSehriyoGrade) {
          return;
        }
        selectedSehriyoGrade = grade;
        renderCharts(currentSelectedRow);
      });
    });
  }

  initStudentSearchPanel();
  initAdminSubjectCharts();
})();
