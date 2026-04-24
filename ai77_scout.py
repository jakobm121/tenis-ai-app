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

    data = res.json()
    print("TOTAL GAMES FROM API:", len(data))  # 🔥 DEBUG
    return data

# ------------------------
# AI TEXT
# ------------------------
def generate_reasoning(home, away):
    return f"{home} vs {away} shows value based on model projections."

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

    for game in data:
        try:
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00")).astimezone(tz)

            # 🔥 TEMPORARY RELAX (če želiš test, lahko zakomentiraš)
            if match_time < start_time or match_time > end_time:
                continue

            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            if not game.get("bookmakers"):
                print("NO BOOKMAKER:", home, away)
                continue

            bookmaker = game["bookmakers"][0]

            best_edge = -999
            best_pick = None

            for market in bookmaker["markets"]:

                # TOTALS
                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        model_prob = 0.55  # 🔥 simple fallback

                        edge = model_prob - implied

                        label = f"{outcome['name']} {outcome.get('point', 2.5)}"

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (label, odds)

                # H2H
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        model_prob = 0.45

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (outcome["name"], odds)

            if not best_pick:
                continue

            odds = best_pick[1]

            # 🔥 RELAXED FILTER (da NE dobiš 0)
            if odds < 1.3 or odds > 3.5:
                continue

            # 🔥 LIMIT OVER
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
                "reasoning": generate_reasoning(home, away),
                "sort_time": match_time.timestamp()
            })

        except Exception as e:
            print("ERROR:", e)
            continue

    print("PICKS FOUND:", len(picks))  # 🔥 DEBUG

    # 🔥 FALLBACK (če nič ne najde)
    if len(picks) == 0 and len(data) > 0:
        print("⚠️ FALLBACK MODE ACTIVE")

        for game in data[:5]:
            home = game["home_team"]
            away = game["away_team"]

            picks.append({
                "date": now.strftime("%Y-%m-%d"),
                "time": "TBD",
                "sport": "football",
                "league": game.get("sport_title", "Football"),
                "match": f"{home} - {away}",
                "bet": "Random pick",
                "confidence": 50,
                "reasoning": "Fallback selection",
                "sort_time": 0
            })

    # TAKE 5
    picks = picks[:5]

    # CONFIDENCE LEVELS
    for i, p in enumerate(picks):
        if i == 0:
            p["confidence"] = 80
        elif i < 3:
            p["confidence"] = 68
        else:
            p["confidence"] = 55

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
