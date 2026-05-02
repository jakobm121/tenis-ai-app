const sportIcons = {
  football: "⚽",
  basketball: "🏀",
  tennis: "🎾",
  hockey: "🏒",
  baseball: "⚾"
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getConfidenceData(confidence) {
  const conf = Number(confidence || 0);

  if (conf < 51) {
    return {
      label: "🟡 Research",
      units: "💸 0.5u",
      color: "#ffc107"
    };
  }

  if (conf < 76) {
    return {
      label: "🟢 Strong",
      units: "💸 1u",
      color: "#28a745"
    };
  }

  if (conf < 100) {
    return {
      label: "🔥 Very Strong",
      units: "💸 2u",
      color: "#d4af37"
    };
  }

  return {
    label: "🏆 Elite",
    units: "💸 3u",
    color: "#e74c3c"
  };
}

function getKickoffStatus(date, time) {
  if (!date || !time) return "";

  const matchTime = new Date(`${date}T${time}:00`);
  if (Number.isNaN(matchTime.getTime())) return "";

  const now = new Date();
  const diff = (matchTime - now) / 60000;

  if (diff < 0) return "";
  if (diff < 60) return `⏰ Starts in ${Math.floor(diff)} min`;
  if (diff < 180) return `🕒 Starts in ${Math.floor(diff / 60)}h`;

  return "";
}

async function loadPredictions() {
  try {
    const response = await fetch("./predictions.json?v=" + Date.now());
    const predictions = await response.json();

    renderPredictions(Array.isArray(predictions) ? predictions : []);

    const now = new Date();
    const formatted =
      now.toLocaleDateString("en-GB") +
      " • " +
      now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const el = document.getElementById("last-updated");
    if (el) el.innerText = "Updated • " + formatted;

  } catch (error) {
    console.error("Error loading predictions!", error);

    const container = document.getElementById("predictions-container");
    if (container) {
      container.innerHTML = `
        <div class="prediction-card">
          <h3>No predictions available</h3>
          <p>Predictions will appear here when the model publishes new picks.</p>
        </div>
      `;
    }
  }
}

function renderPredictions(data) {
  const container = document.getElementById("predictions-container");
  if (!container) return;

  container.innerHTML = "";

  if (!data.length) {
    container.innerHTML = `
      <div class="prediction-card">
        <h3>No active predictions</h3>
        <p>The model did not publish picks for the current window.</p>
      </div>
    `;
    return;
  }

  const avgOdds =
    data.reduce((sum, p) => sum + Number(p.odds || 0), 0) / Math.max(data.length, 1);

  const avgConfidence =
    data.reduce((sum, p) => sum + Number(p.confidence || p.confidence_score || 0), 0) /
    Math.max(data.length, 1);

  const board = document.createElement("div");
  board.classList.add("prediction-card", "board-card");

  board.innerHTML = `
    <h3>AI77 Filtered Board</h3>
    <p class="league">Today’s model-qualified picks</p>

    <div class="board-stats">
      <div>
        <strong>${data.length}</strong>
        <span>Picks</span>
      </div>
      <div>
        <strong>${avgOdds.toFixed(2)}</strong>
        <span>Avg Odds</span>
      </div>
      <div>
        <strong>${avgConfidence.toFixed(0)}/100</strong>
        <span>Avg Rating</span>
      </div>
    </div>

    <p>
      No forced picks. Each selection must pass form, league, odds and bookmaker filters.
    </p>
  `;

  container.appendChild(board);

  data.forEach((p, index) => {
    const confidence = Number(p.confidence || p.confidence_score || 0);
    const conf = getConfidenceData(confidence);
    const kickoff = getKickoffStatus(p.date, p.time);

    const sport = p.sport || "football";
    const league = p.league || "Football";
    const match = p.match || "Unknown match";
    const bet = p.bet || "Pick";
    const odds = Number(p.odds || 0);

    const reasoning =
      p.reasoning ||
      "This pick was selected by the AI77 model based on value, market odds and available match data.";

    const details = [];

    if (p.edge !== undefined && p.edge !== null) {
      details.push(`Edge ${(Number(p.edge) * 100).toFixed(1)}%`);
    }

    if (p.model_prob !== undefined && p.model_prob !== null) {
      details.push(`Model ${(Number(p.model_prob) * 100).toFixed(1)}%`);
    }

    if (p.bookmakers_used !== undefined && p.bookmakers_used !== null) {
      details.push(`${p.bookmakers_used} bookmakers`);
    }

    if (p.expected_total_goals !== undefined && p.expected_total_goals !== null) {
      details.push(`xG Total ${Number(p.expected_total_goals).toFixed(2)}`);
    }

    const card = document.createElement("div");
    card.classList.add("prediction-card");

    card.innerHTML = `
      <div class="prediction-meta">
        <span>📅 ${escapeHtml(p.date || "")}</span>
        <span>🕒 ${escapeHtml(p.time || "?")}</span>
        <span>${sportIcons[sport] || "⚽"} ${escapeHtml(String(sport).toUpperCase())}</span>
        <span>🏆 ${escapeHtml(league)}</span>
      </div>

      <h3>${escapeHtml(match)}</h3>

      <p class="bet-type">
        Tip: ${escapeHtml(bet)}${odds > 0 ? ` @ ${odds.toFixed(2)}` : ""}
      </p>

      ${kickoff ? `<p class="kickoff">${escapeHtml(kickoff)}</p>` : ""}

      ${details.length ? `<p class="league">${escapeHtml(details.join(" • "))}</p>` : ""}

      <div class="ai-reasoning">
        <p><strong>AI Analysis:</strong> ${escapeHtml(reasoning)}</p>
      </div>

      <canvas id="chart${index}"></canvas>

      <p class="confidence-label" style="color:${conf.color}">
        ${conf.label} • ${conf.units}
      </p>

      <a href="https://stzns.lynmonkel.com/?mid=309891_1838278" class="btn" target="_blank" rel="nofollow sponsored">
        Check Best Odds 💥
      </a>
    `;

    container.appendChild(card);

    const chartEl = document.getElementById(`chart${index}`);

    if (chartEl && typeof Chart !== "undefined") {
      new Chart(chartEl, {
        type: "doughnut",
        data: {
          datasets: [{
            data: [confidence, Math.max(0, 100 - confidence)],
            backgroundColor: [conf.color, "#e0e0e0"],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          cutout: "75%",
          plugins: {
            legend: { display: false },
            tooltip: { enabled: false }
          }
        }
      });
    }
  });
}

async function loadStats() {
  try {
    const res = await fetch("./results.json?v=" + Date.now());
    const rawData = await res.json();

    if (!Array.isArray(rawData)) {
      throw new Error("results.json is not an array");
    }

    const seen = new Set();
    const data = [];

    rawData.forEach(p => {
      if (!p || typeof p !== "object") return;

      const key =
        p.pick_id ||
        `${p.date || ""}|${p.time || ""}|${p.match || ""}|${p.bet || ""}`;

      if (seen.has(key)) return;
      seen.add(key);
      data.push(p);
    });

    let settled = 0;
    let wins = 0;
    let losses = 0;
    let voids = 0;

    let profit = 0;
    let totalStaked = 0;

    let avgOddsSum = 0;
    let avgOddsCount = 0;

    const dailyProfit = {};

    function getStake(p) {
      if (typeof p.stake === "number" && p.stake > 0) {
        return p.stake;
      }

      const conf = Number(p.confidence || p.confidence_score || 0);

      if (conf >= 76) return 2;
      if (conf >= 51) return 1;
      return 0.5;
    }

    data.forEach(p => {
      const result = String(p.result || "").toLowerCase();

      if (!["win", "loss", "storno", "void", "push"].includes(result)) {
        return;
      }

      const odds = Number(p.odds || 0);
      const stake = getStake(p);
      const dateKey = p.date || "Unknown";

      settled++;

      if (odds > 1) {
        avgOddsSum += odds;
        avgOddsCount++;
      }

      let pickProfit = 0;

      if (result === "win") {
        wins++;
        totalStaked += stake;
        pickProfit = odds > 1 ? (odds - 1) * stake : stake;
      } else if (result === "loss") {
        losses++;
        totalStaked += stake;
        pickProfit = -stake;
      } else {
        voids++;
        pickProfit = 0;
      }

      profit += pickProfit;

      if (!dailyProfit[dateKey]) dailyProfit[dateKey] = 0;
      dailyProfit[dateKey] += pickProfit;
    });

    const roi = totalStaked > 0 ? (profit / totalStaked) * 100 : 0;
    const avgOdds = avgOddsCount > 0 ? avgOddsSum / avgOddsCount : 0;

    const statTotal = document.getElementById("stat-total");
    const statWins = document.getElementById("stat-wins");
    const statAvgOdds = document.getElementById("stat-avg-odds");
    const statRoi = document.getElementById("stat-roi");
    const statsStatus = document.getElementById("stats-status");

    if (statTotal) statTotal.innerText = settled;
    if (statWins) statWins.innerText = wins;
    if (statAvgOdds) statAvgOdds.innerText = avgOdds.toFixed(2);
    if (statRoi) statRoi.innerText = `${roi >= 0 ? "+" : ""}${roi.toFixed(1)}%`;

    if (statsStatus) {
      if (settled === 0) {
        statsStatus.innerText = "📊 Statistics will appear after pending picks are settled.";
      } else {
        statsStatus.innerText =
          `📊 Settled: ${settled} • Wins: ${wins} • Losses: ${losses} • Void: ${voids} • Profit: ${profit >= 0 ? "+" : ""}${profit.toFixed(2)} units`;
      }
    }

    const profitCtx = document.getElementById("profitChart");

    if (!profitCtx || typeof Chart === "undefined") return;

    if (settled === 0) {
      profitCtx.style.display = "none";
      return;
    }

    profitCtx.style.display = "block";

    const sortedDates = Object.keys(dailyProfit).sort();

    let runningProfit = 0;
    const labels = [];
    const values = [];

    sortedDates.forEach(date => {
      runningProfit += dailyProfit[date];
      labels.push(date);
      values.push(Number(runningProfit.toFixed(2)));
    });

    if (window.profitChartInstance) {
      window.profitChartInstance.destroy();
    }

    window.profitChartInstance = new Chart(profitCtx.getContext("2d"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: "Profit Growth (Units)",
          data: values,
          borderColor: "#ffd700",
          backgroundColor: "rgba(255, 215, 0, 0.15)",
          borderWidth: 3,
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            ticks: { color: "#fff" },
            grid: { color: "rgba(255,255,255,0.1)" }
          },
          y: {
            ticks: { color: "#fff" },
            grid: { color: "rgba(255,255,255,0.1)" }
          }
        }
      }
    });

  } catch (e) {
    console.log("Stats error", e);

    const profitCtx = document.getElementById("profitChart");
    if (profitCtx) profitCtx.style.display = "none";

    const statsStatus = document.getElementById("stats-status");
    if (statsStatus) {
      statsStatus.innerText = "📊 Statistics will appear after settled picks are available.";
    }
  }
}

const title = document.getElementById("howWePlayTitle");
const content = document.getElementById("howWePlayContent");

if (title && content) {
  title.addEventListener("click", () => {
    content.classList.toggle("hidden");
  });
}

loadPredictions();
loadStats();
