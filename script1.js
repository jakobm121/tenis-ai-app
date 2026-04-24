const sportIcons = {
  football: "⚽",
  basketball: "🏀",
  tennis: "🎾",
  hockey: "🏒",
  baseball: "⚾"
};

// ------------------------
// LOAD DATA
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
// CONFIDENCE LOGIC
// ------------------------
function getConfidenceLabel(conf) {
  if (conf < 60) return { text: "Medium", class: "medium" };
  if (conf < 75) return { text: "Strong", class: "strong" };
  return { text: "Very Strong", class: "very-strong" };
}

function getUnits(conf) {
  if (conf < 50) return "0.5u";
  if (conf < 75) return "1u";
  if (conf < 90) return "2u";
  return "3u";
}

// ------------------------
// RENDER
// ------------------------
function renderPredictions(data) {
  const container = document.getElementById("predictions-container");
  if (!container) return;

  container.innerHTML = "";

  data.forEach((p, index) => {
    const label = getConfidenceLabel(p.confidence);
    const units = getUnits(p.confidence);

    const card = document.createElement("div");
    card.classList.add("prediction-card");

    card.innerHTML = `
      <div class="prediction-meta">
        <span>📅 ${p.date}</span>
        <span>${sportIcons[p.sport] || "⚽"} ${p.sport.charAt(0).toUpperCase() + p.sport.slice(1)}</span>
        <span>🏆 ${p.league}</span>
      </div>

      <h3>${p.match}</h3>

      <p class="bet-type">🎯 ${p.bet}</p>

      <div style="margin-top:10px;">
        <span class="badge ${label.class}">🔥 ${label.text}</span>
        <span class="badge units-badge">💰 ${units}</span>
      </div>

      <div class="ai-reasoning">
        <p><strong>AI Analysis:</strong> ${p.reasoning}</p>
      </div>

      <canvas id="chart${index}"></canvas>

      <a href="https://stzns.lynmonkel.com/?mid=309891_1838278"
         class="cta-btn" target="_blank">
         Check Best Odds 🔥
      </a>
    `;

    container.appendChild(card);

    // CHART
    new Chart(document.getElementById(`chart${index}`), {
      type: 'doughnut',
      data: {
        labels: ['Confidence', 'Risk'],
        datasets: [{
          data: [p.confidence, 100 - p.confidence],
          backgroundColor: ['#28a745', '#e0e0e0'],
          borderWidth: 0
        }]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        cutout: '75%'
      }
    });
  });
}

// ------------------------
// INIT
// ------------------------
loadPredictions();

// ------------------------
// PROFIT CHART (unchanged)
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
// TOGGLE HOW WE PLAY
// ------------------------
const title = document.getElementById('howWePlayTitle');
const content = document.getElementById('howWePlayContent');

if (title && content) {
  title.addEventListener('click', () => {
    content.classList.toggle('hidden');
  });
}
