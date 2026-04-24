import requests
import json
import os
from datetime import datetime

API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.odds-api.io/v3"

def fetch_events():
    params = {
        "apiKey": API_KEY,
        "sport": "football"
    }

    try:
        res = requests.get(f"{BASE_URL}/events", params=params, timeout=20)
        print("STATUS:", res.status_code)

        if res.status_code != 200:
            print(res.text)
            return []

        return res.json()

    except Exception as e:
        print("ERROR:", e)
        return []


def score_event(event):
    league = event.get("league", "")
    home = event.get("home", "")
    away = event.get("away", "")

    score = 50

    if "premier-league" in league:
        score += 15
    elif "la-liga" in league:
        score += 12
    elif "serie-a" in league:
        score += 12
    elif "bundesliga" in league:
        score += 12
    elif "championship" in league:
        score += 8

    if len(home) >= 5 and len(away) >= 5:
        score += 5

    return min(score, 85)


def build_predictions():
    events = fetch_events()
    predictions = []

    for event in events:
        try:
            home = event["home"]
            away = event["away"]
            league = event["league"]
            date_raw = event.get("date", "")
            date = date_raw[:10] if date_raw else datetime.now().strftime("%Y-%m-%d")

            confidence = score_event(event)

            predictions.append({
                "date": date,
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": home,
                "confidence": confidence,
                "reasoning": (
                    f"Selected from available football fixtures. "
                    f"League strength and matchup quality give this pick an AI77 confidence of {confidence}%."
                )
            })

        except Exception as e:
            print("Parse error:", e)
            continue

    predictions = sorted(predictions, key=lambda x: x["confidence"], reverse=True)

    return predictions[:3]


def main():
    predictions = build_predictions()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(predictions)} predictions.")


if __name__ == "__main__":
    main()
