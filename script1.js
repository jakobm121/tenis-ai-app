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
// CONFIDENCE + UNITS SYSTEM (FINAL)
// ------------------------
function getConfidenceData(conf) {
  if (conf < 60) {
    return {
      label: "🟡 Medium",
      units: "1u"
    };
  }

  if (conf < 75) {
    return {
      label: "🟢 Strong",
      units: "1.5u"
    };
  }

  return {
    label: "🔥 Very Strong",
    units: "2u"
  };
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

      <p class="bet-type">Bet: ${p.bet}</p>

      <div class="ai-reasoning">
        <p><strong>AI Analysis:</strong> ${p.reasoning}</p>
      </div>

      <p class="confidence-label">${conf.label} • ${conf.units}</p>

      <a href="https://stzns.lynmonkel.com/?mid=309891_1838278" class="btn">Claim Bonus ✅</a>
    `;

    container.appendChild(card);
  });
}

// ------------------------
// LOAD STATS
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

    document.querySelector(".stat-box:nth-child(1) h3").innerText = total;
    document.querySelector(".stat-box:nth-child(2) h3").innerText = wins;
    document.querySelector(".stat-box:nth-child(4) h3").innerText = roi + "%";

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
