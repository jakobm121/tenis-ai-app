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
    date: "19 Sep 2025",
    sport: "football",
    league: "Premier League",
    match: "Manchester City vs Arsenal",
    bet: "Over 2.5 Goals",
    confidence: 78
  },
  {
    date: "19 Sep 2025",
    sport: "basketball",
    league: "EuroLeague",
    match: "Real Madrid vs Fenerbahce",
    bet: "Real Madrid -5.5",
    confidence: 65
  },
  {
    date: "19 Sep 2025",
    sport: "tennis",
    league: "ATP Tour",
    match: "Djokovic vs Alcaraz",
    bet: "Djokovic to Win",
    confidence: 72
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
      <p class="bet-type">Bet: ${p.bet}</p>
      <canvas id="chart${index}"></canvas>
      <p class="confidence-label">Confidence</p>
      <a href="reviews.html" class="btn">Bet with Bonus</a>
    `;

    container.appendChild(card);

    // Ustvarimo graf
    new Chart(document.getElementById(`chart${index}`), {
      type: 'doughnut',
      data: {
        labels: ['Confidence', 'Other'],
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