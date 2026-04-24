import requests
import json
import os
from datetime import datetime

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

ODDS_BASE = "https://api.odds-api.io/v3"
FOOTBALL_BASE = "https://v3.football.api-sports.io"

team_cache = {}

# ------------------------
# EVENTS
# ------------------------
def fetch_events():
    try:
        res = requests.get(
            f"{ODDS_BASE}/events",
            params={"apiKey": ODDS_API_KEY, "sport": "football"},
            timeout=10
        )
        if res.status_code != 200:
            print("EVENT ERROR:", res.text)
            return []
        return res.json()
    except Exception as e:
        print("EVENT EXCEPTION:", e)
        return []

# ------------------------
# ODDS
# ------------------------
def fetch_odds(event_id):
    try:
        res = requests.get(
            f"{ODDS_BASE}/odds",
            params={"apiKey": ODDS_API_KEY, "eventId": event_id},
            timeout=5
        )
        if res.status_code != 200:
            return None
        return res.json()
    except:
        return None

# ------------------------
# TEAM FORM (API-Football)
# ------------------------
def get_team_form(team_name):
    if team_name in team_cache:
        return team_cache[team_name]

    try:
        headers = {
            "x-apisports-key": FOOTBALL_API_KEY
        }

        res = requests.get(
            f"{FOOTBALL_BASE}/teams",
            headers=headers,
            params={"search": team_name},
            timeout=5
        )

        data = res.json()

        if not data["response"]:
            team_cache[team_name] = 0
            return 0

        team_id = data["response"][0]["team"]["id"]

        res = requests.get(
            f"{FOOTBALL_BASE}/fixtures",
            headers=headers,
            params={"team": team_id, "last": 5},
            timeout=5
        )

        fixtures = res.json()["response"]

        score = 0

        for f in fixtures:
            gf = f["goals"]["for"]
            ga = f["goals"]["against"]

            if gf > ga:
                score += 3
            elif gf == ga:
                score += 1

        team_cache[team_name] = score
        return score

    except:
        team_cache[team_name] = 0
        return 0

# ------------------------
# MODEL
# ------------------------
def build_predictions():
    events = fetch_events()[:8]  # limit za hitrost
    picks = []

    for event in events:
        try:
            event_id = event["id"]
            home = event["home"]
            away = event["away"]
            league = event["league"]

            odds_data = fetch_odds(event_id)
            if not odds_data:
                continue

            home_odds = float(odds_data.get("home", 0))
            away_odds = float(odds_data.get("away", 0))

            if not home_odds or not away_odds:
                continue

            # 🔥 TEAM FORM
            home_form = get_team_form(home)
            away_form = get_team_form(away)

            total = home_form + away_form
            if total == 0:
                continue

            home_prob = home_form / total
            away_prob = 1 - home_prob

            # 📊 IMPLIED
            home_implied = 1 / home_odds
            away_implied = 1 / away_odds

            # 💰 EDGE
            home_edge = home_prob - home_implied
            away_edge = away_prob - away_implied

            if home_edge > away_edge:
                edge = home_edge
                bet = home
                odds = home_odds
            else:
                edge = away_edge
                bet = away
                odds = away_odds

            # 🔥 POPRAVEK (manj strog filter)
            if edge < -0.05:
                continue

            # 🔥 CONFIDENCE
            confidence = int(50 + (edge * 300))
            confidence = max(55, min(confidence, 92))

            picks.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": bet,
                "confidence": confidence,
                "reasoning": f"Form vs market edge. Edge: {round(edge,3)} | Odds: {odds}"
            })

        except:
            continue

    # 🔥 SORT
    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    # 🔥 FALLBACK (da ni prazno)
    if len(picks) == 0:
        print("No strong value → fallback")

        for event in events[:3]:
            picks.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sport": "football",
                "league": event["league"],
                "match": f"{event['home']} - {event['away']}",
                "bet": event["home"],
                "confidence": 60,
                "reasoning": "Fallback pick (no strong value found)"
            })

    return picks[:3]

# ------------------------
# MAIN
# ------------------------
def main():
    predictions = build_predictions()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4)

    print(f"Saved {len(predictions)} predictions.")


if __name__ == "__main__":
    main()
