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

function formatPercent(value) {
  const n = safeNumber(value, 0);
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
}

function formatEdge(edge) {
  return formatPercent(safeNumber(edge, 0) * 100);
}

function getPickGrade(confidence) {
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

  if (!year || !month || !day) return "";

  const now = new Date();
  const matchTime = new Date(year, month - 1, day, hours || 0, minutes || 0, 0, 0);
  const diffMinutes = Math.floor((matchTime - now) / 60000);

  if (diffMinutes <= 0) return "";
  if (diffMinutes < 60) return `⏰ Starts in ${diffMinutes} min`;
  if (diffMinutes < 180) return `🕒 Starts in ${Math.floor(diffMinutes / 60)}h`;

  return "";
}

function getMarketLabel(bucket, bet) {
  if (bucket === "over_2_5" || String(bet).toLowerCase().includes("over")) return "Totals";
  if (bucket === "under_2_5" || String(bet).toLowerCase().includes("under")) return "Totals";
  if (bucket === "home") return "Home Value";
  if (bucket === "away") return "Away Value";
  if (bucket === "draw") return "Draw Value";
  return "Value Pick";
}

function createMetric(label, value, extraClass = "") {
  return `
    <div class="ai77-metric ${extraClass}">
      <small>${label}</small>
      <strong>${value}</strong>
    </div>
  `;
}

function buildBoardSummary(predictions) {
  const total = predictions.length;

  if (!total) {
    return `
      <section class="ai77-board-summary">
        <div>
          <span class="ai77-eyebrow">AI77 Filtered Board</span>
          <h2>No qualified picks right now</h2>
          <p>The model did not find enough value after odds, form, league and bookmaker filters.</p>
        </div>
      </section>
    `;
  }

  const avgOdds = predictions.reduce((sum, p) => sum + safeNumber(p.odds), 0) / total;
  const avgRating = predictions.reduce((sum, p) => sum + safeNumber(p.confidence), 0) / total;
  const avgEdge = predictions.reduce((sum, p) => sum + safeNumber(p.edge), 0) / total;

  const bucketCounts = {};
  predictions.forEach((p) => {
    const label = getMarketLabel(p.bucket, p.bet);
    bucketCounts[label] = (bucketCounts[label] || 0) + 1;
  });

  const topMarket = Object.entries(bucketCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "Value Picks";

  return `
    <section class="ai77-board-summary">
      <div>
        <span class="ai77-eyebrow">AI77 Filtered Board</span>
        <h2>Today’s model-qualified betting card</h2>
        <p>No forced picks. Every published selection must pass form, league, odds and bookmaker filters.</p>
      </div>

      <div class="ai77-summary-grid">
        ${createMetric("Published Picks", total)}
        ${createMetric("Average Odds", avgOdds.toFixed(2))}
        ${createMetric("Average Rating", `${avgRating.toFixed(0)}/100`)}
        ${createMetric("Average Edge", formatPercent(avgEdge * 100))}
        ${createMetric("Main Market", topMarket)}
      </div>
    </section>
  `;
}

async function loadPredictions() {
  try {
    const response = await fetch("./predictions.json", { cache: "no-store" });
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
        <section class="ai77-board-summary">
          <div>
            <span class="ai77-eyebrow">AI77 Board</span>
            <h2>Predictions temporarily unavailable</h2>
            <p>Please check again shortly.</p>
          </div>
        </section>
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

  container.innerHTML = buildBoardSummary(predictions);

  if (!predictions.length) return;

  const list = document.createElement("section");
  list.className = "ai77-prediction-list";

  predictions.forEach((p, index) => {
    const confidence = safeNumber(p.confidence);
    const grade = getPickGrade(confidence);

    const stakeUnits = safeNumber(p.stake_units, safeNumber(p.stake, grade.stake));
    const riskLevel = p.risk_level || grade.risk;
    const gradeLabel = p.grade || grade.label;

    const kickoff = getKickoffStatus(p.date, p.time);
    const sport = p.sport || "football";
    const icon = sportIcons[sport] || "🎯";

    const odds = safeNumber(p.odds, 0);
    const quality = safeNumber(p.quality_score, 0);
    const edge = safeNumber(p.edge, 0);
    const bookmakers = safeNumber(p.bookmakers_used, 0);
    const marketMedian = safeNumber(p.market_median_odds, 0);

    const expHome = safeNumber(p.expected_home_goals, null);
    const expAway = safeNumber(p.expected_away_goals, null);
    const expTotal = safeNumber(p.expected_total_goals, null);

    const card = document.createElement("article");
    card.className = `ai77-prediction-card ${grade.className}`;

    card.innerHTML = `
      <div class="ai77-card-top">
        <div>
          <span class="ai77-market-tag">${getMarketLabel(p.bucket, p.bet)}</span>
          <h3>${p.match || "Unknown match"}</h3>
          <p class="ai77-league-line">${icon} ${sport.toUpperCase()} · ${p.league || "Football"} · ${p.date || "-"} · ${p.time || "-"}</p>
        </div>

        <div class="ai77-rating-box">
          <canvas id="chart${index}" width="90" height="90"></canvas>
          <strong>${Math.round(confidence)}</strong>
          <span>AI Rating</span>
        </div>
      </div>

      ${kickoff ? `<div class="ai77-kickoff">${kickoff}</div>` : ""}

      <div class="ai77-main-pick">
        <div>
          <small>Selection</small>
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
      </div>

      <div class="ai77-metrics-grid">
        ${createMetric("Value Edge", formatEdge(edge), "positive")}
        ${createMetric("Quality", quality ? `${quality.toFixed(1)}/100` : "-")}
        ${createMetric("Bookmakers", bookmakers || "-")}
        ${createMetric("Risk Level", riskLevel)}
        ${createMetric("Grade", gradeLabel)}
        ${createMetric("Market Median", marketMedian ? marketMedian.toFixed(2) : "-")}
      </div>

      ${
        expHome !== null && expAway !== null && expTotal !== null
          ? `
            <div class="ai77-projection">
              <span>Projected Goals</span>
              <strong>Home ${expHome.toFixed(2)} · Away ${expAway.toFixed(2)} · Total ${expTotal.toFixed(2)}</strong>
            </div>
          `
          : ""
      }

      <details class="ai77-analysis" open>
        <summary>AI Analysis</summary>
        <p>${p.reasoning || "No detailed analysis available."}</p>
      </details>

      <a href="https://stzns.lynmonkel.com/?mid=309891_1838278" class="btn ai77-odds-btn" target="_blank" rel="nofollow sponsored">
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
          datasets: [
            {
              data: [confidence, Math.max(0, 100 - confidence)],
              backgroundColor: [grade.color, "#e5e7eb"],
              borderWidth: 0
            }
          ]
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

function uniqueSettledPicks(data) {
  const seen = new Set();
  const output = [];

  data.forEach((p) => {
    if (!p || p.result === "pending") return;

    const key =
      p.pick_id ||
      `${p.date || ""}|${p.time || ""}|${p.match || ""}|${p.bet || ""}|${p.odds || ""}`;

    if (seen.has(key)) return;

    seen.add(key);
    output.push(p);
  });

  return output;
}

async function loadStats() {
  try {
    const res = await fetch("./results.json", { cache: "no-store" });
    const raw = await res.json();

    if (!Array.isArray(raw)) return;

    const data = uniqueSettledPicks(raw);

    let total = 0;
    let wins = 0;
    let profit = 0;
    let totalStaked = 0;
    let avgOddsSum = 0;
    let avgOddsCount = 0;

    const dailyProfit = {};

    data.forEach((p) => {
      const result = p.result;
      if (!["win", "loss", "storno"].includes(result)) return;

      const confidence = safeNumber(p.confidence);
      const grade = getPickGrade(confidence);
      const units = safeNumber(p.stake_units, safeNumber(p.stake, grade.stake));
      const odds = safeNumber(p.odds, 0);

      total++;

      if (odds > 1) {
        avgOddsSum += odds;
        avgOddsCount++;
      }

      let pickProfit = 0;

      if (result === "win") {
        wins++;
        totalStaked += units;
        pickProfit = odds > 1 ? (odds - 1) * units : units;
      } else if (result === "loss") {
        totalStaked += units;
        pickProfit = -units;
      } else if (result === "storno") {
        pickProfit = 0;
      }

      profit += pickProfit;

      const dateKey = p.date || "Unknown";
      if (!dailyProfit[dateKey]) dailyProfit[dateKey] = 0;
      dailyProfit[dateKey] += pickProfit;
    });

    const roi = totalStaked > 0 ? ((profit / totalStaked) * 100).toFixed(1) : "0.0";
    const avgOdds = avgOddsCount > 0 ? (avgOddsSum / avgOddsCount).toFixed(2) : "0.00";

    const statBoxes = document.querySelectorAll(".stat-box h3");
    if (statBoxes.length >= 4 && total > 0) {
      statBoxes[0].innerText = total;
      statBoxes[1].innerText = wins;
      statBoxes[2].innerText = avgOdds;
      statBoxes[3].innerText = `${roi}%`;
    }

    const profitCtx = document.getElementById("profitChart");
    if (!profitCtx || typeof Chart === "undefined") return;

    const sortedDates = Object.keys(dailyProfit).sort();

    let runningProfit = 0;
    const labels = [];
    const values = [];

    sortedDates.forEach((date) => {
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
        labels,
        datasets: [
          {
            label: "Profit Growth (Units)",
            data: values,
            borderColor: "#d4af37",
            backgroundColor: "rgba(212, 175, 55, 0.15)",
            borderWidth: 3,
            tension: 0.3,
            fill: true,
            pointRadius: 2
          }
        ]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: {
            ticks: { color: "#333" },
            grid: { color: "rgba(0,0,0,0.08)" }
          },
          y: {
            ticks: { color: "#333" },
            grid: { color: "rgba(0,0,0,0.08)" }
          }
        }
      }
    });
  } catch (e) {
    console.log("Stats error", e);
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
