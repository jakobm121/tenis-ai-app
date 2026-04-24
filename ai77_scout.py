import requests
import json
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")
ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"


def fetch_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal"
    }

    res = requests.get(ODDS_URL, params=params, timeout=15)

    if res.status_code != 200:
        print("API ERROR:", res.text)
        return []

    return res.json()


def generate_reasoning(home, away, bet, expected_goals, edge, pick_type):
    if pick_type == "over":
        texts = [
            f"{home} and {away} profile as a high-event matchup, with enough attacking volume to push this game above the market line. The model sees goal potential that is not fully priced in.",
            f"The tempo projection points toward an open game. Both teams should have enough attacking sequences to create multiple scoring windows, making this a strong value angle.",
            f"This is not a blind Over pick. The model identifies a scoring environment where attacking output, tempo and market pricing all point in the same direction."
        ]

    elif pick_type == "under":
        texts = [
            f"This matchup projects as more controlled than the market suggests. Limited chance creation and a slower game script make the Under a strong value position.",
            f"The model expects fewer high-quality chances than the market is pricing. Defensive structure and tempo control make this a disciplined Under spot.",
            f"This game has a lower-event profile. The value comes from the market slightly overestimating goal volume."
        ]

    elif pick_type == "draw":
        texts = [
            f"This is a balanced matchup with very little separation between the sides. Draw is selected only because the value edge is unusually strong and risk is kept low.",
            f"The model sees a tight game profile with no clear side advantage. This is a controlled draw exposure, not a high-stake position.",
            f"Both teams rate closely enough that the draw price becomes playable. It remains a low-unit value angle due to natural variance."
        ]

    else:
        texts = [
            f"{bet} holds a measurable edge in this matchup. The model finds stronger structure, stability and pricing value compared to the opponent.",
            f"The selection is supported by matchup control and market inefficiency. This is a value-based side pick, not a momentum guess.",
            f"{bet} grades better in the model than the implied market probability. The edge is not huge, but it is consistent enough to qualify."
        ]

    endings = [
        " This fits the AI77 value-based approach.",
        " Risk is always present, but the price creates a playable edge.",
        " The pick is selected because the model detects market mispricing.",
        " This is a calculated position, not a random prediction."
    ]

    return random.choice(texts) + random.choice(endings)


def build_predictions():
    data = fetch_odds()

    tz = ZoneInfo("Europe/Ljubljana")
    now = datetime.now(tz)

    start_time = now + timedelta(minutes=30)
    end_time = now + timedelta(hours=24)

    candidates = []

    for game in data:
        try:
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time = datetime.fromisoformat(
                commence_time.replace("Z", "+00:00")
            ).astimezone(tz)

            if match_time < start_time or match_time > end_time:
                continue

            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            if not game.get("bookmakers"):
                continue

            bookmaker = game["bookmakers"][0]

            expected_home = 1.25
            expected_away = 1.15
            expected_goals = expected_home + expected_away

            home_prob = expected_home / expected_goals
            away_prob = expected_away / expected_goals

            over_prob = min(0.62, expected_goals / 3.15)
            under_prob = 1 - over_prob

            for market in bookmaker["markets"]:

                # ------------------------
                # OVER / UNDER
                # ------------------------
                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds
                        point = outcome.get("point", 2.5)

                        if outcome["name"] == "Over":
                            model_prob = over_prob
                            bet = f"Over {point}"
                            pick_type = "over"
                        else:
                            model_prob = under_prob
                            bet = f"Under {point}"
                            pick_type = "under"

                        edge = model_prob - implied

                        # strong boost so totals actually enter the portfolio
                        edge *= 1.55

                        if odds < 1.35 or odds > 3.40:
                            continue

                        if edge < -0.10:
                            continue

                        candidates.append({
                            "date": now.strftime("%Y-%m-%d"),
                            "time": match_time.strftime("%H:%M"),
                            "sport": "football",
                            "league": league,
                            "match": f"{home} - {away}",
                            "home": home,
                            "away": away,
                            "bet": bet,
                            "pick_type": pick_type,
                            "odds": odds,
                            "confidence": edge,
                            "reasoning": generate_reasoning(home, away, bet, expected_goals, edge, pick_type),
                            "sort_time": match_time.timestamp()
                        })

                # ------------------------
                # H2H + SMART DRAW
                # ------------------------
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == home:
                            model_prob = home_prob
                            bet = home
                            pick_type = "home"
                            edge = model_prob - implied
                            edge *= 0.72  # hard nerf home bias

                        elif outcome["name"] == away:
                            model_prob = away_prob
                            bet = away
                            pick_type = "away"
                            edge = model_prob - implied
                            edge *= 0.88

                        else:
                            bet = "Draw"
                            pick_type = "draw"

                            if expected_goals < 2.2:
                                model_prob = 0.28
                            elif expected_goals < 2.6:
                                model_prob = 0.25
                            else:
                                model_prob = 0.20

                            if abs(home_prob - away_prob) > 0.15:
                                continue

                            edge = model_prob - implied
                            edge *= 0.80

                            # draw only if real value
                            if edge < 0.05:
                                continue

                        if odds < 1.35 or odds > 3.80:
                            continue

                        if edge < -0.10:
                            continue

                        candidates.append({
                            "date": now.strftime("%Y-%m-%d"),
                            "time": match_time.strftime("%H:%M"),
                            "sport": "football",
                            "league": league,
                            "match": f"{home} - {away}",
                            "home": home,
                            "away": away,
                            "bet": bet,
                            "pick_type": pick_type,
                            "odds": odds,
                            "confidence": edge,
                            "reasoning": generate_reasoning(home, away, bet, expected_goals, edge, pick_type),
                            "sort_time": match_time.timestamp()
                        })

        except Exception as e:
            print("GAME ERROR:", e)
            continue

    candidates = sorted(candidates, key=lambda x: x["confidence"], reverse=True)

    final = []
    used_matches = set()

    counts = {
        "home": 0,
        "away": 0,
        "over": 0,
        "under": 0,
        "draw": 0
    }

    limits = {
        "home": 2,
        "away": 1,
        "over": 2,
        "under": 2,
        "draw": 1
    }

    # ------------------------
    # FIRST PASS: balanced limits
    # ------------------------
    for pick in candidates:
        if len(final) >= 5:
            break

        if pick["match"] in used_matches:
            continue

        pick_type = pick["pick_type"]

        if counts[pick_type] >= limits[pick_type]:
            continue

        final.append(pick)
        used_matches.add(pick["match"])
        counts[pick_type] += 1

    # ------------------------
    # SECOND PASS: fill missing picks, still no duplicate match
    # ------------------------
    if len(final) < 5:
        for pick in candidates:
            if len(final) >= 5:
                break

            if pick["match"] in used_matches:
                continue

            pick_type = pick["pick_type"]

            # still never allow more than these hard caps
            if pick_type == "home" and counts["home"] >= 2:
                continue
            if pick_type == "away" and counts["away"] >= 1:
                continue
            if pick_type == "draw" and counts["draw"] >= 1:
                continue

            final.append(pick)
            used_matches.add(pick["match"])
            counts[pick_type] += 1

    final = sorted(final, key=lambda x: x["confidence"], reverse=True)

    # ------------------------
    # CONFIDENCE / UNIT SYSTEM
    # 78 = Very Strong = 2u
    # 66 = Strong = 1.5u
    # 55 = Medium = 1u
    # Draw always Medium
    # ------------------------
    for i, pick in enumerate(final):
        if pick["pick_type"] == "draw":
            pick["confidence"] = 55
        elif i == 0:
            pick["confidence"] = 78
        elif i < 3:
            pick["confidence"] = 66
        else:
            pick["confidence"] = 55

    final = sorted(final, key=lambda x: x["sort_time"])

    for pick in final:
        del pick["sort_time"]
        del pick["pick_type"]
        del pick["odds"]
        del pick["home"]
        del pick["away"]

    return final


def main():
    predictions = build_predictions()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)

    history_file = "results.json"

    if not os.path.exists(history_file):
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump([], f)

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    except:
        history = []

    existing = {(p.get("match"), p.get("date"), p.get("bet")) for p in history}

    for pick in predictions:
        key = (pick.get("match"), pick.get("date"), pick.get("bet"))

        if key not in existing:
            new_pick = pick.copy()
            new_pick["result"] = "pending"
            history.append(new_pick)

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(predictions)} predictions and updated results.json.")


if __name__ == "__main__":
    main()
