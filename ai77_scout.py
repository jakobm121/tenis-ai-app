import requests
import json
import os
from datetime import datetime

API_KEY = os.getenv("ODDS_API_KEY")

SPORTS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga"
]

def fetch_odds(sport):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

    params = {
        "apiKey": API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    try:
        res = requests.get(url, params=params)
        return res.json()
    except:
        return []


def smart_pick(game):
    try:
        teams = game["teams"]
        home = game["home_team"]
        away = [t for t in teams if t != home][0]

        bookmakers = game.get("bookmakers", [])
        if not bookmakers:
            return None

        market = bookmakers[0]["markets"][0]["outcomes"]

        # SORT ODDS (ni več samo favorit)
        sorted_odds = sorted(market, key=lambda x: x["price"])

        best = sorted_odds[0]  # favorit
        second = sorted_odds[1]  # underdog/value candidate

        # 🔥 LOGIKA (to je upgrade)
        if best["price"] < 1.5:
            # premajhna kvota → skip (ni value)
            return None

        if 1.5 <= best["price"] <= 2.2:
            pick = best
            confidence = int(100 / best["price"])

        else:
            # če so kvote blizu → lahko value na drugi strani
            pick = second
            confidence = int(100 / second["price"])

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "sport": "football",
            "league": game["sport_key"],
            "match": f"{home} - {away}",
            "bet": pick["name"],
            "confidence": min(confidence, 85),
            "reasoning": f"Odds analysis suggests value on {pick['name']} (odds {pick['price']})."
        }

    except:
        return None


def main():
    all_picks = []

    for sport in SPORTS:
        data = fetch_odds(sport)

        for game in data:
            pick = smart_pick(game)
            if pick:
                all_picks.append(pick)

    # sort by confidence
    all_picks = sorted(all_picks, key=lambda x: x["confidence"], reverse=True)

    # fallback
    if len(all_picks) < 3:
        print("Using fallback")
        all_picks += [
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sport": "football",
                "league": "fallback",
                "match": "Arsenal - Chelsea",
                "bet": "Arsenal",
                "confidence": 65,
                "reasoning": "Fallback pick"
            }
        ]

    top3 = all_picks[:3]

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(top3, f, indent=4)

    print("DONE:", len(top3))


if __name__ == "__main__":
    main()
