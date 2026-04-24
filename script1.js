const sportIcons = {
  football: "⚽",
  basketball: "🏀",
  tennis: "🎾",
  hockey: "🏒",
  baseball: "⚾"
};

// ------------------------
// LOAD PREDICTIONS
// ------------------------
async function loadPredictions() {
  try {
    const response = await fetch('./predictions.json');
    const predictions = await response.json();
    renderPredictions(predictions);
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

    // CHART
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
// STATS (fake until real)
// ------------------------
async function loadStats() {
  try {
    const res = await fetch('./results.json');
    const data = await res.json();

    let total = 0;
    let wins = 0;
    let profit = 0;

    data.forEach(p => {
      if (p.result === "pending") return;

      total++;

      let units = 1;
      if (p.confidence >= 75) units = 2;
      else if (p.confidence >= 60) units = 1.5;

      if (p.result === "win") {
        wins++;
        profit += units;
      } else {
        profit -= units;
      }
    });

    const roi = total ? ((profit / total) * 100).toFixed(1) : 0;

    if (total > 10) {
      document.querySelector(".stat-box:nth-child(1) h3").innerText = total;
      document.querySelector(".stat-box:nth-child(2) h3").innerText = wins;
      document.querySelector(".stat-box:nth-child(4) h3").innerText = roi + "%";
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
// PROFIT CHART (tvoj graf ostane)
// ------------------------
const profitCtx = document.getElementById('profitChart');

if (profitCtx) {
  new Chart(profitCtx.getContext('2d'), {
    type: 'line',
    data: {
      labels: ['Sep 1', 'Sep 5', 'Sep 10', 'Sep 15', 'Sep 20', 'Sep 25', 'Sep 30'],
      datasets: [{
        label: 'Profit Growth (%)',
        data: [0, 2.3, 3.5, 4.1, 5.8, 6.3, 7.2],
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
        x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
        y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }
      }
    }
  });
}

// ------------------------
// RUN
// ------------------------
loadPredictions();
loadStats();
