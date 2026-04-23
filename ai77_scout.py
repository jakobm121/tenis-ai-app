import requests
import json
import os
from datetime import datetime

API_KEY = os.getenv("ODDS_API_KEY")

URL = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"

def fetch_matches():
    params = {
        "apiKey": API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    try:
        res = requests.get(URL, params=params, timeout=15)
        print("STATUS:", res.status_code)

        if res.status_code != 200:
            print(res.text)
            return []

        data = res.json()

    except Exception as e:
        print("ERROR:", e)
        return []

    matches = []

    for game in data:
        try:
            home = game["home_team"]
            away = game["away_team"]

            bookmakers = game.get("bookmakers", [])
            if not bookmakers:
                continue

            outcomes = bookmakers[0]["markets"][0]["outcomes"]

            best = min(outcomes, key=lambda x: x["price"])

            matches.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sport": "football",
                "league": "Premier League",
                "match": f"{home} - {away}",
                "bet": best["name"],
                "confidence": int(100 / best["price"]),
                "reasoning": f"Odds suggest {best['name']} is favorite ({best['price']})."
            })

        except:
            continue

    return matches[:3]


def main():
    matches = fetch_matches()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=4)

    print(f"Saved {len(matches)} predictions.")


if __name__ == "__main__":
    main()
