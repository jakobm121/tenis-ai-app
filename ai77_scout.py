import requests
import json
import os
from datetime import datetime, timedelta

API_KEY = os.getenv("ODDS_API_KEY")

SPORTS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga"
]

LEAGUE_NAMES = {
    "soccer_epl": "Premier League",
    "soccer_spain_la_liga": "La Liga",
    "soccer_italy_serie_a": "Serie A",
    "soccer_germany_bundesliga": "Bundesliga"
}

def fetch_matches():
    all_matches = []

    for sport in SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

        params = {
            "apiKey": API_KEY,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal"
        }

        try:
            res = requests.get(url, params=params)
            data = res.json()
        except:
            continue

        for game in data:
            try:
                commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', ''))

                # filter: naslednji 3 dni
                if commence_time > datetime.utcnow() + timedelta(days=3):
                    continue

                home = game['home_team']
                away = [t for t in game['teams'] if t != home][0]

                bookmaker = game['bookmakers'][0]
                market = bookmaker['markets'][0]
                outcomes = market['outcomes']

                # najdi favorita (najnižja kvota)
                best = min(outcomes, key=lambda x: x['price'])

                all_matches.append({
                    "date": commence_time.strftime("%Y-%m-%d"),
                    "sport": "football",
                    "league": LEAGUE_NAMES.get(sport, sport),
                    "match": f"{home} - {away}",
                    "bet": best['name'],
                    "confidence": int(100 / best['price']),
                    "reasoning": f"Lower odds ({best['price']}) indicate stronger probability."
                })

            except:
                continue

    return all_matches


def main():
    matches = fetch_matches()

    if not matches:
        print("No matches found.")
        return

    matches = sorted(matches, key=lambda x: x['date'])
    top3 = matches[:3]

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(top3, f, indent=4)

    print("Saved 3 predictions.")


if __name__ == "__main__":
    main()
