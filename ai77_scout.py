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
        "markets": "h2h,totals,btts",
        "oddsFormat": "decimal"
    }

    res = requests.get(ODDS_URL, params=params, timeout=10)

    if res.status_code != 200:
        print("API ERROR:", res.text)
        return []

    return res.json()

# ------------------------
# AI ANALYSIS
# ------------------------
def generate_reasoning(home, away, bet, expected_goals):
    if "Over" in bet:
        return f"{home} and {away} project an open game with strong attacking output. Expected goals suggest above-average scoring potential."

    elif "Under" in bet:
        return f"This matchup trends toward a controlled tempo with fewer clear chances, favoring a lower scoring outcome."

    elif "BTTS" in bet:
        return f"Both teams show consistent attacking involvement while allowing chances. The profile supports goals on both sides."

    else:
        return f"{home} shows more stability and control compared to {away}, creating a slight edge in this matchup."

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

    # BALANCE COUNTERS
    over_count = 0
    under_count = 0
    h2h_home_count = 0
    h2h_away_count = 0
    btts_count = 0

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

            # SIMPLE MODEL
            expected_home = 1.3
            expected_away = 1.1
            expected_goals = expected_home + expected_away

            home_prob = expected_home / expected_goals
            away_prob = expected_away / expected_goals

            over_prob = min(0.60, expected_goals / 3.3)
            under_prob = 1 - over_prob

            if not game.get("bookmakers"):
                continue

            bookmaker = game["bookmakers"][0]

            best_edge = -999
            best_pick = None
            best_type = None

            for market in bookmaker["markets"]:

                # ------------------------
                # TOTALS
                # ------------------------
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

                # ------------------------
                # H2H (NO DRAW)
                # ------------------------
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        if outcome["name"] == "Draw":
                            continue

                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == home:
                            model_prob = home_prob
                            pick_type = "home"
                        else:
                            model_prob = away_prob
                            pick_type = "away"

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (outcome["name"], odds)
                            best_type = pick_type

                # ------------------------
                # BTTS
                # ------------------------
                if market["key"] == "btts":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == "Yes":
                            model_prob = 0.56
                            label = "BTTS Yes"
                        else:
                            model_prob = 0.44
                            label = "BTTS No"

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (label, odds)
                            best_type = "btts"

            if not best_pick:
                continue

            odds = best_pick[1]

            # LIGHT FILTER
            if best_edge < -0.04:
                continue

            if odds < 1.4 or odds > 3.2:
                continue

            # SMALL BOOSTS
            if best_type in ["over", "under"]:
                best_edge *= 1.05
            if best_type == "btts":
                best_edge *= 1.05

            # BALANCE CONTROL
            if best_type == "over" and over_count >= 2:
                continue
            if best_type == "under" and under_count >= 2:
                continue
            if best_type == "btts" and btts_count >= 2:
                continue
            if best_type == "home" and h2h_home_count >= 2:
                continue
            if best_type == "away" and h2h_away_count >= 2:
                continue

            # INCREMENT COUNTS
            if best_type == "over":
                over_count += 1
            elif best_type == "under":
                under_count += 1
            elif best_type == "btts":
                btts_count += 1
            elif best_type == "home":
                h2h_home_count += 1
            elif best_type == "away":
                h2h_away_count += 1

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

    # SORT & SELECT
    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)
    picks = picks[:5]

    # CONFIDENCE → YOUR UNIT SYSTEM
    for i, p in enumerate(picks):
        if i == 0:
            p["confidence"] = 78   # 2u
        elif i < 3:
            p["confidence"] = 66   # 1.5u
        else:
            p["confidence"] = 55   # 1u

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
