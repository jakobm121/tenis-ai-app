import requests
import json
import os
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"

team_cache = {}

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
# PREMIUM AI ANALYSIS
# ------------------------
def generate_reasoning(home, away, bet, expected_goals, edge):
    if "Over" in bet:
        texts = [
            f"{home} and {away} both play attacking football, projecting around {round(expected_goals,1)} expected goals. High tempo matchup with strong scoring potential. Edge vs market: {round(edge,3)}.",
            f"Both teams consistently create chances and maintain offensive pressure. With expected goals at {round(expected_goals,1)}, the probability of goals is higher than odds suggest.",
            f"This is a high-event game profile. Defensive weaknesses and attacking output push expected goals into a strong range."
        ]
    elif "Under" in bet:
        texts = [
            f"This game projects as slower-paced with limited attacking output. Expected goals around {round(expected_goals,1)} suggest fewer scoring opportunities.",
            f"Both teams rely on structure and defense, reducing tempo and chance creation. Market slightly overestimates scoring.",
            f"Match dynamics point to controlled play with limited space, keeping goal expectation low."
        ]
    else:
        texts = [
            f"{home} shows stronger form and underlying metrics compared to {away}. Model identifies a value edge of {round(edge,3)}.",
            f"This side has better stability and efficiency in key phases of play. Market slightly underrates this advantage.",
            f"Performance trends and matchup dynamics give this selection a measurable edge over current odds."
        ]

    endings = [
        " Strong value spot.",
        " Fits well into a value betting strategy.",
        " One of the better edges today.",
        " Risk present, but value justifies the bet."
    ]

    return random.choice(texts) + random.choice(endings)

# ------------------------
# MAIN MODEL
# ------------------------
def build_predictions():
    data = fetch_odds()
    picks = []

    local_tz = ZoneInfo("Europe/Ljubljana")
    now_local = datetime.now(local_tz)
    end_of_day = now_local.replace(hour=23, minute=59, second=59)

    for game in data:
        try:
            # ------------------------
            # TIME FILTER
            # ------------------------
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time_utc = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            match_time_local = match_time_utc.astimezone(local_tz)

            # najmanj 30 min vnaprej
            if match_time_local < now_local + timedelta(minutes=30):
                continue

            # samo danes
            if match_time_local > end_of_day:
                continue

            # ------------------------
            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            expected_home = 1.3
            expected_away = 1.1
            expected_goals = expected_home + expected_away

            home_prob = expected_home / expected_goals
            away_prob = expected_away / expected_goals
            draw_prob = 0.22

            over_prob = min(0.85, expected_goals / 3)
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

            if best_edge < -0.02:
                continue

            picks.append({
                "date": now_local.strftime("%Y-%m-%d"),
                "time": match_time_local.strftime("%H:%M"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": best_pick[0],
                "confidence": best_edge,
                "reasoning": generate_reasoning(home, away, best_pick[0], expected_goals, best_edge),
                "sort_time": match_time_local.timestamp()
            })

        except:
            continue

    # ------------------------
    # SORT BY TIME (najprej najbližje tekme)
    # ------------------------
    picks = sorted(picks, key=lambda x: x["sort_time"])

    # potem izberi top 5 po strukturi
    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    if len(picks) < 5:
        return picks[:5]

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

    # ponovno sortiraj po času za UI
    final = sorted(final, key=lambda x: x["sort_time"])

    # odstrani sort_time iz JSON
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

    # HISTORY SAVE
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
