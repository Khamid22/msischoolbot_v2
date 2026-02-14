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

  const data = window.dashboardData || readJsonScript("dashboardDataJson", null);

  const profileMenuToggle = document.getElementById("profileMenuToggle");
  const profileMenu = document.getElementById("profileMenu");
  const subjectMenuToggle = document.getElementById("subjectMenuToggle");
  const subjectMenu = document.getElementById("subjectMenu");
  const logoutMenuItem = document.getElementById("logoutMenuItem");
  const profileMenuItem = document.getElementById("profileMenuItem");
  const logoutConfirmModal = document.getElementById("logoutConfirmModal");
  const logoutConfirmBtn = document.getElementById("logoutConfirmBtn");
  const logoutCancelBtn = document.getElementById("logoutCancelBtn");
  const studentProfileModal = document.getElementById("studentProfileModal");
  const profileCloseBtn = document.getElementById("profileCloseBtn");
  const dashboardLogoutForm = document.getElementById("dashboardLogoutForm");

  function closeProfileMenu() {
    if (!profileMenu || !profileMenuToggle) {
      return;
    }
    profileMenu.hidden = true;
    profileMenuToggle.setAttribute("aria-expanded", "false");
  }

  function openProfileMenu() {
    if (!profileMenu || !profileMenuToggle) {
      return;
    }
    profileMenu.hidden = false;
    profileMenuToggle.setAttribute("aria-expanded", "true");
  }

  function closeSubjectMenu() {
    if (!subjectMenu || !subjectMenuToggle) {
      return;
    }
    subjectMenu.hidden = true;
    subjectMenuToggle.setAttribute("aria-expanded", "false");
  }

  function openSubjectMenu() {
    if (!subjectMenu || !subjectMenuToggle) {
      return;
    }
    subjectMenu.hidden = false;
    subjectMenuToggle.setAttribute("aria-expanded", "true");
  }

  function closeLogoutModal() {
    if (!logoutConfirmModal) {
      return;
    }
    logoutConfirmModal.hidden = true;
  }

  function openLogoutModal() {
    if (!logoutConfirmModal) {
      return;
    }
    logoutConfirmModal.hidden = false;
  }

  function closeProfileModal() {
    if (!studentProfileModal) {
      return;
    }
    studentProfileModal.hidden = true;
  }

  function openProfileModal() {
    if (!studentProfileModal) {
      return;
    }
    studentProfileModal.hidden = false;
  }

  if (profileMenuToggle && profileMenu) {
    profileMenuToggle.addEventListener("click", function () {
      if (profileMenu.hidden) {
        closeSubjectMenu();
        openProfileMenu();
      } else {
        closeProfileMenu();
      }
    });

    document.addEventListener("click", function (event) {
      if (
        !profileMenu.hidden &&
        !profileMenu.contains(event.target) &&
        !profileMenuToggle.contains(event.target)
      ) {
        closeProfileMenu();
      }
    });
  }

  if (subjectMenuToggle && subjectMenu) {
    subjectMenuToggle.addEventListener("click", function () {
      if (subjectMenu.hidden) {
        closeProfileMenu();
        openSubjectMenu();
      } else {
        closeSubjectMenu();
      }
    });

    document.addEventListener("click", function (event) {
      if (
        !subjectMenu.hidden &&
        !subjectMenu.contains(event.target) &&
        !subjectMenuToggle.contains(event.target)
      ) {
        closeSubjectMenu();
      }
    });
  }

  if (logoutMenuItem) {
    logoutMenuItem.addEventListener("click", function () {
      closeProfileMenu();
      openLogoutModal();
    });
  }

  if (profileMenuItem) {
    profileMenuItem.addEventListener("click", function () {
      closeProfileMenu();
      openProfileModal();
    });
  }

  if (logoutCancelBtn) {
    logoutCancelBtn.addEventListener("click", function () {
      closeLogoutModal();
    });
  }

  if (logoutConfirmModal) {
    logoutConfirmModal.addEventListener("click", function (event) {
      const target = event.target;
      if (target && target.getAttribute("data-close-modal") === "true") {
        closeLogoutModal();
      }
    });
  }

  if (studentProfileModal) {
    studentProfileModal.addEventListener("click", function (event) {
      const target = event.target;
      if (target && target.getAttribute("data-close-profile-modal") === "true") {
        closeProfileModal();
      }
    });
  }

  if (profileCloseBtn) {
    profileCloseBtn.addEventListener("click", function () {
      closeProfileModal();
    });
  }

  if (logoutConfirmBtn) {
    logoutConfirmBtn.addEventListener("click", function () {
      if (dashboardLogoutForm) {
        dashboardLogoutForm.submit();
      }
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
      return;
    }
    closeProfileMenu();
    closeSubjectMenu();
    closeLogoutModal();
    closeProfileModal();
  });

  const progressFill = document.getElementById("programProgressFill");
  if (progressFill) {
    const rawRate = Number(progressFill.dataset.rate || "0");
    const safeRate = Number.isFinite(rawRate) ? Math.min(Math.max(rawRate, 0), 100) : 0;
    progressFill.style.width = `${safeRate}%`;
  }

  if (!data) {
    return;
  }

  function showChartMessage(canvas, message) {
    const chartBox = canvas && canvas.parentElement;
    if (!chartBox) {
      return;
    }

    canvas.style.display = "none";
    let messageNode = chartBox.querySelector(".chart-empty");
    if (!messageNode) {
      messageNode = document.createElement("p");
      messageNode.className = "chart-empty";
      chartBox.appendChild(messageNode);
    }
    messageNode.textContent = message;
  }

  const hasChartLibrary = Boolean(window.Chart);
  if (!hasChartLibrary) {
    const canvases = document.querySelectorAll("canvas");
    canvases.forEach((canvas) => showChartMessage(canvas, "Chart library failed to load."));
  }

  const prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isNarrowScreen = window.matchMedia && window.matchMedia("(max-width: 720px)").matches;
  const dpr = Math.min(window.devicePixelRatio || 1, isNarrowScreen ? 1.5 : 2);

  const barValuePlugin = {
    id: "barValuePlugin",
    afterDatasetsDraw(chart) {
      if (chart.config.type !== "bar") {
        return;
      }

      const ctx = chart.ctx;
      ctx.save();
      ctx.font = `${isNarrowScreen ? 12 : 13}px \"Plus Jakarta Sans\", sans-serif`;
      ctx.fillStyle = "#111827";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";

      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (meta.hidden) {
          return;
        }

        meta.data.forEach((barElement, dataIndex) => {
          const rawValue = dataset.data[dataIndex];
          if (rawValue === null || rawValue === undefined) {
            return;
          }

          const value = Number(rawValue);
          if (Number.isNaN(value)) {
            return;
          }

          ctx.fillText(value.toFixed(1), barElement.x, barElement.y - 4);
        });
      });

      ctx.restore();
    },
  };

  function createExamResultsChart() {
    const canvas = document.getElementById("examResultsChart");
    if (!canvas) {
      return;
    }

    const rawExamResults = Array.isArray(data.examResults) ? data.examResults : [];
    if (!rawExamResults.length) {
      showChartMessage(canvas, "No exam results yet.");
      return;
    }

    const examNames = [];
    const attemptToExamScores = new Map();

    for (const item of rawExamResults) {
      const examName = item.examName || item.label || "Exam";
      const attempt = item.attempt || "Attempt";
      const score = Number(item.score);

      if (!Number.isFinite(score)) {
        continue;
      }

      if (!examNames.includes(examName)) {
        examNames.push(examName);
      }

      if (!attemptToExamScores.has(attempt)) {
        attemptToExamScores.set(attempt, {});
      }
      attemptToExamScores.get(attempt)[examName] = score;
    }

    if (!examNames.length) {
      showChartMessage(canvas, "No exam results yet.");
      return;
    }

    const preferredAttemptOrder = {
      "First Attempt": 1,
      "Second Attempt": 2,
      Attempt: 3,
    };

    const attempts = [...attemptToExamScores.keys()].sort((a, b) => {
      const rankA = preferredAttemptOrder[a] || 99;
      const rankB = preferredAttemptOrder[b] || 99;
      if (rankA !== rankB) {
        return rankA - rankB;
      }
      return a.localeCompare(b);
    });

    const attemptColors = {
      "First Attempt": "#6b7280",
      "Second Attempt": "#111827",
      Attempt: "#374151",
    };

    const datasets = attempts.map((attempt) => {
      const scoreMap = attemptToExamScores.get(attempt);
      return {
        label: attempt,
        data: examNames.map((examName) =>
          Object.prototype.hasOwnProperty.call(scoreMap, examName) ? scoreMap[examName] : null
        ),
        borderColor: "#000000",
        backgroundColor: attemptColors[attempt] || "#374151",
        borderWidth: 1.2,
        borderRadius: 6,
        maxBarThickness: isNarrowScreen ? 34 : 44,
        barPercentage: 0.84,
        categoryPercentage: 0.86,
      };
    });

    new Chart(canvas, {
      type: "bar",
      data: {
        labels: examNames,
        datasets,
      },
      plugins: [barValuePlugin],
      options: {
        normalized: true,
        responsive: true,
        maintainAspectRatio: false,
        devicePixelRatio: dpr,
        animation: prefersReducedMotion || isNarrowScreen ? false : { duration: 700 },
        plugins: {
          legend: {
            display: datasets.length > 1,
            position: "bottom",
            labels: {
              color: "#334155",
              padding: isNarrowScreen ? 10 : 14,
              boxWidth: isNarrowScreen ? 10 : 14,
              font: { size: isNarrowScreen ? 11 : 12 },
            },
          },
          tooltip: {
            backgroundColor: "rgba(255,255,255,0.96)",
            titleColor: "#334155",
            bodyColor: "#000000",
            borderColor: "rgba(148,163,184,0.2)",
            borderWidth: 1,
            padding: isNarrowScreen ? 10 : 12,
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: "#64748b",
              autoSkip: true,
              maxRotation: 0,
              minRotation: 0,
              maxTicksLimit: isNarrowScreen ? 6 : 12,
              font: { size: isNarrowScreen ? 9 : 10 },
            },
          },
          y: {
            min: 1,
            max: 9,
            ticks: {
              color: "#64748b",
              stepSize: 1,
              font: { size: isNarrowScreen ? 9 : 10 },
            },
            grid: { color: "#e2e8f0" },
          },
        },
      },
    });
  }

  function createAttendanceChart() {
    const pieCanvas = document.getElementById("attendanceChart");
    if (!pieCanvas) {
      return;
    }

    const attendanceRecord =
      data && typeof data.attendanceRecord === "object" && data.attendanceRecord
        ? data.attendanceRecord
        : {};
    const present = Number(attendanceRecord.presentCount) || 0;
    const absent = Number(attendanceRecord.absentCount) || 0;
    const justifiedAbsent = Number(attendanceRecord.justifiedAbsentCount) || 0;
    if (present + absent + justifiedAbsent <= 0) {
      showChartMessage(pieCanvas, "No attendance records yet.");
      return;
    }

    new Chart(pieCanvas, {
      type: "doughnut",
      data: {
        labels: ["Present", "Absent", "Justified Absent"],
        datasets: [
          {
            data: [present, absent, justifiedAbsent],
            backgroundColor: ["#000000", "#e5e7eb", "#FDE68A"],
            borderWidth: 0,
            spacing: isNarrowScreen ? 2 : 3,
            hoverOffset: isNarrowScreen ? 2 : 3,
          },
        ],
      },
      options: {
        normalized: true,
        responsive: true,
        maintainAspectRatio: false,
        devicePixelRatio: dpr,
        animation: prefersReducedMotion || isNarrowScreen ? false : { duration: 700 },
        cutout: isNarrowScreen ? "64%" : "66%",
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              usePointStyle: true,
              pointStyle: "circle",
              color: "#334155",
              padding: isNarrowScreen ? 12 : 18,
              boxWidth: isNarrowScreen ? 8 : 10,
              font: { size: isNarrowScreen ? 11 : 12 },
            },
          },
        },
      },
    });
  }

  function createHomeworkChart() {
    const chartSvg = document.getElementById("homeworkGradesChart");
    const yAxisSvg = document.getElementById("homeworkGradesYAxis");
    if (!chartSvg) {
      return;
    }

    const rawHomeworkGrades = Array.isArray(data.homeworkGrades) ? data.homeworkGrades : [];
    const scores = rawHomeworkGrades
      .map((item) => Number(item && item.score))
      .filter((score) => Number.isFinite(score) && score >= 1 && score <= 9);

    if (!scores.length) {
      if (yAxisSvg) {
        yAxisSvg.style.display = "none";
        yAxisSvg.innerHTML = "";
      }
      showChartMessage(chartSvg, "No homework grades yet.");
      return;
    }

    const labels = scores.map((_score, index) => `L${index + 1}`);
    const scrollContainer = chartSvg.closest(".chart-scroll");
    const homeworkBox = chartSvg.closest(".chart-box-homework");

    if (!scrollContainer || !homeworkBox) {
      if (yAxisSvg) {
        yAxisSvg.style.display = "none";
        yAxisSvg.innerHTML = "";
      }
      showChartMessage(chartSvg, "Failed to render chart data.");
      return;
    }

    const visiblePoints = 15;
    const axisWidth = Math.max(yAxisSvg && yAxisSvg.parentElement ? yAxisSvg.parentElement.clientWidth : 36, 34);
    const paddingRight = 14;
    const paddingTop = 12;
    const paddingBottom = 34;
    const yMin = 1;
    const yMax = 9;

    const viewportWidth = Math.max(scrollContainer.clientWidth, 320);
    const plotVisibleWidth = Math.max(120, viewportWidth - paddingRight);
    const pointSpacing = plotVisibleWidth / Math.max(visiblePoints - 1, 1);
    const fullWidth = Math.round(paddingRight + Math.max(0, labels.length - 1) * pointSpacing);
    const fullHeight = Math.max(Math.round(homeworkBox.clientHeight || 240), 210);
    const plotHeight = Math.max(120, fullHeight - paddingTop - paddingBottom);
    const canScroll = labels.length > visiblePoints;

    scrollContainer.style.overflowX = canScroll ? "scroll" : "hidden";
    scrollContainer.style.touchAction = canScroll ? "pan-x" : "auto";
    scrollContainer.scrollLeft = 0;

    homeworkBox.style.setProperty("width", `${fullWidth}px`, "important");
    homeworkBox.style.setProperty("min-width", `${fullWidth}px`, "important");

    const chartEmptyMessage = homeworkBox.querySelector(".chart-empty");
    if (chartEmptyMessage) {
      chartEmptyMessage.remove();
    }

    chartSvg.style.removeProperty("display");
    chartSvg.setAttribute("width", String(fullWidth));
    chartSvg.setAttribute("height", String(fullHeight));
    chartSvg.setAttribute("viewBox", `0 0 ${fullWidth} ${fullHeight}`);
    chartSvg.setAttribute("aria-label", "Homework grades by lesson");
    chartSvg.innerHTML = "";

    if (yAxisSvg) {
      yAxisSvg.style.removeProperty("display");
      yAxisSvg.setAttribute("width", String(axisWidth));
      yAxisSvg.setAttribute("height", String(fullHeight));
      yAxisSvg.setAttribute("viewBox", `0 0 ${axisWidth} ${fullHeight}`);
      yAxisSvg.setAttribute("aria-label", "Homework grade axis");
      yAxisSvg.innerHTML = "";
    }

    const NS = "http://www.w3.org/2000/svg";
    const appendChart = (name, attributes) => {
      const element = document.createElementNS(NS, name);
      Object.entries(attributes).forEach(([key, value]) => {
        element.setAttribute(key, String(value));
      });
      chartSvg.appendChild(element);
      return element;
    };
    const appendAxis = yAxisSvg
      ? (name, attributes) => {
          const element = document.createElementNS(NS, name);
          Object.entries(attributes).forEach(([key, value]) => {
            element.setAttribute(key, String(value));
          });
          yAxisSvg.appendChild(element);
          return element;
        }
      : null;

    const xScale = (index) => index * pointSpacing;
    const yScale = (grade) => {
      const ratio = (grade - yMin) / (yMax - yMin);
      return paddingTop + (1 - ratio) * plotHeight;
    };
    const yTop = yScale(yMax);
    const yBottom = yScale(yMin);
    const clampY = (value) => Math.min(yBottom, Math.max(yTop, value));

    const points = scores.map((score, index) => ({
      x: xScale(index),
      y: yScale(score),
    }));

    const toSmoothPath = (pts) => {
      if (!pts.length) {
        return "";
      }
      if (pts.length === 1) {
        return `M ${pts[0].x} ${pts[0].y}`;
      }

      let d = `M ${pts[0].x} ${pts[0].y}`;
      for (let i = 0; i < pts.length - 1; i += 1) {
        const p0 = pts[i - 1] || pts[i];
        const p1 = pts[i];
        const p2 = pts[i + 1];
        const p3 = pts[i + 2] || p2;

        const cp1x = p1.x + (p2.x - p0.x) / 6;
        const cp1y = clampY(p1.y + (p2.y - p0.y) / 6);
        const cp2x = p2.x - (p3.x - p1.x) / 6;
        const cp2y = clampY(p2.y - (p3.y - p1.y) / 6);
        d += ` C ${cp1x} ${cp1y} ${cp2x} ${cp2y} ${p2.x} ${p2.y}`;
      }
      return d;
    };

    appendChart("rect", {
      x: 0,
      y: 0,
      width: fullWidth,
      height: fullHeight,
      fill: "#ffffff",
    });
    if (appendAxis) {
      appendAxis("rect", {
        x: 0,
        y: 0,
        width: axisWidth,
        height: fullHeight,
        fill: "#ffffff",
      });
    }

    for (let grade = yMin; grade <= yMax; grade += 1) {
      const y = yScale(grade);
      appendChart("line", {
        x1: 0,
        y1: y,
        x2: fullWidth - paddingRight,
        y2: y,
        stroke: "#e2e8f0",
        "stroke-width": 1,
      });
      if (appendAxis) {
        appendAxis("text", {
          x: axisWidth - 8,
          y: y + 4,
          "text-anchor": "end",
          fill: "#64748b",
          "font-size": 11,
        }).textContent = String(grade);
      }
    }

    if (appendAxis) {
      appendAxis("line", {
        x1: axisWidth - 1,
        y1: paddingTop,
        x2: axisWidth - 1,
        y2: fullHeight - paddingBottom,
        stroke: "#111827",
        "stroke-width": 1.2,
      });
    }

    appendChart("line", {
      x1: 0,
      y1: paddingTop,
      x2: 0,
      y2: fullHeight - paddingBottom,
      stroke: "#111827",
      "stroke-width": 1.2,
    });
    appendChart("line", {
      x1: 0,
      y1: fullHeight - paddingBottom,
      x2: fullWidth - paddingRight,
      y2: fullHeight - paddingBottom,
      stroke: "#111827",
      "stroke-width": 1.2,
    });

    const maxLabelChars = Math.max(2, `L${labels.length}`.length);
    const computedLabelFontSize = Math.floor((pointSpacing * 0.9) / (maxLabelChars * 0.56));
    const labelFontSize = Math.max(6, Math.min(9, computedLabelFontSize));

    labels.forEach((label, index) => {
      appendChart("text", {
        x: xScale(index),
        y: fullHeight - paddingBottom + 16,
        "text-anchor": "middle",
        fill: "#64748b",
        "font-size": labelFontSize,
      }).textContent = label;
    });

    const linePath = toSmoothPath(points);
    const baselineY = fullHeight - paddingBottom;
    const firstPoint = points[0];
    const lastPoint = points[points.length - 1];
    const areaPath = `${linePath} L ${lastPoint.x} ${baselineY} L ${firstPoint.x} ${baselineY} Z`;

    const defs = appendChart("defs", {});
    const gradient = document.createElementNS(NS, "linearGradient");
    gradient.setAttribute("id", "homeworkAreaGradientMain");
    gradient.setAttribute("x1", "0");
    gradient.setAttribute("y1", "0");
    gradient.setAttribute("x2", "0");
    gradient.setAttribute("y2", "1");
    const stopTop = document.createElementNS(NS, "stop");
    stopTop.setAttribute("offset", "0%");
    stopTop.setAttribute("stop-color", "rgba(17,24,39,0.38)");
    const stopBottom = document.createElementNS(NS, "stop");
    stopBottom.setAttribute("offset", "100%");
    stopBottom.setAttribute("stop-color", "rgba(17,24,39,0.04)");
    gradient.appendChild(stopTop);
    gradient.appendChild(stopBottom);
    defs.appendChild(gradient);

    appendChart("path", {
      d: areaPath,
      fill: "url(#homeworkAreaGradientMain)",
      stroke: "none",
    });

    appendChart("path", {
      d: linePath,
      fill: "none",
      stroke: "#111827",
      "stroke-width": 3,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    });
  }

  function initCharts() {
    try {
      if (hasChartLibrary) {
        createExamResultsChart();
        createAttendanceChart();
      }
      createHomeworkChart();
    } catch (_error) {
      const chartNodes = document.querySelectorAll("canvas, svg");
      chartNodes.forEach((node) => showChartMessage(node, "Failed to render chart data."));
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCharts, { once: true });
    return;
  }

  window.setTimeout(initCharts, 0);
})();
