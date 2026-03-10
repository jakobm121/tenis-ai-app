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
    date: "10 Mar 2026",
    sport: "football",
    league: "Champions League",
    match: "Newcastle - Barcelona",
    bet: "Draw no bet 2 @ 1.80",
    confidence: 70
  },
  {
    date: "10 Mar 2026",
    sport: "football",
    league: "Champions League",
    match: "Atletico (M) - Tottenham",
    bet: "Under 2.5 odd@ 1.90",
    confidence: 55
  },
  {
    date: "10 Mar 2026",
    sport: "football",
    league: "Champions League",
    match: "Atalanta - Bayern M.",
    bet: " BTTS odd@ 1.55",
    confidence: 60
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
      <a href="https://tracker.bet-at-home.com/link?btag=99940614_467104" class="btn">Claim 100% Bonus ✅</a>
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

const ctx = document.getElementById('profitChart').getContext('2d');
new Chart(ctx, {
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
      fill: true,
      pointRadius: 5,
      pointBackgroundColor: '#ffd700'
    }]
  },
  options: {
    plugins: {
      legend: { display: false }
    },
    scales: {
      x: {
        ticks: { color: '#fff' },
        grid: { color: 'rgba(255,255,255,0.1)' }
      },
      y: {
        ticks: { color: '#fff', callback: value => value + '%' },
        grid: { color: 'rgba(255,255,255,0.1)' }
      }
    }
  }
});

const howWePlayTitle = document.getElementById('howWePlayTitle');
const howWePlayContent = document.getElementById('howWePlayContent');

if (howWePlayTitle && howWePlayContent) {
  howWePlayTitle.addEventListener('click', () => {
    howWePlayContent.classList.toggle('hidden');
  });
}
