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
// CONFIDENCE SYSTEM
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

function getStrengthBar(conf) {
  let bars = Math.round(conf / 10);
  let filled = "█".repeat(bars);
  let empty = "░".repeat(10 - bars);
  return filled + empty;
}

// ------------------------
// RENDER
// ------------------------
function renderPredictions(data) {
  const container = document.getElementById("predictions-container");
  if (!container) return;

  container.innerHTML = "";

  data.forEach((p) => {
    const label = getConfidenceLabel(p.confidence);
    const units = getUnits(p.confidence);
    const bar = getStrengthBar(p.confidence);

    const card = document.createElement("div");
    card.classList.add("prediction-card");

    card.innerHTML = `
      <div class="prediction-meta">
        <span>📅 ${p.date}</span>
        <span>${sportIcons[p.sport] || "⚽"} ${p.sport}</span>
        <span>🏆 ${p.league}</span>
      </div>

      <h3>${p.match}</h3>

      <p class="bet-type">🎯 ${p.bet}</p>

      <div class="badges">
        <span class="badge ${label.class}">🔥 ${label.text}</span>
        <span class="badge units-badge">💰 ${units}</span>
      </div>

      <div class="strength-box">
        <div class="strength-label">AI Strength</div>
        <div class="strength-bar">${bar}</div>
      </div>

      <div class="ai-reasoning">
        <p><strong>AI Analysis:</strong> ${p.reasoning}</p>
      </div>

      <a href="https://stzns.lynmonkel.com/?mid=309891_1838278"
         class="cta-btn" target="_blank">
         Check Best Odds 🔥
      </a>
    `;

    container.appendChild(card);
  });
}

// ------------------------
loadPredictions();

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
