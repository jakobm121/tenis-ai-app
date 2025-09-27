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
    date: "27 Sep 2025",
    sport: "football",
    league: "First Slovenian League",
    match: "Celje - Maribor",
    bet: " 1 @ 1.60",
    confidence: 90
  },
  {
    date: "27 Sep 2025",
    sport: "football",
    league: "La Liga",
    match: "Atletico Madrid - Real Madrid",
    bet: "Draw no bet 2 @ 1.60",
    confidence:80
  },
  {
    date: "27 Sep 2025",
    sport: "football",
    league: "Premier League",
    match: "Chelsea - Brighton",
    bet: "bet builder 💉: " 1,BTTS,Over2,5, @ 3.50"
    confidence: 80
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
      <a href="reviews.html" class="btn">💰Bet with Bonus</a>
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
