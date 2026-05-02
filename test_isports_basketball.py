import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

ISPORTS_API_KEY = os.getenv("ISPORTS_API_KEY")

BASES = [
    "http://api.isportsapi.com",
    "http://api2.isportsapi.com",
]

TZ_NAME = "Europe/Ljubljana"
REQUEST_TIMEOUT = 30

TODAY = datetime.now(ZoneInfo(TZ_NAME)).strftime("%Y-%m-%d")

TESTS = [
    {
        "path": "/sport/basketball/schedule",
        "params": {"date": TODAY},
    },
    {
        "path": "/sport/basketball/odds/main",
        "params": {},
    },
    {
        "path": "/sport/basketball/odds",
        "params": {},
    },
    {
        "path": "/sport/basketball/odds/list",
        "params": {},
    },
    {
        "path": "/sport/basketball/bookmaker",
        "params": {},
    },
    {
        "path": "/sport/basketball/league/basic",
        "params": {},
    },
    {
        "path": "/sport/basketball/team",
        "params": {},
    },
    {
        "path": "/sport/basketball/standings",
        "params": {},
    },
    {
        "path": "/sport/basketball/matches",
        "params": {},
    },
    {
        "path": "/sport/basketball/fixtures",
        "params": {},
    },
]


def short_preview(value, limit=900):
    text = json.dumps(value, ensure_ascii=False)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def print_response_info(data):
    if not isinstance(data, dict):
        print("RESPONSE IS NOT DICT")
        print(type(data))
        return

    print("KEYS:", list(data.keys()))

    code = data.get("code")
    message = data.get("message")
    print("CODE:", code)
    print("MESSAGE:", message)

    if "data" not in data:
        return

    payload = data.get("data")

    if isinstance(payload, list):
        print("DATA TYPE: list")
        print("DATA LEN:", len(payload))

        if payload:
            first = payload[0]
            if isinstance(first, dict):
                print("FIRST KEYS:", list(first.keys()))
                print("FIRST ITEM:", short_preview(first, 1200))
            else:
                print("FIRST ITEM:", str(first)[:1200])

    elif isinstance(payload, dict):
        print("DATA TYPE: dict")
        print("DATA DICT KEYS:", list(payload.keys()))

        for key, value in payload.items():
            if isinstance(value, list):
                print(f"  {key}: list len={len(value)}")
                if value:
                    first = value[0]
                    print(f"  {key} FIRST:", str(first)[:700])
            elif isinstance(value, dict):
                print(f"  {key}: dict keys={list(value.keys())}")
            else:
                print(f"  {key}: {type(value).__name__} = {str(value)[:300]}")

    else:
        print("DATA TYPE:", type(payload).__name__)
        print("DATA:", str(payload)[:1200])


def call_api(base, path, params):
    if not ISPORTS_API_KEY:
        raise RuntimeError("Missing ISPORTS_API_KEY environment variable.")

    final_params = dict(params or {})
    final_params["api_key"] = ISPORTS_API_KEY

    url = base + path

    response = requests.get(
        url,
        params=final_params,
        timeout=REQUEST_TIMEOUT,
    )

    print()
    print("=" * 90)
    print("BASE:", base)
    print("PATH:", path)
    print("PARAMS:", params)
    print("URL:", response.url.replace(ISPORTS_API_KEY, "***"))
    print("STATUS:", response.status_code)

    try:
        data = response.json()
    except Exception:
        print("NON JSON RESPONSE:")
        print(response.text[:1500])
        return None

    print("PREVIEW:", short_preview(data, 1000))
    print_response_info(data)

    return data


def inspect_schedule(data):
    if not isinstance(data, dict):
        return

    if data.get("code") != 0:
        return

    matches = data.get("data")
    if not isinstance(matches, list) or not matches:
        return

    print()
    print("-" * 90)
    print("SCHEDULE INSPECTION")
    print("-" * 90)

    print("MATCH COUNT:", len(matches))

    status_counts = {}
    league_counts = {}

    for m in matches:
        status = m.get("status")
        status_counts[status] = status_counts.get(status, 0) + 1

        league = m.get("leagueName") or m.get("league") or "Unknown"
        league_counts[league] = league_counts.get(league, 0) + 1

    print("STATUS COUNTS:", sorted(status_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    print("TOP LEAGUES:", sorted(league_counts.items(), key=lambda x: x[1], reverse=True)[:20])

    print()
    print("FIRST 5 MATCHES:")
    for m in matches[:5]:
        print(short_preview(m, 1500))


def inspect_odds_main(data):
    if not isinstance(data, dict):
        return

    if data.get("code") != 0:
        return

    payload = data.get("data")
    if not isinstance(payload, dict):
        return

    print()
    print("-" * 90)
    print("ODDS MAIN INSPECTION")
    print("-" * 90)

    for market_name, rows in payload.items():
        if not isinstance(rows, list):
            continue

        print()
        print("=" * 80)
        print(f"{market_name} count:", len(rows))
        print("=" * 80)

        for row in rows[:10]:
            print(row)
            parts = str(row).split(",")
            print("parts len:", len(parts))
            for i, part in enumerate(parts[:20]):
                print(f"{i} = {part}")
            print("-" * 40)


def main():
    print("iSports Basketball API Test")
    print("TODAY:", TODAY)
    print("API KEY:", "OK" if ISPORTS_API_KEY else "MISSING")

    all_results = {}

    for base in BASES:
        all_results[base] = {}

        for test in TESTS:
            path = test["path"]
            params = test["params"]

            try:
                data = call_api(base, path, params)
                all_results[base][path] = data

                if path == "/sport/basketball/schedule":
                    inspect_schedule(data)

                if path == "/sport/basketball/odds/main":
                    inspect_odds_main(data)

            except Exception as e:
                print()
                print("=" * 90)
                print("ERROR")
                print("BASE:", base)
                print("PATH:", path)
                print("PARAMS:", params)
                print("ERROR:", e)

    with open("basketball_api_test_output.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 90)
    print("DONE")
    print("Saved full response to basketball_api_test_output.json")


if __name__ == "__main__":
    main()
