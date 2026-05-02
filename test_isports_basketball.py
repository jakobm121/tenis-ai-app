import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = os.getenv("FOOTBALL_API_KEY")

TZ_NAME = "Europe/Ljubljana"
TODAY = datetime.now(ZoneInfo(TZ_NAME)).strftime("%Y-%m-%d")
REQUEST_TIMEOUT = 30

BASE_URL = "https://v1.basketball.api-sports.io"

TESTS = [
    {
        "name": "status",
        "endpoint": "/status",
        "params": {},
    },
    {
        "name": "leagues",
        "endpoint": "/leagues",
        "params": {},
    },
    {
        "name": "games_today",
        "endpoint": "/games",
        "params": {"date": TODAY},
    },
    {
        "name": "odds_today",
        "endpoint": "/odds",
        "params": {"date": TODAY},
    },
    {
        "name": "odds_bets",
        "endpoint": "/odds/bets",
        "params": {},
    },
    {
        "name": "odds_bookmakers",
        "endpoint": "/odds/bookmakers",
        "params": {},
    },
]


def headers():
    return {
        "x-apisports-key": API_KEY
    }


def preview(obj, limit=1500):
    try:
        text = json.dumps(obj, ensure_ascii=False)
    except Exception:
        text = str(obj)

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def call_api(endpoint, params):
    url = BASE_URL + endpoint

    response = requests.get(
        url,
        headers=headers(),
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    print()
    print("=" * 100)
    print("BASE:", BASE_URL)
    print("ENDPOINT:", endpoint)
    print("PARAMS:", params)
    print("STATUS:", response.status_code)
    print("URL:", response.url)

    try:
        data = response.json()
    except Exception:
        print("NON-JSON RESPONSE:")
        print(response.text[:1500])
        return None

    print("PREVIEW:")
    print(preview(data, 1500))

    return data


def inspect_response(name, data):
    if not isinstance(data, dict):
        print("Response is not dict.")
        return

    print()
    print("-" * 100)
    print("INSPECT:", name)
    print("-" * 100)

    print("KEYS:", list(data.keys()))

    errors = data.get("errors")
    if errors:
        print("ERRORS:", preview(errors, 1200))

    parameters = data.get("parameters")
    if parameters is not None:
        print("PARAMETERS:", preview(parameters, 800))

    results = data.get("results")
    if results is not None:
        print("RESULTS:", results)

    paging = data.get("paging")
    if paging is not None:
        print("PAGING:", preview(paging, 800))

    response = data.get("response")

    if isinstance(response, list):
        print("RESPONSE TYPE: list")
        print("RESPONSE LEN:", len(response))

        if response:
            first = response[0]
            print("FIRST ITEM KEYS:", list(first.keys()) if isinstance(first, dict) else type(first))
            print("FIRST ITEM:")
            print(preview(first, 2500))

            if name == "games_today":
                inspect_game_item(first)

            if name == "odds_today":
                inspect_odds_item(first)

            if name == "odds_bets":
                inspect_bets(response)

    elif isinstance(response, dict):
        print("RESPONSE TYPE: dict")
        print("RESPONSE KEYS:", list(response.keys()))
        print("RESPONSE:")
        print(preview(response, 2500))

    else:
        print("RESPONSE TYPE:", type(response).__name__)
        print("RESPONSE:", response)


def inspect_game_item(item):
    print()
    print("-" * 100)
    print("GAME ITEM DEEP INSPECTION")
    print("-" * 100)

    if not isinstance(item, dict):
        return

    print("TOP KEYS:", list(item.keys()))

    for key in ["id", "date", "time", "timestamp", "timezone"]:
        if key in item:
            print(f"{key}:", item.get(key))

    for key in ["league", "country", "teams", "scores", "status"]:
        if key in item:
            print(f"{key.upper()}:")
            print(preview(item.get(key), 1500))


def inspect_bets(response):
    print()
    print("-" * 100)
    print("ODDS BETS INSPECTION")
    print("-" * 100)

    if not isinstance(response, list):
        return

    print("BET TYPES COUNT:", len(response))

    for bet in response[:80]:
        if isinstance(bet, dict):
            bet_id = bet.get("id")
            name = bet.get("name")
            print(f"{bet_id} | {name}")
        else:
            print(bet)


def inspect_odds_item(item):
    print()
    print("-" * 100)
    print("ODDS ITEM DEEP INSPECTION")
    print("-" * 100)

    if not isinstance(item, dict):
        return

    print("TOP KEYS:", list(item.keys()))

    league = item.get("league")
    game = item.get("game")
    bookmakers = item.get("bookmakers")

    print("LEAGUE:")
    print(preview(league, 800))

    print("GAME:")
    print(preview(game, 1200))

    if isinstance(bookmakers, list):
        print("BOOKMAKERS LEN:", len(bookmakers))

        for bm in bookmakers[:5]:
            print()
            print("-" * 70)
            print("BOOKMAKER:", bm.get("name") or bm.get("id"))
            bets = bm.get("bets", [])
            print("BETS LEN:", len(bets))

            for bet in bets[:20]:
                print("BET:")
                print(preview(bet, 1500))


def save_output(all_results):
    out_file = "apisports_basketball_odds_test_output.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 100)
    print("DONE")
    print("Saved:", out_file)


def main():
    print("API-SPORTS Basketball Odds Test")
    print("TODAY:", TODAY)
    print("FOOTBALL_API_KEY:", "OK" if API_KEY else "MISSING")

    if not API_KEY:
        raise RuntimeError("Missing FOOTBALL_API_KEY environment variable.")

    all_results = {}

    for test in TESTS:
        name = test["name"]
        endpoint = test["endpoint"]
        params = test["params"]

        try:
            data = call_api(endpoint, params)
            all_results[name] = data
            inspect_response(name, data)

        except Exception as e:
            print()
            print("=" * 100)
            print("ERROR")
            print("ENDPOINT:", endpoint)
            print("ERROR:", e)

            all_results[name] = {
                "error": str(e),
            }

    save_output(all_results)


if __name__ == "__main__":
    main()
