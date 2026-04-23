import requests
import json
import os
from datetime import datetime

API_KEY = os.getenv("ODDS_API_KEY")

URL = "https://api.odds-api.io/v1/odds"  # ✅ PRAVI endpoint

def fetch_matches():
    headers = {
        "X-API-Key": API_KEY
    }

    params = {
        "sport": "football",
        "region": "eu",
        "market": "match_winner"
    }

    try:
        res = requests.get(URL, headers=headers, params=params)
        print("STATUS:", res.status_code)
        data = res.json()
        print("DATA SAMPLE:", str(data)[:500])
    except Exception as e:
        print("API error:", e)
        return []

    matches = []

    try:
        for game in data.get("data", []):
            home = game.get("home_team")
            away = game.get("away_team")
            league = game.get("league", "Unknown")

            odds = game.get("odds", {})
            home_odds = odds.get("home")
            away_odds = odds.get("away")

            if not home_odds or not away_odds:
                continue

            # izberi favorita
            if home_odds < away_odds:
                bet = home
                best_odds = home_odds
            else:
                bet = away
                best_odds = away_odds

            confidence = max(40, min(int(100 / best_odds), 85))

            matches.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": bet,
                "confidence": confidence,
                "reasoning": f"Odds suggest {bet} is favorite (odds {best_odds})."
            })

    except Exception as e:
        print("Parse error:", e)

    return matches


def main():
    matches = fetch_matches()

    if not matches:
        print("No matches found. Writing empty JSON.")
        top3 = []
    else:
        top3 = matches[:3]

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(top3, f, indent=4)

    print(f"Saved {len(top3)} predictions.")


if __name__ == "__main__":
    main()
