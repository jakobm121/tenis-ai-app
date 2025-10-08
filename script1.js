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
    date: "07 Oct 2025",
    sport: "football",
    league: "World cup U-20",
    match: "Ukraine u20 vs Spain u20",
    bet: "2 @ 1.58",
    confidence: 88
  },
  {
    date: "07 Oct 2025",
    sport: "football",
    league: "W Champions League",
    match: "Barcelona W vs Bayern W",
    bet: "Over 3.50 @ 1.65",
    confidence: 88
  },
  {
    date: "07 Oct 2025",
    sport: "football",
    league: "W Champions League",
    match: "Juventus W vs Benfica W",
    bet: "1 @ 1.50",
    confidence: 90
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
