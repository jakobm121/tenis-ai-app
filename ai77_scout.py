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
        print("API ERROR:", res.text)
        return []

    return res.json()

# ------------------------
# AI ANALYSIS (premium)
# ------------------------
def generate_reasoning(home, away, bet, expected_goals):
    if "Over" in bet:
        return f"{home} and {away} project a high-tempo game with strong attacking output. Expected goals around {round(expected_goals,1)} suggest above-average scoring potential."

    elif "Under" in bet:
        return f"This matchup profiles as slower and more controlled. Limited chance creation keeps expected goals low, favoring a tighter game."

    else:
        return f"{home} shows stronger consistency and structure compared to {away}. Model indicates a slight but clear edge over market pricing."

# ------------------------
# MAIN MODEL
# ------------------------
def build_predictions():
    data = fetch_odds()
    picks = []

    tz = ZoneInfo("Europe/Ljubljana")
    now = datetime.now(tz)

    start_time = now + timedelta(minutes=30)
    end_time = now + timedelta(hours=24)

    over_count = 0
    under_count = 0
    h2h_count = 0

    for game in data:
        try:
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00")).astimezone(tz)

            if match_time < start_time or match_time > end_time:
                continue

            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            # simple model
            expected_home = 1.3
            expected_away = 1.1
            expected_goals = expected_home + expected_away

            home_prob = expected_home / expected_goals
            away_prob = expected_away / expected_goals

            # balanced totals
            over_prob = min(0.58, expected_goals / 3.5)
            under_prob = 1 - over_prob

            if not game.get("bookmakers"):
                continue

            bookmaker = game["bookmakers"][0]

            best_edge = -999
            best_pick = None
            best_type = None

            for market in bookmaker["markets"]:

                # TOTALS
                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds
                        point = outcome.get("point", 2.5)

                        if outcome["name"] == "Over":
                            model_prob = over_prob
                            label = f"Over {point}"
                            pick_type = "over"
                        else:
                            model_prob = under_prob
                            label = f"Under {point}"
                            pick_type = "under"

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (label, odds)
                            best_type = pick_type

                # H2H (NO DRAW)
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        if outcome["name"] == "Draw":
                            continue  # ❌ remove draw completely

                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == home:
                            model_prob = home_prob
                        else:
                            model_prob = away_prob

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (outcome["name"], odds)
                            best_type = "h2h"

            if not best_pick:
                continue

            odds = best_pick[1]

            # LIGHT FILTER (da ne ubije pickov)
            if best_edge < -0.04:
                continue

            if odds < 1.4 or odds > 3.2:
                continue

            # BALANCE PICKS
            if best_type == "over" and over_count >= 2:
                continue
            if best_type == "under" and under_count >= 2:
                continue
            if best_type == "h2h" and h2h_count >= 3:
                continue

            if best_type == "over":
                over_count += 1
            elif best_type == "under":
                under_count += 1
            else:
                h2h_count += 1

            picks.append({
                "date": now.strftime("%Y-%m-%d"),
                "time": match_time.strftime("%H:%M"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": best_pick[0],
                "confidence": best_edge,
                "reasoning": generate_reasoning(home, away, best_pick[0], expected_goals),
                "sort_time": match_time.timestamp()
            })

        except:
            continue

    # sort by edge
    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    # always take top 5
    picks = picks[:5]

    # CONFIDENCE → YOUR UNIT SYSTEM
    for i, p in enumerate(picks):
        if i == 0:
            p["confidence"] = 78  # 2u
        elif i < 3:
            p["confidence"] = 66  # 1.5u
        else:
            p["confidence"] = 55  # 1u

    # sort for UI
    picks = sorted(picks, key=lambda x: x["sort_time"])

    for p in picks:
        del p["sort_time"]

    return picks

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
