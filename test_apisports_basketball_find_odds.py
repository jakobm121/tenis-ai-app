import os
import json
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"
TZ_NAME = "Europe/Ljubljana"

TODAY = datetime.now(ZoneInfo(TZ_NAME)).strftime("%Y-%m-%d")
REQUEST_TIMEOUT = 30
MAX_GAMES_TO_TEST = 25


def headers():
    return {"x-apisports-key": API_KEY}


def api_get(endpoint, params=None):
    res = requests.get(
        BASE_URL + endpoint,
        headers=headers(),
        params=params or {},
        timeout=REQUEST_TIMEOUT,
    )

    print(f"GET {endpoint} {params or {}} -> {res.status_code}")

    try:
        return res.json()
    except Exception:
        print(res.text[:1000])
        return None


def short(obj, limit=1200):
    text = json.dumps(obj, ensure_ascii=False)
    return text[:limit] + ("..." if len(text) > limit else "")


def main():
    print("API-SPORTS Basketball Find Odds")
    print("TODAY:", TODAY)
    print("FOOTBALL_API_KEY:", "OK" if API_KEY else "MISSING")

    if not API_KEY:
        raise RuntimeError("Missing FOOTBALL_API_KEY environment variable.")

    games_data = api_get("/games", {"date": TODAY})

    if not games_data or not isinstance(games_data.get("response"), list):
        print("No games response.")
        return

    games = games_data["response"]
    print("GAMES:", len(games))

    found = []

    for game in games[:MAX_GAMES_TO_TEST]:
        game_id = game.get("id")
        league = game.get("league", {})
        teams = game.get("teams", {})
        status = game.get("status", {})

        home = teams.get("home", {}).get("name")
        away = teams.get("away", {}).get("name")
        league_name = league.get("name")

        print()
        print("=" * 90)
        print(f"TEST GAME {game_id}: {home} - {away}")
        print("LEAGUE:", league_name)
        print("STATUS:", status)

        odds_data = api_get("/odds", {"game": game_id})

        if not odds_data:
            continue

        errors = odds_data.get("errors")
        results = odds_data.get("results")
        response = odds_data.get("response")

        print("ERRORS:", errors)
        print("RESULTS:", results)

        if isinstance(response, list) and response:
            print("ODDS FOUND!")
            print(short(response[0], 5000))

            found.append({
                "game_id": game_id,
                "home": home,
                "away": away,
                "league": league_name,
                "odds": response,
            })
        else:
            print("No odds for this game.")

        time.sleep(0.5)

    with open("apisports_basketball_found_odds.json", "w", encoding="utf-8") as f:
        json.dump(found, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 90)
    print("DONE")
    print("ODDS FOUND GAMES:", len(found))
    print("Saved: apisports_basketball_found_odds.json")


if __name__ == "__main__":
    main()
