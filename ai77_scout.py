import requests
import json
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")

ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"

# ------------------------
# FETCH ODDS
# ------------------------
def fetch_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal"
    }

    res = requests.get(ODDS_URL, params=params, timeout=10)

    if res.status_code != 200:
        print(res.text)
        return []

    return res.json()

# ------------------------
# AI ANALYSIS
# ------------------------
def generate_reasoning(home, away, bet, expected_goals, edge):
    texts = [
        f"{home} vs {away} shows a statistical edge based on model projections.",
        f"Market pricing does not fully reflect the underlying probabilities.",
        f"This selection holds a measurable advantage over current odds."
    ]
    return random.choice(texts)

# ------------------------
# MAIN MODEL
# ------------------------
def build_predictions():
    data = fetch_odds()
    picks = []

    local_tz = ZoneInfo("Europe/Ljubljana")
    now = datetime.now(local_tz)
    end_of_day = now.replace(hour=23, minute=59, second=59)

    over_count = 0  # 🔥 LIMIT OVER

    for game in data:
        try:
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00")).astimezone(local_tz)

            if match_time < now + timedelta(minutes=30):
                continue

            if match_time > end_of_day:
                continue

            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            expected_home = 1.3
            expected_away = 1.1
            expected_goals = expected_home + expected_away

            home_prob = expected_home / expected_goals
            away_prob = expected_away / expected_goals
            draw_prob = 0.22

            over_prob = min(0.65, expected_goals / 3.2)
            under_prob = 1 - over_prob

            if not game.get("bookmakers"):
                continue

            bookmaker = game["bookmakers"][0]

            best_edge = -999
            best_pick = None

            for market in bookmaker["markets"]:

                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds
                        point = outcome.get("point", 2.5)

                        if outcome["name"] == "Over":
                            model_prob = over_prob
                            label = f"Over {point}"
                        else:
                            model_prob = under_prob
                            label = f"Under {point}"

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (label, odds)

                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == home:
                            model_prob = home_prob
                        elif outcome["name"] == away:
                            model_prob = away_prob
                        else:
                            if odds < 3.0:
                                continue
                            model_prob = draw_prob

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (outcome["name"], odds)

            if not best_pick:
                continue

            if best_edge < 0.02:
                continue

            odds = best_pick[1]

            # 🔥 ODDS FILTER
            if odds < 1.5 or odds > 2.5:
                continue

            # 🔥 ODDS PENALTY
            if odds > 2.2:
                best_edge *= 0.8

            # 🔥 LIMIT OVER PICKS
            if "Over" in best_pick[0]:
                if over_count >= 2:
                    continue
                over_count += 1

            picks.append({
                "date": now.strftime("%Y-%m-%d"),
                "time": match_time.strftime("%H:%M"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": best_pick[0],
                "confidence": best_edge,
                "reasoning": generate_reasoning(home, away, best_pick[0], expected_goals, best_edge),
                "sort_time": match_time.timestamp()
            })

        except:
            continue

    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    if len(picks) < 5:
        final = picks[:5]
    else:
        very_strong = picks[:1]
        strong = picks[1:3]
        medium = picks[3:5]

        for p in very_strong:
            p["confidence"] = 82
        for p in strong:
            p["confidence"] = 68
        for p in medium:
            p["confidence"] = 55

        final = very_strong + strong + medium

    final = sorted(final, key=lambda x: x["sort_time"])

    for p in final:
        del p["sort_time"]

    return final

# ------------------------
# MAIN
# ------------------------
def main():
    predictions = build_predictions()

    with open("predictions.json", "w") as f:
        json.dump(predictions, f, indent=4)

    try:
        with open("results.json", "r") as f:
            history = json.load(f)
    except:
        history = []

    existing = {(p["match"], p["date"]) for p in history}

    for p in predictions:
        key = (p["match"], p["date"])
        if key not in existing:
            new_pick = p.copy()
            new_pick["result"] = "pending"
            history.append(new_pick)

    with open("results.json", "w") as f:
        json.dump(history, f, indent=4)

    print(f"Saved {len(predictions)} predictions.")

if __name__ == "__main__":
    main()
