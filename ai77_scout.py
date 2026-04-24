import requests
import json
import os
from datetime import datetime

API_KEY = os.getenv("ODDS_API_KEY")
URL = "https://api.odds-api.io/v3/events"

def fetch_matches():
    params = {
        "apiKey": API_KEY,
        "sport": "football"
    }

    try:
        res = requests.get(URL, params=params)
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
            home = game["home"]
            away = game["away"]
            league = game["league"]

            # ❌ filter slabih / čudnih tekem
            if len(home) < 3 or len(away) < 3:
                continue

            # 🧠 basic “confidence” logika (placeholder)
            confidence = 50 + (len(home) % 20)

            matches.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": home,
                "confidence": confidence,
                "reasoning": f"{home} shows stronger baseline metrics vs {away}."
            })

        except:
            continue

    # 🔥 SORTIRANJE (najbolj pomembno)
    matches = sorted(matches, key=lambda x: x["confidence"], reverse=True)

    return matches[:3]


def main():
    matches = fetch_matches()

    if not matches:
        print("No matches found")
        matches = []

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=4)

    print(f"Saved {len(matches)} predictions.")


if __name__ == "__main__":
    main()
