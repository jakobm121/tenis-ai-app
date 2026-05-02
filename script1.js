const sportIcons = {
  football: "⚽",
  basketball: "🏀",
  tennis: "🎾",
  hockey: "🏒",
  baseball: "⚾"
};

function safeNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function getGrade(confidence) {
  const c = safeNumber(confidence);

  if (c >= 80) {
    return {
      label: "Top Rated",
      stake: 1.5,
      risk: "Medium",
      color: "#d4af37",
      className: "grade-top"
    };
  }

  if (c >= 70) {
    return {
      label: "Strong",
      stake: 1.25,
      risk: "Medium",
      color: "#28a745",
      className: "grade-strong"
    };
  }

  if (c >= 60) {
    return {
      label: "Standard",
      stake: 1.0,
      risk: "Medium-High",
      color: "#0077b6",
      className: "grade-standard"
    };
  }

  return {
    label: "Research",
    stake: 0.5,
    risk: "High",
    color: "#ffc107",
    className: "grade-research"
  };
}

function getKickoffStatus(dateStr, timeStr) {
  if (!dateStr || !timeStr) return "";

  const [year, month, day] = dateStr.split("-").map(Number);
  const [hours, minutes] = timeStr.split(":").map(Number);

  const now = new Date();
  const matchTime = new Date(year, month - 1, day, hours || 0, minutes || 0, 0, 0);
  const diffMinutes = Math.floor((matchTime - now) / 60000);

  if (diffMinutes <= 0) return "";
  if (diffMinutes < 60) return `⏰ Starts in ${diffMinutes} min`;
  if (diffMinutes < 180) return `🕒 Starts in ${Math.floor(diffMinutes / 60)}h`;

  return "";
}

function getMarketLabel(bucket, bet) {
  const b = String(bucket || "").toLowerCase();
  const tip = String(bet || "").toLowerCase();

  if (b.includes("over") || tip.includes("over")) return "Totals";
  if (b.includes("under") || tip.includes("under")) return "Totals";
  if (b === "home") return "Home Value";
  if (b === "away") return "Away Value";
  if (b === "draw") return "Draw Value";

  return "Value Pick";
}

function shortAnalysis(p) {
  const bet = String(p.bet || "");
  const bucket = String(p.bucket || "");
  const total = safeNumber(p.expected_total_goals, null);
  const edge = safeNumber(p.edge, 0) * 100;
  const books = safeNumber(p.bookmakers_used, 0);

  if (bucket.includes("over")) {
    return `The model projects this match above the market goal line, with a ${edge.toFixed(1)}% estimated value edge and support from ${books || "multiple"} bookmakers.`;
  }

  if (bucket.includes("under")) {
    return `The model projects a more controlled scoring profile than the current market line, with a ${edge.toFixed(1)}% estimated value edge.`;
  }

  if (bucket === "home" || bucket === "away") {
    return `${bet} is rated as a side-value position. The model sees a better win probability than the market price implies, with a ${edge.toFixed(1)}% estimated value edge.`;
  }

  if (total) {
    return `The model projection, market price and bookmaker support align strongly enough for this selection.`;
  }

  return p.reasoning || "This selection passed the AI77 value, form and bookmaker filters.";
}

async function loadMiniStats() {
  try {
    const res = await fetch("./results.json", { cache: "no-store" });
    const raw = await res.json();

    if (!Array.isArray(raw)) return null;

    const seen = new Set();
    const data = [];

    raw.forEach((p) => {
      if (!p) return;
      const key = p.pick_id || `${p.date}|${p.time}|${p.match}|${p.bet}|${p.odds}`;
      if (seen.has(key)) return;
      seen.add(key);
      data.push(p);
    });

    let total = data.length;
    let settled = 0;
    let pending = 0;
    let wins = 0;
    let profit = 0;
    let staked = 0;

    data.forEach((p) => {
      const result = p.result;
      const grade = getGrade(p.confidence);
      const stake = safeNumber(p.stake_units, safeNumber(p.stake, grade.stake));
      const odds = safeNumber(p.odds, 0);

      if (result === "pending") {
        pending++;
        return;
      }

      if (!["win", "loss", "storno"].includes(result)) return;

      settled++;

      if (result === "win") {
        wins++;
        staked += stake;
        profit += odds > 1 ? (odds - 1) * stake : stake;
      } else if (result === "loss") {
        staked += stake;
        profit -= stake;
      }
    });

    const hitRate = settled > 0 ? (wins / settled) * 100 : 0;
    const roi = staked > 0 ? (profit / staked) * 100 : 0;

    return {
      total,
      settled,
      pending,
      wins,
      hitRate,
      roi,
      profit
    };
  } catch (e) {
    return null;
  }
}

function renderMiniStats(stats) {
  const wrap = document.getElementById("mini-results-snapshot");
  if (!wrap) return;

  if (!stats) {
    wrap.innerHTML = `
      <div class="mini-results-card">
        <div>
          <span>AI77 Record</span>
          <strong>Starting fresh</strong>
        </div>
        <a href="results.html">View Results →</a>
      </div>
    `;
    return;
  }

  wrap.innerHTML = `
    <div class="mini-results-card">
      <div>
        <span>Settled Picks</span>
        <strong>${stats.settled}</strong>
      </div>
      <div>
        <span>Pending</span>
        <strong>${stats.pending}</strong>
      </div>
      <div>
        <span>Hit Rate</span>
        <strong>${stats.hitRate.toFixed(1)}%</strong>
      </div>
      <div>
        <span>Profit</span>
        <strong class="${stats.profit >= 0 ? "positive-text" : "negative-text"}">${stats.profit.toFixed(2)}u</strong>
      </div>
      <div>
        <span>ROI</span>
        <strong class="${stats.roi >= 0 ? "positive-text" : "negative-text"}">${stats.roi.toFixed(1)}%</strong>
      </div>
      <a href="results.html">Full Results →</a>
    </div>
  `;
}

async function loadPredictions() {
  try {
    const response = await fetch("./predictions.json", { cache: "no-store" });
    const predictions = await response.json();

    renderPredictions(Array.isArray(predictions) ? predictions : []);

    const stats = await loadMiniStats();
    renderMiniStats(stats);

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
        <article class="clean-board-empty">
          <h2>Predictions temporarily unavailable</h2>
          <p>Please check again shortly.</p>
        </article>
      `;
    }
  }
}

function renderPredictions(data) {
  const container = document.getElementById("predictions-container");
  if (!container) return;

  const predictions = [...data].sort((a, b) => {
    const ad = `${a.date || ""} ${a.time || ""}`;
    const bd = `${b.date || ""} ${b.time || ""}`;
    return ad.localeCompare(bd);
  });

  container.innerHTML = "";

  const intro = document.createElement("section");
  intro.className = "clean-board-header";

  if (!predictions.length) {
    intro.innerHTML = `
      <span>AI77 Filtered Board</span>
      <h2>No qualified picks right now</h2>
      <p>The model did not find enough value after odds, form, league and bookmaker filters.</p>
    `;
    container.appendChild(intro);
    return;
  }

  const avgOdds = predictions.reduce((s, p) => s + safeNumber(p.odds), 0) / predictions.length;
  const avgRating = predictions.reduce((s, p) => s + safeNumber(p.confidence), 0) / predictions.length;

  intro.innerHTML = `
    <span>AI77 Filtered Board</span>
    <h2>Today’s model-qualified picks</h2>
    <p>No forced picks. Each selection must pass form, league, odds and bookmaker filters.</p>
    <div class="clean-board-stats">
      <div><small>Picks</small><strong>${predictions.length}</strong></div>
      <div><small>Avg Odds</small><strong>${avgOdds.toFixed(2)}</strong></div>
      <div><small>Avg Rating</small><strong>${avgRating.toFixed(0)}/100</strong></div>
    </div>
  `;

  container.appendChild(intro);

  const list = document.createElement("section");
  list.className = "clean-prediction-list";

  predictions.forEach((p, index) => {
    const confidence = safeNumber(p.confidence);
    const grade = getGrade(confidence);
    const stakeUnits = safeNumber(p.stake_units, safeNumber(p.stake, grade.stake));
    const riskLevel = p.risk_level || grade.risk;

    const kickoff = getKickoffStatus(p.date, p.time);
    const sport = p.sport || "football";
    const icon = sportIcons[sport] || "🎯";

    const odds = safeNumber(p.odds, 0);

    const card = document.createElement("article");
    card.className = `clean-prediction-card ${grade.className}`;

    card.innerHTML = `
      <div class="clean-card-top">
        <div>
          <span class="market-pill">${getMarketLabel(p.bucket, p.bet)}</span>
          <h3>${p.match || "Unknown match"}</h3>
          <p>${icon} ${String(sport).toUpperCase()} · ${p.league || "Football"} · ${p.date || "-"} · ${p.time || "-"}</p>
        </div>

        <div class="rating-ring">
          <canvas id="chart${index}" width="76" height="76"></canvas>
          <strong>${Math.round(confidence)}</strong>
          <span>AI Rating</span>
        </div>
      </div>

      ${kickoff ? `<div class="kickoff-pill">${kickoff}</div>` : ""}

      <div class="pick-strip">
        <div>
          <small>Pick</small>
          <strong>${p.bet || "-"}</strong>
        </div>
        <div>
          <small>Odds</small>
          <strong>${odds ? odds.toFixed(2) : "-"}</strong>
        </div>
        <div>
          <small>Stake Guide</small>
          <strong>${stakeUnits.toFixed(2)}u</strong>
        </div>
        <div>
          <small>Risk</small>
          <strong>${riskLevel}</strong>
        </div>
      </div>

      <div class="short-note">
        <strong>AI Note:</strong>
        <p>${shortAnalysis(p)}</p>
      </div>

      <a href="https://stzns.lynmonkel.com/?mid=309891_1838278" class="btn clean-odds-btn" target="_blank" rel="nofollow sponsored">
        Check Best Odds
      </a>
    `;

    list.appendChild(card);

    setTimeout(() => {
      const chartCanvas = document.getElementById(`chart${index}`);
      if (!chartCanvas || typeof Chart === "undefined") return;

      new Chart(chartCanvas, {
        type: "doughnut",
        data: {
          datasets: [{
            data: [confidence, Math.max(0, 100 - confidence)],
            backgroundColor: [grade.color, "#e5e7eb"],
            borderWidth: 0
          }]
        },
        options: {
          cutout: "76%",
          responsive: false,
          plugins: {
            legend: { display: false },
            tooltip: { enabled: false }
          }
        }
      });
    }, 0);
  });

  container.appendChild(list);
}

const title = document.getElementById("howWePlayTitle");
const content = document.getElementById("howWePlayContent");

if (title && content) {
  title.addEventListener("click", () => {
    content.classList.toggle("hidden");
  });
}

loadPredictions();
