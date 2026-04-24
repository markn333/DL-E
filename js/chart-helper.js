// chart-helper.js - Chart.js wrapper
const ChartHelper = {
  historyChart: null,
  weaknessChart: null,

  renderHistoryChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const history = Storage.getHistory();
    if (history.length === 0) {
      ctx.parentElement.innerHTML = '<p style="color:#6b7280;text-align:center;padding:20px">まだ学習履歴がありません</p>';
      return;
    }

    const labels = history.map((h, i) => {
      const d = new Date(h.date);
      return `${d.getMonth() + 1}/${d.getDate()}`;
    });
    const data = history.map(h => h.percent);

    if (this.historyChart) this.historyChart.destroy();

    this.historyChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '正解率 (%)',
          data,
          borderColor: '#1a56db',
          backgroundColor: 'rgba(26, 86, 219, 0.1)',
          fill: true,
          tension: 0.3,
          pointBackgroundColor: '#1a56db',
          pointRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: { callback: v => v + '%' },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => `${ctx.parsed.y}%`
            }
          }
        }
      }
    });
  },

  renderWeaknessChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const stats = Storage.getWrongStats();
    const questions = Quiz.questions;

    // Build category stats
    const catStats = {};
    for (const q of questions) {
      const s = stats[q.id];
      if (!s) continue;
      if (!catStats[q.category]) {
        catStats[q.category] = { attempts: 0, correct: 0 };
      }
      catStats[q.category].attempts += s.attempts;
      catStats[q.category].correct += (s.attempts - s.wrong);
    }

    const entries = Object.entries(catStats).filter(([, s]) => s.attempts > 0);
    if (entries.length === 0) {
      ctx.parentElement.innerHTML = '<p style="color:#6b7280;text-align:center;padding:20px">まだ学習データがありません</p>';
      return;
    }

    const labels = entries.map(([cat]) => cat);
    const data = entries.map(([, s]) => Math.round(s.correct / s.attempts * 100));

    if (this.weaknessChart) this.weaknessChart.destroy();

    this.weaknessChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: '正解率 (%)',
          data,
          backgroundColor: data.map(v => v >= 70 ? '#16a34a' : v >= 50 ? '#f59e0b' : '#dc2626'),
          borderRadius: 6,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            min: 0,
            max: 100,
            ticks: { callback: v => v + '%' },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => `${ctx.parsed.x}%`
            }
          }
        }
      }
    });
  },
};
