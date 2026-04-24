import requests
import json
import os
from datetime import datetime

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"
FOOTBALL_URL = "https://v3.football.api-sports.io"

team_cache = {}

# ------------------------
# ODDS
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
# TEAM GOALS MODEL
# ------------------------
def get_team_goals(team):
    if team in team_cache:
        return team_cache[team]

    try:
        headers = {"x-apisports-key": FOOTBALL_API_KEY}

        # find team
        res = requests.get(
            f"{FOOTBALL_URL}/teams",
            headers=headers,
            params={"search": team},
            timeout=5
        )

        data = res.json()

        if not data["response"]:
            team_cache[team] = 1.2
            return 1.2

        team_id = data["response"][0]["team"]["id"]

        # last matches
        res = requests.get(
            f"{FOOTBALL_URL}/fixtures",
            headers=headers,
            params={"team": team_id, "last": 5},
            timeout=5
        )

        fixtures = res.json()["response"]

        goals = 0

        for f in fixtures:
            goals += f["goals"]["for"]

        avg_goals = goals / max(len(fixtures), 1)

        team_cache[team] = avg_goals
        return avg_goals

    except:
        team_cache[team] = 1.2
        return 1.2

# ------------------------
# MODEL
# ------------------------
def build_predictions():
    data = fetch_odds()
    picks = []

    for game in data:
        try:
            home = game["home_team"]
            away = game["away_team"]

            home_goals = get_team_goals(home)
            away_goals = get_team_goals(away)

            expected_goals = home_goals + away_goals

            bookmaker = game["bookmakers"][0]

            best_edge = -999
            best_pick = None

            for market in bookmaker["markets"]:

                # 🎯 OVER/UNDER MODEL
                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == "Over":
                            model_prob = min(0.85, expected_goals / 3)
                            edge = model_prob - implied
                            label = f"Over {outcome['point']}"
                        else:
                            model_prob = 1 - min(0.85, expected_goals / 3)
                            edge = model_prob - implied
                            label = f"Under {outcome['point']}"

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (label, odds)

                # 🎯 MATCH WINNER fallback
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        model_prob = 0.5
                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (outcome["name"], odds)

            if best_pick and best_edge > -0.03:
                confidence = int(50 + best_edge * 300)
                confidence = max(55, min(confidence, 92))

                picks.append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "sport": "football",
                    "league": game["sport_title"],
                    "match": f"{home} - {away}",
                    "bet": best_pick[0],
                    "confidence": confidence,
                    "reasoning": f"Model vs market edge. Edge: {round(best_edge,3)} | Odds: {best_pick[1]}"
                })

        except:
            continue

    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    return picks[:3]

# ------------------------
def main():
    predictions = build_predictions()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4)

    print(f"Saved {len(predictions)} predictions.")

if __name__ == "__main__":
    main()
