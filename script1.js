// Ikone za športe
const sportIcons = {
  football: "⚽",
  basketball: "🏀",
  tennis: "🎾",
  hockey: "🏒",
  baseball: "⚾"
};

// Definicija analiz
const predictions = [
  {
    date: "30 Sep 2025",
    sport: "football",
    league: "UEFA Champions League",
    match: "Bodø/Glimt -Tottenham",
    bet: " Draw no bet 2 @ 1.55",
    confidence: 66
  },
  {
    date: "30 Sep 2025",
    sport: "football",
    league: "UEFA Champions League",
    match: "FC Kairat - Real Madrid",
    bet: "Under 4.5 @ 1.55",
    confidence:65
  },
  {
    date: "30 Sep 2025",
    sport: "football",
    league: "UEFA Champions League",
    match: "Medvedev - Zverev",
    bet: "BET BUILDER 🔥 1•Over 3.5•GG @ 3.35",
    confidence: 40
  }
];

// Render funkcija
function renderPredictions() {
  const container = document.getElementById("predictions-container");
  container.innerHTML = "";

  predictions.forEach((p, index) => {
    const card = document.createElement("div");
    card.classList.add("prediction-card");

    card.innerHTML = `
      <div class="prediction-meta">
        <span>📅 ${p.date}</span>
        <span>${sportIcons[p.sport] || "❓"} ${p.sport.charAt(0).toUpperCase() + p.sport.slice(1)}</span>
        <span>🏆 ${p.league}</span>
      </div>
      <h3>${p.match}</h3>
      <p class="bet-type">🎯Bet: ${p.bet}</p>
      <canvas id="chart${index}"></canvas>
      <p class="confidence-label">AI77 Confidence %</p>
      <a href="https://stzns.naralvin.com/?mid=309891_1835232" class="btn">💰Grab 100% Bonus!</a>
    `;

    container.appendChild(card);

    // Ustvarimo graf
    new Chart(document.getElementById(`chart${index}`), {
      type: 'doughnut',
      data: {
        labels: ['Confidence by AI77', 'Other'],
        datasets: [{
          data: [p.confidence, 100 - p.confidence],
          backgroundColor: ['#28a745', '#e0e0e0']
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        cutout: '70%'
      }
    });
  });
}

// Zaženi render
renderPredictions();
