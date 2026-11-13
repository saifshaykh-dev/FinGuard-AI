function makeActivityChart(id, labels, values) {
  const el = document.getElementById(id);
  if (!el || typeof Chart === "undefined") return;
  new Chart(el, {
    type: "line",
    data: { labels, datasets: [{ data: values, borderColor: "#48d5c3",
      backgroundColor: "rgba(72,213,195,.10)", fill: true, tension: .38,
      pointRadius: 3, pointBackgroundColor: "#48d5c3", borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { grid: { display: false }, ticks: { color: "#8495b1", font: { size: 9 } } },
        y: { beginAtZero: true, grid: { color: "rgba(130,150,180,.10)" },
          ticks: { color: "#8495b1", precision: 0, font: { size: 9 } } } } }
  });
}
function makeRiskChart(id, labels, values) {
  const el = document.getElementById(id);
  if (!el || typeof Chart === "undefined") return;
  new Chart(el, {
    type: "doughnut",
    data: { labels, datasets: [{ data: values,
      backgroundColor: ["#52d6a1", "#f4bd5d", "#ff7185"],
      borderColor: "#111b30", borderWidth: 4, hoverOffset: 5 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: "76%",
      plugins: { legend: { display: false } } }
  });
}
