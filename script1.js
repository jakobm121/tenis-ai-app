const sportIcons = {
  football: "⚽",
  basketball: "🏀",
  tennis: "🎾",
  hockey: "🏒",
  baseball: "⚾"
};

// ------------------------
// LOAD PREDICTIONS + LAST UPDATED
// ------------------------
async function loadPredictions() {
  try {
    const response = await fetch('./predictions.json');
    const predictions = await response.json();

    renderPredictions(predictions);

    // 🔥 LAST UPDATED (PRAVILNO - CURRENT TIME)
    const now = new Date();

    const formatted =
      now.toLocaleDateString('en-GB') +
      " • " +
      now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const el = document.getElementById("last-updated");
    if (el) el.innerText = "Updated • " + formatted;

  } catch (error) {
    console.error("Error loading predictions!", error);
  }
}

// ------------------------
// CONFIDENCE SYSTEM
// ------------------------
function getConfidenceData(conf) {
  if (conf < 60) {
    return {
      label: "🟡 Medium",
      units: "💸 1u",
      color: "#ffc107"
    };
  }

  if (conf < 75) {
    return {
      label: "🟢 Strong",
      units: "💸 1.5u",
      color: "#28a745"
    };
  }

  return {
    label: "🔥 Very Strong",
    units: "💸 2u",
    color: "#d4af37"
  };
}

// ------------------------
// TIME UNTIL MATCH
// ------------------------
function getKickoffStatus(time) {
  if (!time) return "";

  const now = new Date();
  const [h, m] = time.split(":");

  const matchTime = new Date();
  matchTime.setHours(h, m, 0);

  const diff = (matchTime - now) / 60000;

  if (diff < 0) return "";
  if (diff < 60) return `⏰ Starts in ${Math.floor(diff)} min`;
  if (diff < 180) return `🕒 Starts in ${Math.floor(diff / 60)}h`;

  return "";
}

// ------------------------
// RENDER CARDS
// ------------------------
function renderPredictions(data) {
  const container = document.getElementById("predictions-container");
  if (!container) return;

  container.innerHTML = "";

  data.forEach((p, index) => {
    const conf = getConfidenceData(p.confidence);
    const kickoff = getKickoffStatus(p.time);

    const card = document.createElement("div");
    card.classList.add("prediction-card");

    card.innerHTML = `
      <div class="prediction-meta">
        <span>📅 ${p.date}</span>
        <span>🕒 ${p.time || "?"}</span>
        <span>${sportIcons[p.sport] || "❓"} ${p.sport.charAt(0).toUpperCase() + p.sport.slice(1)}</span>
        <span>🏆 ${p.league}</span>
      </div>

      <h3>${p.match}</h3>

      <p class="bet-type">Tip: ${p.bet}</p>

      ${kickoff ? `<p class="kickoff">${kickoff}</p>` : ""}

      <div class="ai-reasoning">
        <p><strong>AI Analysis:</strong> ${p.reasoning}</p>
      </div>

      <canvas id="chart${index}"></canvas>

      <p class="confidence-label" style="color:${conf.color}">
        ${conf.label} • ${conf.units}
      </p>

      <a href="https://stzns.lynmonkel.com/?mid=309891_1838278" class="btn">
        Check Best Odds 💥
      </a>
    `;

    container.appendChild(card);

    new Chart(document.getElementById(`chart${index}`), {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [p.confidence, 100 - p.confidence],
          backgroundColor: [conf.color, '#e0e0e0'],
          borderWidth: 0
        }]
      },
      options: {
        cutout: '75%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        }
      }
    });
  });
}

// ------------------------
// STATS + REAL PROFIT CHART
// ------------------------
async function loadStats() {
  try {
    const res = await fetch('./results.json');
    const data = await res.json();

    let total = 0;
    let wins = 0;
    let profit = 0;
    let totalStaked = 0;
    let avgOddsSum = 0;
    let avgOddsCount = 0;

    const dailyProfit = {};

    data.forEach(p => {
      if (p.result === "pending") return;

      let units = 1;
      if (p.confidence >= 75) units = 2;
      else if (p.confidence >= 60) units = 1.5;

      total++;

      if (typeof p.odds === "number") {
        avgOddsSum += p.odds;
        avgOddsCount++;
      }

      let pickProfit = 0;

      if (p.result === "win") {
        wins++;
        totalStaked += units;

        if (typeof p.odds === "number") {
          pickProfit = (p.odds - 1) * units;
        } else {
          pickProfit = units;
        }

      } else if (p.result === "loss") {
        totalStaked += units;
        pickProfit = -units;

      } else if (p.result === "storno") {
        pickProfit = 0;
      }

      profit += pickProfit;

      const dateKey = p.date || "Unknown";
      if (!dailyProfit[dateKey]) dailyProfit[dateKey] = 0;
      dailyProfit[dateKey] += pickProfit;
    });

    const roi = totalStaked > 0 ? ((profit / totalStaked) * 100).toFixed(1) : 0;
    const avgOdds = avgOddsCount > 0 ? (avgOddsSum / avgOddsCount).toFixed(2) : "0.00";

    if (total > 0) {
      document.querySelector(".stat-box:nth-child(1) h3").innerText = total;
      document.querySelector(".stat-box:nth-child(2) h3").innerText = wins;
      document.querySelector(".stat-box:nth-child(3) h3").innerText = avgOdds;
      document.querySelector(".stat-box:nth-child(4) h3").innerText = roi + "%";
    }

    // ------------------------
    // REAL PROFIT CHART
    // ------------------------
    const profitCtx = document.getElementById('profitChart');

    if (profitCtx) {
      const sortedDates = Object.keys(dailyProfit).sort();

      let runningProfit = 0;
      const labels = [];
      const values = [];

      sortedDates.forEach(date => {
        runningProfit += dailyProfit[date];
        labels.push(date);
        values.push(Number(runningProfit.toFixed(2)));
      });

      if (window.profitChartInstance) {
        window.profitChartInstance.destroy();
      }

      window.profitChartInstance = new Chart(profitCtx.getContext('2d'), {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Profit Growth (Units)',
            data: values,
            borderColor: '#ffd700',
            backgroundColor: 'rgba(255, 215, 0, 0.15)',
            borderWidth: 3,
            tension: 0.3,
            fill: true
          }]
        },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            x: {
              ticks: { color: '#fff' },
              grid: { color: 'rgba(255,255,255,0.1)' }
            },
            y: {
              ticks: { color: '#fff' },
              grid: { color: 'rgba(255,255,255,0.1)' }
            }
          }
        }
      });
    }

  } catch (e) {
    console.log("Stats error", e);
  }
}

// ------------------------
// TOGGLE HOW WE PLAY
// ------------------------
const title = document.getElementById('howWePlayTitle');
const content = document.getElementById('howWePlayContent');

if (title && content) {
  title.addEventListener('click', () => {
    content.classList.toggle('hidden');
  });
}

// ------------------------
// RUN
// ------------------------
loadPredictions();
loadStats();
