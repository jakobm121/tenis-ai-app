import requests
import json
import os
from datetime import datetime

API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.odds-api.io/v3"


def fetch_events():
    try:
        res = requests.get(
            f"{BASE_URL}/events",
            params={"apiKey": API_KEY, "sport": "football"},
            timeout=15
        )
        if res.status_code != 200:
            print(res.text)
            return []
        return res.json()
    except:
        return []


def fetch_odds(event_id):
    try:
        res = requests.get(
            f"{BASE_URL}/odds",
            params={"apiKey": API_KEY, "eventId": event_id},
            timeout=10
        )
        if res.status_code != 200:
            return None
        return res.json()
    except:
        return None


def calculate_value(home_odds, away_odds):
    try:
        # implied probability
        home_prob = 1 / home_odds
        away_prob = 1 / away_odds

        total = home_prob + away_prob

        # normalize
        home_prob /= total
        away_prob /= total

        # “fair odds”
        home_fair = 1 / home_prob
        away_fair = 1 / away_prob

        # edge = odds - fair
        home_edge = home_odds - home_fair
        away_edge = away_odds - away_fair

        if home_edge > away_edge:
            return "home", home_edge, home_odds
        else:
            return "away", away_edge, away_odds

    except:
        return None, 0, 0


def build_predictions():
    events = fetch_events()
    picks = []

    for event in events:
        try:
            event_id = event["id"]
            home = event["home"]
            away = event["away"]
            league = event["league"]
            date_raw = event.get("date", "")
            date = date_raw[:10] if date_raw else datetime.now().strftime("%Y-%m-%d")

            odds_data = fetch_odds(event_id)
            if not odds_data:
                continue

            home_odds = odds_data.get("home")
            away_odds = odds_data.get("away")

            if not home_odds or not away_odds:
                continue

            side, edge, odds = calculate_value(home_odds, away_odds)

            if edge < 0:
                continue  # only value bets

            bet = home if side == "home" else away

            confidence = max(50, min(int(edge * 100), 90))

            picks.append({
                "date": date,
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": bet,
                "confidence": confidence,
                "reasoning": f"Value bet detected. Edge: {round(edge, 2)} | Odds: {odds}"
            })

        except Exception as e:
            continue

    # sort by edge/confidence
    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    return picks[:3]


def main():
    predictions = build_predictions()

    if not predictions:
        print("No value bets found")
        predictions = []

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(predictions)} predictions.")


if __name__ == "__main__":
    main()
