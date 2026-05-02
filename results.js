function safeNumber(v, f = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : f;
}

function getGradeFromPick(p) {
  const label = String(p.stake_label || "").trim();

  if (label) {
    if (label === "Top Rated") {
      return { label: "Top Rated", stake: safeNumber(p.stake, 1.5) };
    }

    if (label === "Strong") {
      return { label: "Strong", stake: safeNumber(p.stake, 1.25) };
    }

    if (label === "Standard") {
      return { label: "Standard", stake: safeNumber(p.stake, 1) };
    }

    if (label === "Small Value") {
      return { label: "Small Value", stake: safeNumber(p.stake, 0.75) };
    }

    if (label === "Research") {
      return { label: "Research", stake: safeNumber(p.stake, 0.5) };
    }
  }

  const c = safeNumber(p.confidence);

  if (c >= 88) return { label: "Top Rated", stake: 1.5 };
  if (c >= 82) return { label: "Strong", stake: 1.25 };
  if (c >= 74) return { label: "Standard", stake: 1 };
  if (c >= 60) return { label: "Small Value", stake: 0.75 };

  return { label: "Research", stake: 0.5 };
}

function normalizeBucket(p) {
  const b = String(p.bucket || "").toLowerCase();
  const bet = String(p.bet || "").toLowerCase();

  if (b === "home") return "Home";
  if (b === "away") return "Away";
  if (b === "draw") return "Draw";
  if (b.includes("over") || bet.includes("over")) return "Over";
  if (b.includes("under") || bet.includes("under")) return "Under";

  return "Other";
}

function getStake(p) {
  const directStake = safeNumber(p.stake, 0);

  if (directStake > 0) {
    return directStake;
  }

  const g = getGradeFromPick(p);
  return g.stake;
}

function getProfit(p) {
  const result = String(p.result || "").toLowerCase();
  const odds = safeNumber(p.odds);
  const stake = getStake(p);

  if (result === "win") {
    return odds > 1 ? (odds - 1) * stake : stake;
  }

  if (result === "loss") {
    return -stake;
  }

  if (result === "storno" || result === "void" || result === "push") {
    return 0;
  }

  return null;
}

function formatUnits(v) {
  const n = safeNumber(v);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}u`;
}

function formatPercent(v) {
  return `${safeNumber(v).toFixed(1)}%`;
}

function dedupe(data) {
  const seen = new Set();
  const out = [];

  data.forEach(p => {
    if (!p) return;

    const key =
      p.pick_id ||
      `${p.date}|${p.time}|${p.match}|${p.bet}|${p.odds}`;

    if (seen.has(key)) return;

    seen.add(key);
    out.push(p);
  });

  return out;
}

function calculateGroupStats(items) {
  let picks = 0;
  let settled = 0;
  let wins = 0;
  let losses = 0;
  let storno = 0;
  let profit = 0;
  let staked = 0;
  let oddsSum = 0;
  let oddsCount = 0;

  items.forEach(p => {
    picks++;

    const odds = safeNumber(p.odds);
    if (odds > 1) {
      oddsSum += odds;
      oddsCount++;
    }

    const result = String(p.result || "").toLowerCase();
    const stake = getStake(p);
    const pickProfit = getProfit(p);

    if (result === "pending") return;

    if (["win", "loss", "storno", "void", "push"].includes(result)) {
      settled++;
    }

    if (result === "win") {
      wins++;
      staked += stake;
      profit += pickProfit;
    } else if (result === "loss") {
      losses++;
      staked += stake;
      profit += pickProfit;
    } else if (result === "storno" || result === "void" || result === "push") {
      storno++;
    }
  });

  const hitRate = settled ? (wins / Math.max(wins + losses, 1)) * 100 : 0;
  const roi = staked ? (profit / staked) * 100 : 0;
  const avgOdds = oddsCount ? oddsSum / oddsCount : 0;

  return {
    picks,
    settled,
    wins,
    losses,
    storno,
    pending: picks - settled,
    profit,
    staked,
    hitRate,
    roi,
    avgOdds
  };
}

function renderSummary(data) {
  const el = document.getElementById("results-summary");
  if (!el) return;

  const s = calculateGroupStats(data);

  el.innerHTML = `
    <div class="summary-box">
      <span>Total Picks</span>
      <strong>${s.picks}</strong>
      <small>All tracked</small>
    </div>

    <div class="summary-box">
      <span>Settled</span>
      <strong>${s.settled}</strong>
      <small>${s.pending} pending</small>
    </div>

    <div class="summary-box">
      <span>Hit Rate</span>
      <strong>${formatPercent(s.hitRate)}</strong>
      <small>${s.wins}W / ${s.losses}L</small>
    </div>

    <div class="summary-box">
      <span>Profit</span>
      <strong class="${s.profit >= 0 ? "positive" : "negative"}">${formatUnits(s.profit)}</strong>
      <small>AI77 stake tracking</small>
    </div>

    <div class="summary-box">
      <span>ROI</span>
      <strong class="${s.roi >= 0 ? "positive" : "negative"}">${formatPercent(s.roi)}</strong>
      <small>On settled stake</small>
    </div>

    <div class="summary-box">
      <span>Avg Odds</span>
      <strong>${s.avgOdds.toFixed(2)}</strong>
      <small>Published price</small>
    </div>
  `;
}

function renderTable(id, rows) {
  const el = document.getElementById(id);
  if (!el) return;

  if (!rows.length) {
    el.innerHTML = '<div class="empty-state">No settled data yet.</div>';
    return;
  }

  el.innerHTML = `
    <table class="results-table">
      <thead>
        <tr>
          <th>Group</th>
          <th>Picks</th>
          <th>Hit</th>
          <th>Profit</th>
          <th>ROI</th>
          <th>Avg Odds</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>
            <td>${r.name}</td>
            <td>${r.stats.settled}</td>
            <td>${formatPercent(r.stats.hitRate)}</td>
            <td class="${r.stats.profit >= 0 ? "positive" : "negative"}">${formatUnits(r.stats.profit)}</td>
            <td class="${r.stats.roi >= 0 ? "positive" : "negative"}">${formatPercent(r.stats.roi)}</td>
            <td>${r.stats.avgOdds.toFixed(2)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderMarketTables(data) {
  const settled = data.filter(p =>
    ["win", "loss", "storno", "void", "push"].includes(String(p.result || "").toLowerCase())
  );

  const byMarket = {};

  settled.forEach(p => {
    const key = normalizeBucket(p);
    if (!byMarket[key]) byMarket[key] = [];
    byMarket[key].push(p);
  });

  const marketRows = Object.entries(byMarket)
    .map(([name, items]) => ({
      name,
      stats: calculateGroupStats(items)
    }))
    .sort((a, b) => b.stats.profit - a.stats.profit);

  renderTable("market-table", marketRows);

  const byRating = {};

  settled.forEach(p => {
    const key = getGradeFromPick(p).label;
    if (!byRating[key]) byRating[key] = [];
    byRating[key].push(p);
  });

  const order = ["Top Rated", "Strong", "Standard", "Small Value", "Research"];

  const ratingRows = Object.entries(byRating)
    .map(([name, items]) => ({
      name,
      stats: calculateGroupStats(items)
    }))
    .sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));

  renderTable("rating-table", ratingRows);
  renderMarketChart(marketRows);
}

function renderProfitChart(data) {
  const ctx = document.getElementById("profitGrowthChart");
  if (!ctx || typeof Chart === "undefined") return;

  const settled = data
    .filter(p => ["win", "loss", "storno", "void", "push"].includes(String(p.result || "").toLowerCase()))
    .sort((a, b) =>
      `${a.date || ""} ${a.time || ""}`.localeCompare(`${b.date || ""} ${b.time || ""}`)
    );

  const daily = {};

  settled.forEach(p => {
    const date = p.date || "Unknown";
    daily[date] = (daily[date] || 0) + (getProfit(p) || 0);
  });

  const labels = Object.keys(daily).sort();

  if (!labels.length) {
    ctx.style.display = "none";
    return;
  }

  ctx.style.display = "block";

  let running = 0;
  const values = labels.map(date => {
    running += daily[date];
    return Number(running.toFixed(2));
  });

  new Chart(ctx.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        data: values,
        borderColor: "#d4af37",
        backgroundColor: "rgba(212,175,55,0.15)",
        borderWidth: 3,
        tension: 0.3,
        fill: true,
        pointRadius: 3
      }]
    },
    options: {
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          grid: { color: "rgba(0,0,0,0.06)" }
        },
        y: {
          grid: { color: "rgba(0,0,0,0.06)" }
        }
      }
    }
  });
}

function renderMarketChart(rows) {
  const ctx = document.getElementById("marketRoiChart");
  if (!ctx || typeof Chart === "undefined" || !rows.length) return;

  new Chart(ctx.getContext("2d"), {
    type: "bar",
    data: {
      labels: rows.map(r => r.name),
      datasets: [{
        data: rows.map(r => Number(r.stats.roi.toFixed(1))),
        backgroundColor: "#0077b6",
        borderWidth: 0
      }]
    },
    options: {
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          grid: { display: false }
        },
        y: {
          grid: { color: "rgba(0,0,0,0.06)" }
        }
      }
    }
  });
}

function renderRecentResults(data) {
  const el = document.getElementById("recent-results");
  if (!el) return;

  const sorted = [...data]
    .sort((a, b) =>
      `${b.date || ""} ${b.time || ""}`.localeCompare(`${a.date || ""} ${a.time || ""}`)
    )
    .slice(0, 40);

  if (!sorted.length) {
    el.innerHTML = '<div class="empty-state">No picks tracked yet.</div>';
    return;
  }

  el.innerHTML = `
    <div class="recent-list">
      ${sorted.map(p => {
        const result = String(p.result || "pending").toLowerCase();
        const profit = getProfit(p);
        const profitText = profit === null ? "-" : formatUnits(profit);
        const grade = getGradeFromPick(p);

        return `
          <article class="result-card">
            <div class="result-top">
              <div>
                <h4>${p.match || "-"}</h4>
                <p>${p.league || "-"} · ${p.date || "-"} · ${p.time || "-"}</p>
              </div>
              <span class="result-status status-${result}">${result.toUpperCase()}</span>
            </div>

            <div class="result-main-grid">
              <div>
                <small>Pick</small>
                <strong>${p.bet || "-"}</strong>
              </div>

              <div>
                <small>Odds</small>
                <strong>${safeNumber(p.odds).toFixed(2)}</strong>
              </div>

              <div>
                <small>Stake</small>
                <strong>${getStake(p).toFixed(2)}u</strong>
              </div>

              <div>
                <small>AI Rating</small>
                <strong>${safeNumber(p.confidence).toFixed(0)}/100</strong>
              </div>

              <div>
                <small>Profit</small>
                <strong class="${safeNumber(profit, 0) >= 0 ? "positive" : "negative"}">${profitText}</strong>
              </div>
            </div>

            <details class="model-details">
              <summary>Detailed model data</summary>

              <div class="details-grid">
                <div>
                  <small>Grade</small>
                  <strong>${grade.label}</strong>
                </div>

                <div>
                  <small>Stake Score</small>
                  <strong>${safeNumber(p.stake_score).toFixed(0)}</strong>
                </div>

                <div>
                  <small>Bucket</small>
                  <strong>${p.bucket || "-"}</strong>
                </div>

                <div>
                  <small>Value Edge</small>
                  <strong>${(safeNumber(p.edge) * 100).toFixed(1)}%</strong>
                </div>

                <div>
                  <small>Quality</small>
                  <strong>${safeNumber(p.quality_score).toFixed(1)}/100</strong>
                </div>

                <div>
                  <small>Model Prob</small>
                  <strong>${(safeNumber(p.model_prob) * 100).toFixed(1)}%</strong>
                </div>

                <div>
                  <small>Implied Prob</small>
                  <strong>${(safeNumber(p.implied_prob) * 100).toFixed(1)}%</strong>
                </div>

                <div>
                  <small>Market Median</small>
                  <strong>${safeNumber(p.market_median_odds).toFixed(2)}</strong>
                </div>

                <div>
                  <small>Bookmakers</small>
                  <strong>${safeNumber(p.bookmakers_used)}</strong>
                </div>

                <div>
                  <small>Exp Home</small>
                  <strong>${safeNumber(p.expected_home_goals).toFixed(2)}</strong>
                </div>

                <div>
                  <small>Exp Away</small>
                  <strong>${safeNumber(p.expected_away_goals).toFixed(2)}</strong>
                </div>

                <div>
                  <small>Exp Total</small>
                  <strong>${safeNumber(p.expected_total_goals).toFixed(2)}</strong>
                </div>

                <div>
                  <small>Final Score</small>
                  <strong>${p.final_score || "-"}</strong>
                </div>

                <div>
                  <small>Model</small>
                  <strong>${p.model_version || "-"}</strong>
                </div>
              </div>

              ${p.reasoning ? `<div class="reasoning-box">${p.reasoning}</div>` : ""}
            </details>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

async function loadResults() {
  try {
    const response = await fetch("./results.json", { cache: "no-store" });
    const raw = await response.json();
    const data = dedupe(Array.isArray(raw) ? raw : []);

    renderSummary(data);
    renderProfitChart(data);
    renderMarketTables(data);
    renderRecentResults(data);

  } catch (e) {
    const container = document.querySelector(".results-container");

    if (container) {
      container.innerHTML = `
        <section class="results-hero">
          <span>AI77 Results</span>
          <h2>No results available yet</h2>
          <p>The results dashboard will activate after the first tracked picks are written to results.json.</p>
        </section>
      `;
    }
  }
}

loadResults();
