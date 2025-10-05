ko// Ikone za športe
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
    date: "05 Oct 2025",
    sport: "football",
    league: "La Liga",
    match: "Celta Vigo - Atletico Madrid",
    bet: " 2 @ 1.80",
    confidence: 65
  },
  {
    date: "05 Oct 2025",
    sport: "football",
    league: "1. Slovenian League",
    match: "Radomlje - Celje",
    bet: " -1.5 handicap 2 @ 1.75",
    confidence: 65
  },
  {
    date: "05 Oct 2025",
    sport: "football",
    league: "La Liga",
    match: "Sevilla  - Barcelona",
    bet: "BB 💉 Over 2.5 & GG & 2 @ 2.50",
    confidence: 50
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
