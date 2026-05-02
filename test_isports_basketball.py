import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = os.getenv("FOOTBALL_API_KEY")

TZ_NAME = "Europe/Ljubljana"
TODAY = datetime.now(ZoneInfo(TZ_NAME)).strftime("%Y-%m-%d")
REQUEST_TIMEOUT = 30

BASE_URLS = [
    "https://v1.basketball.api-sports.io",
    "https://v1.api-basketball.com",
]

TESTS = [
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
        "name": "bets",
        "endpoint": "/odds/bets",
        "params": {},
    },
    {
        "name": "bookmakers",
        "endpoint": "/odds/bookmakers",
        "params": {},
    },
]


def headers():
    return {"x-apisports-key": API_KEY}


def preview(obj, limit=1200):
    try:
        text = json.dumps(obj, ensure_ascii=False)
    except Exception:
        text = str(obj)

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def call_api(base_url, endpoint, params):
    url = base_url + endpoint

    response = requests.get(
        url,
        headers=headers(),
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    print()
    print("=" * 100)
    print("BASE:", base_url)
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
        return

    print()
    print("-" * 100)
    print("INSPECT:", name)
    print("-" * 100)

    print("KEYS:", list(data.keys()))

    errors = data.get("errors")
    if errors:
        print("ERRORS:", errors)

    response = data.get("response")

    if isinstance(response, list):
        print("RESPONSE TYPE: list")
        print("RESPONSE LEN:", len(response))

        if response:
            first = response[0]
            print("FIRST ITEM KEYS:", list(first.keys()) if isinstance(first, dict) else type(first))
            print("FIRST ITEM:")
            print(preview(first, 2500))

            if name == "odds_today":
                inspect_odds_item(first)

    elif isinstance(response, dict):
        print("RESPONSE TYPE: dict")
        print("RESPONSE KEYS:", list(response.keys()))
        print("RESPONSE:")
        print(preview(response, 2000))

    else:
        print("RESPONSE TYPE:", type(response).__name__)
        print("RESPONSE:", response)


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

    print("LEAGUE:", preview(league, 600))
    print("GAME:", preview(game, 900))

    if isinstance(bookmakers, list):
        print("BOOKMAKERS LEN:", len(bookmakers))

        for bm in bookmakers[:3]:
            print()
            print("BOOKMAKER:", bm.get("name") or bm.get("id"))
            bets = bm.get("bets", [])
            print("BETS LEN:", len(bets))

            for bet in bets[:10]:
                print("BET:")
                print(preview(bet, 1200))


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

    for base_url in BASE_URLS:
        all_results[base_url] = {}

        for test in TESTS:
            name = test["name"]
            endpoint = test["endpoint"]
            params = test["params"]

            try:
                data = call_api(base_url, endpoint, params)
                all_results[base_url][name] = data
                inspect_response(name, data)

            except Exception as e:
                print()
                print("=" * 100)
                print("ERROR")
                print("BASE:", base_url)
                print("ENDPOINT:", endpoint)
                print("ERROR:", e)

                all_results[base_url][name] = {
                    "error": str(e),
                }

    save_output(all_results)


if __name__ == "__main__":
    main()
