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
    date: "15 Oct 2025",
    sport: "tennis",
    league: "WTA - Ningbo",
    match: "Tomljanovic A. vs Sonmez Z.",
    bet: "2 odd@ 2.10",
    confidence: 75
  },
  {
    date: "15 Oct 2025",
    sport: "tennis",
    league: "ATP - Stockholm",
    match: "De Jong J. vs Fucsovics M.",
    bet: "2 odd@ 1.55",
    confidence: 82
  },
  {
    date: "15 Oct 2025",
    sport: "basketball",
    league: "Eurocup",
    match: "Panionios vs JL Bourg",
    bet: "2 Handicap -3.5 odd@ 1.90",
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
      <p class="bet-type">Bet: ${p.bet}</p>
      <canvas id="chart${index}"></canvas>
      <p class="confidence-label">Confidence by AI77</p>
      <a href="https://stzns.naralvin.com/?mid=309891_1835232" class="btn">Claim 100% Bonus ✅</a>
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
