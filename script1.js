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
    date: "14 Oct 2025",
    sport: "football",
    league: "World cup - Quali",
    match: "Ireland vs Armenia",
    bet: "Under 2.5 odd@ 2",
    confidence: 70
  },
  {
    date: "14 Oct 2025",
    sport: "football",
    league: "Euro U21 - Quali",
    match: "Austria U21 UTD vs Wales U21",
    bet: "Handicap -1.5  odd@ 1.82",
    confidence: 82
  },
  {
    date: "14 Oct 2025",
    sport: "basketball",
    league: "Eurocup",
    match: "Cedevita Olimpija vs Aris",
    bet: "2 handicap +4.5 odd@ 1.75",
    confidence: 63
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
