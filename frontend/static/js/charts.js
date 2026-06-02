/* Admin dashboard analytics (Chart.js). Data from window.CHART_DATA. */
(function () {
  const data = window.CHART_DATA;
  if (!data || typeof Chart === "undefined") return;

  const GREEN = "#228b4a";
  const GRAY = "#e5e7eb";
  const BLUE = "#2563eb";
  const t = (k, fb) => (typeof I18n !== "undefined" && I18n.t(k) !== k) ? I18n.t(k) : fb;

  Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
  Chart.defaults.color = "#4b5563";

  // Donut — acknowledged vs not (relative to AD total)
  const donut = document.getElementById("chart-donut");
  if (donut) {
    new Chart(donut, {
      type: "doughnut",
      data: {
        labels: [t("chart_ack", "Tanishgan"), t("chart_not_ack", "Tanishmagan")],
        datasets: [{
          data: [data.donut.ack, data.donut.not_ack],
          backgroundColor: [GREEN, GRAY],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "65%",
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  // Bar — acknowledged users per department
  const dept = document.getElementById("chart-dept");
  if (dept) {
    new Chart(dept, {
      type: "bar",
      data: {
        labels: data.dept.labels,
        datasets: [{
          label: t("chart_ack", "Tanishgan"),
          data: data.dept.data,
          backgroundColor: GREEN,
          borderRadius: 4,
          maxBarThickness: 38,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  // Line — daily acknowledgements (30 days)
  const daily = document.getElementById("chart-daily");
  if (daily) {
    new Chart(daily, {
      type: "line",
      data: {
        labels: data.daily.labels,
        datasets: [{
          label: t("chart_ack", "Tanishgan"),
          data: data.daily.data,
          borderColor: BLUE,
          backgroundColor: "rgba(37,99,235,.12)",
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }
})();
