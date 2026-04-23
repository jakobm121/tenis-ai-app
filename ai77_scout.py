import requests
import json
import os
from datetime import datetime, timedelta

API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.odds-api.io/v3"

SPORT = "football"
MAX_DAYS_AHEAD = 7
MAX_EVENTS_TO_CHECK = 25


def get_json(endpoint, params=None):
    if params is None:
        params = {}

    params["apiKey"] = API_KEY

    url = f"{BASE_URL}{endpoint}"

    try:
        r = requests.get(url, params=params, timeout=20)
        print("URL:", r.url.replace(API_KEY or "", "HIDDEN"))
        print("STATUS:", r.status_code)

        if r.status_code != 200:
            print("ERROR BODY:", r.text[:1000])
            return None

        return r.json()

    except Exception as e:
        print("Request error:", e)
        return None


def get_events():
    data = get_json("/events", {
        "sport": SPORT,
        "limit": 50
    })

    if not isinstance(data, list):
        print("Events response is not a list:", str(data)[:500])
        return []

    now = datetime.utcnow()
    max_date = now + timedelta(days=MAX_DAYS_AHEAD)

    events = []

    for e in data:
        try:
            event_date = datetime.fromisoformat(e["date"].replace("Z", ""))

            if event_date < now or event_date > max_date:
                continue

            events.append(e)

        except Exception as err:
            print("Event parse error:", err)
            continue

    return events


def extract_pick_from_odds(odds_data, event):
    try:
        bookmakers = odds_data.get("bookmakers", {})

        for bookmaker_name, markets in bookmakers.items():
            for market in markets:
                if market.get("name") != "ML":
                    continue

                odds_list = market.get("odds", [])
                if not odds_list:
                    continue

                odds = odds_list[0]

                home_odds = odds.get("home")
                away_odds = odds.get("away")
                draw_odds = odds.get("draw")

                prices = []

                if home_odds:
                    prices.append(("home", event["home"], float(home_odds)))

                if away_odds:
                    prices.append(("away", event["away"], float(away_odds)))

                if draw_odds:
                    prices.append(("draw", "Draw", float(draw_odds)))

                if not prices:
                    continue

                best = min(prices, key=lambda x: x[2])
                side, selection, price = best

                confidence = max(35, min(int(100 / price), 85))

                return {
                    "selection": selection,
                    "odds": price,
                    "bookmaker": bookmaker_name,
                    "confidence": confidence
                }

    except Exception as e:
        print("Odds parse error:", e)

    return None


def build_predictions():
    if not API_KEY:
        print("Missing ODDS_API_KEY")
        return []

    events = get_events()
    print(f"Found {len(events)} upcoming events")

    predictions = []

    for event in events[:MAX_EVENTS_TO_CHECK]:
        event_id = event.get("id")

        if not event_id:
            continue

        odds_data = get_json("/odds", {
            "eventId": event_id
        })

        if not isinstance(odds_data, dict):
            continue

        pick = extract_pick_from_odds(odds_data, event)

        if not pick:
            continue

        league = event.get("league", {}).get("name", "Football")
        date = event.get("date", "")[:10]

        predictions.append({
            "date": date,
            "sport": "football",
            "league": league,
            "match": f"{event.get('home')} - {event.get('away')}",
            "bet": pick["selection"],
            "confidence": pick["confidence"],
            "reasoning": (
                f"Market odds from {pick['bookmaker']} suggest "
                f"{pick['selection']} is the strongest available pick "
                f"at odds {pick['odds']}."
            )
        })

        if len(predictions) >= 3:
            break

    return predictions


def main():
    predictions = build_predictions()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(predictions)} predictions.")


if __name__ == "__main__":
    main()
